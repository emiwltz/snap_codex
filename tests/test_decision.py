"""Tests for POC decision reports."""

from __future__ import annotations

import json
from pathlib import Path

from src.db import ResponseRecord, SoulBenchDB
from src.decision import build_decision_report
from src.prompt_builder import load_configs


def _single_model_bundle():
    bundle = load_configs("config")
    bundle.models["models"] = [
        {
            "id": "test-model",
            "label": "Test Model",
            "openrouter_model_id": "test/model",
            "provider": "Test",
            "thinking_mode": "not_available",
            "active": True,
        }
    ]
    bundle.protocol["system_prompts"] = ["SP_ABS"]
    bundle.protocol["run_schedule"] = [
        {
            "run": run,
            "scenario": "base" if run % 2 else "variation",
            "formulation": "F1",
            "temperature": 0.0,
        }
        for run in range(1, 7)
    ]
    bundle.items_personality["items"] = [bundle.items_personality["items"][0]]
    bundle.items_moral["items"] = []
    return bundle


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


def _insert_complete_collection_metadata(db: SoulBenchDB) -> None:
    db.upsert_collection_metadata(
        model="test-model",
        total_planned=6,
        randomization_seed="123",
        thinking_mode="not_available",
        api_endpoint="https://example.test",
        dataset_id="snap_poc_v3_1_2026-04",
        protocol_version="3.1",
        items_version="items_v1_2026-04",
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
    bundle = _single_model_bundle()
    with SoulBenchDB(tmp_path / "snap.db") as db:
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=tmp_path / "reports",
        )

    assert report["decision"] == "NOT_READY"


def test_decision_not_ready_when_campaign_is_incomplete(tmp_path: Path) -> None:
    bundle = _single_model_bundle()
    reports_dir = tmp_path / "reports"
    _write_stability_report(reports_dir)

    with SoulBenchDB(tmp_path / "snap.db") as db:
        _insert_passing_rows(db)
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=reports_dir,
        )

    assert report["decision"] == "NOT_READY"
    assert report["campaign_completion"]["status"] == "incomplete"
    assert report["campaign_completion"]["incomplete_models"] == ["test-model"]
    reasons = report["campaign_completion"]["models"]["test-model"]["reasons"]
    assert "missing_collection_metadata" in reasons


def test_decision_passes_when_thresholds_are_met(tmp_path: Path) -> None:
    bundle = _single_model_bundle()
    reports_dir = tmp_path / "reports"
    _write_stability_report(reports_dir)

    with SoulBenchDB(tmp_path / "snap.db") as db:
        _insert_passing_rows(db)
        _insert_complete_collection_metadata(db)
        report = build_decision_report(
            db=db,
            bundle=bundle,
            reports_dir=reports_dir,
        )

    assert report["decision"] == "PASS"
    assert report["campaign_completion"]["status"] == "complete"
    assert all(check["status"] == "pass" for check in report["checks"])
