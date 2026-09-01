"""Sevo FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import catch_up, chat, events, health, sources
from app.catch_up import CatchUpService
from app.chat import ChatService
from app.config import Settings
from app.events.repository import EventRepository
from app.events.service import EventService
from app.tools.calendar_tool import FakeCalendarTool
from app.tools.eufy_tool import FakeEufyTool
from app.tools.x_tool import FakeXTool

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        repository = EventRepository(app_settings.database_path)
        repository.initialize()
        event_service = EventService(
            repository=repository,
            x_tool=FakeXTool(app_settings.data_dir),
            eufy_tool=FakeEufyTool(app_settings.data_dir),
            calendar_tool=FakeCalendarTool(app_settings.data_dir),
        )
        app.state.settings = app_settings
        app.state.repository = repository
        app.state.event_service = event_service
        app.state.catch_up_service = CatchUpService(event_service)
        app.state.chat_service = ChatService(event_service, app.state.catch_up_service)
        event_service.refresh()
        yield

    app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(catch_up.router)
    app.include_router(chat.router)
    app.include_router(sources.router)
    return app


app = create_app()
