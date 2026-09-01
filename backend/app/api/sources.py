from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


@router.get("/sources")
def sources(request: Request) -> dict[str, list[dict[str, str]]]:
    x_status = "api" if request.app.state.settings.x_source == "api" else "fake"
    return {
        "sources": [
            {"id": "x", "name": "X", "status": x_status},
            {"id": "eufy", "name": "Eufy", "status": "fake"},
            {"id": "calendar", "name": "Calendar", "status": "fake"},
        ]
    }
