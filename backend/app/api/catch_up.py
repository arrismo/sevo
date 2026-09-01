from fastapi import APIRouter, Request

from app.catch_up import CatchUpResponse

router = APIRouter(prefix="/api")


@router.post("/catch-up", response_model=CatchUpResponse)
def catch_up(request: Request) -> CatchUpResponse:
    return request.app.state.catch_up_service.build()
