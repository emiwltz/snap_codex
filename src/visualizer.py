"""Visualization skeletons for SoulBench SNAP pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .db import SoulBenchDB

LOGGER = logging.getLogger(__name__)


def _empty_figure(output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center")
    ax.set_title(title)
    ax.axis("off")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _score_df(db: SoulBenchDB) -> pd.DataFrame:
    return db.get_numeric_scores_dataframe()


def plot_big_five_radar(
    db: SoulBenchDB,
    output_dir: str | Path = "outputs/figures",
) -> list[str]:
    """Generate one radar chart per model for Big Five profile."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = _score_df(db)

    if df.empty:
        out = out_dir / "radar_empty.png"
        _empty_figure(out, "Big Five Radar")
        return [str(out)]

    personality = df[df["item_type"] == "personality"].copy()
    if personality.empty:
        out = out_dir / "radar_empty.png"
        _empty_figure(out, "Big Five Radar")
        return [str(out)]

    personality["trait"] = personality["item_id"].astype(str).str[0].map(
        {
            "O": "Openness",
            "C": "Conscientiousness",
            "E": "Extraversion",
            "A": "Agreeableness",
            "N": "Neuroticism",
        }
    )

    output_paths: list[str] = []
    traits = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
    angles = np.linspace(0, 2 * np.pi, len(traits), endpoint=False).tolist()
    angles += angles[:1]

    for model, group in personality.groupby("model"):
        means = group.groupby("trait")["score_numeric"].mean().reindex(traits).fillna(0.0)
        values = means.tolist()
        values += values[:1]

        fig = plt.figure(figsize=(6, 6))
        ax = plt.subplot(111, polar=True)
        ax.plot(angles, values, linewidth=2)
        ax.fill(angles, values, alpha=0.2)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(traits)
        ax.set_title(f"Big Five Radar - {model}")

        output_path = out_dir / f"radar_{model}.png"
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        output_paths.append(str(output_path))

    return output_paths


def plot_scores_heatmap(
    db: SoulBenchDB,
    output_file: str | Path = "outputs/figures/scores_heatmap.png",
) -> str:
    """Generate heatmap of mean scores by model and item."""
    out = Path(output_file)
    df = _score_df(db)
    if df.empty:
        _empty_figure(out, "Scores Heatmap")
        return str(out)

    pivot = df.pivot_table(index="model", columns="item_id", values="score_numeric", aggfunc="mean")
    if pivot.empty:
        _empty_figure(out, "Scores Heatmap")
        return str(out)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(pivot, cmap="coolwarm", center=0, annot=False, ax=ax)
    ax.set_title("Mean Score Heatmap (Model x Item)")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_stability_boxplots(
    db: SoulBenchDB,
    output_file: str | Path = "outputs/figures/stability_boxplots.png",
) -> str:
    """Generate run-wise score distribution boxplots by model."""
    out = Path(output_file)
    df = _score_df(db)
    if df.empty:
        _empty_figure(out, "Stability Boxplots")
        return str(out)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=df, x="run", y="score_numeric", hue="model", ax=ax)
    ax.set_title("Score Distribution by Run")
    ax.legend(loc="best", fontsize=8)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_variance_bar(
    db: SoulBenchDB,
    output_file: str | Path = "outputs/figures/variance_eta_squared.png",
) -> str:
    """Generate eta-squared bar chart approximation for H4."""
    out = Path(output_file)
    df = _score_df(db)
    if df.empty:
        _empty_figure(out, "Variance Decomposition")
        return str(out)

    factors = ["model", "system_prompt", "temperature", "scenario", "formulation", "item_id", "run"]
    eta_values: dict[str, float] = {}

    grand_mean = float(df["score_numeric"].mean())
    ss_total = float(((df["score_numeric"] - grand_mean) ** 2).sum())

    for factor in factors:
        if ss_total <= 0:
            eta_values[factor] = 0.0
            continue
        grouped = df.groupby(factor)["score_numeric"]
        ss_between = 0.0
        for _, values in grouped:
            n = len(values)
            if n == 0:
                continue
            ss_between += n * ((float(values.mean()) - grand_mean) ** 2)
        eta_values[factor] = float(ss_between / ss_total)

    fig, ax = plt.subplots(figsize=(10, 4))
    x_values = list(eta_values.keys())
    y_values = [eta_values[f] for f in x_values]
    ax.bar(x_values, y_values)
    ax.set_title("Eta Squared by Factor (Approximation)")
    ax.set_ylabel("eta^2")
    ax.tick_params(axis="x", rotation=45)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_cross_temperature_profiles(
    db: SoulBenchDB,
    output_file: str | Path = "outputs/figures/cross_temperature_profiles.png",
) -> str:
    """Generate overlay profiles for temperatures 0.1 vs 1.0."""
    out = Path(output_file)
    df = _score_df(db)
    if df.empty:
        _empty_figure(out, "Cross Temperature Profiles")
        return str(out)

    profile = df.groupby(["model", "item_id", "temperature"], as_index=False)["score_numeric"].mean()
    if profile.empty:
        _empty_figure(out, "Cross Temperature Profiles")
        return str(out)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.lineplot(
        data=profile,
        x="item_id",
        y="score_numeric",
        hue="model",
        style="temperature",
        markers=True,
        dashes=True,
        ax=ax,
    )
    ax.set_title("Cross-Temperature Profiles")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_cross_sp_profiles(
    db: SoulBenchDB,
    output_file: str | Path = "outputs/figures/cross_sp_profiles.png",
) -> str:
    """Generate overlay profiles for SP_ABS/SP_DIR/SP_PER."""
    out = Path(output_file)
    df = _score_df(db)
    if df.empty:
        _empty_figure(out, "Cross SP Profiles")
        return str(out)

    profile = df.groupby(["model", "item_id", "system_prompt"], as_index=False)["score_numeric"].mean()
    if profile.empty:
        _empty_figure(out, "Cross SP Profiles")
        return str(out)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.lineplot(
        data=profile,
        x="item_id",
        y="score_numeric",
        hue="model",
        style="system_prompt",
        markers=True,
        dashes=True,
        ax=ax,
    )
    ax.set_title("Cross-SP Profiles")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def generate_all(
    db: SoulBenchDB,
    output_dir: str | Path = "outputs/figures",
) -> dict[str, Any]:
    """Generate all required figure families."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "radar": plot_big_five_radar(db=db, output_dir=out_dir),
        "heatmap": plot_scores_heatmap(db=db, output_file=out_dir / "scores_heatmap.png"),
        "boxplots": plot_stability_boxplots(db=db, output_file=out_dir / "stability_boxplots.png"),
        "variance_bar": plot_variance_bar(db=db, output_file=out_dir / "variance_eta_squared.png"),
        "cross_temperature": plot_cross_temperature_profiles(
            db=db,
            output_file=out_dir / "cross_temperature_profiles.png",
        ),
        "cross_sp": plot_cross_sp_profiles(
            db=db,
            output_file=out_dir / "cross_sp_profiles.png",
        ),
    }
    LOGGER.info("Generated visualizations in %s", out_dir)
    return results
