from fastapi import APIRouter, HTTPException, Request, status

from app.agent.hermes import HermesUnavailableError
from app.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api")

_TOOL_SOURCES = {
    "get_x_timeline": "x",
    "get_x_summary": "x",
    "get_eufy_events": "eufy",
    "get_calendar_events": "calendar",
    "get_recent_events": "events",
}


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    if not request.app.state.settings.agent_enabled:
        return request.app.state.chat_service.answer(payload.message)

    try:
        reply = await request.app.state.hermes_client.ask(
            payload.message,
            request.state.request_id,
        )
    except HermesUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    sources = list(
        dict.fromkeys(
            source
            for tool in reply.selected_tools
            if (source := _TOOL_SOURCES.get(tool)) is not None
        )
    )
    return ChatResponse(answer=reply.answer, sources=sources)
