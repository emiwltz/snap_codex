"""Tests for analyzer skeleton behavior."""

from __future__ import annotations

from pathlib import Path

from src.analyzer import (
    analyze_cross_sp_diagnostic,
    analyze_sensitivity,
    analyze_stability,
    analyze_variance_decomposition,
)
from src.db import ResponseRecord, SoulBenchDB
from src.prompt_builder import generate_conditions_for_model, load_configs

SCORES_BY_VALUE = {-1: "-1", 0: "0", 1: "+1"}


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


def _insert_full_v31_rotated_campaign(
    db: SoulBenchDB, temperature_applied: bool | None = None
) -> str:
    bundle = load_configs("config")
    model_id = "test-model-v31"
    conditions, _ = generate_conditions_for_model(model_id, bundle, seed=12345)
    item_order = {
        item["id"]: idx
        for idx, item in enumerate(
            bundle.items_personality["items"] + bundle.items_moral["items"]
        )
    }
    system_prompt_order = {"SP_ABS": 0, "SP_DIR": 1, "SP_PER": 2}

    for condition in conditions:
        item_idx = item_order[condition.item_id]
        sp_idx = system_prompt_order[condition.system_prompt]
        raw_value = (
            1
            if (item_idx + sp_idx + condition.run) % 3 == 0
            else -1 if (item_idx + 2 * sp_idx + 2 * condition.run) % 4 == 0 else 0
        )
        db.insert_response(
            ResponseRecord(
                dataset_id=condition.dataset_id,
                protocol_version=condition.protocol_version,
                items_version=condition.items_version,
                condition_block=condition.condition_block,
                trial_id=condition.trial_id,
                model=condition.model,
                item_id=condition.item_id,
                item_type=condition.item_type,
                scenario=condition.scenario,
                formulation=condition.formulation,
                system_prompt=condition.system_prompt,
                temperature=condition.temperature,
                run=condition.run,
                user_prompt_text=condition.user_prompt_text,
                raw_response="Synthetic v3.1 response",
                temperature_applied=temperature_applied,
                score_final=SCORES_BY_VALUE[raw_value],
            )
        )

    return model_id


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


def test_v31_rotated_stability_metrics_are_computable(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        model_id = _insert_full_v31_rotated_campaign(db)
        stability = analyze_stability(db=db, output_dir=output_dir)

    model_report = stability["models"][model_id]
    assert stability["n_rows_after_exclusions"] == 450
    assert model_report["icc_runs"]["status"] == "ok"
    assert model_report["icc_runs"]["eligible_targets"] == 45
    assert model_report["test_retest_pearson_split_half"]["status"] == "ok"
    assert model_report["test_retest_pearson_split_half"]["n_pairs"] == 45
    assert model_report["cross_temperature_corr"] is not None
    assert model_report["cross_sp_corr"]["SP_ABS_vs_SP_DIR"] is not None

    by_item = model_report["aggregation_levels"]["by_item"]["summary"]
    assert by_item["total"] == 15
    assert by_item["icc_computable"] == 15
    assert by_item["split_half_computable"] == 15

    by_group = model_report["aggregation_levels"]["by_trait_or_foundation"]["summary"]
    assert by_group["total"] == 10
    assert by_group["icc_computable"] == 10
    assert by_group["split_half_computable"] == 10


def test_v31_rotated_sensitivity_uses_item_sp_pairing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        model_id = _insert_full_v31_rotated_campaign(db)
        sensitivity = analyze_sensitivity(db=db, output_dir=output_dir)

    model_report = sensitivity["models"][model_id]
    scenario = model_report["scenario_effect_wilcoxon"]
    formulation = model_report["formulation_effect_friedman"]
    temperature = model_report["temperature_effect"]

    assert scenario["status"] == "ok"
    assert scenario["n_pairs"] == 45
    assert scenario["pairing_unit"] == ["item_id", "system_prompt"]

    assert formulation["status"] == "ok"
    assert formulation["n_pairs"] == 45
    assert formulation["pairing_unit"] == ["item_id", "system_prompt"]

    assert temperature["status"] == "ok"
    assert temperature["n_pairs"] == 45
    assert temperature["levels"] == [0.0, 0.5, 1.0]


def test_v31_temperature_effect_skips_models_without_temperature_parameter(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        model_id = _insert_full_v31_rotated_campaign(db, temperature_applied=False)
        stability = analyze_stability(db=db, output_dir=output_dir)
        sensitivity = analyze_sensitivity(db=db, output_dir=output_dir)

    assert stability["models"][model_id]["cross_temperature_corr"] is None
    request_parameters = stability["models"][model_id]["request_parameters"]
    assert request_parameters["temperature_applied"]["false"] == 450

    temperature = sensitivity["models"][model_id]["temperature_effect"]
    assert temperature["status"] == "not_applicable"
    assert temperature["reason"] == "Temperature parameter was not sent for this model."


def test_cross_sp_diagnostic_writes_reports(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_dir = tmp_path / "reports"

    with SoulBenchDB(db_path) as db:
        _insert_full_v31_rotated_campaign(db)
        diagnostic = analyze_cross_sp_diagnostic(db=db, output_dir=output_dir)

    assert diagnostic["status"] == "ok"
    assert diagnostic["top_cells_by_sp_range"]
    assert diagnostic["critical_response_examples"]
    assert (output_dir / "cross_sp_diagnostic.json").exists()
    assert (output_dir / "cross_sp_model_pairs.csv").exists()
    assert (output_dir / "cross_sp_item_amplitudes.csv").exists()
    assert (output_dir / "cross_sp_top_cells.csv").exists()
