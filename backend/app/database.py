"""SQLite setup for the privacy-minimising Quiet Steps prototype."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def database_path() -> Path:
    """Return the configured local SQLite path without creating it yet."""
    default_path = Path(__file__).resolve().parents[1] / "data" / "quiet_steps.sqlite3"
    return Path(os.getenv("QUIET_STEPS_DB_PATH", default_path)).expanduser()


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Yield a short-lived SQLite connection with foreign keys enabled."""
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialise_database() -> None:
    """Create the small local schema used by the prototype if necessary."""
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                skill TEXT NOT NULL CHECK (skill IN ('paced_breathing', 'stop')),
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'left')),
                seconds_completed INTEGER NOT NULL DEFAULT 0
                    CHECK (seconds_completed >= 0 AND seconds_completed <= 90),
                checkin_submitted INTEGER NOT NULL DEFAULT 0
                    CHECK (checkin_submitted IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS conversation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user_event', 'assistant')),
                event_type TEXT NOT NULL CHECK (
                    event_type IN ('checkin_submitted', 'bounded_acknowledgement')
                ),
                content TEXT,
                suggested_skill TEXT CHECK (
                    suggested_skill IS NULL
                    OR suggested_skill IN ('paced_breathing', 'stop')
                ),
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
                ON sessions(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_conversation_session
                ON conversation_events(session_id, id);

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                client_message_id TEXT,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'complete', 'failed')),
                suggested_skill TEXT CHECK (
                    suggested_skill IS NULL
                    OR suggested_skill IN ('paced_breathing', 'stop')
                ),
                supporting_message_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                UNIQUE(conversation_id, client_message_id)
            );

            CREATE TABLE IF NOT EXISTS rag_requests (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                user_message_id TEXT NOT NULL
                    REFERENCES messages(id) ON DELETE CASCADE,
                planned_sql TEXT,
                retrieval_status TEXT NOT NULL
                    CHECK (retrieval_status IN ('completed', 'rejected', 'provider_failed')),
                retrieved_message_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_updated_at
                ON conversations(updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id, id);
            CREATE INDEX IF NOT EXISTS idx_rag_requests_conversation_id
                ON rag_requests(conversation_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS local_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                preferred_skill TEXT CHECK (
                    preferred_skill IS NULL
                    OR preferred_skill IN ('paced_breathing', 'stop')
                ),
                motion_preference TEXT NOT NULL DEFAULT 'system'
                    CHECK (motion_preference IN ('system', 'reduce', 'standard')),
                chat_personalization_enabled INTEGER NOT NULL DEFAULT 0
                    CHECK (chat_personalization_enabled IN (0, 1)),
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mood_entries (
                day TEXT PRIMARY KEY,
                mood TEXT NOT NULL CHECK (
                    mood IN ('very_low', 'low', 'in_between', 'good', 'very_good')
                ),
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_mood_entries_day
                ON mood_entries(day DESC);
            """
        )
        # One accountless profile belongs to this local prototype installation.
        # It stores only voluntarily selected interface and practice preferences.
        db.execute("INSERT OR IGNORE INTO local_profile (id) VALUES (1)")
