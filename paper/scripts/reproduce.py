#!/usr/bin/env python3
"""Offline manuscript evidence: consistent backups, aggregate outputs, frozen gates.

Run from any directory with the repository's analysis dependencies installed.
Does not run collection/scoring. Raw text is read only
for equality checks and is never serialized to the manuscript results.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(PAPER / "private/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(PAPER / "private/cache"))
os.environ.setdefault("MPLBACKEND", "Agg")


def no_network(*args, **kwargs):
    raise RuntimeError("Network access is disabled in manuscript reproduction")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
import matplotlib.pyplot as plt

from src.db import SoulBenchDB
from src.analyzer import Analyzer
from src.decision import build_decision_report
from src.prompt_builder import load_configs, load_items, build_user_prompt
from src.scorer import compute_kappa
from scripts import reproduce_preliminary as prior


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(value, indent=2, default=prior._json_value, allow_nan=False) + "\n"
    )


def readonly(path):
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def backup(source, destination):
    with readonly(source) as src, sqlite3.connect(destination) as dest:
        src.backup(dest)
        assert dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def independent_icc2(matrix):
    """ANOVA ICC(2,1), complete targets x runs; no imputation or deletion."""
    x = np.asarray(matrix, dtype=float)
    if not np.isfinite(x).all():
        return None
    n, k = x.shape
    grand = x.mean()
    ms_targets = k * np.square(x.mean(1) - grand).sum() / (n - 1)
    ms_runs = n * np.square(x.mean(0) - grand).sum() / (k - 1)
    error = x - x.mean(1)[:, None] - x.mean(0)[None, :] + grand
    ms_error = np.square(error).sum() / ((n - 1) * (k - 1))
    return float(
        (ms_targets - ms_error)
        / (ms_targets + (k - 1) * ms_error + k * (ms_runs - ms_error) / n)
    )


def compare(a, b, path="", tolerance=1e-8):
    """Recursive numeric comparison; only volatile generation timestamps ignored."""
    differences = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key == "generated_at":
                continue
            differences += compare(a.get(key), b.get(key), path + "/" + key, tolerance)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            differences.append({"path": path, "kind": "length"})
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                differences += compare(x, y, path + f"/{i}", tolerance)
    elif isinstance(a, (float, int)) and isinstance(b, (float, int)):
        if not np.isclose(a, b, rtol=tolerance, atol=tolerance):
            differences.append({"path": path, "archived": a, "recomputed": b})
    elif a != b:
        differences.append({"path": path, "archived": a, "recomputed": b})
    return differences


def figure_outputs(cross, reliability, means, coverage, out):
    out.mkdir(parents=True, exist_ok=True)
    labels = {
        "claude-sonnet-4-5": "Claude Sonnet 4.5",
        "gemini-3-pro": "Gemini 3.1 Pro",
        "gpt-5-2": "GPT 5.2",
        "grok-4-3": "Grok 4.3",
        "mistral-large-3": "Mistral Large 3",
        "qwen3-max": "Qwen3 Max",
    }
    colors = ["#356078", "#9f6534", "#8b3850"]
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
            "font.family": "DejaVu Sans",
        }
    )
    fig, axes = plt.subplots(
        1, 3, figsize=(10.5, 4.4), sharey=True, layout="constrained"
    )
    for ax, (a, b), color in zip(axes, prior.SYSTEM_PROMPT_PAIRS, colors):
        rows = cross[cross.pair == f"{a}_vs_{b}"].set_index("model").loc[list(labels)]
        for y, (_, row) in enumerate(rows.iterrows()):
            lo, hi = row.pearson_item_run_95ci_item_cluster_bootstrap
            ax.plot([lo, hi], [y, y], color=color, linewidth=2)
            ax.plot(row.pearson_item_run, y, "o", color=color)
        ax.axvline(0.6, color="#777777", ls="--", lw=1)
        ax.set_xlim(-0.25, 1.02)
        ax.set_title(f"{a[3:]} vs {b[3:]}", fontsize=12)
        ax.set_xlabel("Pearson r")
        ax.set_yticks(range(6), list(labels.values()))
        ax.grid(axis="x", alpha=0.15)
    axes[0].invert_yaxis()
    fig.suptitle("Cross-prompt association across matched item-run scores", fontsize=14)
    fig.savefig(out / "cross_prompt.png", dpi=240)
    fig.savefig(out / "cross_prompt.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True, layout="constrained")
    for y, row in reliability.iterrows():
        axes[0].plot(row.split_half, y, "o", color=colors[0])
        if pd.notna(row.icc2):
            axes[1].plot(row.icc2, y, "o", color=colors[2])
        else:
            axes[1].text(0.12, y, "Not computable", va="center", fontsize=9)
    for ax, title in zip(
        axes, ["Correlation of half means", "Single-measure ICC(2,1)"]
    ):
        ax.set_xlim(0, 1.02)
        ax.axvline(0.6, color="#777777", ls="--", lw=1)
        ax.set_title(title)
        ax.set_yticks(range(6), list(labels.values()))
        ax.grid(axis="x", alpha=0.15)
    axes[0].invert_yaxis()
    fig.savefig(out / "reliability.png", dpi=240)
    fig.savefig(out / "reliability.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), layout="constrained")
    e2 = means[means.item_id == "E2"]
    for i, sp in enumerate(["SP_ABS", "SP_DIR", "SP_PER"]):
        scores = e2[e2.system_prompt == sp].set_index("model").loc[list(labels)]
        axes[0].plot(
            scores["mean"],
            np.arange(6) + (i - 1) * 0.17,
            "o",
            color=colors[i],
            label=sp[3:],
        )
    axes[0].set_yticks(range(6), list(labels.values()))
    axes[0].invert_yaxis()
    axes[0].set_xlim(-1.08, 1.08)
    axes[0].set_title("E2: mean coded initiative")
    axes[0].set_xlabel("-1 receptive  /  +1 initiative")
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8)
    axes[0].grid(axis="x", alpha=0.15)
    counts = coverage.set_index("model").loc[list(labels)].n_human_coded
    axes[1].barh(range(6), counts, color=colors[0])
    axes[1].set_yticks(range(6), list(labels.values()))
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, 53)
    axes[1].set_title("Historical validation coverage")
    axes[1].set_xlabel("Rows labelled human_validation")
    for y, n in enumerate(counts):
        axes[1].text(n + 1, y, str(n), va="center")
    fig.savefig(out / "diagnostics.png", dpi=240)
    fig.savefig(out / "diagnostics.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--output-dir", type=Path, default=PAPER / "results")
    args = parser.parse_args()
    if args.bootstrap < 1000:
        parser.error("Use at least 1000 bootstrap replicates for review artifacts")
    out = args.output_dir.resolve()
    if (
        out == ROOT
        or out == PAPER
        or not out.is_relative_to(PAPER)
        or out.is_relative_to(PAPER / "private")
    ):
        parser.error("Use a dedicated results directory under paper/, outside private/")
    out.mkdir(parents=True, exist_ok=True)
    (PAPER / "private").mkdir(exist_ok=True)
    files = [ROOT / p for p in prior.FINGERPRINT_PATHS]
    files += sorted((ROOT / "config").glob("*.yaml"))
    files += sorted((ROOT / "outputs/reports").glob("*.json"))
    files += sorted((ROOT / "outputs/reports").glob("*.csv"))
    files += sorted((ROOT / "src").glob("*.py")) + [
        ROOT / "scripts/reproduce_preliminary.py",
        Path(__file__),
    ]
    before = {str(p.relative_to(ROOT)): sha(p) for p in files}
    with tempfile.TemporaryDirectory(
        prefix="manuscript-", dir=PAPER / "private"
    ) as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / "config", tmp / "config")
        for name in ["snap_poc_v3_1.db", "snap_poc_v3_1_human_validation_clean.db"]:
            backup(ROOT / "data" / name, tmp / name)
        dbpath = tmp / "snap_poc_v3_1.db"
        humanpath = tmp / "snap_poc_v3_1_human_validation_clean.db"
        snapshot_hashes = {p.name: sha(p) for p in [dbpath, humanpath]}
        with readonly(dbpath) as conn, readonly(humanpath) as human_conn:
            # Full rows stay in memory solely to audit exact cross-source fidelity.
            raw = pd.read_sql_query("SELECT * FROM responses ORDER BY id", conn)
            validation_raw = pd.read_sql_query(
                "SELECT * FROM responses ORDER BY id", human_conn
            )
            metadata = pd.read_sql_query(
                "SELECT model, model_version, start_time, end_time, randomization_seed FROM collection_metadata",
                conn,
            )
            human = pd.read_sql_query(
                "SELECT response_id,human_score FROM manual_verification WHERE source='human_validation' ORDER BY response_id",
                human_conn,
            )
            source_counts = pd.read_sql_query(
                "SELECT source,count(*) AS n FROM manual_verification GROUP BY source",
                human_conn,
            ).to_dict("records")
        bundle = load_configs(tmp / "config")
        items = {i["id"]: i for i in load_items(bundle)}
        schedule = {r["run"]: r for r in bundle.protocol["run_schedule"]}
        human_csv = pd.read_csv(ROOT / "data/manual_sample_coded.csv", dtype=str)
        human_csv["response_id"] = human_csv.response_id.astype(int)
        merged = human.merge(
            human_csv, on="response_id", suffixes=("_db", "_csv"), validate="one_to_one"
        )
        checks = {
            "2700_unique_trials": len(raw) == 2700 and raw.trial_id.nunique() == 2700,
            "270_unique_model_item_prompt_cells_with_10_runs": len(
                raw.groupby(["model", "item_id", "system_prompt"])
            )
            == 270
            and raw.groupby(["model", "item_id", "system_prompt"])
            .run.nunique()
            .eq(10)
            .all(),
            "no_errors_or_unresolved_scores": raw.is_error.eq(0).all()
            and raw.score_final.notna().all()
            and raw.manual_review_needed.eq(0).all(),
            "human_database_responses_identical_to_campaign": raw.equals(
                validation_raw
            ),
            "csv_human_labels_equal_validation_database": len(merged)
            == len(human)
            == len(human_csv)
            == 200
            and merged.human_score_db.eq(merged.human_score_csv).all(),
            "stored_user_prompts_match_config": all(
                r.user_prompt_text
                == build_user_prompt(items[r.item_id], r.scenario, r.formulation)
                for r in raw.itertuples()
            ),
            "stored_system_prompts_match_config": all(
                ("" if pd.isna(r.system_prompt_text) else r.system_prompt_text).strip()
                == (
                    bundle.system_prompts["system_prompts"][r.system_prompt] or ""
                ).strip()
                for r in raw.itertuples()
            ),
            "run_schedule_matches_config": all(
                all(
                    getattr(r, k) == schedule[r.run][k]
                    for k in ["scenario", "formulation", "temperature"]
                )
                for r in raw.itertuples()
            ),
        }
        score_context = raw.set_index("id")
        checks["csv_response_text_model_and_final_score_match_campaign"] = all(
            all(
                str(row[k]) == str(score_context.loc[int(row.response_id), k])
                for k in [
                    "raw_response",
                    "model",
                    "item_id",
                    "system_prompt",
                    "score_final",
                ]
            )
            for _, row in human_csv.iterrows()
        )
        # Existing wrapper may migrate; only this disposable backup is opened.
        core = out / "core"
        with SoulBenchDB(dbpath) as db:
            analyzer = Analyzer(db, core)
            stability = analyzer.analyze_stability()
            sensitivity = analyzer.analyze_sensitivity()
            variance = analyzer.analyze_variance_decomposition()
            decision = build_decision_report(db, bundle, core)
            dump(core / "decision_report.json", decision)
        with SoulBenchDB(humanpath) as db:
            human_kappa = compute_kappa(db)
        dump(core / "human_kappa.json", human_kappa)
        print("Core analyses completed; computing descriptive uncertainty", flush=True)
        numeric = raw.assign(score_numeric=raw.score_final.map(prior.SCORE_MAP)).dropna(
            subset=["score_numeric"]
        )
        campaign = prior._campaign_summary(raw)
        judge = prior._agreement_summary(raw.score_judge1, raw.score_judge2)
        human_summary, coverage = prior._human_validation_summary(
            humanpath, sorted(raw.model.unique())
        )
        split = prior._split_half_metrics(numeric, args.bootstrap, prior.SEED)
        cross = prior._cross_sp_metrics(numeric, args.bootstrap, prior.SEED)
        means = (
            numeric.groupby(["model", "item_id", "system_prompt"])
            .score_numeric.agg(["mean", "count"])
            .reset_index()
        )
        reliability_rows = []
        for model, group in numeric.groupby("model"):
            matrix = group.pivot(
                index=["item_id", "system_prompt"],
                columns="run",
                values="score_numeric",
            )
            independent = independent_icc2(matrix)
            reported = stability["models"][model]["icc"]
            checks["independent_icc_matches_" + model] = (
                independent is None and reported is None
            ) or (
                independent is not None
                and reported is not None
                and np.isclose(independent, reported, atol=1e-10)
            )
            reliability_rows.append(
                {
                    "model": model,
                    "icc2": reported,
                    "independent_icc2": independent,
                    "split_half": stability["models"][model]["test_retest_pearson"],
                    "minimum_cross_sp": min(
                        stability["models"][model]["cross_sp_corr"].values()
                    ),
                }
            )
        reliability = pd.DataFrame(reliability_rows)
        comparison = {}
        for name, value in [
            ("stability", stability),
            ("sensitivity", sensitivity),
            ("variance_decomposition", variance),
            ("decision", decision),
        ]:
            historical = json.loads(
                (ROOT / f"outputs/reports/{name}_report.json").read_text()
            )
            comparison[name] = compare(historical, value)
        tests = [
            {"model": m, "factor": factor, "p_unadjusted": result["p_value"]}
            for m, vals in sensitivity["models"].items()
            for factor, result in vals.items()
            if result.get("p_value") is not None
        ]
        sens = pd.DataFrame(tests)
        sens["p_holm_all_17"] = multipletests(sens.p_unadjusted, method="holm")[1]
        changes = []
        for name, frame in [
            ("exclude_truncated", numeric[numeric.is_truncated == 0]),
            (
                "judge1_only",
                raw.assign(score_numeric=raw.score_judge1.map(prior.SCORE_MAP)).dropna(
                    subset=["score_numeric"]
                ),
            ),
            (
                "judge2_only",
                raw.assign(score_numeric=raw.score_judge2.map(prior.SCORE_MAP)).dropna(
                    subset=["score_numeric"]
                ),
            ),
        ]:
            for model, group in frame.groupby("model"):
                pivot = group.pivot(
                    index=["item_id", "run"],
                    columns="system_prompt",
                    values="score_numeric",
                )
                for a, b in prior.SYSTEM_PROMPT_PAIRS:
                    pair = pivot[[a, b]].dropna()
                    changes.append(
                        {
                            "analysis": name,
                            "model": model,
                            "pair": f"{a}_vs_{b}",
                            "n_pairs": len(pair),
                            "pearson": prior._safe_pearson(pair[a], pair[b]),
                        }
                    )
        checks["historical_gate_reproduces_FAIL"] = (
            decision["decision"] == "FAIL"
            and decision["campaign_completion"]["status"] == "complete"
        )
        checks["interjudge_kappa_reproduced"] = np.isclose(
            judge["unweighted_kappa"], 0.7509073105151067, atol=1e-12
        )
        checks["all_reference_inputs_unchanged"] = all(
            sha(ROOT / p) == h for p, h in before.items()
        )
        for name, frame in [
            ("cross_sp", cross),
            ("split_half", split),
            ("reliability", reliability),
            ("item_prompt_means", means),
            ("human_coverage", coverage),
            ("sensitivity_multiplicity", sens),
            ("sensitivity_scoring_truncation", pd.DataFrame(changes)),
            ("model_metadata", metadata),
            ("run_schedule", pd.DataFrame(bundle.protocol["run_schedule"])),
        ]:
            prior._write_csv_with_json_lists(frame, out / f"{name}.csv")
        dump(
            out / "audit.json",
            {
                "checks": {k: bool(v) for k, v in checks.items()},
                "known_limitations": {
                    "human_covers_all_models": False,
                    "human_coder_identity_and_independence_verified": False,
                    "preregistration_timestamp_verified": False,
                    "resolved_model_versions_recorded": bool(
                        metadata.model_version.notna().all()
                    ),
                },
                "human_source_counts": source_counts,
                "input_sha256": before,
                "consistent_backup_sha256_before_migration": snapshot_hashes,
                "archived_comparison_tolerance": 1e-8,
                "archived_comparison": comparison,
                "environment": {
                    d.metadata["Name"]: d.version
                    for d in importlib.metadata.distributions()
                },
                "python": sys.version,
                "network": "disabled by socket guard",
            },
        )
        truncation = raw[raw.is_truncated == 1]
        dump(
            out / "metrics.json",
            {
                "seed": prior.SEED,
                "bootstrap_replicates": args.bootstrap,
                "campaign": campaign,
                "score_counts": raw.score_final.value_counts().to_dict(),
                "agreement_status_counts": raw.agreement_status.value_counts().to_dict(),
                "truncation": {
                    "count": len(truncation),
                    "completion_tokens": truncation.completion_tokens.value_counts().to_dict(),
                    "agreement_status": truncation.agreement_status.value_counts().to_dict(),
                },
                "judge_agreement": judge,
                "human_validation": human_summary,
                "critical_cell": prior._critical_cell_summary(
                    numeric, args.bootstrap, prior.SEED
                ),
                "minimum_cross_sp": cross.pearson_item_run.min(),
                "variance_eta_squared": variance["factors"],
            },
        )
        figure_outputs(cross, reliability, means, coverage, out / "figures")
        print(
            json.dumps(
                {
                    "checks": {k: bool(v) for k, v in checks.items()},
                    "archived_differences": {k: len(v) for k, v in comparison.items()},
                    "decision": decision["decision"],
                },
                indent=2,
            )
        )
        if not all(checks.values()):
            raise SystemExit(
                "Evidence audit failed; inspect audit.json before writing conclusions"
            )


if __name__ == "__main__":
    main()
