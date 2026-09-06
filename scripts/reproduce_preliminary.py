#!/usr/bin/env python3
"""Recompute publication-facing SNAP v3.1 evidence from immutable inputs.

The script deliberately opens both SQLite databases in read-only mode. It
produces an audit report, decomposes cross-system-prompt correlations, adds
cluster-bootstrap uncertainty intervals, and records input fingerprints and
the Python package versions used for the run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import itertools
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy import stats


SEED = 20260904
SYSTEM_PROMPT_PAIRS = [
    ("SP_ABS", "SP_DIR"),
    ("SP_ABS", "SP_PER"),
    ("SP_DIR", "SP_PER"),
]
SCORE_MAP = {"-1": -1.0, "0": 0.0, "+1": 1.0}
FINGERPRINT_PATHS = [
    "data/snap_poc_v3_1.db",
    "data/snap_poc_v3_1_human_validation_clean.db",
    "data/manual_sample_coded.csv",
    "config/protocol.yaml",
    "config/models.yaml",
    "config/system_prompts.yaml",
    "config/items_personality.yaml",
    "config/items_moral.yaml",
    "config/scoring_rubrics.yaml",
    "outputs/reports/decision_report.json",
    "outputs/reports/stability_report.json",
    "outputs/reports/cross_sp_diagnostic.json",
]


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _read_sqlite(path: Path, query: str) -> pd.DataFrame:
    uri = f"file:{path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        return pd.read_sql_query(query, connection)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_pearson(a: Iterable[float], b: Iterable[float]) -> float | None:
    a_array = np.asarray(list(a), dtype=float)
    b_array = np.asarray(list(b), dtype=float)
    mask = np.isfinite(a_array) & np.isfinite(b_array)
    a_array = a_array[mask]
    b_array = b_array[mask]
    if len(a_array) < 2 or np.unique(a_array).size < 2 or np.unique(b_array).size < 2:
        return None
    return float(stats.pearsonr(a_array, b_array).statistic)


def _safe_spearman(a: Iterable[float], b: Iterable[float]) -> float | None:
    a_array = np.asarray(list(a), dtype=float)
    b_array = np.asarray(list(b), dtype=float)
    mask = np.isfinite(a_array) & np.isfinite(b_array)
    a_array = a_array[mask]
    b_array = b_array[mask]
    if len(a_array) < 2 or np.unique(a_array).size < 2 or np.unique(b_array).size < 2:
        return None
    return float(stats.spearmanr(a_array, b_array).statistic)


def _percentile_interval(values: list[float]) -> list[float] | None:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=float)
    if finite.size < 2:
        return None
    return [float(value) for value in np.quantile(finite, [0.025, 0.975])]


def _stable_rng(label: str, seed: int) -> np.random.Generator:
    label_hash = int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:8], 16)
    return np.random.default_rng((seed + label_hash) % (2**32))


def _cluster_bootstrap_pair(
    paired: pd.DataFrame,
    sp_a: str,
    sp_b: str,
    n_bootstrap: int,
    seed: int,
    label: str,
) -> dict[str, list[float] | None]:
    blocks = [
        group[[sp_a, sp_b]].to_numpy(dtype=float)
        for _, group in paired.groupby("item_id", sort=True)
    ]
    if len(blocks) < 2:
        return {"pearson_95ci": None, "mean_absolute_difference_95ci": None}

    rng = _stable_rng(label, seed)
    pearson_values: list[float] = []
    mad_values: list[float] = []
    for _ in range(n_bootstrap):
        sampled_indices = rng.integers(0, len(blocks), size=len(blocks))
        sampled = np.concatenate([blocks[index] for index in sampled_indices], axis=0)
        corr = _safe_pearson(sampled[:, 0], sampled[:, 1])
        if corr is not None:
            pearson_values.append(corr)
        mad_values.append(float(np.mean(np.abs(sampled[:, 1] - sampled[:, 0]))))

    return {
        "pearson_95ci": _percentile_interval(pearson_values),
        "mean_absolute_difference_95ci": _percentile_interval(mad_values),
    }


def _cohen_kappa(labels_a: Iterable[str], labels_b: Iterable[str]) -> float | None:
    pairs = [(str(a), str(b)) for a, b in zip(labels_a, labels_b)]
    if not pairs:
        return None
    categories = sorted({value for pair in pairs for value in pair})
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    marginal_a = {category: sum(a == category for a, _ in pairs) / n for category in categories}
    marginal_b = {category: sum(b == category for _, b in pairs) / n for category in categories}
    expected = sum(marginal_a[category] * marginal_b[category] for category in categories)
    if math.isclose(expected, 1.0):
        return 1.0
    return float((observed - expected) / (1.0 - expected))


def _weighted_kappa(
    labels_a: Iterable[str], labels_b: Iterable[str], quadratic: bool
) -> float | None:
    categories = ["-1", "0", "+1"]
    index = {category: position for position, category in enumerate(categories)}
    pairs = [
        (str(a), str(b))
        for a, b in zip(labels_a, labels_b)
        if str(a) in index and str(b) in index
    ]
    if not pairs:
        return None

    observed = np.zeros((len(categories), len(categories)), dtype=float)
    for label_a, label_b in pairs:
        observed[index[label_a], index[label_b]] += 1.0
    observed /= observed.sum()
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))

    weights = np.zeros_like(observed)
    scale = len(categories) - 1
    for row in range(len(categories)):
        for column in range(len(categories)):
            distance = abs(row - column) / scale
            weights[row, column] = distance**2 if quadratic else distance

    observed_disagreement = float(np.sum(weights * observed))
    expected_disagreement = float(np.sum(weights * expected))
    if math.isclose(expected_disagreement, 0.0):
        return 1.0
    return float(1.0 - observed_disagreement / expected_disagreement)


def _agreement_summary(labels_a: pd.Series, labels_b: pd.Series) -> dict[str, Any]:
    eligible = pd.DataFrame({"a": labels_a, "b": labels_b}).dropna()
    eligible["a"] = eligible["a"].astype(str)
    eligible["b"] = eligible["b"].astype(str)
    ordinal = eligible[eligible["a"].isin(SCORE_MAP) & eligible["b"].isin(SCORE_MAP)]
    return {
        "n_pairs": int(len(eligible)),
        "exact_agreement": float((eligible["a"] == eligible["b"]).mean()),
        "unweighted_kappa": _cohen_kappa(eligible["a"], eligible["b"]),
        "n_ordinal_pairs": int(len(ordinal)),
        "linear_weighted_kappa_ordinal_only": _weighted_kappa(
            ordinal["a"], ordinal["b"], quadratic=False
        ),
        "quadratic_weighted_kappa_ordinal_only": _weighted_kappa(
            ordinal["a"], ordinal["b"], quadratic=True
        ),
        "note": "Weighted kappas exclude pairs containing REFUS because refusal is not an ordinal pole.",
    }


def _campaign_summary(responses: pd.DataFrame) -> dict[str, Any]:
    per_model = (
        responses.groupby("model", sort=True)
        .agg(
            responses=("id", "size"),
            errors=("is_error", "sum"),
            refusals=("is_refusal", "sum"),
            truncated=("is_truncated", "sum"),
            final_scores=("score_final", "count"),
        )
        .reset_index()
    )
    return {
        "response_count": int(len(responses)),
        "distinct_trial_ids": int(responses["trial_id"].nunique()),
        "non_error_count": int((responses["is_error"] == 0).sum()),
        "final_score_count": int(responses["score_final"].notna().sum()),
        "first_timestamp": str(responses["timestamp"].min()),
        "last_timestamp": str(responses["timestamp"].max()),
        "per_model": per_model.to_dict(orient="records"),
    }


def _split_half_metrics(
    numeric: pd.DataFrame, n_bootstrap: int, seed: int
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model, group in numeric.groupby("model", sort=True):
        pivot = group.pivot_table(
            index=["item_id", "system_prompt"],
            columns="run",
            values="score_numeric",
            aggfunc="mean",
        )
        early_columns = [run for run in range(1, 6) if run in pivot.columns]
        late_columns = [run for run in range(6, 11) if run in pivot.columns]
        paired = pd.DataFrame(
            {
                "early": pivot[early_columns].mean(axis=1),
                "late": pivot[late_columns].mean(axis=1),
            }
        ).dropna()
        paired = paired.reset_index()
        pearson = _safe_pearson(paired["early"], paired["late"])
        mae = float(np.mean(np.abs(paired["late"] - paired["early"])))

        bootstrap = _cluster_bootstrap_pair(
            paired=paired.rename(columns={"early": "SP_A", "late": "SP_B"}),
            sp_a="SP_A",
            sp_b="SP_B",
            n_bootstrap=n_bootstrap,
            seed=seed,
            label=f"split-half:{model}",
        )
        target_variation = group.groupby(["item_id", "system_prompt"])[
            "score_numeric"
        ].nunique()
        rows.append(
            {
                "model": model,
                "n_targets": int(len(paired)),
                "pearson": pearson,
                "pearson_95ci_item_cluster_bootstrap": bootstrap["pearson_95ci"],
                "mean_absolute_half_difference": mae,
                "mean_absolute_half_difference_95ci_item_cluster_bootstrap": bootstrap[
                    "mean_absolute_difference_95ci"
                ],
                "constant_target_fraction_across_runs": float(
                    (target_variation == 1).mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def _cross_sp_metrics(
    numeric: pd.DataFrame, n_bootstrap: int, seed: int
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model, group in numeric.groupby("model", sort=True):
        pivot = group.pivot_table(
            index=["item_id", "run"],
            columns="system_prompt",
            values="score_numeric",
            aggfunc="mean",
        ).reset_index()
        for sp_a, sp_b in SYSTEM_PROMPT_PAIRS:
            paired = pivot[["item_id", "run", sp_a, sp_b]].dropna()
            item_means = paired.groupby("item_id")[[sp_a, sp_b]].mean()
            centered_a = paired[sp_a] - paired.groupby("item_id")[sp_a].transform("mean")
            centered_b = paired[sp_b] - paired.groupby("item_id")[sp_b].transform("mean")
            bootstrap = _cluster_bootstrap_pair(
                paired=paired,
                sp_a=sp_a,
                sp_b=sp_b,
                n_bootstrap=n_bootstrap,
                seed=seed,
                label=f"cross-sp:{model}:{sp_a}:{sp_b}",
            )
            difference = paired[sp_b] - paired[sp_a]
            rows.append(
                {
                    "model": model,
                    "pair": f"{sp_a}_vs_{sp_b}",
                    "n_item_run_pairs": int(len(paired)),
                    "pearson_item_run": _safe_pearson(paired[sp_a], paired[sp_b]),
                    "pearson_item_run_95ci_item_cluster_bootstrap": bootstrap[
                        "pearson_95ci"
                    ],
                    "spearman_item_run": _safe_spearman(paired[sp_a], paired[sp_b]),
                    "pearson_item_means_n15": _safe_pearson(
                        item_means[sp_a], item_means[sp_b]
                    ),
                    "within_item_centered_pearson": _safe_pearson(
                        centered_a, centered_b
                    ),
                    "exact_agreement": float((difference == 0).mean()),
                    "mean_signed_difference_b_minus_a": float(difference.mean()),
                    "mean_absolute_difference": float(np.abs(difference).mean()),
                    "mean_absolute_difference_95ci_item_cluster_bootstrap": bootstrap[
                        "mean_absolute_difference_95ci"
                    ],
                }
            )
    return pd.DataFrame(rows)


def _paired_bootstrap_difference(
    differences: np.ndarray, n_bootstrap: int, seed: int, label: str
) -> list[float] | None:
    differences = np.asarray(differences, dtype=float)
    differences = differences[np.isfinite(differences)]
    if differences.size < 2:
        return None
    rng = _stable_rng(label, seed)
    means = [
        float(rng.choice(differences, size=differences.size, replace=True).mean())
        for _ in range(n_bootstrap)
    ]
    return _percentile_interval(means)


def _exact_sign_flip_p_value(differences: np.ndarray) -> float | None:
    differences = np.asarray(differences, dtype=float)
    differences = differences[np.isfinite(differences)]
    if differences.size == 0 or differences.size > 20:
        return None
    observed = abs(float(differences.mean()))
    exceedances = 0
    total = 0
    for signs in itertools.product([-1.0, 1.0], repeat=differences.size):
        permuted = abs(float(np.mean(differences * np.asarray(signs))))
        exceedances += permuted >= observed - 1e-12
        total += 1
    return float(exceedances / total)


def _critical_cell_summary(
    numeric: pd.DataFrame, n_bootstrap: int, seed: int
) -> dict[str, Any]:
    cell = numeric[
        (numeric["model"] == "mistral-large-3") & (numeric["item_id"] == "E2")
    ]
    pivot = cell.pivot_table(
        index="run", columns="system_prompt", values="score_numeric", aggfunc="mean"
    )
    means = {prompt: float(pivot[prompt].mean()) for prompt in pivot.columns}
    contrasts: dict[str, Any] = {}
    for sp_a, sp_b in [("SP_DIR", "SP_PER"), ("SP_ABS", "SP_PER")]:
        paired = pivot[[sp_a, sp_b]].dropna()
        differences = (paired[sp_b] - paired[sp_a]).to_numpy(dtype=float)
        contrasts[f"{sp_b}_minus_{sp_a}"] = {
            "n_paired_runs": int(len(differences)),
            "mean_difference": float(differences.mean()),
            "paired_bootstrap_95ci": _paired_bootstrap_difference(
                differences,
                n_bootstrap=n_bootstrap,
                seed=seed,
                label=f"critical:{sp_a}:{sp_b}",
            ),
            "exact_two_sided_sign_flip_p": _exact_sign_flip_p_value(differences),
        }
    return {
        "selection_note": (
            "This cell was selected after inspecting v3.1 and is exploratory; "
            "its interval and p-value do not remove selection bias."
        ),
        "means": means,
        "range": float(max(means.values()) - min(means.values())),
        "contrasts": contrasts,
    }


def _human_validation_summary(
    validation_db: Path, expected_models: list[str]
) -> tuple[dict[str, Any], pd.DataFrame]:
    human = _read_sqlite(
        validation_db,
        """
        SELECT
            r.model,
            r.item_id,
            r.system_prompt,
            r.score_judge1,
            r.score_judge2,
            r.score_final,
            mv.human_score
        FROM manual_verification AS mv
        JOIN responses AS r ON r.id = mv.response_id
        WHERE mv.source = 'human_validation'
        ORDER BY r.id
        """,
    )
    counts = human.groupby("model").size().to_dict()
    coverage = pd.DataFrame(
        [
            {
                "model": model,
                "n_human_coded": int(counts.get(model, 0)),
                "covered": bool(counts.get(model, 0) > 0),
            }
            for model in expected_models
        ]
    )
    return (
        {
            "n_human_coded": int(len(human)),
            "covered_models": int(coverage["covered"].sum()),
            "expected_models": int(len(coverage)),
            "missing_models": coverage.loc[~coverage["covered"], "model"].tolist(),
            "human_vs_judge1": _agreement_summary(
                human["human_score"], human["score_judge1"]
            ),
            "human_vs_judge2": _agreement_summary(
                human["human_score"], human["score_judge2"]
            ),
            "human_vs_final": _agreement_summary(
                human["human_score"], human["score_final"]
            ),
            "scope_warning": (
                "The historical v3.1 human sample is not six-model representative; "
                "agreement estimates do not cover the missing model."
            ),
        },
        coverage,
    )


def _package_versions() -> dict[str, str | None]:
    packages = [
        "httpx",
        "numpy",
        "pandas",
        "scipy",
        "pingouin",
        "statsmodels",
        "matplotlib",
        "seaborn",
        "PyYAML",
        "pytest",
    ]
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _write_csv_with_json_lists(frame: pd.DataFrame, path: Path) -> None:
    serializable = frame.copy()
    for column in serializable.columns:
        if serializable[column].map(lambda value: isinstance(value, list)).any():
            serializable[column] = serializable[column].map(
                lambda value: json.dumps(value) if isinstance(value, list) else value
            )
    serializable.to_csv(path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/reproduction/v3.1-publication"),
    )
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    root = args.project_root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    main_db = root / "data/snap_poc_v3_1.db"
    validation_db = root / "data/snap_poc_v3_1_human_validation_clean.db"
    responses = _read_sqlite(main_db, "SELECT * FROM responses ORDER BY id")
    responses["score_numeric"] = responses["score_final"].map(SCORE_MAP)
    numeric = responses[
        (responses["is_error"] == 0) & responses["score_numeric"].notna()
    ].copy()

    campaign = _campaign_summary(responses)
    expected_models = sorted(responses["model"].unique().tolist())
    human_summary, human_coverage = _human_validation_summary(
        validation_db, expected_models
    )
    judge_pairs = responses[
        responses["score_judge1"].notna() & responses["score_judge2"].notna()
    ]
    judge_agreement = _agreement_summary(
        judge_pairs["score_judge1"], judge_pairs["score_judge2"]
    )
    split_half = _split_half_metrics(numeric, args.bootstrap, args.seed)
    cross_sp = _cross_sp_metrics(numeric, args.bootstrap, args.seed)

    assertions = {
        "response_count_is_2700": campaign["response_count"] == 2700,
        "trial_ids_are_unique": campaign["distinct_trial_ids"] == 2700,
        "all_responses_are_non_error": campaign["non_error_count"] == 2700,
        "all_responses_have_final_scores": campaign["final_score_count"] == 2700,
        "six_models_have_450_rows_each": len(campaign["per_model"]) == 6
        and all(row["responses"] == 450 for row in campaign["per_model"]),
        "interjudge_kappa_matches_archived_value": math.isclose(
            float(judge_agreement["unweighted_kappa"]),
            0.7509073105,
            rel_tol=0,
            abs_tol=1e-10,
        ),
        "historical_human_sample_covers_all_models": not human_summary[
            "missing_models"
        ],
    }

    fingerprints = {
        relative_path: _sha256(root / relative_path)
        for relative_path in FINGERPRINT_PATHS
    }
    report = {
        "analysis": "snap_v3_1_publication_reproduction",
        "script_version": "1.0",
        "seed": args.seed,
        "bootstrap_replicates": args.bootstrap,
        "campaign": campaign,
        "judge_agreement": judge_agreement,
        "human_validation": human_summary,
        "critical_cell_mistral_large_3_E2": _critical_cell_summary(
            numeric, args.bootstrap, args.seed
        ),
        "assertions": assertions,
        "interpretation_guardrails": [
            "Scores describe prompt-conditioned outputs, not intrinsic personality or values.",
            "System-prompt contrasts are exploratory because v3.1 was not preregistered for publication.",
            "Scenario, formulation, and temperature are confounded with the deterministic run schedule.",
            "Cluster-bootstrap intervals resample the 15 items and do not address model-version drift.",
            "The historical human-validation sample excludes Claude Sonnet 4.5.",
        ],
        "input_sha256": fingerprints,
        "environment": _package_versions(),
    }

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=False, default=_json_value)
        file_handle.write("\n")
    _write_csv_with_json_lists(split_half, output_dir / "split_half_by_model.csv")
    _write_csv_with_json_lists(cross_sp, output_dir / "cross_sp_robustness.csv")
    human_coverage.to_csv(output_dir / "human_validation_coverage.csv", index=False)

    manifest_lines = [
        f"{digest}  {relative_path}" for relative_path, digest in fingerprints.items()
    ]
    (output_dir / "input_manifest.sha256").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )

    print(json.dumps({"output_dir": str(output_dir), "assertions": assertions}, indent=2))
    return 0 if all(value for key, value in assertions.items() if key != "historical_human_sample_covers_all_models") else 1


if __name__ == "__main__":
    raise SystemExit(main())
