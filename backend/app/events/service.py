"""Source ingestion and normalization into the local event store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from time import perf_counter
from typing import Protocol

from app.tools.calendar_tool import FakeCalendarTool
from app.tools.eufy_tool import FakeEufyTool
from app.tools.models import XPost

from .models import EventCreate
from .repository import EventRepository

logger = logging.getLogger(__name__)


@dataclass
class SourceSnapshot:
    x_posts: list = field(default_factory=list)
    eufy_events: list = field(default_factory=list)
    calendar_events: list = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)

    def relevant(self, now: datetime, recent_window_hours: float) -> "SourceSnapshot":
        """Keep recent past activity and only genuinely upcoming calendar events."""
        cutoff = now - timedelta(hours=recent_window_hours)
        return SourceSnapshot(
            x_posts=[post for post in self.x_posts if cutoff <= post.created_at <= now],
            eufy_events=[event for event in self.eufy_events if cutoff <= event.timestamp <= now],
            calendar_events=[event for event in self.calendar_events if event.start >= now],
            failures=dict(self.failures),
        )


class XTimelineTool(Protocol):
    def get_x_timeline(self) -> list[XPost]: ...


class EventService:
    def __init__(
        self,
        repository: EventRepository,
        x_tool: XTimelineTool,
        eufy_tool: FakeEufyTool,
        calendar_tool: FakeCalendarTool,
    ) -> None:
        self.repository = repository
        self.x_tool = x_tool
        self.eufy_tool = eufy_tool
        self.calendar_tool = calendar_tool

    def collect(self) -> SourceSnapshot:
        snapshot = SourceSnapshot()
        for source, attribute, operation in (
            ("x", "x_posts", self.x_tool.get_x_timeline),
            ("eufy", "eufy_events", self.eufy_tool.get_eufy_events),
            ("calendar", "calendar_events", self.calendar_tool.get_calendar_events),
        ):
            started = perf_counter()
            try:
                setattr(snapshot, attribute, operation())
                logger.info(
                    "tool_completed tool=%s duration_ms=%.2f",
                    source,
                    (perf_counter() - started) * 1000,
                )
            except Exception:  # A source failure must not expose internals or stop other sources.
                logger.warning(
                    "tool_failed tool=%s duration_ms=%.2f",
                    source,
                    (perf_counter() - started) * 1000,
                )
                snapshot.failures[source] = f"The {source.title()} source is currently unavailable."
        return snapshot

    def refresh(self) -> SourceSnapshot:
        snapshot = self.collect()
        normalized: list[EventCreate] = []

        for post in snapshot.x_posts:
            engagement = post.likes + (2 * post.reposts)
            normalized.append(
                EventCreate(
                    id=post.id,
                    source="x",
                    event_type="timeline_post",
                    title=post.topic,
                    summary=post.text,
                    occurred_at=post.created_at,
                    importance=min(1.0, 0.35 + engagement / 2000),
                    metadata={"author": post.author, "likes": post.likes, "reposts": post.reposts},
                )
            )

        for event in snapshot.eufy_events:
            readable_type = event.event_type.replace("_", " ")
            normalized.append(
                EventCreate(
                    id=event.id,
                    source="eufy",
                    event_type=event.event_type,
                    title=f"{event.camera} {readable_type}",
                    summary=f"{readable_type.title()} detected by {event.camera}.",
                    occurred_at=event.timestamp,
                    importance=0.8 if event.event_type == "person_detected" else 0.6,
                    metadata={"camera": event.camera},
                )
            )

        for event in snapshot.calendar_events:
            normalized.append(
                EventCreate(
                    id=event.id,
                    source="calendar",
                    event_type="meeting",
                    title=event.title,
                    summary=f"Scheduled from {event.start.strftime('%-I:%M %p')} to {event.end.strftime('%-I:%M %p')}.",
                    occurred_at=event.start,
                    importance=0.7,
                    metadata={"end": event.end.isoformat()},
                )
            )

        if normalized:
            self.repository.upsert_many(normalized)
        return snapshot
