from fastapi import APIRouter, Request

from app.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    return request.app.state.chat_service.answer(payload.message)
