from fastapi import APIRouter, Request, Response, status

router = APIRouter()


@router.get("/health")
async def health(request: Request, response: Response) -> dict[str, str | None]:
    payload: dict[str, str | None] = {
        "status": "ok",
        "service": request.app.state.settings.app_name,
    }
    if not request.app.state.settings.agent_enabled:
        return payload

    agent_health = await request.app.state.hermes_client.health()
    payload["agent"] = agent_health.status
    payload["model"] = agent_health.model
    payload["agent_mode"] = agent_health.mode
    if agent_health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        payload["status"] = "degraded"
        payload["message"] = agent_health.message or "LM Studio is unavailable."
    return payload
