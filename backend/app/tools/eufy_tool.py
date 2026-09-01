"""Fake Eufy event metadata adapter; it never accesses images or video."""

from pathlib import Path

from .json_source import JsonSource
from .models import EufyEvent


class FakeEufyTool(JsonSource):
    def __init__(self, data_dir: Path) -> None:
        super().__init__(data_dir / "fake_eufy.json", EufyEvent)

    def get_eufy_events(self) -> list[EufyEvent]:
        return self.load()
