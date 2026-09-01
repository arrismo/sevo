from fastapi import APIRouter, Query, Request

from app.events.models import Event

router = APIRouter(prefix="/api")


@router.get("/events", response_model=list[Event])
def events(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> list[Event]:
    request.app.state.event_service.refresh()
    return request.app.state.repository.list_recent(limit)
