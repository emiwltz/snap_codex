"""Tests for scoring parser, resolution, and pipeline behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.api_client import ApiCallResult
from src.db import ResponseRecord, SoulBenchDB
from src.scorer import (
    JudgeParseResult,
    export_manual_sample,
    parse_judge_output,
    resolve_disagreement,
    score_pending_for_judge,
)


class FakeClient:
    """Deterministic fake client for scorer tests."""

    def __init__(self, payloads: list[str]) -> None:
        self.payloads = payloads
        self.index = 0
        self.api_key = "fake-key"

    async def generate(self, **_: object) -> ApiCallResult:
        if self.index >= len(self.payloads):
            payload = self.payloads[-1]
        else:
            payload = self.payloads[self.index]
        self.index += 1
        return ApiCallResult(
            content=payload,
            prompt_tokens=10,
            completion_tokens=10,
            response_time_ms=20,
            status_code=200,
            error=None,
        )


def _seed_response(db: SoulBenchDB, response_id: int = 1) -> None:
    db.insert_response(
        ResponseRecord(
            model="test-model",
            item_id="O1",
            item_type="personality",
            scenario="base",
            formulation="F1",
            system_prompt="SP_ABS",
            temperature=0.1,
            run=response_id,
            user_prompt_text="Scenario\n\nQuestion",
            raw_response="I would probably do X.",
        )
    )


def test_parse_judge_output_valid() -> None:
    parsed = parse_judge_output(
        "SCORE: +1\nINDICATEURS: empathy, fairness\nJUSTIFICATION: aligns with positive pole."
    )
    assert parsed.valid is True
    assert parsed.score == "+1"


def test_parse_judge_output_valid_english_labels() -> None:
    parsed = parse_judge_output(
        "SCORE: -1\nINDICATORS: risk aversion, caution\nRATIONALE: aligns with negative pole."
    )
    assert parsed.valid is True
    assert parsed.score == "-1"


def test_parse_judge_output_invalid() -> None:
    parsed = parse_judge_output("SCORE: maybe\nINDICATEURS: none")
    assert parsed.valid is False
    assert parsed.error is not None


def test_resolve_disagreement_cases() -> None:
    assert resolve_disagreement("+1", "+1") == ("+1", "agree", False)
    assert resolve_disagreement("+1", "0") == ("0", "minor_disagree", False)
    assert resolve_disagreement("-1", "0") == ("0", "minor_disagree", False)
    assert resolve_disagreement("+1", "-1") == (None, "major_disagree", True)
    assert resolve_disagreement("REFUS", "+1") == (None, "type_disagree", True)


def test_invalid_parse_triggers_retry_then_manual_flag(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        _seed_response(db)
        fake_client = FakeClient(payloads=["bad output", "still bad"])

        processed = asyncio.run(
            score_pending_for_judge(
                db=db,
                client=fake_client,  # type: ignore[arg-type]
                judge="haiku",
                config_dir="config",
                max_rows=10,
            )
        )

        assert processed == 0
        row = db._conn.execute(
            "SELECT manual_review_needed, score_judge1 FROM responses LIMIT 1;"
        ).fetchone()
        assert int(row["manual_review_needed"]) == 1
        assert row["score_judge1"] is None


def test_export_manual_sample(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    output_file = tmp_path / "manual_sample.csv"

    with SoulBenchDB(db_path) as db:
        for run in range(1, 6):
            db.insert_response(
                ResponseRecord(
                    model="test-model",
                    item_id="O1",
                    item_type="personality",
                    scenario="base",
                    formulation="F1",
                    system_prompt="SP_ABS",
                    temperature=0.1,
                    run=run,
                    user_prompt_text="Scenario\n\nQuestion",
                    raw_response="Response",
                    score_final="0",
                )
            )

        exported = export_manual_sample(db=db, n=3, output_file=output_file)
        assert exported == 3
        assert output_file.exists()
