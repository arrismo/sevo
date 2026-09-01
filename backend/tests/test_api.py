from datetime import datetime, timezone

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Sevo"}


def test_sources_report_fake_x_by_default(client: TestClient) -> None:
    response = client.get("/api/sources")
    assert response.status_code == 200
    x_source = next(source for source in response.json()["sources"] if source["id"] == "x")
    assert x_source["status"] == "fake"


def test_events_are_normalized_and_persisted(client: TestClient) -> None:
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 7
    assert {event["source"] for event in events} == {"x", "eufy", "calendar"}
    front_door = next(event for event in events if event["id"] == "eufy_001")
    assert front_door["event_type"] == "motion"
    assert front_door["metadata"] == {"camera": "Front Door"}


def test_catch_up_is_concise_and_complete(client: TestClient) -> None:
    response = client.post("/api/catch-up")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 3
    assert [item["source"] for item in payload["items"]] == ["eufy", "x", "calendar"]
    assert "OpenAI developer news" in payload["summary"]
    assert "Team Standup" in payload["summary"]
    assert payload["summary"].endswith("That's everything notable right now.")
    assert "importance" not in payload["items"][0]


def test_calendar_label_uses_event_timezone(client: TestClient) -> None:
    now = datetime(2026, 9, 1, 18, 47, tzinfo=timezone.utc)
    briefing = client.app.state.catch_up_service.build(now=now)
    calendar_item = next(item for item in briefing.items if item.source == "calendar")
    assert "tomorrow" in calendar_item.summary


def test_catch_up_excludes_stale_activity_and_past_calendar(client: TestClient) -> None:
    now = datetime(2026, 9, 3, 18, 0, tzinfo=timezone.utc)
    briefing = client.app.state.catch_up_service.build(now=now)
    assert briefing.items == []
    assert briefing.summary == "0 things worth knowing:\n\nThat's everything notable right now."


def test_past_calendar_event_is_not_used_as_upcoming(client: TestClient) -> None:
    now = datetime(2026, 9, 2, 14, 0, tzinfo=timezone.utc)
    briefing = client.app.state.catch_up_service.build(now=now)
    assert "calendar" not in {item.source for item in briefing.items}


def test_one_source_failure_returns_partial_briefing(client: TestClient, monkeypatch) -> None:
    service = client.app.state.event_service

    def unavailable():
        raise ConnectionError("secret internal detail")

    monkeypatch.setattr(service.eufy_tool, "get_eufy_events", unavailable)
    payload = client.post("/api/catch-up").json()
    assert payload["unavailable_sources"] == ["eufy"]
    assert {item["source"] for item in payload["items"]} == {"x", "calendar"}
    assert "secret internal detail" not in str(payload)


def test_event_limit_is_validated(client: TestClient) -> None:
    assert client.get("/api/events?limit=0").status_code == 422
