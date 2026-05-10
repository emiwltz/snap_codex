"""Tests for preflight checks."""

from __future__ import annotations

from pathlib import Path

from src.preflight import build_preflight_report
from src.prompt_builder import load_configs


def _catalog_for_config() -> list[dict[str, object]]:
    bundle = load_configs("config")
    ids = [
        model["openrouter_model_id"]
        for model in bundle.models["models"]
        if model.get("active", True)
    ]
    ids.extend(
        judge["openrouter_model_id"] for judge in bundle.models["judges"].values()
    )
    return [
        {
            "id": model_id,
            "name": model_id,
            "context_length": 200000,
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            "top_provider": {"max_completion_tokens": 8192},
            "supported_parameters": ["max_tokens", "temperature", "top_p"],
        }
        for model_id in ids
    ]


def test_preflight_report_estimates_cost_and_model_availability(
    tmp_path: Path,
) -> None:
    bundle = load_configs("config")
    report = build_preflight_report(
        bundle=bundle,
        catalog=_catalog_for_config(),
        db_path=tmp_path / "snap.db",
        catalog_source="https://example.test/models",
        expected_response_tokens=100,
        scoring_completion_tokens=32,
    )

    assert report["status"] == "ok"
    assert report["catalog_source"] == "https://example.test/models"
    assert len(report["model_checks"]) == 8
    assert all(check["status"] == "available" for check in report["model_checks"])
    assert report["database"]["clean_for_v31"] is True
    assert report["cost_estimate"]["expected"]["total"] > 0
    assert report["cost_estimate"]["max_budget"]["total"] >= (
        report["cost_estimate"]["expected"]["total"]
    )


def test_preflight_blocks_missing_configured_model(tmp_path: Path) -> None:
    bundle = load_configs("config")
    catalog = _catalog_for_config()[1:]

    report = build_preflight_report(
        bundle=bundle,
        catalog=catalog,
        db_path=tmp_path / "snap.db",
    )

    assert report["status"] == "blocked"
    assert report["blocking_issues"]


def test_preflight_accepts_configured_disabled_parameters(tmp_path: Path) -> None:
    bundle = load_configs("config")
    catalog = _catalog_for_config()
    for entry in catalog:
        if entry["id"] == "openai/gpt-5.2":
            entry["supported_parameters"] = ["max_tokens"]

    report = build_preflight_report(
        bundle=bundle,
        catalog=catalog,
        db_path=tmp_path / "snap.db",
    )

    gpt_check = next(
        check
        for check in report["model_checks"]
        if check["configured_id"] == "openai/gpt-5.2"
    )
    warning_text = "\n".join(report["warnings"])

    assert report["status"] == "ok"
    assert gpt_check["request_policy"]["omitted_missing_parameters"] == [
        "temperature",
        "top_p",
    ]
    assert "openai/gpt-5.2 does not advertise collection parameters" not in warning_text
