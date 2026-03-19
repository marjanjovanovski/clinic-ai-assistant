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


def _build_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent

    ai_agent.SESSION_STATE.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_booking_transition_and_contact_collection(monkeypatch):
    from app.services import lead_store

    client = _build_client(monkeypatch)

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


def test_unknown_name_confirmation_can_store_user_value(monkeypatch):
    from app.services import ai_agent, lead_store

    client = _build_client(monkeypatch)
    monkeypatch.setattr(ai_agent.random, "choice", lambda options: ai_agent.UNKNOWN_NAME_CONFIRM_MODE)

    first = client.post("/chat?tenant=milena_dental", json={"message": "болка и пломба"}).json()
    session_id = first["session_id"]

    client.post("/chat?tenant=milena_dental", json={"message": "да", "session_id": session_id})
    third = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "V.", "session_id": session_id},
    ).json()
    fourth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "може", "session_id": session_id},
    ).json()

    assert "V." in third["reply"]
    assert fourth["session_status"] == "collecting_contact"
    assert "телефон" in fourth["reply"]

    stored = lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"]["name"] == "V."


def test_unknown_name_retry_accepts_second_attempt(monkeypatch):
    from app.services import ai_agent, lead_store

    client = _build_client(monkeypatch)
    monkeypatch.setattr(ai_agent.random, "choice", lambda options: ai_agent.UNKNOWN_NAME_REPEAT_MODE)

    first = client.post("/chat?tenant=milena_dental", json={"message": "болка и пломба"}).json()
    session_id = first["session_id"]

    client.post("/chat?tenant=milena_dental", json={"message": "да", "session_id": session_id})
    third = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "V.", "session_id": session_id},
    ).json()
    fourth = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "Vasilie", "session_id": session_id},
    ).json()

    assert "повторно" in third["reply"]
    assert fourth["session_status"] == "collecting_contact"
    assert "телефон" in fourth["reply"]

    stored = lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"]["name"] == "Vasilie"


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
