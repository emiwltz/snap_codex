"""Tests for POC decision reports."""

from __future__ import annotations

import json
from pathlib import Path

from src.db import ResponseRecord, SoulBenchDB
from src.decision import build_decision_report
from src.prompt_builder import load_configs


def _insert_passing_rows(db: SoulBenchDB) -> None:
    scores = ["+1", "0", "-1", "+1", "0", "-1"]
    for run, score in enumerate(scores, start=1):
        db.insert_response(
            ResponseRecord(
                model="test-model",
                item_id="O1",
                item_type="personality",
                scenario="base" if run % 2 else "variation",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.0,
                run=run,
                user_prompt_text="Prompt",
                raw_response="Response",
                score_judge1=score,
                score_judge2=score,
                score_final=score,
                agreement_status="agree",
            )
        )


def _write_stability_report(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "ok",
        "models": {
            "test-model": {
                "icc": 0.72,
                "test_retest_pearson": 0.75,
                "cross_sp_corr": {
                    "SP_ABS_vs_SP_DIR": 0.7,
                    "SP_ABS_vs_SP_PER": 0.68,
                    "SP_DIR_vs_SP_PER": 0.69,
                },
            }
        },
    }
    (output_dir / "stability_report.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_decision_not_ready_without_scored_rows(tmp_path: Path) -> None:
    bundle = load_configs("config")
    with SoulBenchDB(tmp_path / "snap.db") as db:
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=tmp_path / "reports",
        )

    assert report["decision"] == "NOT_READY"


def test_decision_passes_when_thresholds_are_met(tmp_path: Path) -> None:
    bundle = load_configs("config")
    reports_dir = tmp_path / "reports"
    _write_stability_report(reports_dir)

    with SoulBenchDB(tmp_path / "snap.db") as db:
        _insert_passing_rows(db)
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=reports_dir,
        )

    assert report["decision"] == "PASS"
    assert all(check["status"] == "pass" for check in report["checks"])
