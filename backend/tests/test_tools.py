from pathlib import Path

import httpx
import pytest

from app.tools.base import ToolAuthorizationError, ToolPermission
from app.tools.calendar_tool import FakeCalendarTool
from app.tools.eufy_tool import FakeEufyTool
from app.tools.x_tool import FakeXTool, XApiTool


def test_x_fake_data_retrieval(data_dir: Path) -> None:
    posts = FakeXTool(data_dir).get_x_timeline()
    assert len(posts) == 3
    assert posts[0].author == "@example"
    assert posts[0].created_at.tzinfo is not None


def test_x_api_maps_home_timeline_without_writes() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "tweet_1",
                        "author_id": "user_1",
                        "text": "Read-only X post",
                        "created_at": "2026-09-01T12:00:00Z",
                        "public_metrics": {"like_count": 4, "retweet_count": 2},
                        "context_annotations": [{"entity": {"name": "AI"}}],
                    }
                ],
                "includes": {"users": [{"id": "user_1", "username": "example"}]},
            },
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    from app.tools import x_tool

    x_tool.httpx.Client = client_factory
    try:
        posts = XApiTool("token", "123", base_url="https://x.test").get_x_timeline()
    finally:
        x_tool.httpx.Client = original_client

    assert len(requests) == 1
    assert requests[0].url.path == "/2/users/123/timelines/reverse_chronological"
    assert posts[0].author == "@example"
    assert posts[0].topic == "AI"
    assert posts[0].likes == 4
    assert posts[0].reposts == 2
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
