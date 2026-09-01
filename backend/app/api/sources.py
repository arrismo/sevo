from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/sources")
def sources() -> dict[str, list[dict[str, str]]]:
    return {
        "sources": [
            {"id": "x", "name": "X", "status": "fake"},
            {"id": "eufy", "name": "Eufy", "status": "fake"},
            {"id": "calendar", "name": "Calendar", "status": "fake"},
        ]
    }
