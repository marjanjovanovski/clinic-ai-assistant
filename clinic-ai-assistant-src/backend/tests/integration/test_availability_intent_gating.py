import importlib

from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "check availability":
            return FakeResponse(
                '{"intent":"availability_lookup","service_id":"unknown","message":"Ќе ми требаат неколку ваши податоци за да закажеме. Да почнеме со вашето име."}'
            )
        if message == "болка и пломба":
            return FakeResponse(
                '{"intent":"suggest_service","service_id":"consultation","message":"Препорачуваме консултација. Дали сакате да закажете?"}'
            )
        return FakeResponse(
            '{"intent":"fallback","service_id":"unknown","message":"fallback"}'
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store, session_trace_logger

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "availability_intent.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app), ai_agent


def test_availability_intent_marks_internal_state_without_starting_booking(monkeypatch, tmp_path):
    client, ai_agent = _build_client(monkeypatch, tmp_path)

    response = client.post("/chat?tenant=milena_dental", json={"message": "check availability"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_status"] == "active"
    assert payload["booking_progress"] is None
    assert "вашето име" in payload["reply"]

    session_key = ai_agent._session_key("milena_dental", payload["session_id"])
    assert ai_agent.SESSION_STATE[session_key][ai_agent.AVAILABILITY_INTENT_MARKER_KEY] is True
    assert ai_agent.SESSION_STATE[session_key].get("stage") is None


def test_normal_booking_path_still_starts_contact_collection(monkeypatch, tmp_path):
    client, _ = _build_client(monkeypatch, tmp_path)

    first = client.post("/chat?tenant=milena_dental", json={"message": "болка и пломба"})
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["session_status"] == "active"

    second = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "да", "session_id": first_payload["session_id"]},
    )

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["session_status"] == "collecting_contact"
    assert second_payload["booking_progress"]["next_field"] == "name"

