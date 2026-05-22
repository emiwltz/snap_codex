"""POC decision report for SNAP v3.1."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import SoulBenchDB
from .prompt_builder import ConfigBundle, expected_conditions_per_model


def build_decision_report(
    db: SoulBenchDB,
    bundle: ConfigBundle,
    reports_dir: str | Path = "outputs/reports",
) -> dict[str, Any]:
    """Build a PASS/BORDERLINE/FAIL decision report from scored data."""
    thresholds = bundle.protocol.get("decision_thresholds", {})
    scored_df = db.get_scored_dataframe()
    response_count = int(len(scored_df))
    scored_count = (
        int(scored_df["score_final"].notna().sum()) if not scored_df.empty else 0
    )
    non_error_count = (
        int((scored_df["is_error"].fillna(0).astype(int) == 0).sum())
        if not scored_df.empty
        else 0
    )

    if response_count == 0 or scored_count == 0:
        return {
            "report": "poc_decision",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision": "NOT_READY",
            "reason": "No scored responses are available yet.",
            "dataset_id": str(bundle.protocol.get("dataset_id")),
            "protocol_version": str(bundle.protocol.get("protocol_version")),
            "checks": [],
            "summary": {
                "response_count": response_count,
                "scored_count": scored_count,
                "non_error_count": non_error_count,
            },
        }

    if scored_count < non_error_count:
        return {
            "report": "poc_decision",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision": "NOT_READY",
            "reason": "Some non-error responses are not resolved to score_final yet.",
            "dataset_id": str(bundle.protocol.get("dataset_id")),
            "protocol_version": str(bundle.protocol.get("protocol_version")),
            "checks": [],
            "summary": {
                "response_count": response_count,
                "scored_count": scored_count,
                "non_error_count": non_error_count,
            },
        }

    campaign_completion = _check_campaign_completion(
        db=db,
        bundle=bundle,
        scored_df=scored_df,
    )
    if campaign_completion["status"] != "complete":
        return {
            "report": "poc_decision",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision": "NOT_READY",
            "reason": "The configured campaign is not fully collected yet.",
            "dataset_id": str(bundle.protocol.get("dataset_id")),
            "protocol_version": str(bundle.protocol.get("protocol_version")),
            "checks": [],
            "campaign_completion": campaign_completion,
            "summary": {
                "response_count": response_count,
                "scored_count": scored_count,
                "non_error_count": non_error_count,
            },
        }

    stability_report = _load_json_report(Path(reports_dir) / "stability_report.json")
    checks = [
        _check_kappa(db, thresholds),
        _check_refusal_rate(scored_df, thresholds),
        _check_major_disagreement_rate(scored_df, thresholds),
        _check_stability_metric(
            stability_report=stability_report,
            metric_key="icc",
            threshold_key="icc_min",
            thresholds=thresholds,
        ),
        _check_stability_metric(
            stability_report=stability_report,
            metric_key="test_retest_pearson",
            threshold_key="split_half_min",
            thresholds=thresholds,
        ),
        _check_cross_context_corr(stability_report, thresholds),
    ]

    failed = [check for check in checks if check["status"] == "fail"]
    borderline = [check for check in checks if check["status"] == "borderline"]
    missing = [check for check in checks if check["status"] == "missing"]

    if failed:
        decision = "FAIL"
    elif borderline or missing:
        decision = "BORDERLINE"
    else:
        decision = "PASS"

    return {
        "report": "poc_decision",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "dataset_id": str(bundle.protocol.get("dataset_id")),
        "protocol_version": str(bundle.protocol.get("protocol_version")),
        "thresholds": thresholds,
        "checks": checks,
        "campaign_completion": campaign_completion,
        "summary": {
            "response_count": response_count,
            "scored_count": scored_count,
            "non_error_count": non_error_count,
            "failed_checks": len(failed),
            "borderline_checks": len(borderline),
            "missing_checks": len(missing),
        },
    }


def _check_campaign_completion(
    db: SoulBenchDB,
    bundle: ConfigBundle,
    scored_df: Any,
) -> dict[str, Any]:
    """Check whether all active model conditions are collected and scored."""
    active_models = [
        str(model_cfg.get("id"))
        for model_cfg in bundle.models.get("models", [])
        if model_cfg.get("active", True)
    ]
    expected_per_model = expected_conditions_per_model(bundle)
    progress_by_model = {
        str(row.get("model")): row for row in db.get_collection_progress()
    }

    if scored_df.empty:
        non_error_counts: dict[str, int] = {}
        scored_counts: dict[str, int] = {}
    else:
        non_error_df = scored_df[scored_df["is_error"].fillna(0).astype(int) == 0]
        non_error_counts = {
            str(model): int(count)
            for model, count in non_error_df.groupby("model").size().items()
        }
        scored_counts = {
            str(model): int(count)
            for model, count in non_error_df[non_error_df["score_final"].notna()]
            .groupby("model")
            .size()
            .items()
        }

    model_reports: dict[str, Any] = {}
    incomplete_models: list[str] = []

    for model_id in active_models:
        row = progress_by_model.get(model_id)
        reasons: list[str] = []
        total_planned = _safe_int(row.get("total_planned")) if row else None
        total_completed = _safe_int(row.get("total_completed")) if row else None
        total_errors = _safe_int(row.get("total_errors")) if row else None
        non_error_count = non_error_counts.get(model_id, 0)
        scored_count = scored_counts.get(model_id, 0)

        if row is None:
            reasons.append("missing_collection_metadata")
        if total_planned != expected_per_model:
            reasons.append("total_planned_does_not_match_protocol")
        if total_completed is None or total_completed < expected_per_model:
            reasons.append("collection_incomplete")
        if total_errors not in {0, None}:
            reasons.append("collection_errors_present")
        if non_error_count < expected_per_model:
            reasons.append("missing_non_error_responses")
        if scored_count < expected_per_model:
            reasons.append("missing_final_scores")

        complete = not reasons
        if not complete:
            incomplete_models.append(model_id)

        model_reports[model_id] = {
            "metadata_present": row is not None,
            "expected_conditions": expected_per_model,
            "total_planned": total_planned,
            "total_completed": total_completed,
            "total_errors": total_errors,
            "non_error_responses": non_error_count,
            "scored_responses": scored_count,
            "complete": complete,
            "reasons": reasons,
        }

    expected_total = expected_per_model * len(active_models)
    completed_total = sum(
        int(model_report["total_completed"] or 0)
        for model_report in model_reports.values()
    )
    scored_total = sum(
        int(model_report["scored_responses"] or 0)
        for model_report in model_reports.values()
    )

    return {
        "status": "complete" if not incomplete_models else "incomplete",
        "expected_models": active_models,
        "expected_conditions_per_model": expected_per_model,
        "expected_total_conditions": expected_total,
        "completed_total": completed_total,
        "scored_total": scored_total,
        "incomplete_models": incomplete_models,
        "models": model_reports,
    }


def save_decision_report(report: dict[str, Any], output_file: str | Path) -> None:
    """Write the decision report as JSON."""
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=True)


def _check_kappa(db: SoulBenchDB, thresholds: dict[str, Any]) -> dict[str, Any]:
    pairs = db.get_interjudge_pairs()
    value = _cohen_kappa(
        [pair[0] for pair in pairs],
        [pair[1] for pair in pairs],
    )
    min_value = _threshold(thresholds, "kappa_interjudge_min")
    target = _threshold(thresholds, "kappa_interjudge_target")
    status = _min_status(value=value, minimum=min_value, target=target)
    return {
        "metric": "kappa_interjudge",
        "value": value,
        "threshold_min": min_value,
        "threshold_target": target,
        "n_pairs": len(pairs),
        "status": status,
    }


def _check_refusal_rate(df: Any, thresholds: dict[str, Any]) -> dict[str, Any]:
    eligible = df[df["is_error"].fillna(0).astype(int) == 0]
    denominator = int(len(eligible))
    value = None
    if denominator > 0:
        value = float(eligible["is_refusal"].fillna(0).astype(int).sum() / denominator)
    maximum = _threshold(thresholds, "refusal_rate_max")
    return {
        "metric": "refusal_rate",
        "value": value,
        "threshold_max": maximum,
        "n_rows": denominator,
        "status": _max_status(value=value, maximum=maximum),
    }


def _check_major_disagreement_rate(
    df: Any, thresholds: dict[str, Any]
) -> dict[str, Any]:
    paired = df[df["score_judge1"].notna() & df["score_judge2"].notna()]
    denominator = int(len(paired))
    note_text = (
        paired["notes"].fillna("").astype(str)
        if "notes" in paired.columns
        else paired["agreement_status"].fillna("").astype(str).str[:0]
    )

    initial_major = (
        (paired["agreement_status"] == "major_disagree")
        | note_text.str.contains("manual_review_required:major_disagree", regex=False)
    )
    initial_type = (
        (paired["agreement_status"] == "type_disagree")
        | note_text.str.contains("manual_review_required:type_disagree", regex=False)
    )
    current_pending_major = (
        (paired["agreement_status"] == "major_disagree")
        & (paired["manual_review_needed"].fillna(0).astype(int) == 1)
    )
    current_pending_type = (
        (paired["agreement_status"] == "type_disagree")
        & (paired["manual_review_needed"].fillna(0).astype(int) == 1)
    )
    current_pending_manual_reviews = (
        df["manual_review_needed"].fillna(0).astype(int) == 1
    )
    manual_adjudicated = df["agreement_status"] == "manual_adjudicated"
    paired_manual_adjudicated = paired["agreement_status"] == "manual_adjudicated"

    value = None
    if denominator > 0:
        value = float(initial_major.sum() / denominator)
    maximum = _threshold(thresholds, "major_disagreement_rate_max")
    return {
        "metric": "initial_major_disagreement_rate",
        "value": value,
        "threshold_max": maximum,
        "n_pairs": denominator,
        "initial_major_disagreements": int(initial_major.sum()),
        "initial_type_disagreements": int(initial_type.sum()),
        "current_pending_disagreements": int(current_pending_manual_reviews.sum()),
        "current_pending_major_disagreements": int(current_pending_major.sum()),
        "current_pending_type_disagreements": int(current_pending_type.sum()),
        "manual_adjudicated_count": int(manual_adjudicated.sum()),
        "manual_adjudicated_with_judge_pairs": int(paired_manual_adjudicated.sum()),
        "note": (
            "Initial disagreement counts include rows later resolved through "
            "manual adjudication."
        ),
        "status": _max_status(value=value, maximum=maximum),
    }


def _check_stability_metric(
    stability_report: dict[str, Any] | None,
    metric_key: str,
    threshold_key: str,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    minimum = _threshold(thresholds, threshold_key)
    if not stability_report or stability_report.get("status") != "ok":
        return {
            "metric": metric_key,
            "value": None,
            "threshold_min": minimum,
            "status": "missing",
            "reason": "Missing or non-ok stability_report.json",
        }

    values = [
        model_report.get(metric_key)
        for model_report in stability_report.get("models", {}).values()
        if model_report.get(metric_key) is not None
    ]
    value = min(values) if values else None
    return {
        "metric": f"minimum_model_{metric_key}",
        "value": value,
        "threshold_min": minimum,
        "n_models": len(values),
        "status": _min_status(value=value, minimum=minimum),
    }


def _check_cross_context_corr(
    stability_report: dict[str, Any] | None, thresholds: dict[str, Any]
) -> dict[str, Any]:
    threshold_key = (
        "cross_context_corr_min"
        if "cross_context_corr_min" in thresholds
        else "cross_formulation_min"
    )
    minimum = _threshold(thresholds, threshold_key)
    if not stability_report or stability_report.get("status") != "ok":
        return {
            "metric": "minimum_cross_sp_corr",
            "value": None,
            "threshold_min": minimum,
            "threshold_key": threshold_key,
            "status": "missing",
            "reason": "Missing or non-ok stability_report.json",
        }

    values: list[float] = []
    for model_report in stability_report.get("models", {}).values():
        for value in (model_report.get("cross_sp_corr") or {}).values():
            if value is not None:
                values.append(float(value))

    value = min(values) if values else None
    return {
        "metric": "minimum_cross_sp_corr",
        "value": value,
        "threshold_min": minimum,
        "threshold_key": threshold_key,
        "n_pairs": len(values),
        "status": _min_status(value=value, minimum=minimum),
    }


def _load_json_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    return payload if isinstance(payload, dict) else None


def _threshold(thresholds: dict[str, Any], key: str) -> float | None:
    if key not in thresholds:
        return None
    try:
        return float(thresholds[key])
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _min_status(
    value: float | None,
    minimum: float | None,
    target: float | None = None,
) -> str:
    if value is None:
        return "missing"
    if minimum is not None and value < minimum:
        return "fail"
    if target is not None and value < target:
        return "borderline"
    return "pass"


def _max_status(value: float | None, maximum: float | None) -> str:
    if value is None:
        return "missing"
    if maximum is not None and value > maximum:
        return "fail"
    return "pass"


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
