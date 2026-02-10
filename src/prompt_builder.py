"""Prompt assembly and experimental condition generation utilities."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptCondition:
    """One fully materialized condition to collect."""

    model: str
    item_id: str
    item_type: str
    scenario: str
    formulation: str
    system_prompt: str
    system_prompt_text: str | None
    temperature: float
    run: int
    user_prompt_text: str


@dataclass(frozen=True)
class ConfigBundle:
    """Typed wrapper for loaded YAML configuration."""

    models: dict[str, Any]
    items_personality: dict[str, Any]
    items_moral: dict[str, Any]
    system_prompts: dict[str, Any]
    scoring_rubrics: dict[str, Any]


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load one YAML file.

    Args:
        path: YAML file path.

    Returns:
        Parsed YAML mapping.
    """
    with Path(path).open("r", encoding="utf-8") as file_handle:
        data = yaml.safe_load(file_handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def load_configs(config_dir: str | Path = "config") -> ConfigBundle:
    """Load all pipeline configuration files from disk."""
    root = Path(config_dir)
    bundle = ConfigBundle(
        models=load_yaml(root / "models.yaml"),
        items_personality=load_yaml(root / "items_personality.yaml"),
        items_moral=load_yaml(root / "items_moral.yaml"),
        system_prompts=load_yaml(root / "system_prompts.yaml"),
        scoring_rubrics=load_yaml(root / "scoring_rubrics.yaml"),
    )
    validate_config_structure(bundle)
    return bundle


def validate_config_structure(bundle: ConfigBundle) -> None:
    """Validate minimal required config keys.

    Args:
        bundle: Loaded config bundle.

    Raises:
        ValueError: If required keys are missing.
    """
    required_model_keys = {"collection", "models", "judges"}
    missing_models = required_model_keys - set(bundle.models)
    if missing_models:
        raise ValueError(f"Missing keys in models.yaml: {sorted(missing_models)}")

    for key in ("items",):
        if key not in bundle.items_personality:
            raise ValueError("Missing 'items' in items_personality.yaml")
        if key not in bundle.items_moral:
            raise ValueError("Missing 'items' in items_moral.yaml")

    system_prompts = bundle.system_prompts.get("system_prompts", {})
    for sp_key in ["SP_ABS", "SP_DIR", "SP_PER"]:
        if sp_key not in system_prompts:
            raise ValueError(f"Missing system prompt key: {sp_key}")

    if "rubrics" not in bundle.scoring_rubrics:
        raise ValueError("Missing 'rubrics' in scoring_rubrics.yaml")


def load_items(bundle: ConfigBundle) -> list[dict[str, Any]]:
    """Return merged personality + moral item descriptors."""
    personality_items = bundle.items_personality.get("items", [])
    moral_items = bundle.items_moral.get("items", [])

    merged: list[dict[str, Any]] = []
    for item in personality_items:
        merged.append({**item, "item_type": "personality"})
    for item in moral_items:
        merged.append({**item, "item_type": "moral"})
    return merged


def build_user_prompt(item: dict[str, Any], scenario: str, formulation: str) -> str:
    """Build user prompt text from scenario and formulation.

    Args:
        item: Item dictionary.
        scenario: Scenario key (base/variation).
        formulation: Formulation key (F1/F2/F3).

    Returns:
        User prompt text with one blank line separator.
    """
    scenarios = item.get("scenarios", {})
    formulations = item.get("formulations", {})
    scenario_obj = scenarios.get(scenario, {})
    scenario_text = str(scenario_obj.get("text", "")).strip()
    formulation_text = str(formulations.get(formulation, "")).strip()
    return f"{scenario_text}\n\n{formulation_text}".strip()


def build_messages(
    system_prompt_key: str,
    user_prompt_text: str,
    system_prompts: dict[str, Any],
) -> list[dict[str, str]]:
    """Build OpenRouter chat message array for one condition.

    Args:
        system_prompt_key: SP_ABS/SP_DIR/SP_PER.
        user_prompt_text: Prompt user text.
        system_prompts: Mapping with key "system_prompts".

    Returns:
        Message list following protocol rules.
    """
    messages: list[dict[str, str]] = []
    prompt_map = system_prompts.get("system_prompts", {})
    prompt_text = prompt_map.get(system_prompt_key)
    if system_prompt_key != "SP_ABS" and prompt_text:
        messages.append({"role": "system", "content": str(prompt_text).strip()})
    messages.append({"role": "user", "content": user_prompt_text})
    return messages


def expected_conditions_per_model(bundle: ConfigBundle) -> int:
    """Compute expected condition count per model from config."""
    items = load_items(bundle)
    collection_cfg = bundle.models.get("collection", {})
    runs = int(collection_cfg.get("runs", 7))
    temperatures = collection_cfg.get("temperatures", [0.1, 1.0])

    if not items:
        return 0

    # 2 scenarios x 3 formulations x 3 system prompts x T temperatures x runs x items
    return len(items) * 2 * 3 * 3 * len(temperatures) * runs


def generate_conditions_for_model(
    model_id: str,
    bundle: ConfigBundle,
    seed: int | str | None = None,
) -> tuple[list[PromptCondition], int]:
    """Generate and shuffle all conditions for a model using deterministic seed.

    Args:
        model_id: Model identifier.
        bundle: Loaded config bundle.
        seed: Optional existing seed.

    Returns:
        Tuple of shuffled conditions and effective numeric seed.
    """
    items = load_items(bundle)
    collection_cfg = bundle.models["collection"]
    temperatures = [float(value) for value in collection_cfg.get("temperatures", [0.1, 1.0])]
    runs = int(collection_cfg.get("runs", 7))
    prompt_map = bundle.system_prompts.get("system_prompts", {})

    if seed is None:
        numeric_seed = random.SystemRandom().randint(1, 2_147_483_647)
    elif isinstance(seed, str):
        numeric_seed = int(seed)
    else:
        numeric_seed = int(seed)

    conditions: list[PromptCondition] = []
    for item in items:
        for scenario in ["base", "variation"]:
            for formulation in ["F1", "F2", "F3"]:
                user_prompt = build_user_prompt(item=item, scenario=scenario, formulation=formulation)
                for system_prompt_key in ["SP_ABS", "SP_DIR", "SP_PER"]:
                    for temperature in temperatures:
                        for run in range(1, runs + 1):
                            conditions.append(
                                PromptCondition(
                                    model=model_id,
                                    item_id=str(item["id"]),
                                    item_type=str(item["item_type"]),
                                    scenario=scenario,
                                    formulation=formulation,
                                    system_prompt=system_prompt_key,
                                    system_prompt_text=(
                                        None
                                        if system_prompt_key == "SP_ABS"
                                        else str(prompt_map.get(system_prompt_key, "")).strip() or None
                                    ),
                                    temperature=float(temperature),
                                    run=run,
                                    user_prompt_text=user_prompt,
                                )
                            )

    rng = random.Random(numeric_seed)
    rng.shuffle(conditions)
    LOGGER.debug("Generated %d conditions for model=%s seed=%s", len(conditions), model_id, numeric_seed)
    return conditions, numeric_seed


def get_model_config(bundle: ConfigBundle, model_id: str) -> dict[str, Any] | None:
    """Return model config entry by id if present."""
    for model_cfg in bundle.models.get("models", []):
        if model_cfg.get("id") == model_id:
            return model_cfg
    return None
