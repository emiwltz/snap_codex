"""Tests for CLI runner orchestration."""

from __future__ import annotations

import asyncio
from argparse import Namespace
from pathlib import Path
from typing import Any

from src import runner
from src.api_client import ApiCallResult
from src.db import SoulBenchDB


class FakeOpenRouterClient:
    """Fake remote client used to test runner collection limits."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **_: object) -> None:
        self.api_key = "fake-key"

    async def __aenter__(self) -> FakeOpenRouterClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def generate(self, **kwargs: object) -> ApiCallResult:
        type(self).calls.append(dict(kwargs))
        return ApiCallResult(
            content=f"Limited response {len(type(self).calls)}",
            prompt_tokens=10,
            completion_tokens=20,
            response_time_ms=30,
            status_code=200,
            error=None,
        )


def test_collect_max_rows_limits_pending_conditions(
    monkeypatch: Any, tmp_path: Path
) -> None:
    FakeOpenRouterClient.calls = []
    monkeypatch.setattr(runner, "OpenRouterClient", FakeOpenRouterClient)

    db_path = tmp_path / "limited.db"
    args = Namespace(
        db_path=str(db_path),
        config_dir="config",
        all=False,
        model="claude-sonnet-4-5",
        max_rows=3,
    )

    exit_code = asyncio.run(runner.run_collect(args))

    assert exit_code == 0
    assert len(FakeOpenRouterClient.calls) == 3

    with SoulBenchDB(db_path) as db:
        response_count = db._conn.execute(
            "SELECT COUNT(*) AS n FROM responses;"
        ).fetchone()["n"]
        metadata = db._conn.execute("""
            SELECT total_planned, total_completed, total_errors, notes
            FROM collection_metadata
            WHERE model = 'claude-sonnet-4-5';
            """).fetchone()

    assert response_count == 3
    assert FakeOpenRouterClient.calls[0]["temperature"] is not None
    assert FakeOpenRouterClient.calls[0]["top_p"] == 1.0
    assert int(metadata["total_planned"]) == 450
    assert int(metadata["total_completed"]) == 3
    assert int(metadata["total_errors"]) == 0
    assert "Limited collection run: max_rows=3" in str(metadata["notes"])


def test_collect_omits_disabled_request_parameters(
    monkeypatch: Any, tmp_path: Path
) -> None:
    FakeOpenRouterClient.calls = []
    monkeypatch.setattr(runner, "OpenRouterClient", FakeOpenRouterClient)

    db_path = tmp_path / "gpt.db"
    args = Namespace(
        db_path=str(db_path),
        config_dir="config",
        all=False,
        model="gpt-5-2",
        max_rows=1,
    )

    exit_code = asyncio.run(runner.run_collect(args))

    assert exit_code == 0
    assert len(FakeOpenRouterClient.calls) == 1
    assert FakeOpenRouterClient.calls[0]["temperature"] is None
    assert FakeOpenRouterClient.calls[0]["top_p"] is None

    with SoulBenchDB(db_path) as db:
        row = db._conn.execute("""
            SELECT temperature_applied, top_p_applied, thinking_enabled
            FROM responses
            LIMIT 1;
            """).fetchone()
        metadata = db._conn.execute("""
            SELECT notes
            FROM collection_metadata
            WHERE model = 'gpt-5-2';
            """).fetchone()

    assert int(row["temperature_applied"]) == 0
    assert int(row["top_p_applied"]) == 0
    assert int(row["thinking_enabled"]) == 1
    assert "Disabled request parameters" in str(metadata["notes"])


def test_collect_rejects_non_positive_max_rows(tmp_path: Path) -> None:
    args = Namespace(
        db_path=str(tmp_path / "invalid.db"),
        config_dir="config",
        all=False,
        model="claude-sonnet-4-5",
        max_rows=0,
    )

    exit_code = asyncio.run(runner.run_collect(args))

    assert exit_code == 2
