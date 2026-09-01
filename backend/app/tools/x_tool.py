"""Fake X timeline adapter."""

from pathlib import Path

from .json_source import JsonSource
from .models import XPost


class FakeXTool(JsonSource):
    def __init__(self, data_dir: Path) -> None:
        super().__init__(data_dir / "fake_x.json", XPost)

    def get_x_timeline(self) -> list[XPost]:
        return self.load()
