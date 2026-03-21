import importlib

from fastapi.testclient import TestClient


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, session_trace_logger

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "cal-ui.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_cal_html_is_served_as_frontend_sandbox(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/cal.html")

    assert response.status_code == 200
    assert "Scheduling Sandbox" in response.text
    assert 'id="loadSlotsButton"' in response.text
    assert 'id="patientNameInput"' in response.text


def test_cal_html_wires_slot_buttons_and_booking_request(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/cal.html")

    assert "function addSlotChoices" in response.text
    assert "async function bookSelectedSlot" in response.text
    assert 'className = "slot-button"' in response.text
    assert "/scheduling/book?tenant=" in response.text
    assert "Booked from cal.html sandbox" in response.text

