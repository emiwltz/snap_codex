"""Tests for scoring parser, resolution, and pipeline behavior."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from src.api_client import ApiCallResult
from src.db import ResponseRecord, SoulBenchDB
from src.scorer import (
    JudgeParseResult,
    adjudicate_pending_interactive,
    compute_kappa,
    export_manual_sample,
    manual_score_sample_csv,
    parse_judge_output,
    resolve_disagreement,
    score_pending_for_judge,
)


class FakeClient:
    """Deterministic fake client for scorer tests."""

    def __init__(self, payloads: list[str]) -> None:
        self.payloads = payloads
        self.index = 0
        self.api_key = "fake-key"
        self.calls: list[dict[str, object]] = []

    async def generate(self, **kwargs: object) -> ApiCallResult:
        self.calls.append(kwargs)
        if self.index >= len(self.payloads):
            payload = self.payloads[-1]
        else:
            payload = self.payloads[self.index]
        self.index += 1
        return ApiCallResult(
            content=payload,
            prompt_tokens=10,
            completion_tokens=10,
            response_time_ms=20,
            status_code=200,
            error=None,
        )


def _seed_response(db: SoulBenchDB, response_id: int = 1) -> None:
    db.insert_response(
        ResponseRecord(
            model="test-model",
            item_id="O1",
            item_type="personality",
            scenario="base",
            formulation="F1",
            system_prompt="SP_ABS",
            temperature=0.1,
            run=response_id,
            user_prompt_text="Scenario\n\nQuestion",
            raw_response="I would probably do X.",
        )
    )


def test_parse_judge_output_valid() -> None:
    parsed = parse_judge_output(
        "SCORE: +1\nINDICATEURS: empathy, fairness\nJUSTIFICATION: aligns with positive pole."
    )
    assert parsed.valid is True
    assert parsed.score == "+1"


def test_parse_judge_output_valid_english_labels() -> None:
    parsed = parse_judge_output(
        "SCORE: -1\nINDICATORS: risk aversion, caution\nRATIONALE: aligns with negative pole."
    )
    assert parsed.valid is True
    assert parsed.score == "-1"


def test_parse_judge_output_invalid() -> None:
    parsed = parse_judge_output("SCORE: maybe\nINDICATEURS: none")
    assert parsed.valid is False
    assert parsed.error is not None


def test_resolve_disagreement_cases() -> None:
    assert resolve_disagreement("+1", "+1") == ("+1", "agree", False)
    assert resolve_disagreement("+1", "0") == ("0", "minor_disagree", False)
    assert resolve_disagreement("-1", "0") == ("0", "minor_disagree", False)
    assert resolve_disagreement("+1", "-1") == (None, "major_disagree", True)
    assert resolve_disagreement("REFUS", "+1") == (None, "type_disagree", True)


def test_invalid_parse_triggers_retry_then_manual_flag(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        _seed_response(db)
        fake_client = FakeClient(payloads=["bad output", "still bad"])

        processed = asyncio.run(
            score_pending_for_judge(
                db=db,
                client=fake_client,  # type: ignore[arg-type]
                judge="haiku",
                config_dir="config",
                max_rows=10,
            )
        )

        assert processed == 0
        row = db._conn.execute(
            "SELECT manual_review_needed, score_judge1 FROM responses LIMIT 1;"
        ).fetchone()
        assert int(row["manual_review_needed"]) == 1
        assert row["score_judge1"] is None


def test_judge_extra_body_is_forwarded_from_config(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        _seed_response(db)
        fake_client = FakeClient(
            payloads=["SCORE: 0\nINDICATORS: neutral\nRATIONALE: balanced response."]
        )

        processed = asyncio.run(
            score_pending_for_judge(
                db=db,
                client=fake_client,  # type: ignore[arg-type]
                judge="kimi",
                config_dir="config",
                max_rows=10,
            )
        )

        assert processed == 1
        assert fake_client.calls[0]["extra_body"] == {"reasoning": {"enabled": False}}


def test_export_manual_sample(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_file = tmp_path / "manual_sample.csv"

    with SoulBenchDB(db_path) as db:
        for run in range(1, 6):
            db.insert_response(
                ResponseRecord(
                    model="test-model",
                    item_id="O1",
                    item_type="personality",
                    scenario="base",
                    formulation="F1",
                    system_prompt="SP_ABS",
                    temperature=0.1,
                    run=run,
                    user_prompt_text="Scenario\n\nQuestion",
                    raw_response="Response",
                    score_final="0",
                )
            )

        exported = export_manual_sample(db=db, n=3, output_file=output_file)
        assert exported == 3
        assert output_file.exists()


def test_compute_kappa_includes_human_vs_final_score(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        for run, score in enumerate(["+1", "0", "-1"], start=1):
            db.insert_response(
                ResponseRecord(
                    model="test-model",
                    item_id="O1",
                    item_type="personality",
                    scenario="base",
                    formulation="F1",
                    system_prompt="SP_ABS",
                    temperature=0.1,
                    run=run,
                    user_prompt_text="Scenario\n\nQuestion",
                    raw_response="Response",
                    score_judge1=score,
                    score_judge2=score,
                    score_final=score,
                )
            )
            db._conn.execute(
                """
                INSERT INTO manual_verification (
                    response_id, human_score, human_justification, verified_at
                ) VALUES (?, ?, ?, ?);
                """,
                (run, score, "matches final", "2026-01-01T00:00:00+00:00"),
            )
        db._conn.commit()

        result = compute_kappa(db)

    assert result["kappa_human_score_final"] == 1.0


def test_compute_kappa_ignores_adjudication_rows_for_human_metrics(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="O1",
                item_type="personality",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.1,
                run=1,
                user_prompt_text="Scenario\n\nQuestion",
                raw_response="Response",
                score_judge1="+1",
                score_judge2="+1",
                score_final="+1",
            )
        )
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="O2",
                item_type="personality",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.1,
                run=2,
                user_prompt_text="Scenario\n\nQuestion",
                raw_response="Response",
                score_judge1="-1",
                score_judge2="-1",
                score_final="-1",
            )
        )

        db._conn.execute(
            """
            INSERT INTO manual_verification (
                response_id, human_score, human_justification, verified_at, source
            ) VALUES (?, ?, ?, ?, ?);
            """,
            (
                1,
                "-1",
                "adjudication-like row",
                "2026-01-01T00:00:00+00:00",
                "adjudication",
            ),
        )
        db._conn.execute(
            """
            INSERT INTO manual_verification (
                response_id, human_score, human_justification, verified_at, source
            ) VALUES (?, ?, ?, ?, ?);
            """,
            (
                2,
                "-1",
                "independent validation",
                "2026-01-01T00:00:00+00:00",
                "human_validation",
            ),
        )
        db._conn.commit()

        result = compute_kappa(db)

        rows = db._conn.execute("""
            SELECT response_id, source, kappa_judge1, kappa_judge2
            FROM manual_verification
            ORDER BY response_id;
            """).fetchall()

    assert result["kappa_human_judge1"] == 1.0
    assert result["kappa_human_judge2"] == 1.0
    assert result["kappa_human_score_final"] == 1.0

    by_source = {(int(row["response_id"]), row["source"]): row for row in rows}
    assert by_source[(1, "adjudication")]["kappa_judge1"] is None
    assert by_source[(1, "adjudication")]["kappa_judge2"] is None
    assert by_source[(2, "human_validation")]["kappa_judge1"] == 1.0
    assert by_source[(2, "human_validation")]["kappa_judge2"] == 1.0


def test_manual_adjudication_prints_item_context(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="O1",
                item_type="personality",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.1,
                run=1,
                user_prompt_text="Scenario\n\nQuestion",
                raw_response="Response",
                score_judge1="+1",
                score_judge2="-1",
                manual_review_needed=True,
            )
        )
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="M_CH",
                item_type="moral",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.1,
                run=1,
                user_prompt_text="Scenario\n\nQuestion",
                raw_response="Response",
                score_judge1="+1",
                score_judge2="-1",
                manual_review_needed=True,
            )
        )

        decisions = iter(["skip", "skip"])
        monkeypatch.setattr("builtins.input", lambda _: next(decisions))

        adjudicated = adjudicate_pending_interactive(
            db=db,
            limit=2,
            config_dir="config",
        )

    output = capsys.readouterr().out
    assert adjudicated == 0
    assert "--- Tested Item ---" in output
    assert "Trait: Openness" in output
    assert "Facet: Exploration vs Conservation" in output
    assert "Value: Care/Harm" in output
    assert "+1: Exploration" in output
    assert "-1: Conservation" in output
    assert "+1: Recommends Mode 1 / Config A" in output
    assert "-1: Recommends Mode 2 / Config B" in output


def test_manual_score_sample_csv_fills_human_score(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    db_path = tmp_path / "test.db"
    csv_path = tmp_path / "manual_sample_coded.csv"
    with SoulBenchDB(db_path) as db:
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="O1",
                item_type="personality",
                scenario="base",
                formulation="F1",
                system_prompt="SP_DIR",
                temperature=0.5,
                run=3,
                user_prompt_text="Scenario text\n\nQuestion text",
                raw_response="I would test the new method on a small pilot.",
                score_final="-1",
            )
        )
        with csv_path.open("w", newline="", encoding="utf-8") as file_handle:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=[
                    "response_id",
                    "model",
                    "item_id",
                    "system_prompt",
                    "temperature",
                    "raw_response",
                    "score_final",
                    "human_score",
                    "human_justification",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "response_id": "1",
                    "model": "test-model",
                    "item_id": "O1",
                    "system_prompt": "SP_DIR",
                    "temperature": "0.5",
                    "raw_response": "CSV response",
                    "score_final": "-1",
                    "human_score": "",
                    "human_justification": "",
                }
            )

        decisions = iter(["+1", "mentions testing"])
        monkeypatch.setattr("builtins.input", lambda _: next(decisions))

        result = manual_score_sample_csv(
            db=db,
            file_path=csv_path,
            config_dir="config",
        )

    with csv_path.open(newline="", encoding="utf-8") as file_handle:
        rows = list(csv.DictReader(file_handle))

    output = capsys.readouterr().out
    assert result["newly_coded"] == 1
    assert result["remaining"] == 0
    assert rows[0]["human_score"] == "+1"
    assert rows[0]["human_justification"] == "mentions testing"
    assert "Trait: Openness" in output
    assert "Scenario text" in output
    assert "I would test the new method" in output
    assert "--- Existing Machine Score ---" not in output
    assert rows[0]["score_final"] == "-1"


def test_manual_score_sample_csv_can_show_machine_score(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    db_path = tmp_path / "test.db"
    csv_path = tmp_path / "manual_sample_coded.csv"
    output_path = tmp_path / "output.csv"
    with SoulBenchDB(db_path) as db:
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="M_CH",
                item_type="moral",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.0,
                run=1,
                user_prompt_text="Scenario\n\nQuestion",
                raw_response="I would choose Mode 1.",
                score_final="+1",
            )
        )
        with csv_path.open("w", newline="", encoding="utf-8") as file_handle:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=[
                    "response_id",
                    "item_id",
                    "raw_response",
                    "score_final",
                    "human_score",
                    "human_justification",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "response_id": "1",
                    "item_id": "M_CH",
                    "raw_response": "I would choose Mode 1.",
                    "score_final": "+1",
                    "human_score": "",
                    "human_justification": "",
                }
            )

        decisions = iter(["skip"])
        monkeypatch.setattr("builtins.input", lambda _: next(decisions))

        result = manual_score_sample_csv(
            db=db,
            file_path=csv_path,
            output_file=output_path,
            config_dir="config",
            show_machine_score=True,
        )

    output = capsys.readouterr().out
    assert result["skipped"] == 1
    assert result["remaining"] == 1
    assert output_path.exists()
    assert "--- Existing Machine Score ---" in output
    assert "+1" in output
