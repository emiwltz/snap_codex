"""SQLite data access layer for SoulBench SNAP pipeline."""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from random import Random
from typing import Any, Iterable

import pandas as pd

LOGGER = logging.getLogger(__name__)

MANUAL_VERIFICATION_SOURCES = {"adjudication", "human_validation"}
DEFAULT_MANUAL_VERIFICATION_SOURCE = "human_validation"
ADJUDICATION_SOURCE = "adjudication"
HUMAN_VALIDATION_SOURCE = "human_validation"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ConditionKey:
    """Logical key for one experimental condition.

    Attributes:
        model: Model identifier.
        item_id: Item identifier.
        item_type: personality or moral.
        scenario: base or variation.
        formulation: F1/F2/F3.
        system_prompt: SP_ABS/SP_DIR/SP_PER.
        temperature: Temperature value.
        run: Run index (1..N).
    """

    model: str
    item_id: str
    item_type: str
    scenario: str
    formulation: str
    system_prompt: str
    temperature: float
    run: int


@dataclass
class ResponseRecord:
    """Payload for inserting one response row."""

    model: str
    item_id: str
    item_type: str
    scenario: str
    formulation: str
    system_prompt: str
    temperature: float
    run: int
    dataset_id: str | None = None
    protocol_version: str | None = None
    items_version: str | None = None
    condition_block: str | None = None
    trial_id: str | None = None
    timestamp: str | None = None
    response_time_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    random_seed: str | None = None
    temperature_applied: bool | None = None
    top_p_applied: bool | None = None
    thinking_enabled: bool | None = None
    system_prompt_text: str | None = None
    user_prompt_text: str = ""
    raw_response: str = ""
    score_judge1: str | None = None
    score_judge2: str | None = None
    score_final: str | None = None
    judge1_indicators: str | None = None
    judge2_indicators: str | None = None
    judge1_justification: str | None = None
    judge2_justification: str | None = None
    agreement_status: str | None = None
    manual_review_needed: bool = False
    manual_score: str | None = None
    is_refusal: bool = False
    is_truncated: bool = False
    is_error: bool = False
    error_type: str | None = None
    notes: str | None = None

    def condition_key(self) -> ConditionKey:
        """Build the associated condition key."""
        return ConditionKey(
            model=self.model,
            item_id=self.item_id,
            item_type=self.item_type,
            scenario=self.scenario,
            formulation=self.formulation,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            run=self.run,
        )


@dataclass
class ScoringUpdate:
    """Judge scoring update payload."""

    response_id: int
    judge_name: str
    score: str
    indicators: str
    justification: str


@dataclass
class ResolutionUpdate:
    """Disagreement resolution payload."""

    response_id: int
    score_final: str | None
    agreement_status: str
    manual_review_needed: bool
    notes: str | None = None


@dataclass
class ManualVerificationRow:
    """Manual coding import payload."""

    response_id: int
    human_score: str
    human_justification: str | None = None
    verified_at: str | None = None
    source: str = DEFAULT_MANUAL_VERIFICATION_SOURCE


