from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _existing_columns_sqlite(engine: Engine, table_name: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def ensure_meetings_schema(engine: Engine) -> None:
    columns = _existing_columns_sqlite(engine, "meetings")
    expected = {
        "processed_status": "TEXT NOT NULL DEFAULT 'idle'",
        "processed_started_at": "DATETIME NULL",
        "processed_finished_at": "DATETIME NULL",
        "processed_error": "TEXT NULL",
        "has_processed_transcript": "BOOLEAN NOT NULL DEFAULT 0",
        "video_file_path": "TEXT NULL",
        "video_url": "TEXT NULL",
    }
    missing = [name for name in expected if name not in columns]
    if not missing:
        return
    logger.info("Applying meetings schema patch, missing columns=%s", ",".join(missing))
    with engine.begin() as conn:
        for name in missing:
            conn.execute(text(f"ALTER TABLE meetings ADD COLUMN {name} {expected[name]}"))
