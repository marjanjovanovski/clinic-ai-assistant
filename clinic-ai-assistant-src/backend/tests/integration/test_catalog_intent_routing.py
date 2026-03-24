# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib

from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "a shto pravite vie?":
            return FakeResponse(
                '{"intent":"list_services","service_id":"unknown","message":"plain catalog text from model"}'
            )
        return FakeResponse(
            '{"intent":"fallback","service_id":"unknown","message":"fallback"}'
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def test_model_catalog_intent_uses_backend_formatted_reply(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store, session_trace_logger

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "catalog_intent.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.post("/chat?tenant=milena_dental", json={"message": "a shto pravite vie?"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["reply"].startswith("• ")
    assert "Консултација" in payload["reply"]
    assert "Превентивна стоматологија" in payload["reply"]
    assert "plain catalog text from model" not in payload["reply"]
