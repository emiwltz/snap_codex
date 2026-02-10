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


async def _collect_for_model(
    db: SoulBenchDB,
    bundle: Any,
    model_cfg: dict[str, Any],
) -> None:
    model_id = str(model_cfg["id"])
    model_openrouter_id = str(model_cfg.get("openrouter_model_id", "PLACEHOLDER"))
    thinking_mode = str(model_cfg.get("thinking_mode", "not_available"))
    collection_cfg = bundle.models["collection"]
    total_planned = expected_conditions_per_model(bundle)

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
        model_version=None,
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
        db.finalize_collection_metadata(model_id, notes="Skipped remote calls: missing OPENROUTER_API_KEY")
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
                temperature=condition.temperature,
                max_tokens=int(collection_cfg.get("max_tokens", 2048)),
                top_p=float(collection_cfg.get("top_p", 1.0)),
            )

            is_error = result.error is not None
            error_type = result.error.error_type if result.error else None
            raw_response = result.content or ""
            is_truncated = bool(
                result.completion_tokens is not None
                and int(result.completion_tokens) >= int(collection_cfg.get("max_tokens", 2048))
            )

            db.insert_response(
                ResponseRecord(
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
                    thinking_enabled=None,
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

    db.finalize_collection_metadata(model_id)


async def run_collect(args: argparse.Namespace) -> int:
    """Run collection stage for one or all models."""
    bundle = load_configs(args.config_dir)
    with SoulBenchDB(args.db_path) as db:
        model_ids: list[str]
        if args.all:
            model_ids = [str(model_cfg["id"]) for model_cfg in bundle.models.get("models", []) if model_cfg.get("active", True)]
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
            await _collect_for_model(db=db, bundle=bundle, model_cfg=model_cfg)
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

        pending_rows = db.get_pending_for_scoring(judge=args.judge, max_rows=args.max_rows)
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


def run_adjudicate(args: argparse.Namespace) -> int:
    """Run interactive manual adjudication for pending rows."""
    with SoulBenchDB(args.db_path) as db:
        adjudicated = adjudicate_pending_interactive(db=db, limit=args.limit)
    LOGGER.info("Adjudicated rows: %d", adjudicated)
    return 0


def run_analyze(args: argparse.Namespace) -> int:
    """Run selected analysis command."""
    from .analyzer import analyze_sensitivity, analyze_stability, analyze_variance_decomposition

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
    parser = argparse.ArgumentParser(description="SoulBench SNAP Pipeline v2.1")
    parser.add_argument("--db-path", default="data/soulbench.db", help="Path to SQLite database file.")
    parser.add_argument("--config-dir", default="config", help="Configuration directory path.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect responses for models.")
    collect_group = collect.add_mutually_exclusive_group(required=True)
    collect_group.add_argument("--model", type=str, help="Collect one specific model by id.")
    collect_group.add_argument("--all", action="store_true", help="Collect all active models.")

    score = subparsers.add_parser("score", help="Run judge scoring or resolve disagreements.")
    score.add_argument("--judge", choices=["haiku", "kimi"], help="Judge to run.")
    score.add_argument("--resolve-disagreements", action="store_true", help="Resolve existing disagreements.")
    score.add_argument("--max-rows", type=int, default=100, help="Max rows to score in one run.")

    subparsers.add_parser("resolve-disagreements", help="Alias for disagreement resolution.")

    export_sample = subparsers.add_parser("export-sample", help="Export sample for manual verification.")
    export_sample.add_argument("--n", type=int, required=True, help="Sample size.")
    export_sample.add_argument("--output", type=str, default="data/manual_sample.csv", help="Output CSV path.")

    import_manual = subparsers.add_parser("import-manual", help="Import manually coded sample.")
    import_manual.add_argument("--file", type=str, required=True, help="Input manual coding CSV.")

    subparsers.add_parser("compute-kappa", help="Compute kappa metrics.")

    adjudicate = subparsers.add_parser("adjudicate", help="Interactive adjudication for manual-review rows.")
    adjudicate.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all pending rows).")

    analyze = subparsers.add_parser("analyze", help="Run analyses.")
    analyze_group = analyze.add_mutually_exclusive_group(required=True)
    analyze_group.add_argument("--stability", action="store_true", help="Run stability analyses.")
    analyze_group.add_argument("--sensitivity", action="store_true", help="Run sensitivity analyses.")
    analyze_group.add_argument(
        "--variance-decomposition",
        action="store_true",
        dest="variance_decomposition",
        help="Run variance decomposition analysis (H4).",
    )
    analyze.add_argument("--output-dir", default="outputs/reports", help="Report output directory.")

    visualize = subparsers.add_parser("visualize", help="Generate visualizations.")
    visualize.add_argument("--all", action="store_true", help="Generate all figures.")
    visualize.add_argument("--output-dir", default="outputs/figures", help="Figure output directory.")

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
