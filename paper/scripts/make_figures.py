"""Render the publication figures of the SNAP v3.1 article from aggregates.

Inputs are aggregate files only, never the raw databases:

- a reproduction directory written by ``scripts/reproduce.py`` (``metrics.json``,
  ``core/decision_report.json``, ``reliability.csv``, ``cross_sp.csv``);
- the item-level judge agreement table (``paper/review/item_agreement.csv``),
  written by ``paper/scripts/audit_diagnostics.py``.

Each figure carries one idea and is written as PDF (vector, for the article)
and PNG (reading copy), together with the CSV of the values it plots.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

MODELS = {
    "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "gemini-3-pro": "Gemini 3.1 Pro",
    "gpt-5-2": "GPT-5.2",
    "grok-4-3": "Grok 4.3",
    "mistral-large-3": "Mistral Large 3",
    "qwen3-max": "Qwen3 Max",
}
PAIRS = {
    "SP_ABS_vs_SP_DIR": "No system prompt vs neutral",
    "SP_ABS_vs_SP_PER": "No system prompt vs persona",
    "SP_DIR_vs_SP_PER": "Neutral vs persona",
}
INK = "#222222"
MUTED = "#8a8a8a"
PASS = "#356078"
FAIL = "#b23a48"
SCORE_COLORS = {"-1": "#9f6534", "0": "#c9c9c9", "+1": "#356078", "REFUS": "#222222"}


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
        }
    )


def save(fig, out: Path, name: str, data: pd.DataFrame) -> None:
    fig.savefig(out / f"{name}.pdf")
    fig.savefig(out / f"{name}.png", dpi=220)
    plt.close(fig)
    data.to_csv(out / f"{name}.csv", index=False)


def box(ax, x, y, w, h, title, body, color=INK, fill="#f4f4f4"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.015",
            linewidth=1.0, edgecolor=color, facecolor=fill,
        )
    )
    ax.text(x + 0.015, y + h - 0.03, title, weight="bold", va="top", color=color)
    ax.text(x + 0.012, y + h - 0.12, body, va="top", fontsize=7.8, color=INK,
            linespacing=1.4)


def arrow(ax, x0, x1, y):
    ax.annotate("", (x1, y), (x0, y),
                arrowprops={"arrowstyle": "-|>", "color": MUTED, "lw": 1.2})


def figure_design(metrics: dict, decision: dict, out: Path) -> None:
    """Fig. 1: the unit of analysis is a coded response under a condition."""
    status = metrics["agreement_status_counts"]
    scores = metrics["score_counts"]
    n = metrics["campaign"]["response_count"]
    verdict = decision["decision"]
    checks = {c["metric"]: c["status"] == "pass" for c in decision["checks"]}
    mark = {True: "✓", False: "✗"}
    fig, ax = plt.subplots(figsize=(10.5, 1.95))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.98, bottom=0.02)
    ax.set_axis_off()
    ax.set_xlim(-0.005, 1.005)
    ax.set_ylim(0, 1)
    w, h, y = 0.225, 0.92, 0.04
    xs = [0.0, 0.258, 0.516, 0.775]
    box(ax, xs[0], y, w, h, "1. Condition",
        "15 free-form items\n(10 personality, 5 moral)\n× 3 system conditions:\n"
        "   none, neutral, persona\n× 10 scheduled runs rotating\n"
        "   scenario, wording and\n   nominal temperature")
    box(ax, xs[1], y, w, h, "2. Response",
        f"6 model endpoints\nvia OpenRouter, May 2026\n\n= {n:,} single-turn responses\n\n"
        "Runs differ by design:\nnot identical repetitions")
    box(ax, xs[2], y, w, h, "3. Coding",
        "2 LLM judges (Claude Haiku 4.5,\nKimi K2.5), item-specific poles\n"
        "+1 / 0 / −1 / REFUS\n\n"
        f"agree {status['agree']:,} · adjacent → 0: {status['minor_disagree']}\n"
        f"manual adjudication: {status['manual_adjudicated']}\n"
        f"final: +1 {scores['+1']} · 0 {scores['0']:,} · −1 {scores['-1']}")
    color = FAIL if verdict == "FAIL" else PASS
    box(ax, xs[3], y, w, h, f"4. Pre-set checks → {verdict}",
        f"{mark[checks['kappa_interjudge']]} judge agreement (κ)\n"
        f"{mark[checks['refusal_rate']]} refusal rate\n"
        f"{mark[checks['initial_major_disagreement_rate']]} major disagreement rate\n"
        f"{mark[checks['minimum_model_test_retest_pearson']]} split-half correlation\n"
        f"{mark[checks['minimum_model_icc']]} single-measure ICC(2,1)\n"
        f"{mark[checks['minimum_cross_sp_corr']]} cross-prompt correlation",
        color=color, fill="#fbf1f2" if verdict == "FAIL" else "#eef3f6")
    for a, b in zip(xs, xs[1:]):
        arrow(ax, a + w + 0.002, b - 0.002, y + h / 2)
    data = pd.DataFrame(
        [
            {"quantity": "responses", "value": n},
            *({"quantity": f"agreement_{k}", "value": v} for k, v in status.items()),
            *({"quantity": f"final_score_{k}", "value": v} for k, v in scores.items()),
            {"quantity": "decision", "value": verdict},
        ]
    )
    save(fig, out, "fig1_design", data)


def figure_verdict(decision: dict, reliability: pd.DataFrame, cross: pd.DataFrame,
                   out: Path) -> None:
    """Fig. 2: judges agree, but stability and robustness criteria fail."""
    checks = {c["metric"]: c for c in decision["checks"]}
    rel = reliability.set_index("model").loc[list(MODELS)]
    rows = [
        ("Judge agreement\n(Cohen's κ, pooled)", {"all responses": checks["kappa_interjudge"]["value"]},
         checks["kappa_interjudge"]["threshold_min"]),
        ("Split-half correlation\n(runs 1–5 vs 6–10)", rel.split_half.to_dict(),
         checks["minimum_model_test_retest_pearson"]["threshold_min"]),
        ("Single-measure ICC(2,1)\n(runs as raters)", rel.icc2.to_dict(),
         checks["minimum_model_icc"]["threshold_min"]),
        ("Lowest cross-prompt\ncorrelation per model", rel.minimum_cross_sp.to_dict(),
         checks["minimum_cross_sp_corr"]["threshold_min"]),
    ]
    fig, ax = plt.subplots(figsize=(8.2, 3.6), layout="constrained")
    records = []
    for i, (label, values, threshold) in enumerate(rows):
        ax.plot([threshold, threshold], [i - 0.35, i + 0.35], color=INK, lw=1.4)
        ax.text(threshold, i - 0.38, f"{threshold:.2f}", ha="center", va="bottom",
                fontsize=7, color=INK)
        for model, value in values.items():
            name = MODELS.get(model, model)
            if pd.isna(value):
                records.append({"criterion": label.replace("\n", " "), "model": name,
                                "value": None, "threshold": threshold, "status": "not computable"})
                continue
            ok = value >= threshold
            ax.plot(value, i, "o", ms=7, color=PASS if ok else FAIL,
                    markeredgecolor="white", markeredgewidth=0.6, zorder=3)
            records.append({"criterion": label.replace("\n", " "), "model": name,
                             "value": value, "threshold": threshold,
                             "status": "pass" if ok else "fail"})
        failed = [r for r in records if r["criterion"] == label.replace("\n", " ") and r["status"] == "fail"]
        verdict = f"{len(failed)} below" if failed else "all above"
        ax.text(1.03, i, verdict, va="center", fontsize=8.5,
                color=FAIL if failed else PASS, weight="bold")
    worst = cross.loc[cross.pearson_item_run.idxmin()]
    ax.annotate(f"{MODELS[worst.model]}, {PAIRS[worst.pair].lower()}:"
                f" r = {worst.pearson_item_run:.2f}",
                (worst.pearson_item_run, 3.08), (0.03, 3.42), fontsize=7.5, color=FAIL,
                va="center", arrowprops={"arrowstyle": "-", "color": FAIL, "lw": 0.7})
    ax.text(0.03, 2.0, "Claude: not computable", fontsize=8, color=MUTED, va="center")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_ylim(len(rows) - 0.3, -0.6)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Coefficient; black bar = pre-set minimum. Dots: one per model (pooled for κ)")
    ax.grid(axis="x", alpha=0.18)
    ax.set_title("Judges agree, but per-model stability and prompt robustness fall below threshold")
    ax.plot([], [], "o", color=PASS, label="at or above minimum")
    ax.plot([], [], "o", color=FAIL, label="below minimum")
    ax.legend(loc="center left", bbox_to_anchor=(0.0, 0.74), ncol=1, frameon=False, fontsize=8)
    save(fig, out, "fig2_verdict", pd.DataFrame(records))


def figure_cross_prompt(cross: pd.DataFrame, threshold: float, out: Path) -> None:
    """Fig. 3: robustness to system framing is uneven across models and pairs."""
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True, layout="constrained")
    below = 0
    for ax, (pair, title) in zip(axes, PAIRS.items()):
        sub = cross[cross.pair == pair].set_index("model").loc[list(MODELS)]
        for y, (model, row) in enumerate(sub.iterrows()):
            lo, hi = row.pearson_item_run_95ci_item_cluster_bootstrap
            ok = row.pearson_item_run >= threshold
            below += not ok
            color = PASS if ok else FAIL
            ax.plot([lo, hi], [y, y], color=color, lw=1.6, alpha=0.55)
            ax.plot(row.pearson_item_run, y, "o", color=color, ms=6, zorder=3)
        ax.axvline(threshold, color=INK, lw=1, ls=(0, (3, 2)))
        ax.set_title(title, fontsize=9.5)
        ax.set_xlim(-0.15, 1.0)
        ax.set_xlabel("Pearson r, matched item-run scores")
        ax.grid(axis="x", alpha=0.18)
    axes[0].set_yticks(range(len(MODELS)), list(MODELS.values()))
    axes[0].invert_yaxis()
    fig.suptitle(
        f"Changing the system prompt shifts response profiles: {below} of {len(cross)} "
        f"model-prompt pairs fall below r = {threshold:.2f}",
        x=0.01, ha="left", weight="bold", fontsize=10,
    )
    data = cross[["model", "pair", "n_item_run_pairs", "pearson_item_run",
                  "pearson_item_run_95ci_item_cluster_bootstrap"]].copy()
    data["model"] = data.model.map(MODELS)
    save(fig, out, "fig3_cross_prompt", data)


def item_labels() -> dict[str, str]:
    labels = {}
    for name, key in (("items_personality.yaml", "trait"), ("items_moral.yaml", "foundation")):
        for item in yaml.safe_load((ROOT / "config" / name).read_text())["items"]:
            labels[item["id"]] = f"{item['id']}  {item[key]}"
    return labels


def figure_items(items: pd.DataFrame, pooled_kappa: float, target: float, out: Path) -> None:
    """Fig. 4: pooled agreement hides item-level heterogeneity."""
    items = items.copy()
    items = items.sort_values("kappa", na_position="first").reset_index(drop=True)
    counts = items.final_counts.map(json.loads)
    labels = item_labels()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.5, 4.6), sharey=True,
                                 gridspec_kw={"width_ratios": [1.1, 1]}, layout="constrained")
    for y, row in items.iterrows():
        if pd.isna(row.kappa):
            ax.text(0.02, y, f"κ undefined: all {row.n} coded +1", va="center", fontsize=8,
                    color=MUTED)
            continue
        ok = row.kappa >= target
        ax.plot(row.kappa, y, "o", color=PASS if ok else FAIL, ms=6)
    ax.axvline(target, color=MUTED, lw=1, ls=(0, (1, 2)))
    ax.text(target - 0.01, -0.9, f"{target:.2f} target", fontsize=8, color=MUTED, ha="right")
    ax.axvline(pooled_kappa, color=INK, lw=1, ls=(0, (3, 2)))
    ax.text(pooled_kappa + 0.01, -0.9, f"pooled κ = {pooled_kappa:.2f}", fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Judge 1 vs judge 2, Cohen's κ per item")
    ax.set_yticks(range(len(items)), [labels.get(i, i) for i in items["item"]])
    ax.set_ylim(len(items) - 0.5, -1.4)
    ax.grid(axis="x", alpha=0.18)
    ax.set_title("Agreement per item")
    left = [0.0] * len(items)
    for code in ["-1", "0", "+1", "REFUS"]:
        share = [c.get(code, 0) / sum(c.values()) for c in counts]
        bx.barh(range(len(items)), share, left=left, color=SCORE_COLORS[code], label=code,
                height=0.72)
        left = [a + b for a, b in zip(left, share)]
    bx.set_xlim(0, 1)
    bx.set_xlabel("Share of final scores")
    bx.set_title("What the items record")
    bx.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, -0.2), frameon=False, fontsize=8)
    fig.suptitle("Pooled judge agreement hides weak or uninformative items",
                 x=0.01, ha="left", weight="bold", fontsize=10)
    data = items[["item", "n", "exact", "kappa"]].copy()
    for code in ["-1", "0", "+1", "REFUS"]:
        data[f"final_{code}"] = [c.get(code, 0) for c in counts]
    save(fig, out, "fig4_items", data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-dir", type=Path, required=True,
                        help="Output directory of scripts/reproduce.py")
    parser.add_argument("--items", type=Path, default=ROOT / "paper/review/item_agreement.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    res = args.results_dir
    metrics = json.loads((res / "metrics.json").read_text())
    decision = json.loads((res / "core/decision_report.json").read_text())
    reliability = pd.read_csv(res / "reliability.csv")
    cross = pd.read_csv(res / "cross_sp.csv")
    cross["pearson_item_run_95ci_item_cluster_bootstrap"] = cross[
        "pearson_item_run_95ci_item_cluster_bootstrap"].map(json.loads)
    items = pd.read_csv(args.items)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    style()
    threshold = decision["thresholds"]["cross_context_corr_min"]
    figure_design(metrics, decision, args.output_dir)
    figure_verdict(decision, reliability, cross, args.output_dir)
    figure_cross_prompt(cross, threshold, args.output_dir)
    figure_items(items, metrics["judge_agreement"]["unweighted_kappa"],
                 decision["thresholds"]["kappa_interjudge_target"], args.output_dir)


if __name__ == "__main__":
    main()
