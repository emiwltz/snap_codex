"""CLI orchestrator for SoulBench SNAP pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .api_client import OPENROUTER_ENDPOINT, OpenRouterClient
from .db import ConditionKey, ResponseRecord, SoulBenchDB
from .prompt_builder import (
    build_messages,
    expected_conditions_per_model,
    generate_conditions_for_model,
    get_model_config,
    load_configs,
)
from .scorer import (
    adjudicate_pending_interactive,
    compute_kappa,
    export_manual_sample,
    import_manual_results,
    resolve_all_disagreements,
    score_pending_for_judge,
)

LOGGER = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _progress_log(model_id: str, completed: int, total: int) -> None:
    pct = (completed / total * 100.0) if total > 0 else 0.0
    LOGGER.info("%s: %d/%d (%.2f%%)", model_id, completed, total, pct)


def _disabled_request_parameters(model_cfg: dict[str, Any]) -> set[str]:
    """Return OpenRouter request parameters intentionally omitted for a model."""
    raw_values = model_cfg.get("disabled_request_parameters") or []
    if not isinstance(raw_values, list):
        return set()
    return {str(value).strip() for value in raw_values if str(value).strip()}


def _thinking_enabled_from_mode(thinking_mode: str) -> bool | None:
    """Map configured thinking mode to the row-level trace field."""
    normalized = thinking_mode.strip().lower()
    if normalized in {"enabled_by_default", "enabled", "explicitly_enabled"}:
        return True
    if normalized in {"disabled", "not_available"}:
        return False
    return None


async def _collect_for_model(
    db: SoulBenchDB,
    bundle: Any,
    model_cfg: dict[str, Any],
    max_rows: int | None = None,
) -> None:
    model_id = str(model_cfg["id"])
    model_openrouter_id = str(model_cfg.get("openrouter_model_id", "PLACEHOLDER"))
    thinking_mode = str(model_cfg.get("thinking_mode", "not_available"))
    thinking_enabled = _thinking_enabled_from_mode(thinking_mode)
    disabled_parameters = _disabled_request_parameters(model_cfg)
    collection_cfg = bundle.models["collection"]
    total_planned = expected_conditions_per_model(bundle)

    request_policy_notes: list[str] = []
    if disabled_parameters:
        disabled_display = ",".join(sorted(disabled_parameters))
        request_policy_notes.append(
            f"Disabled request parameters for provider compatibility: {disabled_display}"
        )
        LOGGER.info(
            "%s: omitting configured request parameter(s): %s",
            model_id,
            disabled_display,
        )

    existing_seed = db.get_model_seed(model_id)
    conditions, effective_seed = generate_conditions_for_model(
        model_id=model_id,
        bundle=bundle,
        seed=existing_seed,
    )

    db.upsert_collection_metadata(
        model=model_id,
        start_time=_utc_now_iso(),
        total_planned=total_planned,
        randomization_seed=str(effective_seed),
        thinking_mode=thinking_mode,
        api_endpoint=str(collection_cfg.get("api_endpoint", OPENROUTER_ENDPOINT)),
        dataset_id=str(bundle.protocol.get("dataset_id")),
        protocol_version=str(bundle.protocol.get("protocol_version")),
        items_version=str(bundle.protocol.get("items_version")),
        model_version=None,
        notes=" | ".join(request_policy_notes) if request_policy_notes else None,
    )

    completed_keys = db.get_completed_condition_keys(model_id)
    pending_conditions = [
        condition
        for condition in conditions
        if ConditionKey(
            model=condition.model,
            item_id=condition.item_id,
            item_type=condition.item_type,
            scenario=condition.scenario,
            formulation=condition.formulation,
            system_prompt=condition.system_prompt,
            temperature=condition.temperature,
            run=condition.run,
        )
        not in completed_keys
    ]

    limit_note = None
    if max_rows is not None:
        limit_note = f"Limited collection run: max_rows={max_rows}"
        if len(pending_conditions) > max_rows:
            LOGGER.info(
                "Limiting collection for model '%s' to %d pending condition(s).",
                model_id,
                max_rows,
            )
            pending_conditions = pending_conditions[:max_rows]

    completed_count = db.get_completed_count(model_id)
    _progress_log(model_id, completed_count, total_planned)

    if not pending_conditions:
        LOGGER.info("No pending conditions for model '%s'.", model_id)
        db.finalize_collection_metadata(model_id)
        return

    client = OpenRouterClient(
        endpoint=str(collection_cfg.get("api_endpoint", OPENROUTER_ENDPOINT)),
        min_delay_seconds=float(collection_cfg.get("min_delay_seconds", 1.0)),
    )

    if not client.api_key:
        LOGGER.warning(
            "OPENROUTER_API_KEY is missing. Skipping collection for model '%s' without crashing.",
            model_id,
        )
        missing_key_note = "Skipped remote calls: missing OPENROUTER_API_KEY"
        db.finalize_collection_metadata(
            model_id,
            notes=(
                f"{limit_note} | {missing_key_note}" if limit_note else missing_key_note
            ),
        )
        return

    async with client:
        for idx, condition in enumerate(pending_conditions, start=1):
            messages = build_messages(
                system_prompt_key=condition.system_prompt,
                user_prompt_text=condition.user_prompt_text,
                system_prompts=bundle.system_prompts,
            )
            result = await client.generate(
                model_id=model_openrouter_id,
                messages=messages,
                temperature=(
                    None
                    if "temperature" in disabled_parameters
                    else condition.temperature
                ),
                max_tokens=int(collection_cfg.get("max_tokens", 2048)),
                top_p=(
                    None
                    if "top_p" in disabled_parameters
                    else float(collection_cfg.get("top_p", 1.0))
                ),
            )

            is_error = result.error is not None
            error_type = result.error.error_type if result.error else None
            raw_response = result.content or ""
            is_truncated = bool(
                result.completion_tokens is not None
                and int(result.completion_tokens)
                >= int(collection_cfg.get("max_tokens", 2048))
            )

            db.insert_response(
                ResponseRecord(
                    dataset_id=condition.dataset_id,
                    protocol_version=condition.protocol_version,
                    items_version=condition.items_version,
                    condition_block=condition.condition_block,
                    trial_id=condition.trial_id,
                    model=condition.model,
                    item_id=condition.item_id,
                    item_type=condition.item_type,
                    scenario=condition.scenario,
                    formulation=condition.formulation,
                    system_prompt=condition.system_prompt,
                    temperature=condition.temperature,
                    run=condition.run,
                    timestamp=_utc_now_iso(),
                    response_time_ms=result.response_time_ms,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    random_seed=str(effective_seed),
                    temperature_applied="temperature" not in disabled_parameters,
                    top_p_applied="top_p" not in disabled_parameters,
                    thinking_enabled=thinking_enabled,
                    system_prompt_text=condition.system_prompt_text,
                    user_prompt_text=condition.user_prompt_text,
                    raw_response=raw_response,
                    is_truncated=is_truncated,
                    is_error=is_error,
                    error_type=error_type,
                    notes=result.error.message if result.error else None,
                )
            )

            if not is_error:
                completed_count += 1

            if idx % 50 == 0 or idx == len(pending_conditions):
                _progress_log(model_id, completed_count, total_planned)

    db.finalize_collection_metadata(model_id, notes=limit_note)


async def run_collect(args: argparse.Namespace) -> int:
    """Run collection stage for one or all models."""
    if args.max_rows is not None and args.max_rows <= 0:
        LOGGER.error("--max-rows must be a positive integer when provided.")
        return 2

    bundle = load_configs(args.config_dir)
    with SoulBenchDB(args.db_path) as db:
        model_ids: list[str]
        if args.all:
            model_ids = [
                str(model_cfg["id"])
                for model_cfg in bundle.models.get("models", [])
                if model_cfg.get("active", True)
            ]
        else:
            model_ids = [str(args.model)]

        if not model_ids:
            LOGGER.warning("No models configured.")
            return 0

        for model_id in model_ids:
            model_cfg = get_model_config(bundle, model_id)
            if model_cfg is None:
                LOGGER.warning(
                    "Model '%s' not found in config/models.yaml. Using placeholder config for smoke execution.",
                    model_id,
                )
                model_cfg = {
                    "id": model_id,
                    "openrouter_model_id": "PLACEHOLDER",
                    "thinking_mode": "not_available",
                }
            await _collect_for_model(
                db=db,
                bundle=bundle,
                model_cfg=model_cfg,
                max_rows=args.max_rows,
            )
    return 0


async def run_score(args: argparse.Namespace) -> int:
    """Run scoring for one judge or resolve disagreements."""
    with SoulBenchDB(args.db_path) as db:
        if args.resolve_disagreements:
            resolve_all_disagreements(db)
            return 0

        if args.judge is None:
            LOGGER.error("Either --judge or --resolve-disagreements is required.")
            return 2

        pending_rows = db.get_pending_for_scoring(
            judge=args.judge, max_rows=args.max_rows
        )
        if not pending_rows:
            LOGGER.info("No rows pending scoring for judge '%s'.", args.judge)
            return 0

        client = OpenRouterClient(min_delay_seconds=0.2)
        if not client.api_key:
            LOGGER.warning(
                "OPENROUTER_API_KEY is missing. Skipping scoring for judge '%s' without crashing.",
                args.judge,
            )
            return 0

        async with client:
            await score_pending_for_judge(
                db=db,
                client=client,
                judge=args.judge,
                config_dir=args.config_dir,
                max_rows=args.max_rows,
            )
    return 0


def run_resolve_disagreements(args: argparse.Namespace) -> int:
    """Alias command to resolve disagreements."""
    with SoulBenchDB(args.db_path) as db:
        resolve_all_disagreements(db)
    return 0


def run_export_sample(args: argparse.Namespace) -> int:
    """Export stratified sample for manual verification."""
    with SoulBenchDB(args.db_path) as db:
        export_manual_sample(db=db, n=args.n, output_file=args.output)
    return 0


def run_import_manual(args: argparse.Namespace) -> int:
    """Import manual coding file."""
    with SoulBenchDB(args.db_path) as db:
        import_manual_results(db=db, file_path=args.file)
    return 0


def run_compute_kappa(args: argparse.Namespace) -> int:
    """Compute kappa metrics."""
    with SoulBenchDB(args.db_path) as db:
        result = compute_kappa(db=db)
    LOGGER.info("Kappa metrics: %s", result)
    return 0


def run_init_db(args: argparse.Namespace) -> int:
    """Create an empty v3.1 database or reset the target DB."""
    db_path = Path(args.db_path)
    if args.reset:
        for candidate in [db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]:
            if candidate.exists():
                candidate.unlink()

    with SoulBenchDB(db_path) as db:
        response_count = int(
            db._conn.execute("SELECT COUNT(*) AS n FROM responses;").fetchone()["n"]
        )
        if response_count > 0 and not args.allow_existing:
            LOGGER.error(
                "DB '%s' already contains %d response(s). Use --reset or --allow-existing.",
                db_path,
                response_count,
            )
            return 2

    LOGGER.info("DB ready: %s", db_path)
    return 0


def run_preflight(args: argparse.Namespace) -> int:
    """Verify model IDs, pricing, cost estimate, and DB readiness."""
    from .preflight import (
        build_preflight_report,
        fetch_openrouter_catalog,
        save_preflight_report,
    )

    bundle = load_configs(args.config_dir)
    catalog = fetch_openrouter_catalog(catalog_url=args.catalog_url)
    report = build_preflight_report(
        bundle=bundle,
        catalog=catalog,
        db_path=args.db_path,
        catalog_source=args.catalog_url,
        chars_per_token=args.chars_per_token,
        expected_response_tokens=args.expected_response_tokens,
        scoring_completion_tokens=args.scoring_completion_tokens,
    )
    save_preflight_report(report, args.output)
    LOGGER.info(
        "Preflight status=%s expected_total_cost=%s max_total_cost=%s output=%s",
        report.get("status"),
        report.get("cost_estimate", {}).get("expected", {}).get("total"),
        report.get("cost_estimate", {}).get("max_budget", {}).get("total"),
        args.output,
    )
    return 2 if report.get("status") == "blocked" else 0


def run_decision(args: argparse.Namespace) -> int:
    """Build PASS/BORDERLINE/FAIL report for the scored POC."""
    from .decision import build_decision_report, save_decision_report

    bundle = load_configs(args.config_dir)
    with SoulBenchDB(args.db_path) as db:
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=args.reports_dir,
        )
    save_decision_report(report, args.output)
    LOGGER.info("POC decision=%s output=%s", report.get("decision"), args.output)
    return 0


def run_adjudicate(args: argparse.Namespace) -> int:
    """Run interactive manual adjudication for pending rows."""
    with SoulBenchDB(args.db_path) as db:
        adjudicated = adjudicate_pending_interactive(
            db=db,
            limit=args.limit,
            config_dir=args.config_dir,
        )
    LOGGER.info("Adjudicated rows: %d", adjudicated)
    return 0


def run_analyze(args: argparse.Namespace) -> int:
    """Run selected analysis command."""
    from .analyzer import (
        analyze_sensitivity,
        analyze_stability,
        analyze_variance_decomposition,
    )

    with SoulBenchDB(args.db_path) as db:
        if args.stability:
            result = analyze_stability(db=db, output_dir=args.output_dir)
            LOGGER.info("Stability analysis done: status=%s", result.get("status"))
            return 0
        if args.sensitivity:
            result = analyze_sensitivity(db=db, output_dir=args.output_dir)
            LOGGER.info("Sensitivity analysis done: status=%s", result.get("status"))
            return 0
        if args.variance_decomposition:
            result = analyze_variance_decomposition(db=db, output_dir=args.output_dir)
            LOGGER.info("Variance decomposition done: status=%s", result.get("status"))
            return 0

    LOGGER.error("No analysis flag provided.")
    return 2


def run_visualize(args: argparse.Namespace) -> int:
    """Run selected visualization command."""
    if not args.all:
        LOGGER.error("Only --all is supported for visualize.")
        return 2

    # Lazy import avoids matplotlib startup side effects for non-visual commands.
    from .visualizer import generate_all

    with SoulBenchDB(args.db_path) as db:
        result = generate_all(db=db, output_dir=args.output_dir)
    LOGGER.info("Generated figures: %s", result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build top-level CLI parser."""
    parser = argparse.ArgumentParser(description="SoulBench SNAP Pipeline v3.1 POC")
    parser.add_argument(
        "--db-path",
        default="data/snap_poc_v3_1.db",
        help="Path to SQLite database file.",
    )
    parser.add_argument(
        "--config-dir", default="config", help="Configuration directory path."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect responses for models.")
    collect_group = collect.add_mutually_exclusive_group(required=True)
    collect_group.add_argument(
        "--model", type=str, help="Collect one specific model by id."
    )
    collect_group.add_argument(
        "--all", action="store_true", help="Collect all active models."
    )
    collect.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Limit pending conditions collected per model; useful for smoke tests.",
    )

    score = subparsers.add_parser(
        "score", help="Run judge scoring or resolve disagreements."
    )
    score.add_argument("--judge", choices=["haiku", "kimi"], help="Judge to run.")
    score.add_argument(
        "--resolve-disagreements",
        action="store_true",
        help="Resolve existing disagreements.",
    )
    score.add_argument(
        "--max-rows", type=int, default=100, help="Max rows to score in one run."
    )

    subparsers.add_parser(
        "resolve-disagreements", help="Alias for disagreement resolution."
    )

    export_sample = subparsers.add_parser(
        "export-sample", help="Export sample for manual verification."
    )
    export_sample.add_argument("--n", type=int, required=True, help="Sample size.")
    export_sample.add_argument(
        "--output", type=str, default="data/manual_sample.csv", help="Output CSV path."
    )

    import_manual = subparsers.add_parser(
        "import-manual", help="Import manually coded sample."
    )
    import_manual.add_argument(
        "--file", type=str, required=True, help="Input manual coding CSV."
    )

    subparsers.add_parser("compute-kappa", help="Compute kappa metrics.")

    init_db = subparsers.add_parser(
        "init-db", help="Create or reset the v3.1 SQLite database."
    )
    init_db.add_argument(
        "--reset",
        action="store_true",
        help="Delete the target DB/WAL/SHM files before creating the schema.",
    )
    init_db.add_argument(
        "--allow-existing",
        action="store_true",
        help="Return success even if the target DB already contains responses.",
    )

    preflight = subparsers.add_parser(
        "preflight", help="Check OpenRouter IDs, pricing, cost, and DB readiness."
    )
    preflight.add_argument(
        "--output",
        default="outputs/reports/preflight_report.json",
        help="Output JSON report path.",
    )
    preflight.add_argument(
        "--catalog-url",
        default="https://openrouter.ai/api/v1/models",
        help="OpenRouter model catalog URL.",
    )
    preflight.add_argument(
        "--chars-per-token",
        type=float,
        default=4.0,
        help="Character/token ratio used for prompt-token estimation.",
    )
    preflight.add_argument(
        "--expected-response-tokens",
        type=int,
        default=800,
        help="Expected collected response length used for planning cost.",
    )
    preflight.add_argument(
        "--scoring-completion-tokens",
        type=int,
        default=256,
        help="Expected judge output tokens per scoring call.",
    )

    decision = subparsers.add_parser(
        "decision", help="Generate the POC PASS/BORDERLINE/FAIL report."
    )
    decision.add_argument(
        "--reports-dir",
        default="outputs/reports",
        help="Directory containing analysis reports.",
    )
    decision.add_argument(
        "--output",
        default="outputs/reports/decision_report.json",
        help="Output JSON report path.",
    )

    adjudicate = subparsers.add_parser(
        "adjudicate", help="Interactive adjudication for manual-review rows."
    )
    adjudicate.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max rows to process (0 = all pending rows).",
    )

    analyze = subparsers.add_parser("analyze", help="Run analyses.")
    analyze_group = analyze.add_mutually_exclusive_group(required=True)
    analyze_group.add_argument(
        "--stability", action="store_true", help="Run stability analyses."
    )
    analyze_group.add_argument(
        "--sensitivity", action="store_true", help="Run sensitivity analyses."
    )
    analyze_group.add_argument(
        "--variance-decomposition",
        action="store_true",
        dest="variance_decomposition",
        help="Run variance decomposition analysis (H4).",
    )
    analyze.add_argument(
        "--output-dir", default="outputs/reports", help="Report output directory."
    )

    visualize = subparsers.add_parser("visualize", help="Generate visualizations.")
    visualize.add_argument("--all", action="store_true", help="Generate all figures.")
    visualize.add_argument(
        "--output-dir", default="outputs/figures", help="Figure output directory."
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    _setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "collect":
        return asyncio.run(run_collect(args))
    if args.command == "score":
        return asyncio.run(run_score(args))
    if args.command == "resolve-disagreements":
        return run_resolve_disagreements(args)
    if args.command == "export-sample":
        return run_export_sample(args)
    if args.command == "import-manual":
        return run_import_manual(args)
    if args.command == "compute-kappa":
        return run_compute_kappa(args)
    if args.command == "init-db":
        return run_init_db(args)
    if args.command == "preflight":
        return run_preflight(args)
    if args.command == "decision":
        return run_decision(args)
    if args.command == "adjudicate":
        return run_adjudicate(args)
    if args.command == "analyze":
        return run_analyze(args)
    if args.command == "visualize":
        return run_visualize(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
