"""Tests for prompt assembly and condition generation."""

from __future__ import annotations

from src.prompt_builder import (
    build_messages,
    build_user_prompt,
    expected_conditions_per_model,
    generate_conditions_for_model,
    load_configs,
)


def test_sp_abs_omits_system_message() -> None:
    bundle = load_configs("config")
    messages = build_messages(
        system_prompt_key="SP_ABS",
        user_prompt_text="hello",
        system_prompts=bundle.system_prompts,
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


def test_user_prompt_assembly_contains_blank_line() -> None:
    item = {
        "scenarios": {"base": {"text": "Scenario"}},
        "formulations": {"F1": "Question"},
    }
    user_prompt = build_user_prompt(item=item, scenario="base", formulation="F1")
    assert user_prompt == "Scenario\n\nQuestion"


def test_generation_count_and_seed_determinism() -> None:
    bundle = load_configs("config")
    assert expected_conditions_per_model(bundle) == 3780

    conditions_a, seed_a = generate_conditions_for_model("test-model", bundle, seed=12345)
    conditions_b, seed_b = generate_conditions_for_model("test-model", bundle, seed=12345)
    conditions_c, seed_c = generate_conditions_for_model("test-model", bundle, seed=98765)

    assert seed_a == seed_b == 12345
    assert seed_c == 98765
    assert len(conditions_a) == 3780
    assert len(conditions_b) == 3780
    assert len(conditions_c) == 3780

    sig_a = [
        (c.item_id, c.scenario, c.formulation, c.system_prompt, c.temperature, c.run)
        for c in conditions_a[:30]
    ]
    sig_b = [
        (c.item_id, c.scenario, c.formulation, c.system_prompt, c.temperature, c.run)
        for c in conditions_b[:30]
    ]
    sig_c = [
        (c.item_id, c.scenario, c.formulation, c.system_prompt, c.temperature, c.run)
        for c in conditions_c[:30]
    ]
    assert sig_a == sig_b
    assert sig_a != sig_c
