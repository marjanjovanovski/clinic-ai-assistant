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
    assert 'id="bookingSummaryNote"' in response.text
    assert 'id="bookingSummaryNoteValue"' in response.text


def test_completed_booking_summary_is_appended_from_template(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert 'const bookingSummaryTemplate = bookingSummary.cloneNode(true);' in response.text
    assert "bookingSummary.remove();" in response.text
    assert "function bookingSummaryKey(summary)" in response.text
    assert "function appendCompletedBookingSummary(summary)" in response.text
    assert 'chatMessages.appendChild(entry);' in response.text
    assert 'element.dataset.summaryKey = bookingSummaryKey(summary) || "";' in response.text


def test_completed_booking_summary_supports_multiple_history_entries(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert "let pendingCompletedSummary = null;" in response.text
    assert "let lastAppendedSummaryKey = null;" in response.text
    assert 'currentSummaryKey !== lastAppendedSummaryKey' in response.text
    assert 'lastAppendedSummaryKey = bookingSummaryKey(pendingCompletedSummary);' in response.text
    assert 'pendingCompletedSummary = progress.summary;' in response.text


def test_completed_booking_summary_shell_is_calendar_ready(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert 'summary.appointment_display || "21 MAR 2026 \\u0432\\u043e 14:00"' in response.text
    assert 'const summaryNote = String(summary.patient_note || summary.note || summary.notes || "").trim();' in response.text
    assert 'noteContainer.classList.add("visible")' in response.text
    assert 'noteContainer.hidden = true;' in response.text
    assert 'min-height: 58px;' in response.text
    assert 'box-shadow: 0 6px 14px rgba(15, 23, 42, 0.04);' in response.text


def test_frontend_uses_internal_booking_edit_message(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert '`__booking_edit__:${fieldName}`' in response.text
    assert "showUserMessage: false" in response.text
    assert 'if (sender === "bot" && pendingCompletedSummary) {' in response.text


def test_reset_behavior_is_local_session_rollover_only(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert "sessionId = null;" in response.text
    assert "window.localStorage.removeItem(sessionStorageKey);" in response.text
    assert "updateBookingProgress(null);" in response.text
    assert "await loadTenantConfig();" in response.text
    assert "/reset" not in response.text
