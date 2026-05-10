"""Preflight checks before launching a SNAP campaign."""

from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .prompt_builder import (
    ConfigBundle,
    generate_conditions_for_model,
)
from .scorer import build_scoring_prompt

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_CHARS_PER_TOKEN = 4.0
DEFAULT_EXPECTED_RESPONSE_TOKENS = 800
DEFAULT_SCORING_COMPLETION_TOKENS = 256
SCORING_COMPLETION_TOKEN_LIMIT = 512


def fetch_openrouter_catalog(
    catalog_url: str = OPENROUTER_MODELS_URL,
    timeout_seconds: float = 30.0,
) -> list[dict[str, Any]]:
    """Fetch the public OpenRouter model catalog."""
    with urllib.request.urlopen(catalog_url, timeout=timeout_seconds) as response:
        payload = json.load(response)
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ValueError("OpenRouter catalog response must contain a data list.")
    return [entry for entry in data if isinstance(entry, dict)]


def build_preflight_report(
    bundle: ConfigBundle,
    catalog: list[dict[str, Any]],
    db_path: str | Path,
    catalog_source: str = OPENROUTER_MODELS_URL,
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
    expected_response_tokens: int = DEFAULT_EXPECTED_RESPONSE_TOKENS,
    scoring_completion_tokens: int = DEFAULT_SCORING_COMPLETION_TOKENS,
) -> dict[str, Any]:
    """Build model availability, cost, and DB readiness checks."""
    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be positive.")
    if expected_response_tokens <= 0:
        raise ValueError("expected_response_tokens must be positive.")
    if scoring_completion_tokens <= 0:
        raise ValueError("scoring_completion_tokens must be positive.")

    catalog_by_id = {str(entry.get("id")): entry for entry in catalog}
    model_checks = _build_model_checks(bundle=bundle, catalog_by_id=catalog_by_id)
    cost_estimate = _estimate_campaign_cost(
        bundle=bundle,
        catalog_by_id=catalog_by_id,
        chars_per_token=chars_per_token,
        expected_response_tokens=expected_response_tokens,
        scoring_completion_tokens=scoring_completion_tokens,
    )
    db_readiness = _inspect_database_readiness(db_path=db_path, bundle=bundle)

    missing_models = [
        row["configured_id"] for row in model_checks if row["status"] == "missing"
    ]
    warnings = [warning for row in model_checks for warning in row.get("warnings", [])]
    if not db_readiness["clean_for_v31"]:
        warnings.append(db_readiness["reason"])

    status = "ok"
    if missing_models:
        status = "blocked"
    elif warnings:
        status = "warning"

    return {
        "report": "preflight",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "catalog_source": catalog_source,
        "dataset_id": str(bundle.protocol.get("dataset_id")),
        "protocol_version": str(bundle.protocol.get("protocol_version")),
        "model_checks": model_checks,
        "database": db_readiness,
        "cost_estimate": cost_estimate,
        "warnings": warnings,
        "blocking_issues": [
            f"Missing OpenRouter model ID: {model_id}" for model_id in missing_models
        ],
    }


def save_preflight_report(report: dict[str, Any], output_file: str | Path) -> None:
    """Write a preflight report as JSON."""
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file_handle:
        json.dump(report, file_handle, indent=2, ensure_ascii=True)


