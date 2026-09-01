"""Read-only X timeline adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .json_source import JsonSource
from .models import XPost


class FakeXTool(JsonSource):
    def __init__(self, data_dir: Path) -> None:
        super().__init__(data_dir / "fake_x.json", XPost)

    def get_x_timeline(self) -> list[XPost]:
        return self.load()


class XApiTool:
    """Read the authenticated user's X home timeline via the X API v2.

    This adapter is intentionally read-only. It only requests timeline data and
    maps it into Sevo's existing XPost model so the rest of the app can keep
    using the fake adapter boundary.
    """

    def __init__(
        self,
        bearer_token: str,
        user_id: str,
        base_url: str = "https://api.x.com",
        timeout_seconds: float = 20.0,
        limit: int = 20,
    ) -> None:
        if not bearer_token:
            raise ValueError("X bearer token is required when SEVO_X_SOURCE=api")
        if not user_id:
            raise ValueError("X user id is required when SEVO_X_SOURCE=api")
        self.bearer_token = bearer_token
        self.user_id = user_id
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.limit = min(max(limit, 5), 100)

    def get_x_timeline(self) -> list[XPost]:
        url = f"{self.base_url}/2/users/{self.user_id}/timelines/reverse_chronological"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params = {
            "max_results": self.limit,
            "tweet.fields": "created_at,public_metrics,context_annotations,entities",
            "expansions": "author_id",
            "user.fields": "username",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
        payload = response.json()
        users = {
            user.get("id"): user.get("username")
            for user in (payload.get("includes") or {}).get("users", [])
            if user.get("id")
        }
        return [self._post_from_record(record, users) for record in payload.get("data", [])]

    def _post_from_record(self, record: dict[str, Any], users: dict[str, str | None]) -> XPost:
        metrics = record.get("public_metrics") or {}
        author_id = record.get("author_id")
        username = users.get(author_id) or author_id or "unknown"
        return XPost(
            id=str(record["id"]),
            author=f"@{username}" if not str(username).startswith("@") else str(username),
            text=str(record.get("text") or ""),
            created_at=record["created_at"],
            likes=int(metrics.get("like_count") or 0),
            reposts=int(metrics.get("retweet_count") or 0),
            topic=self._topic(record),
        )

    def _topic(self, record: dict[str, Any]) -> str:
        annotations = record.get("context_annotations") or []
        for annotation in annotations:
            entity = annotation.get("entity") or {}
            name = str(entity.get("name") or "").strip()
            if name:
                return name
        hashtags = (record.get("entities") or {}).get("hashtags") or []
        if hashtags:
            tag = str(hashtags[0].get("tag") or "").strip()
            if tag:
                return tag
        return "X"
