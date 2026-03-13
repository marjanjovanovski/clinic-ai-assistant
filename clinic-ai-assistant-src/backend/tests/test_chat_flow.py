import importlib

from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "болка и пломба":
            return FakeResponse(
                '{"intent":"suggest_service","service_id":"filling","message":"Препорачуваме пломба. Дали сакате да закажете?"}'
            )
        if message == "здраво":
            return FakeResponse(
                '{"intent":"greeting","service_id":"unknown","message":"Здраво! Како можам да помогнам?"}'
            )
        return FakeResponse(
            '{"intent":"fallback","service_id":"unknown","message":"Извинете, не можев да разберам."}'
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def test_booking_transition_and_contact_collection(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store

    ai_agent.SESSION_STATE.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    first = client.post("/chat?tenant=milena_dental", json={"message": "болка и пломба"}).json()
    session_id = first["session_id"]

    second = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "да", "session_id": session_id},
    ).json()
    third = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "Марјан", "session_id": session_id},
    ).json()
    fourth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "070000000", "session_id": session_id},
    ).json()
    fifth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "mail@test.mk", "session_id": session_id},
    ).json()

    assert first["session_status"] == "active"
    assert second["session_status"] == "collecting_contact"
    assert "име" in second["reply"]
    assert "телефон" in third["reply"]
    assert "е-пошта" in fourth["reply"]
    assert fifth["session_status"] == "completed"

    stored = lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["stage"] == "completed"
    assert stored["data"]["name"] == "Марјан"


def test_request_validation(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.post("/chat?tenant=milena_dental", json={"message": "   "})
    assert response.status_code == 422

    response = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "ok", "session_id": "x" * 129},
    )
    assert response.status_code == 422
