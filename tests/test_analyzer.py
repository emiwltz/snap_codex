"""Tests for analyzer skeleton behavior."""

from __future__ import annotations

from pathlib import Path

from src.analyzer import (
    analyze_sensitivity,
    analyze_stability,
    analyze_variance_decomposition,
)
from src.db import ResponseRecord, SoulBenchDB


def _insert_synthetic_scored_data(db: SoulBenchDB) -> None:
    item_ids = ["O1", "O2", "M_CH"]
    item_types = {"O1": "personality", "O2": "personality", "M_CH": "moral"}
    scores = ["-1", "0", "+1"]

    run_idx = 0
    for item_id in item_ids:
        for scenario in ["base", "variation"]:
            for formulation in ["F1", "F2", "F3"]:
                for system_prompt in ["SP_ABS", "SP_DIR", "SP_PER"]:
                    for temperature in [0.1, 1.0]:
                        for run in [1, 2]:
                            run_idx += 1
                            score = scores[(run_idx + run) % 3]
                            db.insert_response(
                                ResponseRecord(
                                    model="test-model",
                                    item_id=item_id,
                                    item_type=item_types[item_id],
                                    scenario=scenario,
                                    formulation=formulation,
                                    system_prompt=system_prompt,
                                    temperature=temperature,
                                    run=run,
                                    user_prompt_text="Scenario\n\nQuestion",
                                    raw_response="Response",
                                    score_final=score,
                                )
                            )


def test_analyze_stability_empty_db(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        report = analyze_stability(db=db, output_dir=output_dir)

    assert report["status"] == "empty"
    assert (output_dir / "stability_report.json").exists()


def test_analyze_suites_non_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        _insert_synthetic_scored_data(db)
        stability = analyze_stability(db=db, output_dir=output_dir)
        sensitivity = analyze_sensitivity(db=db, output_dir=output_dir)
        variance = analyze_variance_decomposition(db=db, output_dir=output_dir)

    assert stability["status"] == "ok"
    assert sensitivity["status"] == "ok"
    assert variance["status"] == "ok"

    assert (output_dir / "stability_report.json").exists()
    assert (output_dir / "sensitivity_report.json").exists()
    assert (output_dir / "variance_decomposition_report.json").exists()
