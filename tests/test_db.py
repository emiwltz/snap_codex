"""Tests for SQLite layer."""

from __future__ import annotations

import csv
import sqlite3
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
        assert "idx_manual_verification_response_source" in indexes

        source_column = next(
            (
                row
                for row in db._conn.execute(
                    "PRAGMA table_info(manual_verification);"
                ).fetchall()
                if row["name"] == "source"
            ),
            None,
        )
        assert source_column is not None
        assert int(source_column["notnull"]) == 1
        assert "human_validation" in str(source_column["dflt_value"])


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
            SELECT response_id, human_score, human_justification, source
            FROM manual_verification
            WHERE response_id = ?;
            """,
            (response_id,),
        ).fetchone()
        assert mv is not None
        assert int(mv["response_id"]) == response_id
        assert mv["human_score"] == "0"
        assert mv["human_justification"] == "tie resolved manually"
        assert mv["source"] == "adjudication"


def test_import_manual_verification_csv_is_idempotent_and_tagged(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    csv_path = tmp_path / "manual_sample.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=[
                "response_id",
                "human_score",
                "human_justification",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "response_id": "1",
                "human_score": "+1",
                "human_justification": "first import",
            }
        )

    with SoulBenchDB(db_path) as db:
        db.insert_response(
            _sample_record(
                score_judge1="+1",
                score_judge2="+1",
                score_final="+1",
            )
        )

        first_import = db.import_manual_verification_csv(csv_path)
        second_import = db.import_manual_verification_csv(csv_path)

        assert first_import == 1
        assert second_import == 1

        rows = db._conn.execute("""
            SELECT response_id, human_score, human_justification, source
            FROM manual_verification
            ORDER BY id;
            """).fetchall()

    assert len(rows) == 1
    assert int(rows[0]["response_id"]) == 1
    assert rows[0]["human_score"] == "+1"
    assert rows[0]["human_justification"] == "first import"
    assert rows[0]["source"] == "human_validation"


def test_legacy_manual_verification_rows_migrate_to_adjudication(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy_manual_verification.db"

    with SoulBenchDB(db_path) as db:
        db.insert_response(
            _sample_record(
                run=5,
                score_judge1="+1",
                score_judge2="-1",
                manual_review_needed=True,
            )
        )
        pending = db.get_pending_manual_review_rows(limit=1)
        response_id = int(pending[0]["id"])
        db.apply_manual_adjudication(
            response_id=response_id,
            final_score="0",
            reason="legacy adjudication seed",
        )

    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            DROP INDEX IF EXISTS idx_manual_verification_response_source;

            UPDATE manual_verification
            SET kappa_judge1 = 0.5,
                kappa_judge2 = 0.5;

            CREATE TABLE manual_verification_legacy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER REFERENCES responses(id),
                human_score TEXT,
                human_justification TEXT,
                verified_at TEXT,
                kappa_judge1 REAL,
                kappa_judge2 REAL
            );

            INSERT INTO manual_verification_legacy (
                id,
                response_id,
                human_score,
                human_justification,
                verified_at,
                kappa_judge1,
                kappa_judge2
            )
            SELECT
                id,
                response_id,
                human_score,
                human_justification,
                verified_at,
                kappa_judge1,
                kappa_judge2
            FROM manual_verification;

            DROP TABLE manual_verification;
            ALTER TABLE manual_verification_legacy RENAME TO manual_verification;
            """)
        conn.commit()

    with SoulBenchDB(db_path) as db:
        migrated = db._conn.execute(
            """
            SELECT source, kappa_judge1, kappa_judge2
            FROM manual_verification
            WHERE response_id = ?;
            """,
            (response_id,),
        ).fetchone()
        assert migrated is not None
        assert migrated["source"] == "adjudication"
        assert migrated["kappa_judge1"] is None
        assert migrated["kappa_judge2"] is None

        source_column = next(
            (
                row
                for row in db._conn.execute(
                    "PRAGMA table_info(manual_verification);"
                ).fetchall()
                if row["name"] == "source"
            ),
            None,
        )
        assert source_column is not None
        assert int(source_column["notnull"]) == 1