class SoulBenchDB:
    """SQLite interface used by all pipeline stages."""

    def __init__(self, db_path: str | Path = "data/soulbench.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._initialize_pragmas()

    def _initialize_pragmas(self) -> None:
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> SoulBenchDB:
        self.initialize_schema()
        return self

    def __exit__(self, exc_type: Any, exc: Any, exc_tb: Any) -> None:
        self.close()

    def initialize_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT,
            protocol_version TEXT,
            items_version TEXT,
            condition_block TEXT,
            trial_id TEXT,
            model TEXT NOT NULL,
            item_id TEXT NOT NULL,
            item_type TEXT NOT NULL,
            scenario TEXT NOT NULL,
            formulation TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            temperature REAL NOT NULL,
            run INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            response_time_ms INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            random_seed TEXT,
            temperature_applied BOOLEAN,
            top_p_applied BOOLEAN,
            thinking_enabled BOOLEAN,
            system_prompt_text TEXT,
            user_prompt_text TEXT NOT NULL,
            raw_response TEXT NOT NULL,
            score_judge1 TEXT,
            score_judge2 TEXT,
            score_final TEXT,
            judge1_indicators TEXT,
            judge2_indicators TEXT,
            judge1_justification TEXT,
            judge2_justification TEXT,
            agreement_status TEXT,
            manual_review_needed BOOLEAN DEFAULT FALSE,
            manual_score TEXT,
            is_refusal BOOLEAN DEFAULT FALSE,
            is_truncated BOOLEAN DEFAULT FALSE,
            is_error BOOLEAN DEFAULT FALSE,
            error_type TEXT,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_model ON responses(model);
        CREATE INDEX IF NOT EXISTS idx_item ON responses(item_id);
        CREATE INDEX IF NOT EXISTS idx_condition ON responses(model, item_id, system_prompt, temperature);
        CREATE INDEX IF NOT EXISTS idx_scoring ON responses(score_final, is_refusal);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_condition_unique
            ON responses(model, item_id, item_type, scenario, formulation, system_prompt, temperature, run);

        CREATE TABLE IF NOT EXISTS collection_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT,
            protocol_version TEXT,
            items_version TEXT,
            model TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            total_planned INTEGER,
            total_completed INTEGER,
            total_errors INTEGER,
            total_refusals INTEGER,
            randomization_seed TEXT,
            thinking_mode TEXT,
            api_endpoint TEXT,
            model_version TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS manual_verification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id INTEGER REFERENCES responses(id),
            human_score TEXT,
            human_justification TEXT,
            verified_at TEXT,
            kappa_judge1 REAL,
            kappa_judge2 REAL,
            source TEXT NOT NULL DEFAULT 'human_validation'
                CHECK (source IN ('adjudication', 'human_validation'))
        );
        """
        self._conn.executescript(schema_sql)
        self._ensure_column("responses", "dataset_id", "TEXT")
        self._ensure_column("responses", "protocol_version", "TEXT")
        self._ensure_column("responses", "items_version", "TEXT")
        self._ensure_column("responses", "condition_block", "TEXT")
        self._ensure_column("responses", "trial_id", "TEXT")
        self._ensure_column("responses", "temperature_applied", "BOOLEAN")
        self._ensure_column("responses", "top_p_applied", "BOOLEAN")
        self._ensure_column("collection_metadata", "dataset_id", "TEXT")
        self._ensure_column("collection_metadata", "protocol_version", "TEXT")
        self._ensure_column("collection_metadata", "items_version", "TEXT")
        self._ensure_manual_verification_schema()
        self._conn.commit()

    def _ensure_column(self, table: str, column: str, column_type: str) -> None:
        existing = {
            row["name"]
            for row in self._conn.execute(f"PRAGMA table_info({table});").fetchall()
        }
        if column not in existing:
            self._conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {column_type};"
            )

    def _ensure_manual_verification_schema(self) -> None:
        if self._manual_verification_requires_rebuild():
            self._rebuild_manual_verification_table()
        self._backfill_manual_verification_sources()
        self._clear_adjudication_manual_kappas()
        self._deduplicate_manual_verification_rows()
        self._conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_manual_verification_response_source
            ON manual_verification(response_id, source);
            """)

    def _manual_verification_requires_rebuild(self) -> bool:
        table_info = self._conn.execute(
            "PRAGMA table_info(manual_verification);"
        ).fetchall()
        source_column = next(
            (row for row in table_info if row["name"] == "source"),
            None,
        )
        if source_column is None:
            return True

        if int(source_column["notnull"]) != 1:
            return True

        default_value = str(source_column["dflt_value"] or "")
        if HUMAN_VALIDATION_SOURCE not in default_value:
            return True

        table_sql_row = self._conn.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'manual_verification';
            """).fetchone()
        normalized_sql = " ".join(str(table_sql_row["sql"] or "").split())
        return (
            "CHECK (source IN ('adjudication', 'human_validation'))"
            not in normalized_sql
        )

    def _rebuild_manual_verification_table(self) -> None:
        """Rebuild manual_verification to enforce the current schema."""
        existing_columns = {
            row["name"]
            for row in self._conn.execute(
                "PRAGMA table_info(manual_verification);"
            ).fetchall()
        }
        has_source_column = "source" in existing_columns

        self._conn.execute("DROP TABLE IF EXISTS manual_verification__rebuilt;")
        self._conn.execute("""
            CREATE TABLE manual_verification__rebuilt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER REFERENCES responses(id),
                human_score TEXT,
                human_justification TEXT,
                verified_at TEXT,
                kappa_judge1 REAL,
                kappa_judge2 REAL,
                source TEXT NOT NULL DEFAULT 'human_validation'
                    CHECK (source IN ('adjudication', 'human_validation'))
            );
            """)

        if has_source_column:
            source_sql = """
                CASE
                    WHEN r.agreement_status = ? THEN ?
                    WHEN LOWER(TRIM(COALESCE(mv.source, ''))) IN (?, ?)
                        THEN LOWER(TRIM(COALESCE(mv.source, '')))
                    ELSE ?
                END
            """
            params = (
                "manual_adjudicated",
                ADJUDICATION_SOURCE,
                ADJUDICATION_SOURCE,
                HUMAN_VALIDATION_SOURCE,
                HUMAN_VALIDATION_SOURCE,
            )
        else:
            source_sql = """
                CASE
                    WHEN r.agreement_status = ? THEN ?
                    ELSE ?
                END
            """
            params = (
                "manual_adjudicated",
                ADJUDICATION_SOURCE,
                HUMAN_VALIDATION_SOURCE,
            )

        self._conn.execute(
            f"""
            INSERT INTO manual_verification__rebuilt (
                id,
                response_id,
                human_score,
                human_justification,
                verified_at,
                kappa_judge1,
                kappa_judge2,
                source
            )
            SELECT
                mv.id,
                mv.response_id,
                mv.human_score,
                mv.human_justification,
                mv.verified_at,
                mv.kappa_judge1,
                mv.kappa_judge2,
                {source_sql}
            FROM manual_verification mv
            LEFT JOIN responses r ON r.id = mv.response_id;
            """,
            params,
        )

        self._conn.execute("DROP TABLE manual_verification;")
        self._conn.execute(
            "ALTER TABLE manual_verification__rebuilt RENAME TO manual_verification;"
        )

    def _backfill_manual_verification_sources(self) -> None:
        """Backfill legacy manual_verification rows with explicit sources."""
        self._conn.execute(
            """
            UPDATE manual_verification
            SET source = ?
            WHERE response_id IN (
                SELECT id
                FROM responses
                WHERE agreement_status = 'manual_adjudicated'
            );
            """,
            (ADJUDICATION_SOURCE,),
        )
        self._conn.execute(
            """
            UPDATE manual_verification
            SET source = ?
            WHERE source IS NULL OR TRIM(source) = '';
            """,
            (HUMAN_VALIDATION_SOURCE,),
        )

    def _clear_adjudication_manual_kappas(self) -> None:
        """Keep human-vs-machine kappas exclusive to blind human validation rows."""
        self._conn.execute(
            """
            UPDATE manual_verification
            SET kappa_judge1 = NULL,
                kappa_judge2 = NULL
            WHERE source = ?;
            """,
            (ADJUDICATION_SOURCE,),
        )

    def _deduplicate_manual_verification_rows(self) -> None:
        """Keep the latest row per response/source before adding uniqueness."""
        self._conn.execute("""
            DELETE FROM manual_verification
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM manual_verification
                GROUP BY response_id, source
            );
            """)

    def _normalize_manual_verification_source(self, source: str) -> str:
        normalized = source.strip().lower()
        if normalized not in MANUAL_VERIFICATION_SOURCES:
            raise ValueError(f"Unsupported manual verification source: {source}")
        return normalized

    def insert_response(self, record: ResponseRecord) -> bool:
        """Insert one response row.

        Args:
            record: Record to insert.

        Returns:
            True if row inserted, False if ignored due to unique key.
        """
        payload = {
            "dataset_id": record.dataset_id,
            "protocol_version": record.protocol_version,
            "items_version": record.items_version,
            "condition_block": record.condition_block,
            "trial_id": record.trial_id,
            "model": record.model,
            "item_id": record.item_id,
            "item_type": record.item_type,
            "scenario": record.scenario,
            "formulation": record.formulation,
            "system_prompt": record.system_prompt,
            "temperature": record.temperature,
            "run": record.run,
            "timestamp": record.timestamp or _utc_now_iso(),
            "response_time_ms": record.response_time_ms,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "random_seed": record.random_seed,
            "temperature_applied": (
                None
                if record.temperature_applied is None
                else int(record.temperature_applied)
            ),
            "top_p_applied": (
                None if record.top_p_applied is None else int(record.top_p_applied)
            ),
            "thinking_enabled": (
                None
                if record.thinking_enabled is None
                else int(record.thinking_enabled)
            ),
            "system_prompt_text": record.system_prompt_text,
            "user_prompt_text": record.user_prompt_text,
            "raw_response": record.raw_response or "",
            "score_judge1": record.score_judge1,
            "score_judge2": record.score_judge2,
            "score_final": record.score_final,
            "judge1_indicators": record.judge1_indicators,
            "judge2_indicators": record.judge2_indicators,
            "judge1_justification": record.judge1_justification,
            "judge2_justification": record.judge2_justification,
            "agreement_status": record.agreement_status,
            "manual_review_needed": int(record.manual_review_needed),
            "manual_score": record.manual_score,
            "is_refusal": int(record.is_refusal),
            "is_truncated": int(record.is_truncated),
            "is_error": int(record.is_error),
            "error_type": record.error_type,
            "notes": record.notes,
        }
        cur = self._conn.execute(
            """
            INSERT INTO responses (
                dataset_id, protocol_version, items_version, condition_block, trial_id,
                model, item_id, item_type, scenario, formulation, system_prompt,
                temperature, run, timestamp, response_time_ms,
                prompt_tokens, completion_tokens, random_seed,
                temperature_applied, top_p_applied, thinking_enabled,
                system_prompt_text, user_prompt_text, raw_response,
                score_judge1, score_judge2, score_final,
                judge1_indicators, judge2_indicators,
                judge1_justification, judge2_justification,
                agreement_status, manual_review_needed, manual_score,
                is_refusal, is_truncated, is_error, error_type, notes
            ) VALUES (
                :dataset_id, :protocol_version, :items_version, :condition_block, :trial_id,
                :model, :item_id, :item_type, :scenario, :formulation, :system_prompt,
                :temperature, :run, :timestamp, :response_time_ms,
                :prompt_tokens, :completion_tokens, :random_seed,
                :temperature_applied, :top_p_applied, :thinking_enabled,
                :system_prompt_text, :user_prompt_text, :raw_response,
                :score_judge1, :score_judge2, :score_final,
                :judge1_indicators, :judge2_indicators,
                :judge1_justification, :judge2_justification,
                :agreement_status, :manual_review_needed, :manual_score,
                :is_refusal, :is_truncated, :is_error, :error_type, :notes
            )
            ON CONFLICT(model, item_id, item_type, scenario, formulation, system_prompt, temperature, run)
            DO UPDATE SET
                timestamp = excluded.timestamp,
                dataset_id = excluded.dataset_id,
                protocol_version = excluded.protocol_version,
                items_version = excluded.items_version,
                condition_block = excluded.condition_block,
                trial_id = excluded.trial_id,
                response_time_ms = excluded.response_time_ms,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                random_seed = excluded.random_seed,
                temperature_applied = excluded.temperature_applied,
                top_p_applied = excluded.top_p_applied,
                thinking_enabled = excluded.thinking_enabled,
                system_prompt_text = excluded.system_prompt_text,
                user_prompt_text = excluded.user_prompt_text,
                raw_response = excluded.raw_response,
                score_judge1 = excluded.score_judge1,
                score_judge2 = excluded.score_judge2,
                score_final = excluded.score_final,
                judge1_indicators = excluded.judge1_indicators,
                judge2_indicators = excluded.judge2_indicators,
                judge1_justification = excluded.judge1_justification,
                judge2_justification = excluded.judge2_justification,
                agreement_status = excluded.agreement_status,
                manual_review_needed = excluded.manual_review_needed,
                manual_score = excluded.manual_score,
                is_refusal = excluded.is_refusal,
                is_truncated = excluded.is_truncated,
                is_error = excluded.is_error,
                error_type = excluded.error_type,
                notes = excluded.notes
            WHERE responses.is_error = 1;
            """,
            payload,
        )
        self._conn.commit()
        return cur.rowcount == 1

    def get_completed_condition_keys(self, model: str) -> set[ConditionKey]:
        """Return condition keys already completed successfully for one model."""
        rows = self._conn.execute(
            """
            SELECT model, item_id, item_type, scenario, formulation, system_prompt, temperature, run
            FROM responses
            WHERE model = ? AND is_error = 0;
            """,
            (model,),
        ).fetchall()
        return {
            ConditionKey(
                model=row["model"],
                item_id=row["item_id"],
                item_type=row["item_type"],
                scenario=row["scenario"],
                formulation=row["formulation"],
                system_prompt=row["system_prompt"],
                temperature=float(row["temperature"]),
                run=int(row["run"]),
            )
            for row in rows
        }

    def get_completed_count(self, model: str) -> int:
        """Return completed response count for one model."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM responses WHERE model = ? AND is_error = 0;",
            (model,),
        ).fetchone()
        return int(row["n"] if row else 0)

    def get_error_count(self, model: str) -> int:
        """Return error response count for one model."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM responses WHERE model = ? AND is_error = 1;",
            (model,),
        ).fetchone()
        return int(row["n"] if row else 0)

    def get_refusal_count(self, model: str) -> int:
        """Return refusal count for one model."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM responses WHERE model = ? AND is_refusal = 1;",
            (model,),
        ).fetchone()
        return int(row["n"] if row else 0)

    def upsert_collection_metadata(
        self,
        model: str,
        total_planned: int,
        randomization_seed: str,
        thinking_mode: str,
        api_endpoint: str,
        dataset_id: str | None = None,
        protocol_version: str | None = None,
        items_version: str | None = None,
        model_version: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Insert or update collection metadata for a model."""
        existing = self._conn.execute(
            "SELECT id FROM collection_metadata WHERE model = ? ORDER BY id DESC LIMIT 1;",
            (model,),
        ).fetchone()
        total_completed = self.get_completed_count(model)
        total_errors = self.get_error_count(model)
        total_refusals = self.get_refusal_count(model)

        if existing:
            self._conn.execute(
                """
                UPDATE collection_metadata
                SET start_time = COALESCE(?, start_time),
                    end_time = COALESCE(?, end_time),
                    dataset_id = COALESCE(?, dataset_id),
                    protocol_version = COALESCE(?, protocol_version),
                    items_version = COALESCE(?, items_version),
                    total_planned = ?,
                    total_completed = ?,
                    total_errors = ?,
                    total_refusals = ?,
                    randomization_seed = ?,
                    thinking_mode = ?,
                    api_endpoint = ?,
                    model_version = COALESCE(?, model_version),
                    notes = COALESCE(?, notes)
                WHERE id = ?;
                """,
                (
                    start_time,
                    end_time,
                    dataset_id,
                    protocol_version,
                    items_version,
                    total_planned,
                    total_completed,
                    total_errors,
                    total_refusals,
                    randomization_seed,
                    thinking_mode,
                    api_endpoint,
                    model_version,
                    notes,
                    int(existing["id"]),
                ),
            )
        else:
            self._conn.execute(
                """
                INSERT INTO collection_metadata (
                    dataset_id, protocol_version, items_version,
                    model, start_time, end_time, total_planned, total_completed,
                    total_errors, total_refusals, randomization_seed,
                    thinking_mode, api_endpoint, model_version, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    dataset_id,
                    protocol_version,
                    items_version,
                    model,
                    start_time,
                    end_time,
                    total_planned,
                    total_completed,
                    total_errors,
                    total_refusals,
                    randomization_seed,
                    thinking_mode,
                    api_endpoint,
                    model_version,
                    notes,
                ),
            )
        self._conn.commit()

    def finalize_collection_metadata(
        self, model: str, notes: str | None = None
    ) -> None:
        """Update end-of-collection counters for a model."""
        existing = self._conn.execute(
            "SELECT id, total_planned, randomization_seed, thinking_mode, api_endpoint, model_version, start_time, notes "
            "FROM collection_metadata WHERE model = ? ORDER BY id DESC LIMIT 1;",
            (model,),
        ).fetchone()
        if not existing:
            LOGGER.warning("Cannot finalize metadata, model '%s' not found.", model)
            return

        merged_notes = existing["notes"]
        if notes:
            merged_notes = (
                f"{existing['notes']} | {notes}" if existing["notes"] else notes
            )

        self._conn.execute(
            """
            UPDATE collection_metadata
            SET end_time = ?,
                total_completed = ?,
                total_errors = ?,
                total_refusals = ?,
                notes = ?
            WHERE id = ?;
            """,
            (
                _utc_now_iso(),
                self.get_completed_count(model),
                self.get_error_count(model),
                self.get_refusal_count(model),
                merged_notes,
                int(existing["id"]),
            ),
        )
        self._conn.commit()

    def get_model_seed(self, model: str) -> str | None:
        """Return stored randomization seed for a model."""
        row = self._conn.execute(
            "SELECT randomization_seed FROM collection_metadata WHERE model = ? ORDER BY id DESC LIMIT 1;",
            (model,),
        ).fetchone()
        if not row:
            return None
        return row["randomization_seed"]

    def get_pending_for_scoring(
        self, judge: str, max_rows: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch pending rows for one judge.

        Args:
            judge: Either "haiku" or "kimi".
            max_rows: Maximum number of rows returned.
        """
        if judge not in {"haiku", "kimi"}:
            raise ValueError(f"Unsupported judge: {judge}")

        score_col = "score_judge1" if judge == "haiku" else "score_judge2"
        query = f"""
            SELECT id, item_id, raw_response
            FROM responses
            WHERE is_error = 0
              AND manual_review_needed = 0
              AND {score_col} IS NULL
              AND raw_response IS NOT NULL
              AND TRIM(raw_response) != ''
            ORDER BY id
            LIMIT ?;
        """
        rows = self._conn.execute(query, (max_rows,)).fetchall()
        return [dict(row) for row in rows]

    def update_scoring(self, update: ScoringUpdate) -> None:
        """Update scoring fields for one judge result."""
        if update.judge_name == "haiku":
            self._conn.execute(
                """
                UPDATE responses
                SET score_judge1 = ?,
                    judge1_indicators = ?,
                    judge1_justification = ?,
                    is_refusal = CASE WHEN ? = 'REFUS' THEN 1 ELSE is_refusal END
                WHERE id = ?;
                """,
                (
                    update.score,
                    update.indicators,
                    update.justification,
                    update.score,
                    update.response_id,
                ),
            )
        elif update.judge_name == "kimi":
            self._conn.execute(
                """
                UPDATE responses
                SET score_judge2 = ?,
                    judge2_indicators = ?,
                    judge2_justification = ?,
                    is_refusal = CASE WHEN ? = 'REFUS' THEN 1 ELSE is_refusal END
                WHERE id = ?;
                """,
                (
                    update.score,
                    update.indicators,
                    update.justification,
                    update.score,
                    update.response_id,
                ),
            )
        else:
            raise ValueError(f"Unsupported judge_name: {update.judge_name}")
        self._conn.commit()

    def flag_manual_review(self, response_id: int, note: str) -> None:
        """Flag one response for manual review."""
        self._conn.execute(
            """
            UPDATE responses
            SET manual_review_needed = 1,
                notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || ' | ' || ?
                END
            WHERE id = ?;
            """,
            (note, note, response_id),
        )
        self._conn.commit()

    def get_rows_for_resolution(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return rows where two judge scores exist and disagreement was not resolved."""
        rows = self._conn.execute(
            """
            SELECT id, score_judge1, score_judge2
            FROM responses
            WHERE score_judge1 IS NOT NULL
              AND score_judge2 IS NOT NULL
              AND agreement_status IS NULL
            ORDER BY id
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_pending_manual_review_rows(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Return rows flagged for manual adjudication and still unresolved."""
        rows = self._conn.execute(
            """
            SELECT
                id,
                model,
                item_id,
                item_type,
                scenario,
                formulation,
                system_prompt,
                temperature,
                run,
                user_prompt_text,
                raw_response,
                score_judge1,
                score_judge2,
                judge1_justification,
                judge2_justification,
                notes
            FROM responses
            WHERE manual_review_needed = 1
              AND (score_final IS NULL OR TRIM(score_final) = '')
            ORDER BY id
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def apply_resolution(self, update: ResolutionUpdate) -> None:
        """Persist disagreement resolution decision."""
        self._conn.execute(
            """
            UPDATE responses
            SET score_final = ?,
                agreement_status = ?,
                manual_review_needed = ?,
                is_refusal = CASE WHEN ? = 'REFUS' THEN 1 ELSE is_refusal END,
                notes = CASE
                    WHEN ? IS NULL THEN notes
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || ' | ' || ?
                END
            WHERE id = ?;
            """,
            (
                update.score_final,
                update.agreement_status,
                int(update.manual_review_needed),
                update.score_final,
                update.notes,
                update.notes,
                update.notes,
                update.response_id,
            ),
        )
        self._conn.commit()

    def apply_manual_adjudication(
        self,
        response_id: int,
        final_score: str,
        reason: str | None = None,
    ) -> None:
        """Apply one manual adjudication decision.

        This writes final score fields on responses and records the
        adjudication in manual_verification for traceability.
        """
        note = f"manual_adjudication:{reason}" if reason else "manual_adjudication"
        self._conn.execute(
            """
            UPDATE responses
            SET score_final = ?,
                manual_score = ?,
                manual_review_needed = 0,
                agreement_status = 'manual_adjudicated',
                is_refusal = CASE WHEN ? = 'REFUS' THEN 1 ELSE is_refusal END,
                notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || ' | ' || ?
                END
            WHERE id = ?;
            """,
            (final_score, final_score, final_score, note, note, response_id),
        )
        self._conn.execute(
            """
            INSERT INTO manual_verification (
                response_id, human_score, human_justification, verified_at, source
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(response_id, source)
            DO UPDATE SET
                human_score = excluded.human_score,
                human_justification = excluded.human_justification,
                verified_at = excluded.verified_at,
                kappa_judge1 = NULL,
                kappa_judge2 = NULL;
            """,
            (
                response_id,
                final_score,
                reason,
                _utc_now_iso(),
                ADJUDICATION_SOURCE,
            ),
        )
        self._conn.commit()

    def sample_for_manual_verification(
        self, n: int, seed: int = 42
    ) -> list[dict[str, Any]]:
        """Return a stratified sample by model/item/SP/temperature.

        Args:
            n: Requested sample size.
            seed: Seed used for random sampling.
        """
        if n <= 0:
            return []

        rows = self._conn.execute(
            """
            SELECT id, model, item_id, system_prompt, temperature, raw_response, score_final
            FROM responses
            WHERE score_final IS NOT NULL
              AND id NOT IN (
                  SELECT response_id
                  FROM manual_verification
                  WHERE source = ?
              )
            ORDER BY id;
            """,
            (HUMAN_VALIDATION_SOURCE,),
        ).fetchall()
        records = [dict(row) for row in rows]
        if not records:
            return []

        total = len(records)
        target = min(n, total)

        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for row in records:
            key = (
                row["model"],
                row["item_id"],
                row["system_prompt"],
                float(row["temperature"]),
            )
            groups.setdefault(key, []).append(row)

        allocations: dict[tuple[Any, ...], int] = {}
        remainders: list[tuple[float, tuple[Any, ...]]] = []
        allocated_total = 0
        for key, group_rows in groups.items():
            raw_alloc = target * (len(group_rows) / total)
            base_alloc = int(raw_alloc)
            allocations[key] = base_alloc
            allocated_total += base_alloc
            remainders.append((raw_alloc - base_alloc, key))

        remainders.sort(reverse=True)
        for _, key in remainders:
            if allocated_total >= target:
                break
            if allocations[key] < len(groups[key]):
                allocations[key] += 1
                allocated_total += 1

        rng = Random(seed)
        sampled: list[dict[str, Any]] = []
        for key, count in allocations.items():
            group_rows = groups[key]
            if count <= 0:
                continue
            if count >= len(group_rows):
                sampled.extend(group_rows)
            else:
                sampled.extend(rng.sample(group_rows, count))

        if len(sampled) < target:
            missing = target - len(sampled)
            selected_ids = {row["id"] for row in sampled}
            residual = [row for row in records if row["id"] not in selected_ids]
            if residual:
                sampled.extend(rng.sample(residual, min(missing, len(residual))))

        sampled.sort(key=lambda row: int(row["id"]))
        return sampled[:target]

    def export_manual_sample_csv(
        self, output_file: str | Path, n: int, seed: int = 42
    ) -> int:
        """Export stratified manual verification sample to CSV."""
        rows = self.sample_for_manual_verification(n=n, seed=seed)
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as file_handle:
            writer = csv.DictWriter(
                file_handle,
                fieldnames=[
                    "response_id",
                    "model",
                    "item_id",
                    "system_prompt",
                    "temperature",
                    "raw_response",
                    "score_final",
                    "human_score",
                    "human_justification",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "response_id": row["id"],
                        "model": row["model"],
                        "item_id": row["item_id"],
                        "system_prompt": row["system_prompt"],
                        "temperature": row["temperature"],
                        "raw_response": row["raw_response"],
                        "score_final": row["score_final"],
                        "human_score": "",
                        "human_justification": "",
                    }
                )
        return len(rows)

    def import_manual_verification_csv(self, file_path: str | Path) -> int:
        """Import manual coding rows from CSV."""
        imported = 0
        source = HUMAN_VALIDATION_SOURCE
        with Path(file_path).open("r", newline="", encoding="utf-8") as file_handle:
            reader = csv.DictReader(file_handle)
            for row in reader:
                response_id_raw = row.get("response_id")
                human_score = (row.get("human_score") or "").strip().upper()
                if not response_id_raw or human_score == "":
                    continue
                self._conn.execute(
                    """
                    INSERT INTO manual_verification (
                        response_id, human_score, human_justification, verified_at, source
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(response_id, source)
                    DO UPDATE SET
                        human_score = excluded.human_score,
                        human_justification = excluded.human_justification,
                        verified_at = excluded.verified_at,
                        kappa_judge1 = NULL,
                        kappa_judge2 = NULL;
                    """,
                    (
                        int(response_id_raw),
                        human_score,
                        row.get("human_justification") or None,
                        _utc_now_iso(),
                        source,
                    ),
                )
                imported += 1
        self._conn.commit()
        return imported

    def get_interjudge_pairs(self) -> list[tuple[str, str]]:
        """Return score pairs for inter-judge kappa."""
        rows = self._conn.execute("""
            SELECT score_judge1, score_judge2
            FROM responses
            WHERE score_judge1 IS NOT NULL
              AND score_judge2 IS NOT NULL;
            """).fetchall()
        return [(row["score_judge1"], row["score_judge2"]) for row in rows]

    def get_human_machine_pairs(
        self,
        source: str = HUMAN_VALIDATION_SOURCE,
    ) -> list[dict[str, Any]]:
        """Return merged judge/human pairs for one manual verification source."""
        normalized_source = self._normalize_manual_verification_source(source)
        rows = self._conn.execute(
            """
            SELECT
                mv.id,
                mv.response_id,
                mv.human_score,
                r.score_judge1,
                r.score_judge2,
                r.score_final
            FROM manual_verification mv
            JOIN responses r ON r.id = mv.response_id
            WHERE mv.human_score IS NOT NULL
              AND mv.source = ?;
            """,
            (normalized_source,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_response_diagnostics_dataframe(self) -> pd.DataFrame:
        """Return scored rows with prompts/responses for qualitative diagnostics."""
        query = """
            SELECT
                id,
                dataset_id,
                protocol_version,
                items_version,
                condition_block,
                trial_id,
                model,
                item_id,
                item_type,
                scenario,
                formulation,
                system_prompt,
                temperature,
                run,
                score_final,
                score_judge1,
                score_judge2,
                agreement_status,
                manual_review_needed,
                manual_score,
                temperature_applied,
                top_p_applied,
                thinking_enabled,
                is_refusal,
                is_error,
                user_prompt_text,
                raw_response,
                notes
            FROM responses;
        """
        return pd.read_sql_query(query, self._conn)

    def get_response_context_by_ids(
        self, response_ids: Iterable[int]
    ) -> dict[int, dict[str, Any]]:
        """Return response display context keyed by response id."""
        ids = [int(response_id) for response_id in response_ids]
        if not ids:
            return {}

        placeholders = ",".join("?" for _ in ids)
        rows = self._conn.execute(
            f"""
            SELECT
                id,
                model,
                item_id,
                item_type,
                scenario,
                formulation,
                system_prompt,
                temperature,
                run,
                user_prompt_text,
                raw_response,
                score_final
            FROM responses
            WHERE id IN ({placeholders});
            """,
            ids,
        ).fetchall()
        return {int(row["id"]): dict(row) for row in rows}

    def update_manual_kappas(
        self,
        kappa_judge1: float | None,
        kappa_judge2: float | None,
        source: str = HUMAN_VALIDATION_SOURCE,
    ) -> None:
        """Persist the latest human-machine kappas on all manual rows."""
        normalized_source = self._normalize_manual_verification_source(source)
        self._conn.execute(
            """
            UPDATE manual_verification
            SET kappa_judge1 = ?, kappa_judge2 = ?
            WHERE source = ?;
            """,
            (kappa_judge1, kappa_judge2, normalized_source),
        )
        self._conn.commit()

    def get_scored_dataframe(self) -> pd.DataFrame:
        """Return scored rows as a pandas DataFrame."""
        query = """
            SELECT
                id, dataset_id, protocol_version, items_version, condition_block, trial_id,
                model, item_id, item_type, scenario, formulation, system_prompt,
                temperature, run, score_final, score_judge1, score_judge2,
                agreement_status, manual_review_needed, manual_score,
                temperature_applied, top_p_applied, thinking_enabled,
                is_refusal, is_error, notes
            FROM responses;
        """
        return pd.read_sql_query(query, self._conn)

    def get_numeric_scores_dataframe(self) -> pd.DataFrame:
        """Return DataFrame with numeric score column for analyses."""
        df = self.get_scored_dataframe()
        if df.empty:
            return df
        score_map = {"+1": 1, "0": 0, "-1": -1}
        df = df.copy()
        df["score_numeric"] = df["score_final"].map(score_map)
        df = df[df["score_numeric"].notna()]
        return df

    def list_models(self) -> list[str]:
        """Return known model identifiers from responses or metadata."""
        rows = self._conn.execute("""
            SELECT DISTINCT model FROM responses
            UNION
            SELECT DISTINCT model FROM collection_metadata
            ORDER BY model;
        """).fetchall()
        return [row["model"] for row in rows]

    def get_collection_progress(self) -> list[dict[str, Any]]:
        """Return latest collection metadata row for each model."""
        rows = self._conn.execute("""
            SELECT cm.*
            FROM collection_metadata cm
            JOIN (
                SELECT model, MAX(id) AS latest_id
                FROM collection_metadata
                GROUP BY model
            ) latest
              ON latest.latest_id = cm.id
            ORDER BY cm.model;
            """).fetchall()
        return [dict(row) for row in rows]

    def save_json_report(self, report: dict[str, Any], output_file: str | Path) -> None:
        """Save a report dictionary as JSON."""
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as file_handle:
            json.dump(report, file_handle, indent=2, ensure_ascii=True)

    def execute_many(self, sql: str, rows: Iterable[tuple[Any, ...]]) -> None:
        """Execute batch statements."""
        self._conn.executemany(sql, rows)
        self._conn.commit()
