"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Sevo"
    data_dir: Path = PROJECT_ROOT / "data"
    database_path: Path = PROJECT_ROOT / ".sevo" / "sevo.db"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("SEVO_APP_NAME", "Sevo"),
            data_dir=Path(os.getenv("SEVO_DATA_DIR", str(PROJECT_ROOT / "data"))),
            database_path=Path(
                os.getenv("SEVO_DATABASE_PATH", str(PROJECT_ROOT / ".sevo" / "sevo.db"))
            ),
        )
