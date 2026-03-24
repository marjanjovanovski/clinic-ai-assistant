# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib

from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if message == "kolku cini plombiranje?":
            return FakeResponse(
                '{"intent":"quote_price","service_id":"filling","message":"Тоа чини 2000 денари."}'
            )
        return FakeResponse(
            '{"intent":"fallback","service_id":"unknown","message":"fallback"}'
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def test_model_price_intent_uses_backend_price_reply(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store, session_trace_logger

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "price_intent.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.post("/chat?tenant=milena_dental", json={"message": "kolku cini plombiranje?"})
    assert response.status_code == 200

    payload = response.json()
    assert "пломбирање" in payload["reply"].casefold()
    assert "2000 денари" not in payload["reply"]
    assert "консултација" in payload["reply"].casefold()
