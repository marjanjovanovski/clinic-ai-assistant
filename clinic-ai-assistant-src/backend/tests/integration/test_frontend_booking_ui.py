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

    assert 'href="/frontend/widgets/booking-summary/booking-summary.css"' in response.text
    assert 'const bookingSummaryTemplate = bookingSummary.cloneNode(true);' in response.text
    assert "bookingSummary.remove();" in response.text
    assert 'import { createBookingSummaryHistory } from "/frontend/widgets/booking-summary/booking-summary.js";' in response.text
    assert 'from "/frontend/widgets/widget-registry.js";' in response.text
    assert "const widgetRegistry = registerDefaultConversationWidgets(" in response.text
    assert "const conversationDispatcher = createConversationWidgetDispatcher({" in response.text
    assert "const bookingSummaryHistory = createBookingSummaryHistory({" in response.text
    assert 'conversationDispatcher.addWidget(' in response.text
    assert '"booking-summary"' in response.text
    assert "bookingSummaryHistory.flushPending();" in response.text


def test_completed_booking_summary_supports_multiple_history_entries(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/widgets/booking-summary/booking-summary.js")

    assert response.status_code == 200
    assert "export function bookingSummaryKey(summary)" in response.text
    assert "export function createBookingSummaryElement({" in response.text
    assert "let pendingSummary = null;" in response.text
    assert "let lastAppendedSummaryKey = null;" in response.text
    assert "function queueIfNew(summary)" in response.text
    assert "function flushPending()" in response.text
    assert "lastAppendedSummaryKey = bookingSummaryKey(summary);" in response.text
    assert "typeof appendSummary === \"function\"" in response.text


def test_completed_booking_summary_shell_is_calendar_ready(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    summary_js = client.get("/frontend/widgets/booking-summary/booking-summary.js")
    summary_css = client.get("/frontend/widgets/booking-summary/booking-summary.css")

    assert summary_js.status_code == 200
    assert summary_css.status_code == 200
    assert 'summary.appointment_display || "21 MAR 2026 во 14:00"' in summary_js.text
    assert 'const summaryNote = String(summary.patient_note || summary.note || summary.notes || "").trim();' in summary_js.text
    assert 'noteContainer.classList.add("visible");' in summary_js.text
    assert 'noteContainer.hidden = true;' in summary_js.text
    assert "min-height: 58px;" in summary_css.text
    assert "box-shadow: 0 6px 14px rgba(15, 23, 42, 0.04);" in summary_css.text


def test_frontend_uses_internal_booking_edit_message(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")
    progress_js = client.get("/frontend/widgets/booking-progress/booking-progress.js")
    registry_js = client.get("/frontend/widgets/widget-registry.js")

    assert progress_js.status_code == 200
    assert registry_js.status_code == 200
    assert 'import { createBookingProgressWidget } from "/frontend/widgets/booking-progress/booking-progress.js";' in response.text
    assert '`__booking_edit__:${fieldName}`' in response.text
    assert 'widgetRegistry.mount("booking-progress", {' in response.text
    assert 'summaryHistory.queueIfNew(progress.summary);' in progress_js.text
    assert 'stepEl.addEventListener("click", () => onEditField(item.field));' in progress_js.text
    assert 'registry.register("booking-progress"' in registry_js.text
    assert 'registry.register("booking-summary"' in registry_js.text
    assert 'registry.register("slot-list"' in registry_js.text


def test_reset_behavior_is_local_session_rollover_only(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert "sessionId = null;" in response.text
    assert "window.localStorage.removeItem(sessionStorageKey);" in response.text
    assert "bookingSummaryHistory.reset();" in response.text
    assert "bookingProgressWidget.reset();" in response.text
    assert "await loadTenantConfig();" in response.text
    assert "/reset" not in response.text
