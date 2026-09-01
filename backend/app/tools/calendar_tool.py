"""Fake read-only calendar adapter."""

from pathlib import Path

from .json_source import JsonSource
from .models import CalendarEvent


class FakeCalendarTool(JsonSource):
    def __init__(self, data_dir: Path) -> None:
        super().__init__(data_dir / "fake_calendar.json", CalendarEvent)

    def get_calendar_events(self) -> list[CalendarEvent]:
        return self.load()
