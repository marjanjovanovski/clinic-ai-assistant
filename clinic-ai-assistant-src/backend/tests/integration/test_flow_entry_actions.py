# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib

from fastapi.testclient import TestClient


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, session_trace_logger

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "flow-entry-actions.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_booking_flow_entry_action_starts_contact_collection(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post(
        "/chat/action?tenant=milena_dental",
        json={"action": "booking"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["received_action"] == "booking"
    assert payload["session_status"] == "collecting_contact"
    assert payload["booking_progress"]["next_field"] == "name"
    assert "име" in payload["reply"].casefold()


def test_availability_flow_entry_action_uses_fresh_session_during_booking(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    booking_response = client.post(
        "/chat/action?tenant=milena_dental",
        json={"action": "booking"},
    )
    assert booking_response.status_code == 200
    booking_payload = booking_response.json()

    availability_response = client.post(
        "/chat/action?tenant=milena_dental",
        json={"action": "availability", "session_id": booking_payload["session_id"]},
    )

    assert availability_response.status_code == 200
    availability_payload = availability_response.json()
    assert availability_payload["received_action"] == "availability"
    assert availability_payload["session_id"] != booking_payload["session_id"]
    assert availability_payload["session_status"] == "active"
    assert availability_payload["booking_progress"] is None
    assert availability_payload["widget_payload"]["type"] == "slot-list"
    assert availability_payload["widget_payload"]["service_id"] == "consultation"


def test_catalog_flow_entry_action_returns_service_list(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post(
        "/chat/action?tenant=milena_dental",
        json={"action": "catalog"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["received_action"] == "catalog"
    assert payload["session_status"] == "active"
    assert "консултација" in payload["reply"].casefold()
