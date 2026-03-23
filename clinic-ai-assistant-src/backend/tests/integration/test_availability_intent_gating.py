import importlib

from fastapi.testclient import TestClient


def _mock_profile_loader(real_loader):
    def _load_profile(tenant: str):
        profile = real_loader(tenant)
        if tenant == "milena_dental":
            profile = dict(profile)
            scheduling = dict(profile.get("scheduling") or {})
            scheduling["provider"] = "mock"
            profile["scheduling"] = scheduling
        return profile

    return _load_profile


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "check availability":
            return FakeResponse(
                '{"intent":"availability_lookup","service_id":"consultation","message":"Еве неколку слободни термини:"}'
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
    import app.services.config_loader as config_loader_module
    import app.services.scheduling.service as scheduling_service_module

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "availability_intent.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)
    mocked_loader = _mock_profile_loader(config_loader_module.load_profile_config)
    monkeypatch.setattr(config_loader_module, "load_profile_config", mocked_loader)
    monkeypatch.setattr(scheduling_service_module, "load_profile_config", mocked_loader)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app), ai_agent


def test_availability_intent_triggers_scheduling_without_starting_booking(monkeypatch, tmp_path):
    client, ai_agent = _build_client(monkeypatch, tmp_path)

    response = client.post("/chat?tenant=milena_dental", json={"message": "check availability"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_status"] == "active"
    assert payload["booking_progress"] is None
    assert "слободни термини" in payload["reply"]
    assert "09:00" in payload["reply"]

    session_key = ai_agent._session_key("milena_dental", payload["session_id"])
    scheduling_state = ai_agent.SESSION_STATE[session_key]["scheduling"]
    assert ai_agent.AVAILABILITY_INTENT_MARKER_KEY not in ai_agent.SESSION_STATE[session_key]
    assert scheduling_state["operation"] == "availability_lookup"
    assert scheduling_state["status"] == "completed"
    assert scheduling_state["output_payload"]["result"]["provider"] == "mock"
    assert scheduling_state["output_payload"]["result"]["slots"][0]["slot_id"].startswith("mock|")
    assert scheduling_state["booking_handoff_ready"] is True


def test_availability_confirmation_hands_off_into_booking_collection(monkeypatch, tmp_path):
    client, ai_agent = _build_client(monkeypatch, tmp_path)

    first = client.post("/chat?tenant=milena_dental", json={"message": "check availability"})
    assert first.status_code == 200
    first_payload = first.json()

    second = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "da", "session_id": first_payload["session_id"]},
    )

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["session_status"] == "collecting_contact"
    assert second_payload["booking_progress"]["next_field"] == "name"

    session_key = ai_agent._session_key("milena_dental", first_payload["session_id"])
    state = ai_agent.SESSION_STATE[session_key]
    assert state["stage"] == "collecting_contact"
    assert state["service_id"] == "consultation"
    assert "scheduling" not in state
    assert state["scheduling_handoff"]["source"] == "scheduling_availability"
    assert state["scheduling_handoff"]["reason"] == "confirmed_interest_after_availability"
    assert state["scheduling_handoff"]["slot_count"] >= 1
    assert state["scheduling_handoff"]["availability_result"]["slots"][0]["slot_id"].startswith("mock|")


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
