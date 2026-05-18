"""Tests for SQLite layer."""

from __future__ import annotations

from pathlib import Path

from src.db import ConditionKey, ResponseRecord, SoulBenchDB


def _sample_record(**overrides):
    payload = {
        "model": "test-model",
        "item_id": "O1",
        "item_type": "personality",
        "scenario": "base",
        "formulation": "F1",
        "system_prompt": "SP_ABS",
        "temperature": 0.1,
        "run": 1,
        "user_prompt_text": "Scenario text\n\nQuestion text",
        "raw_response": "Sample response",
    }
    payload.update(overrides)
    return ResponseRecord(**payload)


def test_schema_and_indexes_created(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        tables = {
            row["name"]
            for row in db._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        assert {"responses", "collection_metadata", "manual_verification"}.issubset(
            tables
        )

        indexes = {
            row["name"]
            for row in db._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index';"
            ).fetchall()
        }
        assert "idx_model" in indexes
        assert "idx_condition_unique" in indexes


def test_insert_duplicate_is_ignored(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        inserted_first = db.insert_response(_sample_record())
        inserted_second = db.insert_response(_sample_record())

        assert inserted_first is True
        assert inserted_second is False
        assert db.get_completed_count("test-model") == 1


def test_checkpoint_completed_keys_skip_errors(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        db.insert_response(_sample_record())
        db.insert_response(
            _sample_record(
                run=2,
                is_error=True,
                error_type="timeout",
                raw_response="",
            )
        )

        completed = db.get_completed_condition_keys("test-model")
        assert len(completed) == 1
        assert (
            ConditionKey(
                model="test-model",
                item_id="O1",
                item_type="personality",
                scenario="base",
                formulation="F1",
                system_prompt="SP_ABS",
                temperature=0.1,
                run=1,
            )
            in completed
        )


def test_error_row_can_be_replaced_by_success_for_same_condition(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        inserted_error = db.insert_response(
            _sample_record(
                is_error=True,
                error_type="timeout",
                raw_response="",
            )
        )
        inserted_success = db.insert_response(
            _sample_record(
                is_error=False,
                error_type=None,
                raw_response="Recovered response",
            )
        )

        assert inserted_error is True
        assert inserted_success is True

        row = db._conn.execute("""
            SELECT is_error, error_type, raw_response
            FROM responses
            WHERE model = 'test-model'
              AND item_id = 'O1'
              AND run = 1;
            """).fetchone()
        assert int(row["is_error"]) == 0
        assert row["error_type"] is None
        assert row["raw_response"] == "Recovered response"


def test_manual_adjudication_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with SoulBenchDB(db_path) as db:
        db.insert_response(
            _sample_record(
                run=3,
                score_judge1="+1",
                score_judge2="-1",
                manual_review_needed=True,
            )
        )

        pending = db.get_pending_manual_review_rows(limit=10)
        assert len(pending) == 1
        assert int(pending[0]["id"]) >= 1
        assert pending[0]["user_prompt_text"] == "Scenario text\n\nQuestion text"

        response_id = int(pending[0]["id"])
        db.apply_manual_adjudication(
            response_id=response_id,
            final_score="0",
            reason="tie resolved manually",
        )

        row = db._conn.execute(
            """
            SELECT score_final, manual_score, manual_review_needed, agreement_status, notes
            FROM responses
            WHERE id = ?;
            """,
            (response_id,),
        ).fetchone()
        assert row is not None
        assert row["score_final"] == "0"
        assert row["manual_score"] == "0"
        assert int(row["manual_review_needed"]) == 0
        assert row["agreement_status"] == "manual_adjudicated"
        assert "manual_adjudication:tie resolved manually" in str(row["notes"])

        mv = db._conn.execute(
            """
            SELECT response_id, human_score, human_justification
            FROM manual_verification
            WHERE response_id = ?;
            """,
            (response_id,),
        ).fetchone()
        assert mv is not None
        assert int(mv["response_id"]) == response_id
        assert mv["human_score"] == "0"
        assert mv["human_justification"] == "tie resolved manually"
