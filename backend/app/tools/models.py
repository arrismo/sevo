"""Structured source records returned by Sevo tools."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class XPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    author: str
    text: str
    created_at: datetime
    likes: int = 0
    reposts: int = 0
    topic: str


class EufyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    camera: str
    event_type: str
    timestamp: datetime


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    start: datetime
    end: datetime
