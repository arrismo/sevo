from dataclasses import replace

from fastapi.testclient import TestClient

from app.agent.hermes import HermesHealth, HermesReply, HermesUnavailableError


class StubHermes:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.message: str | None = None
        self.request_id: str | None = None

    async def ask(self, message: str, request_id: str) -> HermesReply:
        self.message = message
        self.request_id = request_id
        if self.unavailable:
            raise HermesUnavailableError(
                "LM Studio is not reachable or no compatible model is loaded. "
                "Start the LM Studio local server and try again."
            )
        return HermesReply(
            answer="There were two Front Door motion events. That's everything recorded.",
            selected_tools=["get_eufy_events"],
            model="local-test-model",
        )

    async def health(self) -> HermesHealth:
        if self.unavailable:
            return HermesHealth(
                status="unavailable",
                message="LM Studio is not reachable.",
            )
        return HermesHealth(status="ok", model="local-test-model")


def enable_agent(client: TestClient, stub: StubHermes) -> None:
    client.app.state.settings = replace(client.app.state.settings, agent_enabled=True)
    client.app.state.hermes_client = stub


def test_chat_uses_hermes_and_reports_selected_source(client: TestClient) -> None:
    stub = StubHermes()
    enable_agent(client, stub)

    response = client.post(
        "/api/chat",
        json={"message": "Was there camera movement?"},
        headers={"X-Request-ID": "request-123"},
    )

    assert response.status_code == 200
    assert response.json()["sources"] == ["eufy"]
    assert stub.message == "Was there camera movement?"
    assert stub.request_id == "request-123"


def test_lm_studio_unavailable_is_actionable(client: TestClient) -> None:
    enable_agent(client, StubHermes(unavailable=True))

    response = client.post("/api/chat", json={"message": "What is trending?"})

    assert response.status_code == 503
    assert "Start the LM Studio local server" in response.json()["detail"]


def test_health_reports_local_agent_and_model(client: TestClient) -> None:
    enable_agent(client, StubHermes())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["agent"] == "ok"
    assert response.json()["model"] == "local-test-model"


def test_health_is_degraded_when_agent_is_unavailable(client: TestClient) -> None:
    enable_agent(client, StubHermes(unavailable=True))
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert "LM Studio" in response.json()["message"]