def _build_model_checks(
    bundle: ConfigBundle, catalog_by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    configured_models: list[dict[str, Any]] = []
    for model_cfg in bundle.models.get("models", []):
        if model_cfg.get("active", True):
            configured_models.append(
                {
                    "role": "collection",
                    "logical_id": str(model_cfg.get("id")),
                    "label": str(model_cfg.get("label", model_cfg.get("id"))),
                    "configured_id": str(model_cfg.get("openrouter_model_id")),
                    "thinking_mode": str(
                        model_cfg.get("thinking_mode", "not_available")
                    ),
                    "disabled_request_parameters": [
                        str(value)
                        for value in model_cfg.get("disabled_request_parameters", [])
                    ],
                }
            )

    for judge_id, judge_cfg in bundle.models.get("judges", {}).items():
        configured_models.append(
            {
                "role": "judge",
                "logical_id": str(judge_id),
                "label": str(judge_cfg.get("label", judge_id)),
                "configured_id": str(judge_cfg.get("openrouter_model_id")),
            }
        )

    checks: list[dict[str, Any]] = []
    required_parameters = {"max_tokens"}
    collection_parameters = {"temperature", "top_p"}

    for configured in configured_models:
        model_id = configured["configured_id"]
        catalog_entry = catalog_by_id.get(model_id)
        if not catalog_entry:
            checks.append(
                {
                    **configured,
                    "status": "missing",
                    "warnings": [],
                }
            )
            continue

        supported = set(catalog_entry.get("supported_parameters") or [])
        disabled_parameters = set(configured.get("disabled_request_parameters", []))
        missing_required = sorted(required_parameters - supported)
        missing_collection = (
            sorted(
                parameter
                for parameter in collection_parameters - supported
                if parameter not in disabled_parameters
            )
            if configured["role"] == "collection"
            else []
        )
        pricing = catalog_entry.get("pricing") or {}
        pricing_missing = [
            field for field in ("prompt", "completion") if field not in pricing
        ]

        warnings: list[str] = []
        if missing_required:
            warnings.append(
                f"{model_id} does not advertise required parameters: {missing_required}"
            )
        if missing_collection:
            warnings.append(
                f"{model_id} does not advertise collection parameters: {missing_collection}"
            )
        if pricing_missing:
            warnings.append(f"{model_id} is missing pricing fields: {pricing_missing}")

        request_policy = {
            "disabled_parameters": sorted(disabled_parameters),
            "omitted_missing_parameters": sorted(disabled_parameters - supported),
        }

        checks.append(
            {
                **configured,
                "status": "available",
                "name": catalog_entry.get("name"),
                "context_length": catalog_entry.get("context_length"),
                "max_completion_tokens": (
                    (catalog_entry.get("top_provider") or {}).get(
                        "max_completion_tokens"
                    )
                ),
                "pricing": {
                    "prompt": pricing.get("prompt"),
                    "completion": pricing.get("completion"),
                },
                "request_policy": request_policy,
                "supported_parameters": sorted(supported),
                "warnings": warnings,
            }
        )

    return checks


def _estimate_campaign_cost(
    bundle: ConfigBundle,
    catalog_by_id: dict[str, dict[str, Any]],
    chars_per_token: float,
    expected_response_tokens: int,
    scoring_completion_tokens: int,
) -> dict[str, Any]:
    collection_cost = 0.0
    scoring_cost = 0.0
    max_collection_cost = 0.0
    max_scoring_cost = 0.0
    per_model: dict[str, Any] = {}

    conditions_by_model: dict[str, Any] = {}
    total_conditions = 0
    for model_cfg in bundle.models.get("models", []):
        if not model_cfg.get("active", True):
            continue
        model_id = str(model_cfg.get("id"))
        conditions, _ = generate_conditions_for_model(
            model_id=model_id, bundle=bundle, seed=1
        )
        conditions_by_model[model_id] = (model_cfg, conditions)
        total_conditions += len(conditions)

    collection_max_tokens = int(
        bundle.models.get("collection", {}).get("max_tokens", 2048)
    )
    for model_id, (model_cfg, conditions) in conditions_by_model.items():
        openrouter_model_id = str(model_cfg.get("openrouter_model_id"))
        pricing = _pricing_for(catalog_by_id.get(openrouter_model_id))
        prompt_tokens = sum(
            _estimate_text_tokens(
                f"{condition.system_prompt_text or ''}\n{condition.user_prompt_text}",
                chars_per_token=chars_per_token,
            )
            for condition in conditions
        )
        expected_completion_tokens = len(conditions) * expected_response_tokens
        max_completion_tokens = len(conditions) * collection_max_tokens

        expected_cost = _token_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=expected_completion_tokens,
            pricing=pricing,
        )
        max_cost = _token_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=max_completion_tokens,
            pricing=pricing,
        )
        collection_cost += expected_cost
        max_collection_cost += max_cost
        per_model[model_id] = {
            "openrouter_model_id": openrouter_model_id,
            "conditions": len(conditions),
            "estimated_prompt_tokens": prompt_tokens,
            "expected_completion_tokens": expected_completion_tokens,
            "max_completion_tokens": max_completion_tokens,
            "expected_cost": expected_cost,
            "max_cost": max_cost,
        }

    rubrics = bundle.scoring_rubrics.get("rubrics", {})
    for judge_id, judge_cfg in bundle.models.get("judges", {}).items():
        judge_model_id = str(judge_cfg.get("openrouter_model_id"))
        pricing = _pricing_for(catalog_by_id.get(judge_model_id))
        judge_prompt_tokens = 0
        max_judge_prompt_tokens = 0
        for _, conditions in conditions_by_model.values():
            for condition in conditions:
                rubric = rubrics.get(
                    condition.item_id, {"description": "Missing rubric"}
                ).get("description", "Missing rubric")
                prompt_without_response = build_scoring_prompt(
                    item_id=condition.item_id,
                    coding_rubric=str(rubric),
                    raw_response="",
                )
                base_tokens = _estimate_text_tokens(
                    prompt_without_response, chars_per_token=chars_per_token
                )
                judge_prompt_tokens += base_tokens + expected_response_tokens
                max_judge_prompt_tokens += base_tokens + collection_max_tokens

        expected_completion = total_conditions * scoring_completion_tokens
        max_completion = total_conditions * SCORING_COMPLETION_TOKEN_LIMIT
        expected_cost = _token_cost(
            prompt_tokens=judge_prompt_tokens,
            completion_tokens=expected_completion,
            pricing=pricing,
        )
        max_cost = _token_cost(
            prompt_tokens=max_judge_prompt_tokens,
            completion_tokens=max_completion,
            pricing=pricing,
        )
        scoring_cost += expected_cost
        max_scoring_cost += max_cost
        per_model[f"judge:{judge_id}"] = {
            "openrouter_model_id": judge_model_id,
            "scoring_calls": total_conditions,
            "estimated_prompt_tokens": judge_prompt_tokens,
            "max_prompt_tokens": max_judge_prompt_tokens,
            "expected_completion_tokens": expected_completion,
            "max_completion_tokens": max_completion,
            "expected_cost": expected_cost,
            "max_cost": max_cost,
        }

    return {
        "currency": "USD",
        "assumptions": {
            "chars_per_token": chars_per_token,
            "expected_collection_completion_tokens_per_response": (
                expected_response_tokens
            ),
            "max_collection_completion_tokens_per_response": collection_max_tokens,
            "expected_scoring_completion_tokens_per_call": scoring_completion_tokens,
            "max_scoring_completion_tokens_per_call": SCORING_COMPLETION_TOKEN_LIMIT,
            "pricing_source": OPENROUTER_MODELS_URL,
            "note": (
                "OpenRouter catalog prices are per token. Expected cost is a "
                "planning estimate; max cost uses configured max_tokens limits."
            ),
        },
        "expected": {
            "collection": round(collection_cost, 6),
            "scoring": round(scoring_cost, 6),
            "total": round(collection_cost + scoring_cost, 6),
        },
        "max_budget": {
            "collection": round(max_collection_cost, 6),
            "scoring": round(max_scoring_cost, 6),
            "total": round(max_collection_cost + max_scoring_cost, 6),
        },
        "details": per_model,
    }


