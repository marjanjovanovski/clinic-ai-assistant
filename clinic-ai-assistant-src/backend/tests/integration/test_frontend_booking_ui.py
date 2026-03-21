import importlib

from fastapi.testclient import TestClient


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, session_trace_logger

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "frontend.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_agent_page_includes_booking_progress_shell(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert response.status_code == 200
    assert 'id="bookingProgress"' in response.text
    assert 'id="bookingResetButton"' in response.text
    assert 'id="bookingProgressSteps"' in response.text
    assert 'id="bookingSummary"' in response.text
    assert 'id="bookingSummaryFields"' in response.text


def test_booking_progress_script_wires_active_and_editable_states(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert 'stepEl.classList.add("editable")' in response.text
    assert 'stepEl.classList.add("active")' in response.text
    assert 'progress.next_field === item.field' in response.text
    assert 'updateBookingSummary(progress.reservation_status === "complete" ? progress.summary : null);' in response.text


def test_completed_booking_summary_shell_is_calendar_ready(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert 'function updateBookingSummary(summary)' in response.text
    assert 'bookingSummary.classList.add("visible")' in response.text
    assert 'summary.appointment_display || "21 MAR 2026 at 14:00"' in response.text
    assert 'summary.service_name || "Стоматолошка консултација"' in response.text


def test_frontend_uses_internal_booking_edit_message(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert '`__booking_edit__:${fieldName}`' in response.text
    assert "showUserMessage: false" in response.text


def test_reset_behavior_is_local_session_rollover_only(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert "sessionId = null;" in response.text
    assert "window.localStorage.removeItem(sessionStorageKey);" in response.text
    assert "updateBookingProgress(null);" in response.text
    assert "await loadTenantConfig();" in response.text
    assert "/reset" not in response.text
