# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
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
    assert 'href="/frontend/chat/chat-shell.css"' in response.text
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
    assert "addSlotListConversationWidget," in response.text
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
    assert 'import { createBookingProgressWidget } from "/frontend/widgets/booking-progress/booking-progress.js";' in registry_js.text
    assert '`__booking_edit__:${fieldName}`' in response.text
    assert 'widgetRegistry.mount("booking-progress", {' in response.text
    assert 'summaryHistory.queueIfNew(progress.summary);' in progress_js.text
    assert 'stepEl.addEventListener("click", () => onEditField(item.field));' in progress_js.text
    assert 'const transcript = createChatTranscript(container, {' in registry_js.text
    assert 'registry.register("booking-progress"' in registry_js.text
    assert 'registry.register("booking-summary"' in registry_js.text
    assert 'registry.register("slot-list"' in registry_js.text


def test_agent_page_mounts_slot_list_widget_from_chat_response(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert response.status_code == 200
    assert 'href="/frontend/widgets/slot-list/slot-list.css"' in response.text
    assert 'const SELECT_SLOT_URL = `/scheduling/select-slot?tenant=${encodeURIComponent(tenant)}`;' in response.text
    assert 'function isSlotListWidgetPayload(widgetPayload)' in response.text
    assert 'function getPrimaryReplyText(replyText, widgetPayload)' in response.text
    assert 'function syncSessionId(nextSessionId)' in response.text
    assert 'function updateStatusFromSessionStatus(nextSessionStatus, fallbackText = "Подготвено")' in response.text
    assert 'function applyBackendConversationUpdate(data, options = {})' in response.text
    assert 'async function handleSlotSelection(slot, widgetPayload, slotListWidget)' in response.text
    assert 'const [primaryReply] = replyText.split(/\\n\\s*\\n/, 1);' in response.text
    assert 'function addResponseWidget(widgetPayload, options = {})' in response.text
    assert 'widgetPayload.type !== "slot-list"' in response.text
    assert 'const { hideTitle = false } = options;' in response.text
    assert 'slotListWidget.disableAll();' in response.text
    assert 'const response = await fetch(SELECT_SLOT_URL, {' in response.text
    assert 'session_id: sessionId,' in response.text
    assert 'service_id: widgetPayload.service_id,' in response.text
    assert 'slot_id: slot.slot_id' in response.text
    assert 'syncSessionId(data.session_id);' in response.text
    assert 'updateBookingProgress(data.booking_progress);' in response.text
    assert 'slotListWidget.enableAll();' in response.text
    assert 'onSelect: (slot, slotListWidget) => handleSlotSelection(slot, widgetPayload, slotListWidget),' in response.text
    assert 'title: hideTitle ? null : (widgetPayload.title || "Изберете термин:")' in response.text
    assert "readOnly: false," in response.text
    assert 'const primaryReplyText = getPrimaryReplyText(data.reply, includeWidget ? data.widget_payload : null);' in response.text
    assert 'applyBackendConversationUpdate(data, {' in response.text
    assert 'addResponseWidget(data.widget_payload, { hideTitle: Boolean(primaryReplyText) });' in response.text


def test_slot_list_widget_supports_read_only_mode(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    widget_js = client.get("/frontend/widgets/slot-list/slot-list.js")
    widget_css = client.get("/frontend/widgets/slot-list/slot-list.css")

    assert widget_js.status_code == 200
    assert widget_css.status_code == 200
    assert "readOnly = false," in widget_js.text
    assert 'const normalizedTitle = typeof title === "string" ? title.trim() : "";' in widget_js.text
    assert "if (normalizedTitle) {" in widget_js.text
    assert 'buttonEl.classList.toggle("slot-list-button--read-only", readOnly);' in widget_js.text
    assert "buttonEl.disabled = readOnly;" in widget_js.text
    assert "if (readOnly) {" in widget_js.text
    assert ".slot-list-button--read-only:disabled {" in widget_css.text


def test_reset_behavior_is_local_session_rollover_only(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/agent/milena_dental")

    assert "sessionId = null;" in response.text
    assert "window.localStorage.removeItem(sessionStorageKey);" in response.text
    assert "bookingSummaryHistory.reset();" in response.text
    assert "bookingProgressWidget.reset();" in response.text
    assert "await loadTenantConfig();" in response.text
    assert "/reset" not in response.text


def test_booking_widget_demo_pages_use_live_assets(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    progress_demo = client.get("/frontend/widgets/booking-progress/demo.html")
    summary_demo = client.get("/frontend/widgets/booking-summary/demo.html")

    assert progress_demo.status_code == 200
    assert summary_demo.status_code == 200
    assert 'href="/frontend/widgets/booking-progress/booking-progress.css"' in progress_demo.text
    assert 'import { createBookingProgressWidget } from "/frontend/widgets/booking-progress/booking-progress.js";' in progress_demo.text
    assert 'href="/frontend/widgets/booking-summary/booking-summary.css"' in summary_demo.text
    assert 'import { createBookingSummaryElement } from "/frontend/widgets/booking-summary/booking-summary.js";' in summary_demo.text
