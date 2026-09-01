"""Deterministic natural-language routing for the fake-data MVP."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel, Field

from app.catch_up import CatchUpService
from app.events.service import EventService


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)


class ChatService:
    """Route a small, explicit set of read-only intents without an LLM."""

    def __init__(self, event_service: EventService, catch_up_service: CatchUpService) -> None:
        self.event_service = event_service
        self.catch_up_service = catch_up_service

    def answer(self, message: str, now: datetime | None = None) -> ChatResponse:
        query = message.strip().casefold()

        if any(phrase in query for phrase in ("catch me up", "what happened", "what should i know", "anything unusual", "what did i miss")):
            briefing = self.catch_up_service.build(now)
            return ChatResponse(answer=briefing.summary, sources=[item.source for item in briefing.items])

        if any(word in query for word in ("camera", "eufy", "motion", "movement", "front door", "backyard")):
            return self._camera_answer(query)

        if any(word in query for word in ("trending", "trend", "timeline", " x ", "twitter")) or query.startswith("x "):
            return self._x_answer()

        if any(word in query for word in ("calendar", "meeting", "schedule", "appointment", "today", "tomorrow")):
            return self._calendar_answer(now)

        return ChatResponse(
            answer=(
                "I can currently answer questions about camera activity, your X timeline, "
                "and upcoming calendar events. You can also ask me to catch you up."
            )
        )

    def _camera_answer(self, query: str) -> ChatResponse:
        snapshot = self.event_service.collect()
        if "eufy" in snapshot.failures:
            return ChatResponse(answer="The Eufy source is currently unavailable.")

        events = snapshot.eufy_events
        camera = None
        for name in {event.camera for event in events}:
            if name.casefold() in query:
                camera = name
                events = [event for event in events if event.camera == name]
                break

        if not events:
            location = f" at the {camera}" if camera else ""
            return ChatResponse(answer=f"No camera activity was recorded{location}.", sources=["eufy"])

        location = camera or "your cameras"
        times = ", ".join(event.timestamp.strftime("%-I:%M %p") for event in events)
        event_word = "event" if len(events) == 1 else "events"
        return ChatResponse(
            answer=f"Yes. {location} recorded {len(events)} activity {event_word}, at {times}. That's all the activity in the sample data.",
            sources=["eufy"],
        )

    def _x_answer(self) -> ChatResponse:
        snapshot = self.event_service.collect()
        if "x" in snapshot.failures:
            return ChatResponse(answer="The X source is currently unavailable.")
        if not snapshot.x_posts:
            return ChatResponse(answer="There are no posts in the sample timeline.", sources=["x"])

        topics: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        for post in snapshot.x_posts:
            count, engagement = topics[post.topic]
            topics[post.topic] = (count + 1, engagement + post.likes + 2 * post.reposts)
        ranked = sorted(topics.items(), key=lambda item: (item[1][0], item[1][1]), reverse=True)
        topic, (count, _) = ranked[0]
        return ChatResponse(
            answer=f"{topic} is the most active topic on your X timeline, appearing in {count} posts. That's the main trend right now.",
            sources=["x"],
        )

    def _calendar_answer(self, now: datetime | None) -> ChatResponse:
        snapshot = self.event_service.collect()
        if "calendar" in snapshot.failures:
            return ChatResponse(answer="The Calendar source is currently unavailable.")
        if not snapshot.calendar_events:
            return ChatResponse(answer="There are no events in the sample calendar.", sources=["calendar"])

        reference = now or datetime.now().astimezone()
        upcoming = [event for event in snapshot.calendar_events if event.start >= reference]
        if not upcoming:
            return ChatResponse(answer="There are no upcoming events in the sample calendar.", sources=["calendar"])

        event = min(upcoming, key=lambda item: item.start)
        local_reference = reference.astimezone(event.start.tzinfo)
        day_delta = (event.start.date() - local_reference.date()).days
        day = "today" if day_delta == 0 else "tomorrow" if day_delta == 1 else f"on {event.start.strftime('%b %-d')}"
        return ChatResponse(
            answer=f"Your next event is {event.title} {day} at {event.start.strftime('%-I:%M %p')}. That's the only upcoming event in the sample calendar.",
            sources=["calendar"],
        )
