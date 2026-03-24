# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib

from fastapi.testclient import TestClient


class GuardedResponses:
    def create(self, *args, **kwargs):
        raise AssertionError("OpenAI should not be called for deterministic social redirect prompts.")


class GuardedOpenAI:
    def __init__(self, api_key=None):
        self.responses = GuardedResponses()


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store, session_trace_logger

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", GuardedOpenAI)
    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "casual_routing.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_social_small_talk_uses_short_goal_redirect(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post("/chat?tenant=milena_dental", json={"message": "shto pravish?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_status"] == "active"
    assert "стоматолошко прашање" in payload["reply"].casefold()
    assert "• " not in payload["reply"]


def test_vague_social_nudge_does_not_dump_catalog(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post("/chat?tenant=milena_dental", json={"message": "ajde togash"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_status"] == "active"
    assert "болка" in payload["reply"].casefold()
    assert "преглед" in payload["reply"].casefold()
    assert "• " not in payload["reply"]
