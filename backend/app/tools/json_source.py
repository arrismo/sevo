"""Safe loader for project-owned fake JSON data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

from .base import ReadOnlyTool, ToolPermission

T = TypeVar("T", bound=BaseModel)


class JsonSource(ReadOnlyTool):
    def __init__(self, path: Path, model: type[T]) -> None:
        self.path = path
        self._adapter = TypeAdapter(list[model])  # type: ignore[valid-type]

    def load(self) -> list[T]:
        self.authorize(ToolPermission.READ)
        # Paths are supplied by application configuration, never source content.
        with self.path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        return self._adapter.validate_python(payload)
