"""Normalized personal event models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    id: str
    source: str
    event_type: str
    title: str
    summary: str
    occurred_at: datetime
    importance: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Event(EventCreate):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
