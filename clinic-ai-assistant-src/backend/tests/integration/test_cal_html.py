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
    assert 'href="/frontend/chat/chat-shell.css"' in response.text
    assert 'id="loadSlotsButton"' in response.text
    assert 'id="patientNameInput"' in response.text


def test_cal_html_wires_slot_buttons_and_booking_request(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/frontend/cal.html")

    assert "function addSlotChoices" in response.text
    assert "async function bookSelectedSlot" in response.text
    assert 'href="/frontend/widgets/slot-list/slot-list.css"' in response.text
    assert 'import { resolveTenantFromPath } from "/frontend/chat/chat-shell.js";' in response.text
    assert 'from "/frontend/widgets/widget-registry.js";' in response.text
    assert "const widgetRegistry = registerDefaultConversationWidgets(createConversationWidgetRegistry());" in response.text
    assert 'return conversationDispatcher.addWidget("slot-list", {' in response.text
    assert "slotListWidget.disableAll()" in response.text
    assert "/scheduling/book?tenant=" in response.text
    assert "Booked from cal.html sandbox" in response.text


def test_slot_list_widget_assets_are_served_for_scheduling_ui(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    widget_js = client.get("/frontend/widgets/slot-list/slot-list.js")
    widget_css = client.get("/frontend/widgets/slot-list/slot-list.css")
    registry_js = client.get("/frontend/widgets/widget-registry.js")
    demo_html = client.get("/frontend/widgets/slot-list/demo.html")

    assert widget_js.status_code == 200
    assert widget_css.status_code == 200
    assert registry_js.status_code == 200
    assert demo_html.status_code == 200
    assert "export function createSlotListWidget" in widget_js.text
    assert 'buttonEl.className = "slot-list-button"' in widget_js.text
    assert ".slot-list-actions {" in widget_css.text
    assert ".slot-list-button:disabled {" in widget_css.text
    assert "export function createConversationWidgetRegistry()" in registry_js.text
    assert "export function createConversationWidgetDispatcher({" in registry_js.text
    assert 'import { createChatTranscript } from "/frontend/chat/chat-shell.js";' in registry_js.text
    assert 'registry.register("slot-list"' in registry_js.text
    assert 'href="/frontend/widgets/slot-list/slot-list.css"' in demo_html.text
    assert 'import { createSlotListWidget } from "/frontend/widgets/slot-list/slot-list.js";' in demo_html.text
