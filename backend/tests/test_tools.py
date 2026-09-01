from pathlib import Path

import pytest

from app.tools.base import ToolAuthorizationError, ToolPermission
from app.tools.calendar_tool import FakeCalendarTool
from app.tools.eufy_tool import FakeEufyTool
from app.tools.x_tool import FakeXTool


def test_x_fake_data_retrieval(data_dir: Path) -> None:
    posts = FakeXTool(data_dir).get_x_timeline()
    assert len(posts) == 3
    assert posts[0].author == "@example"
    assert posts[0].created_at.tzinfo is not None


def test_eufy_retrieves_metadata_only(data_dir: Path) -> None:
    events = FakeEufyTool(data_dir).get_eufy_events()
    assert {event.camera for event in events} == {"Front Door", "Backyard"}
    assert set(events[0].model_fields) == {"id", "camera", "event_type", "timestamp"}


def test_calendar_retrieval(data_dir: Path) -> None:
    events = FakeCalendarTool(data_dir).get_calendar_events()
    assert events[0].title == "Team Standup"
    assert events[0].end > events[0].start


def test_tools_reject_write_authorization(data_dir: Path) -> None:
    tool = FakeXTool(data_dir)
    with pytest.raises(ToolAuthorizationError):
        tool.authorize(ToolPermission.WRITE)
