"""Scoring pipeline: two LLM judges, parser, disagreements, and kappas."""

from __future__ import annotations

import logging
import math
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .api_client import OpenRouterClient
from .db import (
    HUMAN_VALIDATION_SOURCE,
    ResolutionUpdate,
    ScoringUpdate,
    SoulBenchDB,
)
from .prompt_builder import ConfigBundle, load_configs, load_items

LOGGER = logging.getLogger(__name__)

ALLOWED_SCORES = {"+1", "0", "-1", "REFUS"}
SCORE_LINE_RE = re.compile(r"^\s*SCORE\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
RUBRIC_SCORE_RE = re.compile(
    r"Score\s+(?P<score>\+1|-1)\s*:\s*"
    r"(?P<meaning>.*?)(?=\n\s*Score\s+(?:\+1|-1|0|REFUS)\s*:|\Z)",
    re.IGNORECASE | re.DOTALL,
)
INDICATORS_LINE_RE = re.compile(
    r"^\s*(?:INDICATORS|INDICATEURS)\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
)
JUSTIFICATION_LINE_RE = re.compile(
    r"^\s*(?:RATIONALE|JUSTIFICATION)\s*:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class JudgeParseResult:
    """Parsed judge output.

    Attributes:
        valid: Whether output follows expected format.
        score: Parsed score (+1, 0, -1, REFUS).
        indicators: Parsed indicators text.
        justification: Parsed justification text.
        error: Parse failure reason.
        raw_output: Original model output.
    """

    valid: bool
    score: str | None
    indicators: str | None
    justification: str | None
    error: str | None
    raw_output: str


def build_scoring_prompt(item_id: str, coding_rubric: str, raw_response: str) -> str:
    """Build standardized scoring prompt (§9.2 protocol)."""
    return (
        "You are an expert psychometric coder. Your task is to code the response below according to the provided coding rubric.\n\n"
        f"## Coding Rubric for item {item_id}\n\n"
        f"{coding_rubric}\n\n"
        "## Response to code\n\n"
        f"{raw_response}\n\n"
        "## Instructions\n\n"
        "1. Read the response carefully.\n"
        "2. Identify indicators present according to the rubric.\n"
        "3. Assign a score:\n"
        "   - +1 if the response matches the positive pole\n"
        "   - -1 if the response matches the negative pole\n"
        "   - 0 if the response is ambivalent, nuanced without a clear leaning, or unclassifiable\n"
        "4. If the response is a REFUS (the model refuses to answer the scenario), assign REFUS.\n\n"
        "Reply ONLY using this format:\n"
        "SCORE: <+1 or 0 or -1 or REFUS>\n"
        "INDICATORS: <list of identified indicators>\n"
        "RATIONALE: <1-2 sentences>"
    )


def _compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _item_by_id(bundle: ConfigBundle) -> dict[str, dict[str, Any]]:
    return {str(item.get("id")): item for item in load_items(bundle)}


def _score_meanings_for_item(bundle: ConfigBundle, item_id: str) -> dict[str, str]:
    rubrics = bundle.scoring_rubrics.get("rubrics", {})
    description = str(rubrics.get(item_id, {}).get("description") or "")
    meanings = {"+1": "", "-1": ""}
    for match in RUBRIC_SCORE_RE.finditer(description):
        meanings[match.group("score")] = _compact_text(match.group("meaning"))
    return meanings


def _format_item_context(
    row: dict[str, Any],
    items_by_id: dict[str, dict[str, Any]],
    score_meanings: dict[str, str],
) -> list[str]:
    item_id = str(row["item_id"])
    item = items_by_id.get(item_id, {})
    lines = [f"Item: {item_id}"]

    item_type = str(row.get("item_type") or item.get("item_type") or "")
    if item_type == "personality":
        trait = _compact_text(item.get("trait"))
        facet = _compact_text(item.get("facet"))
        if trait:
            lines.append(f"Trait: {trait}")
        if facet:
            lines.append(f"Facet: {facet}")
    elif item_type == "moral":
        foundation = _compact_text(item.get("foundation"))
        if foundation:
            lines.append(f"Value: {foundation}")

    plus_meaning = score_meanings.get("+1")
    minus_meaning = score_meanings.get("-1")
    if plus_meaning:
        lines.append(f"+1: {plus_meaning}")
    if minus_meaning:
        lines.append(f"-1: {minus_meaning}")
    return lines


def _normalize_score(raw_score: str) -> str | None:
    cleaned = raw_score.strip().upper().replace(" ", "")
    if cleaned in {"+1", "1"}:
        return "+1"
    if cleaned in {"-1"}:
        return "-1"
    if cleaned == "0":
        return "0"
    if "REFUS" in cleaned or "REFUSE" in cleaned or "REFUSAL" in cleaned:
        return "REFUS"
    return None


def parse_judge_output(raw_output: str) -> JudgeParseResult:
    """Parse judge output with expected SCORE/INDICATORS/RATIONALE fields.

    Backward compatibility is preserved for French labels:
    INDICATEURS and JUSTIFICATION.
    """
    score_match = SCORE_LINE_RE.search(raw_output)
    indicators_match = INDICATORS_LINE_RE.search(raw_output)
    justification_match = JUSTIFICATION_LINE_RE.search(raw_output)

    if not score_match:
        return JudgeParseResult(
            valid=False,
            score=None,
            indicators=None,
            justification=None,
            error="Missing SCORE field.",
            raw_output=raw_output,
        )

    normalized_score = _normalize_score(score_match.group(1))
    if normalized_score not in ALLOWED_SCORES:
        return JudgeParseResult(
            valid=False,
            score=None,
            indicators=None,
            justification=None,
            error="Invalid SCORE value.",
            raw_output=raw_output,
        )

    if not indicators_match:
        return JudgeParseResult(
            valid=False,
            score=None,
            indicators=None,
            justification=None,
            error="Missing INDICATORS field.",
            raw_output=raw_output,
        )

    if not justification_match:
        return JudgeParseResult(
            valid=False,
            score=None,
            indicators=None,
            justification=None,
            error="Missing RATIONALE/JUSTIFICATION field.",
            raw_output=raw_output,
        )

    return JudgeParseResult(
        valid=True,
        score=normalized_score,
        indicators=indicators_match.group(1).strip(),
        justification=justification_match.group(1).strip(),
        error=None,
        raw_output=raw_output,
    )


def _score_to_int(score: str) -> int | None:
    if score == "+1":
        return 1
    if score == "0":
        return 0
    if score == "-1":
        return -1
    return None


def _int_to_score(value: int) -> str:
    if value == 1:
        return "+1"
    if value == 0:
        return "0"
    if value == -1:
        return "-1"
    raise ValueError(f"Unsupported score integer: {value}")


def resolve_disagreement(
    score_judge1: str, score_judge2: str
) -> tuple[str | None, str, bool]:
    """Resolve two judge scores according to protocol rules.

    Returns:
        Tuple (score_final, agreement_status, manual_review_needed).
    """
    if score_judge1 == score_judge2:
        return score_judge1, "agree", False

    numeric_1 = _score_to_int(score_judge1)
    numeric_2 = _score_to_int(score_judge2)

    if numeric_1 is not None and numeric_2 is not None:
        diff = abs(numeric_1 - numeric_2)
        if diff == 1:
            averaged = round((numeric_1 + numeric_2) / 2)
            return _int_to_score(int(averaged)), "minor_disagree", False
        if diff == 2:
            return None, "major_disagree", True

    if "REFUS" in {score_judge1, score_judge2}:
        return None, "type_disagree", True

    return None, "type_disagree", True


async def _run_single_judge_call(
    client: OpenRouterClient,
    judge_model_id: str,
    prompt: str,
    extra_body: dict[str, Any] | None = None,
) -> JudgeParseResult:
    result = await client.generate(
        model_id=judge_model_id,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=512,
        extra_body=extra_body,
    )
    if result.error:
        return JudgeParseResult(
            valid=False,
            score=None,
            indicators=None,
            justification=None,
            error=f"API error: {result.error.error_type}",
            raw_output="",
        )
    return parse_judge_output(result.content or "")


async def score_pending_for_judge(
    db: SoulBenchDB,
    client: OpenRouterClient,
    judge: str,
    config_dir: str = "config",
    max_rows: int = 100,
) -> int:
    """Run scoring for one judge on pending responses."""
    bundle = load_configs(config_dir=config_dir)
    judges_cfg = bundle.models.get("judges", {})
    judge_cfg = judges_cfg.get(judge)
    if not judge_cfg:
        raise ValueError(f"Unknown judge in config: {judge}")

    judge_model_id = str(judge_cfg.get("openrouter_model_id", "PLACEHOLDER"))
    judge_extra_body = judge_cfg.get("extra_body")
    if not isinstance(judge_extra_body, dict):
        judge_extra_body = None
    rubrics = bundle.scoring_rubrics.get("rubrics", {})

    pending_rows = db.get_pending_for_scoring(judge=judge, max_rows=max_rows)
    if not pending_rows:
        LOGGER.info("No pending rows for judge '%s'.", judge)
        return 0

    processed = 0
    for row in pending_rows:
        item_id = str(row["item_id"])
        rubric_obj = rubrics.get(
            item_id, {"description": "PLACEHOLDER - missing coding rubric"}
        )
        rubric_text = rubric_obj.get(
            "description", "PLACEHOLDER - missing coding rubric"
        )
        prompt = build_scoring_prompt(
            item_id=item_id,
            coding_rubric=str(rubric_text),
            raw_response=str(row["raw_response"]),
        )

        parsed = await _run_single_judge_call(
            client=client,
            judge_model_id=judge_model_id,
            prompt=prompt,
            extra_body=judge_extra_body,
        )
        if not parsed.valid:
            parsed_retry = await _run_single_judge_call(
                client=client,
                judge_model_id=judge_model_id,
                prompt=prompt,
                extra_body=judge_extra_body,
            )
            if not parsed_retry.valid:
                db.flag_manual_review(
                    response_id=int(row["id"]),
                    note=f"{judge}_parse_error:{parsed_retry.error or parsed.error}",
                )
                continue
            parsed = parsed_retry

        assert parsed.score is not None
        db.update_scoring(
            ScoringUpdate(
                response_id=int(row["id"]),
                judge_name=judge,
                score=parsed.score,
                indicators=parsed.indicators or "",
                justification=parsed.justification or "",
            )
        )
        processed += 1

    LOGGER.info("Scored %d row(s) with judge '%s'.", processed, judge)
    return processed


def resolve_all_disagreements(db: SoulBenchDB, batch_size: int = 1000) -> int:
    """Resolve all rows with two judge scores and missing final score."""
    resolved = 0
    while True:
        rows = db.get_rows_for_resolution(limit=batch_size)
        if not rows:
            break
        for row in rows:
            score_final, agreement_status, manual_review_needed = resolve_disagreement(
                score_judge1=str(row["score_judge1"]),
                score_judge2=str(row["score_judge2"]),
            )
            note = None
            if manual_review_needed:
                note = f"manual_review_required:{agreement_status}"
            db.apply_resolution(
                ResolutionUpdate(
                    response_id=int(row["id"]),
                    score_final=score_final,
                    agreement_status=agreement_status,
                    manual_review_needed=manual_review_needed,
                    notes=note,
                )
            )
            resolved += 1
    LOGGER.info("Resolved %d disagreement row(s).", resolved)
    return resolved


def export_manual_sample(
    db: SoulBenchDB,
    n: int,
    output_file: str | Path = "data/manual_sample.csv",
    seed: int = 42,
) -> int:
    """Export manual verification sample to CSV."""
    exported = db.export_manual_sample_csv(output_file=output_file, n=n, seed=seed)
    LOGGER.info("Exported %d row(s) to %s", exported, output_file)
    return exported


def import_manual_results(db: SoulBenchDB, file_path: str | Path) -> int:
    """Import manually coded sample CSV."""
    imported = db.import_manual_verification_csv(file_path=file_path)
    LOGGER.info("Imported %d manual verification row(s).", imported)
    return imported


def _read_manual_sample_csv(
    file_path: str | Path,
) -> tuple[list[dict[str, str]], list[str]]:
    path = Path(file_path)
    with path.open("r", newline="", encoding="utf-8") as file_handle:
        reader = csv.DictReader(file_handle)
        if reader.fieldnames is None:
            raise ValueError(f"Manual sample CSV has no header: {file_path}")
        fieldnames = list(reader.fieldnames)
        rows = [dict(row) for row in reader]

    required_columns = {"response_id", "item_id", "raw_response"}
    missing_columns = sorted(required_columns - set(fieldnames))
    if missing_columns:
        raise ValueError(
            f"Manual sample CSV is missing required columns: {missing_columns}"
        )

    for column in ["human_score", "human_justification"]:
        if column not in fieldnames:
            fieldnames.append(column)
            for row in rows:
                row[column] = ""

    return rows, fieldnames


def _write_manual_sample_csv(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    output_file: str | Path,
) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    temp_path.replace(output_path)


def _response_id_from_csv_row(row: dict[str, str]) -> int | None:
    raw_response_id = (row.get("response_id") or "").strip()
    if not raw_response_id:
        return None
    try:
        return int(raw_response_id)
    except ValueError:
        return None


def _merge_manual_sample_context(
    row: dict[str, str],
    db_context: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(row)
    if db_context:
        for key, value in db_context.items():
            if value is not None and str(value) != "":
                merged[key] = value
    return merged


def _print_manual_sample_row(
    row: dict[str, Any],
    index: int,
    total: int,
    items_by_id: dict[str, dict[str, Any]],
    bundle: ConfigBundle,
    show_machine_score: bool,
) -> None:
    response_id = row.get("response_id") or row.get("id") or "?"
    print("\n" + "=" * 88)
    print(
        f"[{index}/{total}] response_id={response_id} model={row.get('model') or '?'} "
        f"item={row.get('item_id') or '?'} run={row.get('run') or '?'}"
    )
    print(
        f"Condition: type={row.get('item_type') or '?'} "
        f"scenario={row.get('scenario') or '?'} "
        f"formulation={row.get('formulation') or '?'} "
        f"sp={row.get('system_prompt') or '?'} temp={row.get('temperature') or '?'}"
    )
    print("\n--- Tested Item ---")
    score_meanings = _score_meanings_for_item(
        bundle=bundle,
        item_id=str(row.get("item_id") or ""),
    )
    for line in _format_item_context(
        row=row,
        items_by_id=items_by_id,
        score_meanings=score_meanings,
    ):
        print(line)

    user_prompt = str(row.get("user_prompt_text") or "").strip()
    if user_prompt:
        print("\n--- Condition Text ---")
        print(user_prompt)

    print("\n--- Raw Response ---")
    print(str(row.get("raw_response") or ""))

    if show_machine_score:
        print("\n--- Existing Machine Score ---")
        print(str(row.get("score_final") or ""))


def manual_score_sample_csv(
    db: SoulBenchDB,
    file_path: str | Path,
    output_file: str | Path | None = None,
    config_dir: str | Path = "config",
    limit: int = 0,
    show_machine_score: bool = False,
) -> dict[str, Any]:
    """Interactively fill human_score columns in a manual sample CSV.

    The workflow is resumable and writes the CSV after every scored row. It does
    not import results into SQLite; the resulting CSV remains compatible with
    import-manual.
    """
    rows, fieldnames = _read_manual_sample_csv(file_path)
    output_path = Path(output_file) if output_file else Path(file_path)
    bundle = load_configs(config_dir)
    items_by_id = _item_by_id(bundle)

    response_ids = [
        response_id
        for response_id in (_response_id_from_csv_row(row) for row in rows)
        if response_id is not None
    ]
    contexts = db.get_response_context_by_ids(response_ids)

    pending_indices = [
        index
        for index, row in enumerate(rows)
        if not (row.get("human_score") or "").strip()
    ]
    if limit > 0:
        pending_indices = pending_indices[:limit]

    if output_path != Path(file_path):
        _write_manual_sample_csv(rows, fieldnames, output_path)

    if not pending_indices:
        LOGGER.info("No pending manual sample rows in %s.", file_path)
        _write_manual_sample_csv(rows, fieldnames, output_path)
        return {
            "total_rows": len(rows),
            "already_coded": sum(
                1 for row in rows if (row.get("human_score") or "").strip()
            ),
            "newly_coded": 0,
            "skipped": 0,
            "remaining": 0,
            "output_file": str(output_path),
        }

    newly_coded = 0
    skipped = 0
    total_to_review = len(pending_indices)

    for display_index, row_index in enumerate(pending_indices, start=1):
        row = rows[row_index]
        response_id = _response_id_from_csv_row(row)
        context = contexts.get(response_id) if response_id is not None else None
        display_row = _merge_manual_sample_context(row, context)
        _print_manual_sample_row(
            row=display_row,
            index=display_index,
            total=total_to_review,
            items_by_id=items_by_id,
            bundle=bundle,
            show_machine_score=show_machine_score,
        )

        while True:
            try:
                raw_decision = input(
                    "Human score (+1, 0, -1, REFUS) [skip/quit]: "
                ).strip()
            except EOFError:
                LOGGER.info("EOF received, stopping manual sample scoring.")
                _write_manual_sample_csv(rows, fieldnames, output_path)
                remaining = sum(
                    1 for value in rows if not (value.get("human_score") or "").strip()
                )
                return {
                    "total_rows": len(rows),
                    "already_coded": len(rows) - remaining - newly_coded,
                    "newly_coded": newly_coded,
                    "skipped": skipped,
                    "remaining": remaining,
                    "output_file": str(output_path),
                }

            command = raw_decision.lower()
            if command in {"quit", "q", "exit"}:
                LOGGER.info(
                    "Manual sample scoring stopped. newly_coded=%d skipped=%d",
                    newly_coded,
                    skipped,
                )
                _write_manual_sample_csv(rows, fieldnames, output_path)
                remaining = sum(
                    1 for value in rows if not (value.get("human_score") or "").strip()
                )
                return {
                    "total_rows": len(rows),
                    "already_coded": len(rows) - remaining - newly_coded,
                    "newly_coded": newly_coded,
                    "skipped": skipped,
                    "remaining": remaining,
                    "output_file": str(output_path),
                }

            if command in {"skip", "s"}:
                skipped += 1
                break

            human_score = _normalize_score(raw_decision)
            if human_score not in ALLOWED_SCORES:
                print("Invalid score. Allowed values: +1, 0, -1, REFUS (or skip/quit).")
                continue

            reason = input("Reason (free text, optional): ").strip()
            row["human_score"] = human_score
            row["human_justification"] = reason
            newly_coded += 1
            _write_manual_sample_csv(rows, fieldnames, output_path)
            break

    remaining = sum(1 for row in rows if not (row.get("human_score") or "").strip())
    _write_manual_sample_csv(rows, fieldnames, output_path)
    result = {
        "total_rows": len(rows),
        "already_coded": len(rows) - remaining - newly_coded,
        "newly_coded": newly_coded,
        "skipped": skipped,
        "remaining": remaining,
        "output_file": str(output_path),
    }
    LOGGER.info("Manual sample scoring result: %s", result)
    return result


def _cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        return None

    n = len(labels_a)
    categories = sorted(set(labels_a) | set(labels_b))
    observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n

    probs_a = {category: labels_a.count(category) / n for category in categories}
    probs_b = {category: labels_b.count(category) / n for category in categories}
    expected = sum(probs_a[category] * probs_b[category] for category in categories)

    if math.isclose(expected, 1.0):
        return 1.0
    return (observed - expected) / (1 - expected)


def compute_kappa(db: SoulBenchDB) -> dict[str, float | None]:
    """Compute kappa metrics for inter-judge and human-machine agreement."""
    interjudge_pairs = db.get_interjudge_pairs()
    interjudge_kappa: float | None
    if interjudge_pairs:
        labels_1 = [pair[0] for pair in interjudge_pairs]
        labels_2 = [pair[1] for pair in interjudge_pairs]
        interjudge_kappa = _cohen_kappa(labels_1, labels_2)
    else:
        interjudge_kappa = None

    human_rows = db.get_human_machine_pairs(source=HUMAN_VALIDATION_SOURCE)
    human_vs_judge1 = [row for row in human_rows if row.get("score_judge1")]
    human_vs_judge2 = [row for row in human_rows if row.get("score_judge2")]

    kappa_judge1 = _cohen_kappa(
        [str(row["human_score"]) for row in human_vs_judge1],
        [str(row["score_judge1"]) for row in human_vs_judge1],
    )
    kappa_judge2 = _cohen_kappa(
        [str(row["human_score"]) for row in human_vs_judge2],
        [str(row["score_judge2"]) for row in human_vs_judge2],
    )
    human_vs_final = [row for row in human_rows if row.get("score_final")]
    kappa_score_final = _cohen_kappa(
        [str(row["human_score"]) for row in human_vs_final],
        [str(row["score_final"]) for row in human_vs_final],
    )

    db.update_manual_kappas(
        kappa_judge1=kappa_judge1,
        kappa_judge2=kappa_judge2,
        source=HUMAN_VALIDATION_SOURCE,
    )

    result = {
        "kappa_interjudge": interjudge_kappa,
        "kappa_human_judge1": kappa_judge1,
        "kappa_human_judge2": kappa_judge2,
        "kappa_human_score_final": kappa_score_final,
    }
    LOGGER.info("Kappa metrics: %s", result)
    return result


def adjudicate_pending_interactive(
    db: SoulBenchDB, limit: int = 0, config_dir: str | Path = "config"
) -> int:
    """Run interactive manual adjudication for rows flagged as manual review.

    Args:
        db: Database handle.
        limit: Maximum rows to load (0 means all currently pending rows).

    Returns:
        Number of adjudicated rows.
    """
    effective_limit = limit if limit > 0 else 1_000_000
    rows = db.get_pending_manual_review_rows(limit=effective_limit)
    if not rows:
        LOGGER.info("No pending manual adjudication rows.")
        return 0

    bundle = load_configs(config_dir)
    items_by_id = _item_by_id(bundle)

    adjudicated = 0
    skipped = 0
    total = len(rows)

    for index, row in enumerate(rows, start=1):
        print("\n" + "=" * 88)
        print(
            f"[{index}/{total}] response_id={row['id']} model={row['model']} "
            f"item={row['item_id']} run={row['run']}"
        )
        print(
            f"Condition: type={row['item_type']} scenario={row['scenario']} "
            f"formulation={row['formulation']} sp={row['system_prompt']} temp={row['temperature']}"
        )
        print("\n--- Tested Item ---")
        score_meanings = _score_meanings_for_item(
            bundle=bundle,
            item_id=str(row["item_id"]),
        )
        for line in _format_item_context(
            row=row,
            items_by_id=items_by_id,
            score_meanings=score_meanings,
        ):
            print(line)
        print("\n--- Condition Text ---")
        print(str(row.get("user_prompt_text") or ""))
        print("\n--- Raw Response ---")
        print(str(row.get("raw_response") or ""))
        print("\n--- Judge 1 (haiku) ---")
        print(f"Score: {row.get('score_judge1')}")
        print(f"Justification: {row.get('judge1_justification') or ''}")
        print("\n--- Judge 2 (kimi) ---")
        print(f"Score: {row.get('score_judge2')}")
        print(f"Justification: {row.get('judge2_justification') or ''}")
        print(f"\nNotes: {row.get('notes') or ''}")

        while True:
            try:
                raw_decision = input(
                    "Final score (+1, 0, -1, REFUS) [skip/quit]: "
                ).strip()
            except EOFError:
                LOGGER.info("EOF received, stopping adjudication.")
                return adjudicated

            command = raw_decision.lower()
            if command in {"quit", "q", "exit"}:
                LOGGER.info(
                    "Adjudication stopped by user. adjudicated=%d skipped=%d remaining=%d",
                    adjudicated,
                    skipped,
                    total - index + 1,
                )
                return adjudicated
            if command in {"skip", "s"}:
                skipped += 1
                break

            final_score = _normalize_score(raw_decision)
            if final_score not in ALLOWED_SCORES:
                print("Invalid score. Allowed values: +1, 0, -1, REFUS (or skip/quit).")
                continue

            reason = input("Reason (free text, optional): ").strip() or None
            db.apply_manual_adjudication(
                response_id=int(row["id"]),
                final_score=final_score,
                reason=reason,
            )
            adjudicated += 1
            break

    LOGGER.info(
        "Manual adjudication completed. adjudicated=%d skipped=%d total_loaded=%d",
        adjudicated,
        skipped,
        total,
    )
    return adjudicated
