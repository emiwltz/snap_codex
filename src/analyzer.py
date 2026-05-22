"""Statistical analysis routines for SoulBench SNAP pipeline."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

try:
    import pingouin as pg
except ImportError:  # pragma: no cover - protected fallback
    pg = None

try:
    import statsmodels.formula.api as smf
except ImportError:  # pragma: no cover - protected fallback
    smf = None

from .db import SoulBenchDB

LOGGER = logging.getLogger(__name__)

MIN_RUNS_FOR_RELIABILITY = 5
SPLIT_HALF_EARLY_RUNS = [1, 2, 3, 4, 5]
SPLIT_HALF_LATE_RUNS = [6, 7, 8, 9, 10]
V31_RELIABILITY_TARGET_COLS = ["item_id", "system_prompt"]
V31_BY_ITEM_TARGET_COLS = ["system_prompt"]
V31_BY_AGGREGATION_TARGET_COLS = ["item_id", "system_prompt"]
V31_SENSITIVITY_PAIRING_COLS = ["item_id", "system_prompt"]
CROSS_SP_PAIRS = [
    ("SP_ABS", "SP_DIR"),
    ("SP_ABS", "SP_PER"),
    ("SP_DIR", "SP_PER"),
]

TRAIT_BY_PREFIX = {
    "O": "Openness",
    "C": "Conscientiousness",
    "E": "Extraversion",
    "A": "Agreeableness",
    "N": "Neuroticism",
}

FOUNDATION_BY_MORAL_ITEM = {
    "M_CH": "Care/Harm",
    "M_FC": "Fairness/Cheating",
    "M_LB": "Loyalty/Betrayal",
    "M_AS": "Authority/Subversion",
    "M_PS": "Purity/Sanctity",
}


@dataclass
class Analyzer:
    """Run analysis suites and write structured reports."""

    db: SoulBenchDB
    output_dir: Path = Path("outputs/reports")

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def analyze_stability(self) -> dict[str, Any]:
        """Compute stability-oriented metrics per model."""
        raw_df = self.db.get_numeric_scores_dataframe()
        df = _apply_protocol_exclusions(raw_df)
        report: dict[str, Any] = {
            "analysis": "stability",
            "n_rows_raw": int(len(raw_df)),
            "n_rows_after_exclusions": int(len(df)),
            "models": {},
            "reliability_rules": {
                "primary_metric": "ICC on protocol runs",
                "secondary_metric": "Pearson split-half (runs 1-5 vs 6-10 for POC v3.1)",
                "target_identifier": V31_RELIABILITY_TARGET_COLS,
                "minimum_runs_required": MIN_RUNS_FOR_RELIABILITY,
                "exclusions": [
                    "is_error = 1",
                    "score_final = REFUS",
                    "manual_review_needed = 1 and manual_score is missing",
                ],
                "design_note": (
                    "In v3.1, scenario/formulation/temperature are assigned by "
                    "the run schedule. Reliability therefore treats item x "
                    "system_prompt as the repeated target observed across runs."
                ),
            },
            "notes": [
                "Alpha moral par fondement incalculable avec 1 item/fondement.",
            ],
        }

        if df.empty:
            report["status"] = "empty"
            self.db.save_json_report(report, self.output_dir / "stability_report.json")
            return report

        for model, group in df.groupby("model"):
            split_half = _compute_split_half_pearson(
                group,
                target_cols=V31_RELIABILITY_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            )
            icc = _compute_icc(
                group,
                target_cols=V31_RELIABILITY_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            )

            by_item = _compute_reliability_by_item(group)
            by_aggregation = _compute_reliability_by_aggregation_group(group)

            report["models"][model] = {
                "cronbach_alpha": _compute_cronbach_alpha(group),
                "test_retest_pearson": split_half.get("value"),
                "test_retest_pearson_split_half": split_half,
                "icc": icc.get("value"),
                "icc_runs": icc,
                "request_parameters": _summarize_request_parameters(group),
                "cross_temperature_corr": _compute_cross_temperature_corr(group),
                "cross_sp_corr": _compute_cross_sp_corr(group),
                "aggregation_levels": {
                    "by_item": by_item,
                    "by_trait_or_foundation": by_aggregation,
                },
            }

        report["status"] = "ok"
        self.db.save_json_report(report, self.output_dir / "stability_report.json")
        return report

    def analyze_sensitivity(self) -> dict[str, Any]:
        """Compute sensitivity metrics for scenario/formulation effects."""
        raw_df = self.db.get_numeric_scores_dataframe()
        df = _apply_protocol_exclusions(raw_df)
        report: dict[str, Any] = {
            "analysis": "sensitivity",
            "n_rows_raw": int(len(raw_df)),
            "n_rows_after_exclusions": int(len(df)),
            "models": {},
        }

        if df.empty:
            report["status"] = "empty"
            self.db.save_json_report(
                report, self.output_dir / "sensitivity_report.json"
            )
            return report

        for model, group in df.groupby("model"):
            report["models"][model] = {
                "scenario_effect_wilcoxon": _compute_scenario_effect(group),
                "formulation_effect_friedman": _compute_formulation_effect(group),
                "temperature_effect": _compute_temperature_effect(group),
            }

        report["status"] = "ok"
        self.db.save_json_report(report, self.output_dir / "sensitivity_report.json")
        return report

    def analyze_variance_decomposition(self) -> dict[str, Any]:
        """Compute exploratory eta-squared and confirmatory LMM for H4."""
        raw_df = self.db.get_numeric_scores_dataframe()
        df = _apply_protocol_exclusions(raw_df)
        report: dict[str, Any] = {
            "analysis": "variance_decomposition",
            "n_rows_raw": int(len(raw_df)),
            "n_rows_after_exclusions": int(len(df)),
            "factors": {},
            "notes": [
                "H4 exploratory: ANOVA-style eta squared by factor.",
                "H4 confirmatory: LMM formula score ~ model * system_prompt + model * temperature + scenario + formulation + (1|item) + (1|run) + (1|model_random).",
                "Fallback if non-convergence: remove (1|model_random), keep (1|item) + (1|run).",
            ],
        }

        if df.empty:
            report["status"] = "empty"
            report["confirmatory_lmm"] = {"status": "empty"}
            self.db.save_json_report(
                report, self.output_dir / "variance_decomposition_report.json"
            )
            return report

        factors = [
            "model",
            "system_prompt",
            "temperature",
            "scenario",
            "formulation",
            "item_id",
            "run",
        ]
        eta_values = {factor: _compute_eta_squared(df, factor) for factor in factors}
        sorted_factors = sorted(
            eta_values.items(),
            key=lambda entry: -1.0 if entry[1] is None else float(entry[1]),
            reverse=True,
        )

        report["factors"] = eta_values
        report["ranking"] = [factor for factor, _ in sorted_factors]
        report["confirmatory_lmm"] = _fit_h4_lmm(df)
        report["status"] = "ok"
        self.db.save_json_report(
            report, self.output_dir / "variance_decomposition_report.json"
        )
        return report

    def analyze_cross_sp_diagnostic(
        self,
        top_n: int = 30,
        examples_per_sp: int = 1,
        response_char_limit: int = 1200,
    ) -> dict[str, Any]:
        """Build a targeted diagnostic report for system-prompt sensitivity."""
        raw_df = self.db.get_response_diagnostics_dataframe()
        df = _prepare_numeric_diagnostic_dataframe(raw_df)
        report: dict[str, Any] = {
            "analysis": "cross_sp_diagnostic",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_rows_raw": int(len(raw_df)),
            "n_rows_after_exclusions": int(len(df)),
            "system_prompt_pairs": [
                f"{sp_a}_vs_{sp_b}" for sp_a, sp_b in CROSS_SP_PAIRS
            ],
            "method": {
                "model_pair_correlations": (
                    "Pearson correlations over item_id x run mean scores."
                ),
                "sp_amplitude": (
                    "For each model x item cell, max(mean score by SP) - "
                    "min(mean score by SP)."
                ),
                "examples": (
                    "One representative raw response per SP for the highest "
                    "amplitude model x item cells, truncated for review."
                ),
            },
        }

        if df.empty:
            report["status"] = "empty"
            self.db.save_json_report(
                report, self.output_dir / "cross_sp_diagnostic.json"
            )
            return report

        pair_long = _compute_cross_sp_pair_table(df)
        pair_wide = _cross_sp_pair_wide(pair_long)
        cell_table = _compute_sp_amplitude_cells(df)
        item_table = _compute_item_sp_amplitude_table(cell_table)
        top_cells = cell_table.head(top_n).copy()
        examples = _extract_cross_sp_examples(
            df=df,
            top_cells=top_cells,
            examples_per_sp=examples_per_sp,
            response_char_limit=response_char_limit,
        )

        pair_long.to_csv(self.output_dir / "cross_sp_model_pairs.csv", index=False)
        item_table.to_csv(self.output_dir / "cross_sp_item_amplitudes.csv", index=False)
        top_cells.to_csv(self.output_dir / "cross_sp_top_cells.csv", index=False)

        report.update(
            {
                "status": "ok",
                "model_pair_correlation_table": _json_records(pair_wide),
                "model_pair_correlation_details": _json_records(pair_long),
                "item_sp_amplitude_table": _json_records(item_table),
                "top_cells_by_sp_range": _json_records(top_cells),
                "critical_response_examples": examples,
                "csv_outputs": {
                    "model_pairs": str(self.output_dir / "cross_sp_model_pairs.csv"),
                    "item_amplitudes": str(
                        self.output_dir / "cross_sp_item_amplitudes.csv"
                    ),
                    "top_cells": str(self.output_dir / "cross_sp_top_cells.csv"),
                },
            }
        )
        self.db.save_json_report(report, self.output_dir / "cross_sp_diagnostic.json")
        return report


def _apply_protocol_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply agreed exclusions used across statistical analyses."""
    if df.empty:
        return df

    working = df.copy()

    if "is_error" in working.columns:
        working["is_error"] = (
            pd.to_numeric(working["is_error"], errors="coerce").fillna(0).astype(int)
        )
        working = working[working["is_error"] == 0]

    if "manual_review_needed" in working.columns:
        working["manual_review_needed"] = (
            pd.to_numeric(working["manual_review_needed"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    if "manual_review_needed" in working.columns and "manual_score" in working.columns:
        manual_score = working["manual_score"].fillna("").astype(str).str.strip()
        pending_manual = (working["manual_review_needed"] == 1) & (manual_score == "")
        working = working[~pending_manual]

    if "score_final" in working.columns:
        working = working[
            working["score_final"].fillna("").astype(str).str.upper() != "REFUS"
        ]

    working["run"] = pd.to_numeric(working["run"], errors="coerce")
    working = working[working["run"].notna()].copy()
    working["run"] = working["run"].astype(int)

    return working


def _prepare_numeric_diagnostic_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply analysis exclusions and add numeric scores for diagnostics."""
    if df.empty:
        return df
    working = df.copy()
    score_map = {"+1": 1, "0": 0, "-1": -1}
    working["score_numeric"] = working["score_final"].map(score_map)
    working = working[working["score_numeric"].notna()]
    return _apply_protocol_exclusions(working)


def _compute_cross_sp_pair_table(df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for model, group in df.groupby("model"):
        pivot = group.pivot_table(
            index=["item_id", "run"],
            columns="system_prompt",
            values="score_numeric",
            aggfunc="mean",
        )
        for sp_a, sp_b in CROSS_SP_PAIRS:
            pair_key = f"{sp_a}_vs_{sp_b}"
            record: dict[str, Any] = {
                "model": model,
                "pair": pair_key,
                "sp_a": sp_a,
                "sp_b": sp_b,
                "correlation": None,
                "n_pairs": 0,
                "status": "not_computable",
                "reason": None,
            }
            if sp_a not in pivot.columns or sp_b not in pivot.columns:
                record["reason"] = "missing_system_prompt_level"
            else:
                paired = pivot[[sp_a, sp_b]].dropna()
                record["n_pairs"] = int(len(paired))
                if len(paired) < 2:
                    record["reason"] = "not_enough_pairs"
                elif paired[sp_a].nunique() < 2 or paired[sp_b].nunique() < 2:
                    record["reason"] = "constant_input"
                else:
                    corr, _ = stats.pearsonr(paired[sp_a], paired[sp_b])
                    record["correlation"] = _safe_float(corr)
                    record["status"] = "ok"
            records.append(record)
    return pd.DataFrame.from_records(records)


def _cross_sp_pair_wide(pair_long: pd.DataFrame) -> pd.DataFrame:
    if pair_long.empty:
        return pair_long
    wide = pair_long.pivot_table(
        index="model",
        columns="pair",
        values="correlation",
        aggfunc="first",
    ).reset_index()
    return wide.sort_values("model").reset_index(drop=True)


def _compute_sp_amplitude_cells(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["model", "item_id", "item_type", "system_prompt"])
        .agg(mean_score=("score_numeric", "mean"), n=("score_numeric", "size"))
        .reset_index()
    )
    means = grouped.pivot_table(
        index=["model", "item_id", "item_type"],
        columns="system_prompt",
        values="mean_score",
        aggfunc="first",
    )
    counts = grouped.pivot_table(
        index=["model", "item_id", "item_type"],
        columns="system_prompt",
        values="n",
        aggfunc="first",
    )
    rows = means.reset_index()
    sp_columns = [sp for sp in ["SP_ABS", "SP_DIR", "SP_PER"] if sp in rows.columns]
    rows["sp_range"] = rows[sp_columns].max(axis=1) - rows[sp_columns].min(axis=1)
    rows["sp_min"] = rows[sp_columns].min(axis=1)
    rows["sp_max"] = rows[sp_columns].max(axis=1)
    for sp in ["SP_ABS", "SP_DIR", "SP_PER"]:
        if sp not in rows.columns:
            rows[sp] = None
        count_col = f"n_{sp}"
        rows[count_col] = (
            counts[sp].reset_index(drop=True).astype("Int64")
            if sp in counts.columns
            else pd.Series([pd.NA] * len(rows), dtype="Int64")
        )
    ordered = [
        "model",
        "item_id",
        "item_type",
        "SP_ABS",
        "SP_DIR",
        "SP_PER",
        "sp_min",
        "sp_max",
        "sp_range",
        "n_SP_ABS",
        "n_SP_DIR",
        "n_SP_PER",
    ]
    return (
        rows[ordered]
        .sort_values(["sp_range", "model", "item_id"], ascending=[False, True, True])
        .reset_index(drop=True)
    )


def _compute_item_sp_amplitude_table(cell_table: pd.DataFrame) -> pd.DataFrame:
    if cell_table.empty:
        return cell_table
    return (
        cell_table.groupby(["item_id", "item_type"], as_index=False)
        .agg(
            mean_sp_range=("sp_range", "mean"),
            max_sp_range=("sp_range", "max"),
            min_sp_range=("sp_range", "min"),
            n_models=("model", "nunique"),
        )
        .sort_values(["mean_sp_range", "max_sp_range"], ascending=False)
        .reset_index(drop=True)
    )


def _extract_cross_sp_examples(
    df: pd.DataFrame,
    top_cells: pd.DataFrame,
    examples_per_sp: int,
    response_char_limit: int,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    if top_cells.empty:
        return examples

    for _, cell in top_cells.iterrows():
        cell_examples: dict[str, Any] = {
            "model": cell["model"],
            "item_id": cell["item_id"],
            "item_type": cell["item_type"],
            "sp_means": {
                sp: _safe_float(cell.get(sp)) for sp in ["SP_ABS", "SP_DIR", "SP_PER"]
            },
            "sp_range": _safe_float(cell.get("sp_range")),
            "examples_by_system_prompt": {},
        }
        cell_rows = df[
            (df["model"] == cell["model"]) & (df["item_id"] == cell["item_id"])
        ].copy()
        for sp in ["SP_ABS", "SP_DIR", "SP_PER"]:
            sp_rows = cell_rows[cell_rows["system_prompt"] == sp].copy()
            if sp_rows.empty:
                cell_examples["examples_by_system_prompt"][sp] = []
                continue
            sp_mean = cell.get(sp)
            if sp_mean is None or pd.isna(sp_mean):
                sp_rows["distance_to_sp_mean"] = 0.0
            else:
                sp_rows["distance_to_sp_mean"] = (
                    sp_rows["score_numeric"].astype(float) - float(sp_mean)
                ).abs()
            selected = sp_rows.sort_values(["distance_to_sp_mean", "run", "id"]).head(
                examples_per_sp
            )
            cell_examples["examples_by_system_prompt"][sp] = [
                {
                    "response_id": int(row["id"]),
                    "run": int(row["run"]),
                    "scenario": row["scenario"],
                    "formulation": row["formulation"],
                    "temperature": _safe_float(row["temperature"]),
                    "score_final": row["score_final"],
                    "score_judge1": row.get("score_judge1"),
                    "score_judge2": row.get("score_judge2"),
                    "agreement_status": row.get("agreement_status"),
                    "user_prompt_excerpt": _truncate_text(
                        row.get("user_prompt_text"), 500
                    ),
                    "raw_response_excerpt": _truncate_text(
                        row.get("raw_response"), response_char_limit
                    ),
                }
                for _, row in selected.iterrows()
            ]
        examples.append(cell_examples)
    return examples


def _truncate_text(value: Any, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 15)].rstrip() + "\n[...truncated]"


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return json.loads(frame.to_json(orient="records"))


def _compute_cronbach_alpha(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    pivot = df.pivot_table(
        index=[
            "model",
            "scenario",
            "formulation",
            "system_prompt",
            "temperature",
            "run",
        ],
        columns="item_id",
        values="score_numeric",
        aggfunc="mean",
    )
    pivot = pivot.dropna(axis=0, how="any")
    if pivot.shape[0] < 2 or pivot.shape[1] < 2:
        return None

    if pg is not None:
        alpha, _ = pg.cronbach_alpha(data=pivot)
        return float(alpha)

    k = pivot.shape[1]
    item_variances = pivot.var(axis=0, ddof=1)
    total_scores = pivot.sum(axis=1)
    total_variance = total_scores.var(ddof=1)
    if total_variance <= 0:
        return None
    alpha = (k / (k - 1)) * (1 - item_variances.sum() / total_variance)
    return float(alpha)


def _filter_targets_with_min_runs(
    df: pd.DataFrame,
    target_cols: list[str],
    min_runs: int,
) -> tuple[pd.DataFrame, int, int]:
    if df.empty:
        return df.copy(), 0, 0

    working = df.copy()
    working["target"] = working[target_cols].astype(str).agg("|".join, axis=1)
    run_counts = working.groupby("target")["run"].nunique()
    eligible_targets = run_counts[run_counts >= min_runs].index
    filtered = working[working["target"].isin(eligible_targets)].copy()
    return filtered, int(len(eligible_targets)), int(len(run_counts))


def _compute_split_half_pearson(
    df: pd.DataFrame,
    target_cols: list[str],
    min_runs: int,
) -> dict[str, Any]:
    working, n_eligible_targets, n_total_targets = _filter_targets_with_min_runs(
        df, target_cols, min_runs
    )
    if working.empty:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "No target reaches minimum scored runs",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    split_runs = set(SPLIT_HALF_EARLY_RUNS + SPLIT_HALF_LATE_RUNS)
    working = working[working["run"].isin(split_runs)]
    if working.empty:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "No rows in split-half run windows",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    pivot = working.pivot_table(
        index="target", columns="run", values="score_numeric", aggfunc="mean"
    )
    early_cols = [run for run in SPLIT_HALF_EARLY_RUNS if run in pivot.columns]
    late_cols = [run for run in SPLIT_HALF_LATE_RUNS if run in pivot.columns]
    if not early_cols or not late_cols:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "Missing required run halves",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    pivot = pivot.copy()
    pivot["early_mean"] = pivot[early_cols].mean(axis=1)
    pivot["late_mean"] = pivot[late_cols].mean(axis=1)
    paired = pivot[["early_mean", "late_mean"]].dropna()

    if len(paired) < 2:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "Not enough paired targets",
            "n_pairs": int(len(paired)),
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    if paired["early_mean"].nunique() < 2 or paired["late_mean"].nunique() < 2:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "Constant input in at least one half",
            "n_pairs": int(len(paired)),
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    corr, _ = stats.pearsonr(paired["early_mean"], paired["late_mean"])
    return {
        "value": _safe_float(corr),
        "status": "ok",
        "n_pairs": int(len(paired)),
        "early_runs": SPLIT_HALF_EARLY_RUNS,
        "late_runs": SPLIT_HALF_LATE_RUNS,
        "eligible_targets": n_eligible_targets,
        "total_targets": n_total_targets,
    }


def _compute_icc(
    df: pd.DataFrame,
    target_cols: list[str],
    min_runs: int,
) -> dict[str, Any]:
    if pg is None:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "pingouin not available",
        }

    working, n_eligible_targets, n_total_targets = _filter_targets_with_min_runs(
        df, target_cols, min_runs
    )
    if working.empty:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "No target reaches minimum scored runs",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    if working["target"].nunique() < 2 or working["run"].nunique() < 2:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "Not enough target/run diversity",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    try:
        icc_table = pg.intraclass_corr(
            data=working,
            targets="target",
            raters="run",
            ratings="score_numeric",
        )
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.warning("ICC computation failed: %s", exc)
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": f"ICC computation failed: {exc}",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    row = icc_table[icc_table["Type"] == "ICC2"]
    if row.empty:
        return {
            "value": None,
            "status": "reliability_not_computable",
            "reason": "ICC2 row not available",
            "eligible_targets": n_eligible_targets,
            "total_targets": n_total_targets,
        }

    return {
        "value": _safe_float(row["ICC"].iloc[0]),
        "status": "ok",
        "eligible_targets": n_eligible_targets,
        "total_targets": n_total_targets,
    }


def _compute_reliability_by_item(df: pd.DataFrame) -> dict[str, Any]:
    metrics_by_item: dict[str, Any] = {}
    for item_id, group in df.groupby("item_id"):
        metrics_by_item[str(item_id)] = {
            "icc_runs": _compute_icc(
                group,
                target_cols=V31_BY_ITEM_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            ),
            "split_half_pearson": _compute_split_half_pearson(
                group,
                target_cols=V31_BY_ITEM_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            ),
        }

    return {
        "metrics": metrics_by_item,
        "summary": _summarize_reliability_map(metrics_by_item),
    }


def _aggregation_group_from_item(item_id: str) -> str:
    if item_id.startswith("M_"):
        foundation = FOUNDATION_BY_MORAL_ITEM.get(item_id, item_id)
        return f"foundation:{foundation}"

    prefix = item_id[:1]
    trait = TRAIT_BY_PREFIX.get(prefix, prefix)
    return f"trait:{trait}"


def _compute_reliability_by_aggregation_group(df: pd.DataFrame) -> dict[str, Any]:
    working = df.copy()
    working["aggregation_group"] = (
        working["item_id"].astype(str).map(_aggregation_group_from_item)
    )

    metrics_by_group: dict[str, Any] = {}
    for group_name, group in working.groupby("aggregation_group"):
        metrics_by_group[str(group_name)] = {
            "icc_runs": _compute_icc(
                group,
                target_cols=V31_BY_AGGREGATION_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            ),
            "split_half_pearson": _compute_split_half_pearson(
                group,
                target_cols=V31_BY_AGGREGATION_TARGET_COLS,
                min_runs=MIN_RUNS_FOR_RELIABILITY,
            ),
        }

    return {
        "metrics": metrics_by_group,
        "summary": _summarize_reliability_map(metrics_by_group),
    }


def _summarize_reliability_map(metrics_map: dict[str, Any]) -> dict[str, Any]:
    if not metrics_map:
        return {
            "total": 0,
            "icc_computable": 0,
            "split_half_computable": 0,
        }

    icc_computable = sum(
        1
        for entry in metrics_map.values()
        if entry["icc_runs"].get("value") is not None
    )
    split_half_computable = sum(
        1
        for entry in metrics_map.values()
        if entry["split_half_pearson"].get("value") is not None
    )
    return {
        "total": int(len(metrics_map)),
        "icc_computable": int(icc_computable),
        "split_half_computable": int(split_half_computable),
    }


def _compute_cross_temperature_corr(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    if not _temperature_parameter_applied(df):
        return None

    pivot = df.pivot_table(
        index=V31_RELIABILITY_TARGET_COLS,
        columns="temperature",
        values="score_numeric",
        aggfunc="mean",
    )
    temperatures = sorted(float(value) for value in pivot.columns)
    if len(temperatures) < 2:
        return None
    low_temp = temperatures[0]
    high_temp = temperatures[-1]
    paired = pivot[[low_temp, high_temp]].dropna()
    if len(paired) < 2:
        return None
    if paired[low_temp].nunique() < 2 or paired[high_temp].nunique() < 2:
        return None
    corr, _ = stats.pearsonr(paired[low_temp], paired[high_temp])
    return _safe_float(corr)


def _compute_cross_sp_corr(df: pd.DataFrame) -> dict[str, float | None]:
    if df.empty:
        return {
            "SP_ABS_vs_SP_DIR": None,
            "SP_ABS_vs_SP_PER": None,
            "SP_DIR_vs_SP_PER": None,
        }

    pivot = df.pivot_table(
        index=["item_id", "run"],
        columns="system_prompt",
        values="score_numeric",
        aggfunc="mean",
    )

    def _pair_corr(sp_a: str, sp_b: str) -> float | None:
        if sp_a not in pivot.columns or sp_b not in pivot.columns:
            return None
        paired = pivot[[sp_a, sp_b]].dropna()
        if len(paired) < 2:
            return None
        if paired[sp_a].nunique() < 2 or paired[sp_b].nunique() < 2:
            return None
        corr, _ = stats.pearsonr(paired[sp_a], paired[sp_b])
        return _safe_float(corr)

    return {
        "SP_ABS_vs_SP_DIR": _pair_corr("SP_ABS", "SP_DIR"),
        "SP_ABS_vs_SP_PER": _pair_corr("SP_ABS", "SP_PER"),
        "SP_DIR_vs_SP_PER": _pair_corr("SP_DIR", "SP_PER"),
    }


def _compute_scenario_effect(df: pd.DataFrame) -> dict[str, Any]:
    return _compute_rotated_factor_effect(
        df=df,
        factor="scenario",
        levels=["base", "variation"],
        test="wilcoxon",
        method="paired_means_by_item_system_prompt",
    )


def _compute_formulation_effect(df: pd.DataFrame) -> dict[str, Any]:
    return _compute_rotated_factor_effect(
        df=df,
        factor="formulation",
        levels=["F1", "F2", "F3"],
        test="friedman",
        method="paired_means_by_item_system_prompt",
    )


def _compute_temperature_effect(df: pd.DataFrame) -> dict[str, Any]:
    temperatures = sorted(float(value) for value in df["temperature"].dropna().unique())
    if not _temperature_parameter_applied(df):
        return {
            "status": "not_applicable",
            "reason": "Temperature parameter was not sent for this model.",
            "statistic": None,
            "p_value": None,
            "n_pairs": 0,
            "levels": temperatures,
            "method": "not_applicable",
            "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        }
    if len(temperatures) < 2:
        return {
            "status": "not_computable",
            "reason": "Need at least 2 observed temperature levels",
            "statistic": None,
            "p_value": None,
            "n_pairs": 0,
            "levels": temperatures,
        }

    test = "wilcoxon" if len(temperatures) == 2 else "friedman"
    return _compute_rotated_factor_effect(
        df=df,
        factor="temperature",
        levels=temperatures,
        test=test,
        method="paired_means_by_item_system_prompt",
    )


def _compute_rotated_factor_effect(
    df: pd.DataFrame,
    factor: str,
    levels: list[Any],
    test: str,
    method: str,
) -> dict[str, Any]:
    """Compute exploratory factor effects for the v3.1 rotated schedule.

    The POC rotation does not repeat every scenario/formulation/temperature
    inside every run. We therefore pair mean scores at the stable
    item x system_prompt target level.
    """
    if df.empty or factor not in df.columns:
        return {
            "status": "not_computable",
            "reason": f"Missing factor column: {factor}",
            "statistic": None,
            "p_value": None,
            "n_pairs": 0,
            "levels": levels,
            "method": method,
            "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        }

    pivot = df.pivot_table(
        index=V31_SENSITIVITY_PAIRING_COLS,
        columns=factor,
        values="score_numeric",
        aggfunc="mean",
    )
    missing_levels = [level for level in levels if level not in pivot.columns]
    if missing_levels:
        return {
            "status": "not_computable",
            "reason": f"Missing levels for {factor}: {missing_levels}",
            "statistic": None,
            "p_value": None,
            "n_pairs": 0,
            "levels": levels,
            "method": method,
            "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        }

    paired = pivot[levels].dropna()
    if len(paired) < 2:
        return {
            "status": "not_computable",
            "reason": "Not enough paired item x system_prompt targets",
            "statistic": None,
            "p_value": None,
            "n_pairs": int(len(paired)),
            "levels": levels,
            "method": method,
            "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        }

    try:
        if test == "wilcoxon":
            stat, p_value = stats.wilcoxon(paired[levels[0]], paired[levels[1]])
        elif test == "friedman":
            stat, p_value = stats.friedmanchisquare(
                *[paired[level] for level in levels]
            )
        else:
            raise ValueError(f"Unsupported test: {test}")
    except ValueError as exc:
        return {
            "status": "not_computable",
            "reason": str(exc),
            "statistic": None,
            "p_value": None,
            "n_pairs": int(len(paired)),
            "levels": levels,
            "method": method,
            "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        }

    return {
        "status": "ok",
        "statistic": _safe_float(stat),
        "p_value": _safe_float(p_value),
        "n_pairs": int(len(paired)),
        "levels": levels,
        "method": method,
        "pairing_unit": V31_SENSITIVITY_PAIRING_COLS,
        "note": (
            "Exploratory v3.1 estimate: factor levels are compared after "
            "averaging across the rotated schedule at item x system_prompt level."
        ),
    }


def _summarize_request_parameters(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "temperature_applied": _summarize_nullable_bool(df, "temperature_applied"),
        "top_p_applied": _summarize_nullable_bool(df, "top_p_applied"),
        "thinking_enabled": _summarize_nullable_bool(df, "thinking_enabled"),
    }


def _summarize_nullable_bool(df: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in df.columns:
        return {"true": 0, "false": 0, "unknown": int(len(df))}
    values = pd.to_numeric(df[column], errors="coerce")
    return {
        "true": int((values == 1).sum()),
        "false": int((values == 0).sum()),
        "unknown": int(values.isna().sum()),
    }


def _temperature_parameter_applied(df: pd.DataFrame) -> bool:
    if "temperature_applied" not in df.columns:
        return True
    values = pd.to_numeric(df["temperature_applied"], errors="coerce").dropna()
    return bool(values.empty or (values == 1).all())


def _compute_eta_squared(df: pd.DataFrame, factor: str) -> float | None:
    if df.empty or factor not in df.columns:
        return None

    scores = df["score_numeric"].astype(float)
    grand_mean = float(scores.mean())
    ss_total = float(((scores - grand_mean) ** 2).sum())
    if ss_total <= 0:
        return None

    grouped = df.groupby(factor)["score_numeric"]
    ss_between = 0.0
    for _, values in grouped:
        n = len(values)
        if n == 0:
            continue
        group_mean = float(values.mean())
        ss_between += n * ((group_mean - grand_mean) ** 2)

    return float(ss_between / ss_total)


def _fit_h4_lmm(df: pd.DataFrame) -> dict[str, Any]:
    """Fit confirmatory LMM with requested fallback strategy."""
    formula = (
        "score_numeric ~ C(model) * C(system_prompt) + C(model) * C(temperature) "
        "+ C(scenario) + C(formulation)"
    )

    if smf is None:
        return {
            "status": "not_available",
            "reason": "statsmodels is not installed",
            "formula": formula,
        }

    if df["item_id"].nunique() < 2:
        return {
            "status": "not_computable",
            "reason": "Need at least 2 item levels for random intercept (1|item)",
            "formula": formula,
        }

    working = df.copy()
    for col in [
        "model",
        "system_prompt",
        "temperature",
        "scenario",
        "formulation",
        "item_id",
        "run",
    ]:
        working[col] = working[col].astype(str)
    working["model_random"] = working["model"]

    attempts: list[dict[str, Any]] = []

    model_specs = [
        ("primary", {"run": "0 + C(run)", "model_random": "0 + C(model_random)"}),
        ("fallback_without_model_random", {"run": "0 + C(run)"}),
    ]

    for label, vc_formula in model_specs:
        try:
            mixed = smf.mixedlm(
                formula=formula,
                data=working,
                groups=working["item_id"],
                re_formula="1",
                vc_formula=vc_formula,
            )
            fit = mixed.fit(reml=False, method="lbfgs", maxiter=300, disp=False)
        except Exception as exc:  # pragma: no cover - defensive
            attempts.append({"model": label, "status": "failed", "error": str(exc)})
            continue

        converged = bool(getattr(fit, "converged", False))
        if not converged:
            attempts.append(
                {"model": label, "status": "failed", "error": "non_converged"}
            )
            continue

        params = {str(k): _safe_float(v) for k, v in fit.params.items()}
        pvalues = {str(k): _safe_float(v) for k, v in fit.pvalues.items()}

        random_effects: dict[str, float | None] = {}
        cov_re = getattr(fit, "cov_re", None)
        if cov_re is not None and hasattr(cov_re, "iloc") and cov_re.shape[0] >= 1:
            random_effects["item_intercept"] = _safe_float(cov_re.iloc[0, 0])

        vcomp_values = getattr(fit, "vcomp", None)
        if vcomp_values is not None:
            names = getattr(getattr(fit, "model", None), "vcomp_names", None)
            if names and len(names) == len(vcomp_values):
                for name, value in zip(names, vcomp_values):
                    random_effects[str(name)] = _safe_float(value)
            else:
                for idx, value in enumerate(vcomp_values):
                    random_effects[f"vc_{idx + 1}"] = _safe_float(value)

        result = {
            "status": "ok",
            "used_model": label,
            "formula": formula,
            "vc_formula": vc_formula,
            "n_obs": int(getattr(fit, "nobs", len(working))),
            "converged": converged,
            "aic": _safe_float(getattr(fit, "aic", None)),
            "bic": _safe_float(getattr(fit, "bic", None)),
            "log_likelihood": _safe_float(getattr(fit, "llf", None)),
            "params": params,
            "pvalues": pvalues,
            "random_effects": random_effects,
            "attempt_history": attempts,
        }
        return result

    return {
        "status": "failed",
        "formula": formula,
        "attempt_history": attempts,
    }


def _safe_float(value: Any) -> float | None:
    """Convert to finite float, otherwise return None."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(number):
        return number
    return None


def analyze_stability(
    db: SoulBenchDB, output_dir: str | Path = "outputs/reports"
) -> dict[str, Any]:
    """Convenience wrapper for stability analysis."""
    return Analyzer(db=db, output_dir=Path(output_dir)).analyze_stability()


def analyze_sensitivity(
    db: SoulBenchDB, output_dir: str | Path = "outputs/reports"
) -> dict[str, Any]:
    """Convenience wrapper for sensitivity analysis."""
    return Analyzer(db=db, output_dir=Path(output_dir)).analyze_sensitivity()


def analyze_variance_decomposition(
    db: SoulBenchDB, output_dir: str | Path = "outputs/reports"
) -> dict[str, Any]:
    """Convenience wrapper for variance decomposition analysis."""
    return Analyzer(db=db, output_dir=Path(output_dir)).analyze_variance_decomposition()


def analyze_cross_sp_diagnostic(
    db: SoulBenchDB,
    output_dir: str | Path = "outputs/reports",
    top_n: int = 30,
    examples_per_sp: int = 1,
    response_char_limit: int = 1200,
) -> dict[str, Any]:
    """Convenience wrapper for targeted cross-system-prompt diagnostics."""
    return Analyzer(db=db, output_dir=Path(output_dir)).analyze_cross_sp_diagnostic(
        top_n=top_n,
        examples_per_sp=examples_per_sp,
        response_char_limit=response_char_limit,
    )
