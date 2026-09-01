"""Private HTTP client for the isolated Hermes Agent service."""

from __future__ import annotations

import logging
from time import perf_counter

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HermesUnavailableError(RuntimeError):
    """Hermes or its local model endpoint is unavailable."""


class HermesReply(BaseModel):
    answer: str
    selected_tools: list[str] = Field(default_factory=list)
    model: str


class HermesHealth(BaseModel):
    status: str
    model: str | None = None
    message: str | None = None


class HermesClient:
    def __init__(self, base_url: str, timeout_seconds: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def ask(self, message: str, request_id: str) -> HermesReply:
        started = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={"message": message},
                    headers={"X-Request-ID": request_id},
                )
                response.raise_for_status()
                reply = HermesReply.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "hermes_request_failed request_id=%s duration_ms=%.2f error_type=%s",
                request_id,
                (perf_counter() - started) * 1000,
                type(exc).__name__,
            )
            raise HermesUnavailableError(
                "LM Studio is not reachable or no compatible model is loaded. "
                "Start the LM Studio local server and try again."
            ) from exc

        logger.info(
            "model_request_completed request_id=%s model=%s tools=%s duration_ms=%.2f",
            request_id,
            reply.model,
            ",".join(reply.selected_tools) or "none",
            (perf_counter() - started) * 1000,
        )
        return reply

    async def health(self) -> HermesHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                payload = response.json()
                return HermesHealth.model_validate(payload)
        except (httpx.HTTPError, ValueError):
            return HermesHealth(
                status="unavailable",
                message="Hermes Agent is not reachable.",
            )
