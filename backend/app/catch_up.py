"""Deterministic cross-source briefing logic for Phase 1."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Callable

from pydantic import BaseModel, Field

from app.events.service import EventService, SourceSnapshot


class CatchUpItem(BaseModel):
    source: str
    title: str
    summary: str
    importance: float = Field(exclude=True)


class CatchUpResponse(BaseModel):
    summary: str
    items: list[CatchUpItem]
    unavailable_sources: list[str] = Field(default_factory=list)


class CatchUpService:
    def __init__(
        self,
        event_service: EventService,
        recent_window_hours: float = 48.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.event_service = event_service
        self.recent_window_hours = recent_window_hours
        self.clock = clock or (lambda: datetime.now().astimezone())

    def build(self, now: datetime | None = None) -> CatchUpResponse:
        reference = now or self.clock()
        snapshot = self.event_service.refresh().relevant(reference, self.recent_window_hours)
        items = self._rank(snapshot, reference)
        count = len(items)
        heading = f"{count} thing{'s' if count != 1 else ''} worth knowing:"
        bullets = "\n".join(f"• {item.summary}" for item in items)
        completion = "That's everything notable right now."
        summary = "\n\n".join(part for part in (heading, bullets, completion) if part)
        return CatchUpResponse(
            summary=summary,
            items=items,
            unavailable_sources=sorted(snapshot.failures),
        )

    def _rank(self, snapshot: SourceSnapshot, now: datetime | None) -> list[CatchUpItem]:
        candidates: list[CatchUpItem] = []

        if snapshot.eufy_events:
            by_camera: dict[str, list] = defaultdict(list)
            for event in snapshot.eufy_events:
                by_camera[event.camera].append(event)
            camera, events = max(by_camera.items(), key=lambda pair: len(pair[1]))
            count = len(events)
            event_word = "event" if count == 1 else "events"
            candidates.append(
                CatchUpItem(
                    source="eufy",
                    title=f"{camera} activity",
                    summary=f"Your {camera} camera recorded {count} activity {event_word}.",
                    importance=0.9,
                )
            )

        if snapshot.x_posts:
            topics: dict[str, tuple[int, int]] = {}
            for post in snapshot.x_posts:
                count, engagement = topics.get(post.topic, (0, 0))
                topics[post.topic] = (count + 1, engagement + post.likes + 2 * post.reposts)
            topic, (count, _) = max(topics.items(), key=lambda pair: (pair[1][0], pair[1][1]))
            candidates.append(
                CatchUpItem(
                    source="x",
                    title=f"{topic} is trending",
                    summary=f"{topic} is the most active topic on your X timeline ({count} posts).",
                    importance=0.8,
                )
            )

        if snapshot.calendar_events:
            reference = now or datetime.now().astimezone()
            event = min(snapshot.calendar_events, key=lambda item: item.start)
            event_reference = reference.astimezone(event.start.tzinfo)
            day_delta = (event.start.date() - event_reference.date()).days
            if day_delta == 0:
                day = "today"
            elif day_delta == 1:
                day = "tomorrow"
            else:
                day = f"on {event.start.strftime('%b %-d')}"
            candidates.append(
                CatchUpItem(
                    source="calendar",
                    title=event.title,
                    summary=f"You have {event.title} {day} at {event.start.strftime('%-I:%M %p')}.",
                    importance=0.7,
                )
            )

        return sorted(candidates, key=lambda item: item.importance, reverse=True)
