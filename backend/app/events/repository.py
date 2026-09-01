"""Small SQLite repository for normalized Sevo events."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Event, EventCreate


class EventRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    importance REAL NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at DESC)"
            )

    def upsert_many(self, events: list[EventCreate]) -> None:
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO events (
                    id, source, event_type, title, summary, occurred_at, importance, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source=excluded.source,
                    event_type=excluded.event_type,
                    title=excluded.title,
                    summary=excluded.summary,
                    occurred_at=excluded.occurred_at,
                    importance=excluded.importance,
                    metadata_json=excluded.metadata_json
                """,
                [
                    (
                        event.id,
                        event.source,
                        event.event_type,
                        event.title,
                        event.summary,
                        event.occurred_at.isoformat(),
                        event.importance,
                        json.dumps(event.metadata),
                    )
                    for event in events
                ],
            )

    def list_recent(self, limit: int = 50) -> list[Event]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY occurred_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            Event(
                id=row["id"],
                source=row["source"],
                event_type=row["event_type"],
                title=row["title"],
                summary=row["summary"],
                occurred_at=row["occurred_at"],
                importance=row["importance"],
                metadata=json.loads(row["metadata_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