def _inspect_database_readiness(
    db_path: str | Path, bundle: ConfigBundle
) -> dict[str, Any]:
    path = Path(db_path)
    siblings = [
        str(path),
        f"{path}-wal",
        f"{path}-shm",
    ]
    existing_files = [file_path for file_path in siblings if Path(file_path).exists()]
    if not existing_files:
        return {
            "path": str(path),
            "exists": False,
            "response_count": 0,
            "clean_for_v31": True,
            "reason": "Target DB does not exist yet.",
        }

    try:
        import sqlite3

        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        response_count = 0
        protocol_versions: list[str] = []
        dataset_ids: list[str] = []
        if "responses" in tables:
            response_count = int(
                conn.execute("SELECT COUNT(*) AS n FROM responses;").fetchone()["n"]
            )
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(responses);")
            }
            if "protocol_version" in columns:
                protocol_versions = [
                    str(row["protocol_version"])
                    for row in conn.execute(
                        "SELECT DISTINCT protocol_version FROM responses WHERE protocol_version IS NOT NULL;"
                    ).fetchall()
                ]
            if "dataset_id" in columns:
                dataset_ids = [
                    str(row["dataset_id"])
                    for row in conn.execute(
                        "SELECT DISTINCT dataset_id FROM responses WHERE dataset_id IS NOT NULL;"
                    ).fetchall()
                ]
        conn.close()
    except Exception as exc:  # pragma: no cover - defensive file inspection
        return {
            "path": str(path),
            "exists": True,
            "existing_files": existing_files,
            "clean_for_v31": False,
            "reason": f"Could not inspect DB: {exc}",
        }

    expected_protocol = str(bundle.protocol.get("protocol_version"))
    expected_dataset = str(bundle.protocol.get("dataset_id"))
    has_wrong_protocol = bool(
        protocol_versions and protocol_versions != [expected_protocol]
    )
    has_wrong_dataset = bool(dataset_ids and dataset_ids != [expected_dataset])
    clean = response_count == 0 and not has_wrong_protocol and not has_wrong_dataset

    reason = "Target DB is empty and ready for v3.1."
    if not clean:
        reason = (
            "Target DB already contains responses or protocol metadata that should "
            "not be mixed with a fresh v3.1 campaign."
        )

    return {
        "path": str(path),
        "exists": True,
        "existing_files": existing_files,
        "response_count": response_count,
        "protocol_versions": protocol_versions,
        "dataset_ids": dataset_ids,
        "expected_protocol_version": expected_protocol,
        "expected_dataset_id": expected_dataset,
        "clean_for_v31": clean,
        "reason": reason,
    }


def _pricing_for(catalog_entry: dict[str, Any] | None) -> dict[str, float | None]:
    pricing = (catalog_entry or {}).get("pricing") or {}
    return {
        "prompt": _safe_price(pricing.get("prompt")),
        "completion": _safe_price(pricing.get("completion")),
    }


def _safe_price(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _estimate_text_tokens(text: str, chars_per_token: float) -> int:
    return max(1, int(math.ceil(len(text) / chars_per_token)))


def _token_cost(
    prompt_tokens: int,
    completion_tokens: int,
    pricing: dict[str, float | None],
) -> float:
    prompt_price = pricing.get("prompt")
    completion_price = pricing.get("completion")
    if prompt_price is None or completion_price is None:
        return 0.0
    return prompt_tokens * prompt_price + completion_tokens * completion_price
