"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def local_now() -> datetime:
    return datetime.now().astimezone()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Sevo"
    data_dir: Path = PROJECT_ROOT / "data"
    database_path: Path = PROJECT_ROOT / ".sevo" / "sevo.db"
    agent_enabled: bool = True
    hermes_base_url: str = "http://hermes:8001"
    hermes_timeout_seconds: float = 240.0
    recent_window_hours: float = 48.0
    clock: Callable[[], datetime] = local_now

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("SEVO_APP_NAME", "Sevo"),
            data_dir=Path(os.getenv("SEVO_DATA_DIR", str(PROJECT_ROOT / "data"))),
            database_path=Path(
                os.getenv("SEVO_DATABASE_PATH", str(PROJECT_ROOT / ".sevo" / "sevo.db"))
            ),
            agent_enabled=os.getenv("SEVO_AGENT_ENABLED", "true").casefold() in {"1", "true", "yes"},
            hermes_base_url=os.getenv("HERMES_BASE_URL", "http://hermes:8001").rstrip("/"),
            hermes_timeout_seconds=float(os.getenv("HERMES_TIMEOUT_SECONDS", "240")),
            recent_window_hours=max(float(os.getenv("SEVO_RECENT_WINDOW_HOURS", "48")), 1.0),
        )
