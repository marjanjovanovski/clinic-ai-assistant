# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib
import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


BOOKING_REQUEST = "need appointment"
BOOKING_CONFIRM = "da"
BOOKING_REJECT = "ne"


class FakeResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text


class FakeResponses:
    def create(self, *args, **kwargs):
        message = kwargs["input"][-1]["content"]
        if isinstance(message, str) and message.startswith("BOOKING_GUIDANCE\n"):
            payload = json.loads(message.split("\n", 1)[1])
            kind = payload["kind"]
            field_prompt = payload["field_prompt"]
            missing_digits = payload.get("missing_digits")
            if kind == "field_clarification":
                return FakeResponse(f"Imeto na pacientot sto treba da dojde. {field_prompt}")
            if kind == "phone_retry":
                label = "cifra" if missing_digits == 1 else "cifri"
                verb = "nedostiga" if missing_digits == 1 else "nedostigaat"
                return FakeResponse(
                    f"Mi deluva deka {verb} uste {missing_digits} {label}, pa pratete mi go brojot ushte ednash."
                )
            if kind == "catalog_redirect":
                return FakeResponse(f"Ke prodolzime so zakazuvanjeto. {field_prompt}")
        if message == BOOKING_REQUEST:
            return FakeResponse(
                json.dumps(
                    {
                        "intent": "suggest_service",
                        "service_id": "consultation",
                        "message": "Mozeme da zakazeme konsultacija. Dali sakate da zakazete?",
                    }
                )
            )
        if message == "tooth pain":
            return FakeResponse(
                json.dumps(
                    {
                        "intent": "suggest_service",
                        "service_id": "filling",
                        "message": "Preporacuvame plombiranje.",
                    }
                )
            )
        if message == "hello":
            return FakeResponse(
                json.dumps(
                    {
                        "intent": "greeting",
                        "service_id": "unknown",
                        "message": "Zdravo! Kako mozam da vi pomognam?",
                    }
                )
            )
        return FakeResponse(
            json.dumps(
                {
                    "intent": "fallback",
                    "service_id": "unknown",
                    "message": "Izvinete, ne mozam da razberam.",
                }
            )
        )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.responses = FakeResponses()


def _build_booking_ctx(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import ai_agent, lead_store, session_trace_logger
    from app.services.config_loader import load_profile_config

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "assistant_velika.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)
    monkeypatch.setattr(ai_agent, "OpenAI", FakeOpenAI)

    ai_agent.SESSION_STATE.clear()
    ai_agent.INTERACTION_HISTORY.clear()
    session_trace_logger._TRACE_FILES.clear()

    import app.main as main_module

    importlib.reload(main_module)
    lead_store.init_leads_db()

    return SimpleNamespace(
        client=TestClient(main_module.app),
        ai_agent=ai_agent,
        lead_store=lead_store,
        profile=load_profile_config("milena_dental"),
    )


@pytest.fixture
def booking_ctx(monkeypatch, tmp_path):
    return _build_booking_ctx(monkeypatch, tmp_path)


def _send(client, message, session_id=None):
    payload = {"message": message}
    if session_id is not None:
        payload["session_id"] = session_id
    response = client.post("/chat?tenant=milena_dental", json=payload)
    assert response.status_code == 200
    return response.json()


def _start_booking(ctx):
    first = _send(ctx.client, BOOKING_REQUEST)
    session_id = first["session_id"]
    return session_id, first


def _confirm_booking(ctx, session_id):
    return _send(ctx.client, BOOKING_CONFIRM, session_id)


def _complete_booking(ctx, name="Marjan", phone="070000000", email="mail@test.mk"):
    session_id, first = _start_booking(ctx)
    second = _confirm_booking(ctx, session_id)
    third = _send(ctx.client, name, session_id)
    fourth = _send(ctx.client, phone, session_id)
    fifth = _send(ctx.client, email, session_id)
    return SimpleNamespace(
        session_id=session_id,
        first=first,
        second=second,
        third=third,
        fourth=fourth,
        fifth=fifth,
    )


def test_main_booking_path_requires_explicit_confirmation_and_persisted_completion(booking_ctx):
    session_id, first = _start_booking(booking_ctx)

    assert first["session_status"] == "active"
    assert first["booking_progress"] is None

    not_confirmed = _send(booking_ctx.client, "thanks", session_id)
    assert not_confirmed["session_status"] == "active"
    assert not_confirmed["booking_progress"] is None

    confirmed = _confirm_booking(booking_ctx, session_id)
    assert confirmed["session_status"] == "collecting_contact"
    assert confirmed["booking_progress"]["next_field"] == "name"

    third = _send(booking_ctx.client, "Marjan", session_id)
    fourth = _send(booking_ctx.client, "070000000", session_id)
    fifth = _send(booking_ctx.client, "mail@test.mk", session_id)

    assert third["booking_progress"]["next_field"] == "phone"
    assert fourth["booking_progress"]["next_field"] == "email"
    assert fifth["session_status"] == "completed"
    assert fifth["booking_progress"]["reservation_status"] == "complete"
    assert fifth["booking_progress"]["collection_status"] == 3
    assert fifth["booking_progress"]["summary"]["service_name"] == "Стоматолошка консултација"
    assert fifth["booking_progress"]["summary"]["appointment_display"] == "21 MAR 2026 во 14:00"
    assert len(fifth["booking_progress"]["summary"]["fields"]) == 3

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["stage"] == "completed"
    assert stored["data"] == {
        "name": "Marjan",
        "phone": "070000000",
        "email": "mail@test.mk",
    }


def test_valid_name_progresses_booking_flow(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    response = _send(booking_ctx.client, "Marjan", session_id)

    assert response["session_status"] == "collecting_contact"
    assert response["booking_progress"]["next_field"] == "phone"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"]["name"] == "Marjan"


def test_unknown_name_confirmation_accepts_candidate_value(booking_ctx, monkeypatch):
    monkeypatch.setattr(
        booking_ctx.ai_agent.random,
        "choice",
        lambda options: booking_ctx.ai_agent.UNKNOWN_NAME_CONFIRM_MODE,
    )

    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    candidate = _send(booking_ctx.client, "V.", session_id)
    accepted = _send(booking_ctx.client, BOOKING_CONFIRM, session_id)

    assert "V." in candidate["reply"]
    assert accepted["booking_progress"]["next_field"] == "phone"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"]["name"] == "V."


def test_unknown_name_rejection_forces_repeat_until_valid_name(booking_ctx, monkeypatch):
    monkeypatch.setattr(
        booking_ctx.ai_agent.random,
        "choice",
        lambda options: booking_ctx.ai_agent.UNKNOWN_NAME_CONFIRM_MODE,
    )

    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    _send(booking_ctx.client, "V.", session_id)
    retry = _send(booking_ctx.client, BOOKING_REJECT, session_id)
    accepted = _send(booking_ctx.client, "Vasilie", session_id)

    assert retry["session_status"] == "collecting_contact"
    assert accepted["booking_progress"]["next_field"] == "phone"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"]["name"] == "Vasilie"


def test_name_field_rejects_conversational_filler(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    response = _send(booking_ctx.client, "ajde", session_id)

    assert response["session_status"] == "collecting_contact"
    assert response["booking_progress"]["next_field"] == "name"
    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert "name" not in stored.get("data", {})


def test_repeated_short_phone_inputs_keep_guided_missing_digits_reply(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)

    first = _send(booking_ctx.client, "123", session_id)
    second = _send(booking_ctx.client, "12", session_id)

    assert first["session_status"] == "collecting_contact"
    assert second["session_status"] == "collecting_contact"
    assert first["booking_progress"]["next_field"] == "phone"
    assert second["booking_progress"]["next_field"] == "phone"
    assert "6 cifri" in first["reply"]
    assert "pratete mi go brojot ushte ednash" in first["reply"]
    assert "7 cifri" in second["reply"]


def test_field_level_clarification_stays_inside_booking_flow(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    clarification = _send(booking_ctx.client, "dali moe ime?", session_id)
    resumed = _send(booking_ctx.client, "Marjan", session_id)

    assert clarification["session_status"] == "collecting_contact"
    assert clarification["booking_progress"]["next_field"] == "name"
    assert resumed["booking_progress"]["next_field"] == "phone"


def test_name_clarification_uses_guided_answer_and_returns_to_name_prompt(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    clarification = _send(
        booking_ctx.client,
        "dali moeto ili imeto na pacientot shto treba da dojde?",
        session_id,
    )

    assert clarification["session_status"] == "collecting_contact"
    assert clarification["booking_progress"]["next_field"] == "name"
    assert "пациентот" in clarification["reply"].lower()
    assert "име" in clarification["reply"].lower()


def test_phone_ownership_clarification_stays_short_and_resumes_phone(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)

    clarification = _send(booking_ctx.client, "na broj toj", session_id)

    assert clarification["session_status"] == "collecting_contact"
    assert clarification["booking_progress"]["next_field"] == "phone"
    assert "бројот на лицето" in clarification["reply"].lower()
    assert "на кој број" in clarification["reply"].lower()


def test_email_ownership_clarification_stays_short_and_resumes_email(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)
    _send(booking_ctx.client, "070000000", session_id)

    clarification = _send(booking_ctx.client, "na mojata poshta", session_id)

    assert clarification["session_status"] == "collecting_contact"
    assert clarification["booking_progress"]["next_field"] == "email"
    assert "е-поштата" in clarification["reply"].lower()
    assert "потврдата" in clarification["reply"].lower()


def test_booking_scope_clarification_resumes_current_field(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)

    clarification = _send(booking_ctx.client, "sto zakazuvame?", session_id)
    resumed = _send(booking_ctx.client, "070000000", session_id)

    assert clarification["session_status"] == "collecting_contact"
    assert clarification["booking_progress"]["next_field"] == "phone"
    assert resumed["booking_progress"]["next_field"] == "email"


def test_explicit_contact_bundle_advances_multiple_fields(booking_ctx):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)

    response = _send(
        booking_ctx.client,
        "ime Marjan telefon 070000000 email mail@test.mk",
        session_id,
    )

    assert response["session_status"] == "completed"
    assert response["booking_progress"]["collection_status"] == 3

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", session_id)
    assert stored["data"] == {
        "name": "Marjan",
        "phone": "070000000",
        "email": "mail@test.mk",
    }


def test_casual_text_is_not_overparsed_as_contact_bundle(booking_ctx):
    extracted = booking_ctx.ai_agent._extract_contact_fields_from_message(
        "Marjan 070000000",
        ["name", "phone", "email"],
        booking_ctx.profile,
    )
    should_parse = booking_ctx.ai_agent._should_attempt_contact_bundle_parse(
        "Marjan 070000000",
        ["name", "phone", "email"],
        booking_ctx.profile,
    )

    assert len(extracted) >= 1
    assert should_parse is False


def test_missing_persisted_required_field_blocks_completion(booking_ctx, monkeypatch):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)
    _send(booking_ctx.client, "070000000", session_id)

    monkeypatch.setattr(
        booking_ctx.ai_agent,
        "save_lead_checkpoint",
        lambda *args, **kwargs: {
            "success": False,
            "persisted_data": {"name": "Marjan", "phone": "070000000", "email": None},
        },
    )

    response = _send(booking_ctx.client, "mail@test.mk", session_id)

    assert response["session_status"] == "collecting_contact"
    assert response["booking_progress"]["next_field"] == "email"


def test_mismatched_persisted_value_blocks_completion(booking_ctx, monkeypatch):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)
    _send(booking_ctx.client, "070000000", session_id)

    monkeypatch.setattr(
        booking_ctx.ai_agent,
        "save_lead_checkpoint",
        lambda *args, **kwargs: {
            "success": False,
            "persisted_data": {
                "name": "Marjan",
                "phone": "070000000",
                "email": "wrong@test.mk",
            },
        },
    )

    response = _send(booking_ctx.client, "mail@test.mk", session_id)

    assert response["session_status"] == "collecting_contact"
    assert response["booking_progress"]["next_field"] == "email"


def test_save_failure_blocks_completion_and_keeps_booking_active(booking_ctx, monkeypatch):
    session_id, _ = _start_booking(booking_ctx)
    _confirm_booking(booking_ctx, session_id)
    _send(booking_ctx.client, "Marjan", session_id)
    _send(booking_ctx.client, "070000000", session_id)

    monkeypatch.setattr(
        booking_ctx.ai_agent,
        "save_lead_checkpoint",
        lambda *args, **kwargs: {
            "success": False,
            "persisted_data": {},
            "error_type": "Error",
        },
    )

    response = _send(booking_ctx.client, "mail@test.mk", session_id)

    assert response["session_status"] == "collecting_contact"
    assert response["booking_progress"]["next_field"] == "email"


def test_completed_name_edit_can_be_confirmed_and_resaved(booking_ctx):
    flow = _complete_booking(booking_ctx)

    confirm = _send(booking_ctx.client, "__booking_edit__:name", flow.session_id)
    value = _send(booking_ctx.client, BOOKING_CONFIRM, flow.session_id)
    saved = _send(booking_ctx.client, "Marjan Petrov", flow.session_id)

    assert confirm["session_status"] == "completed"
    assert value["session_status"] == "completed"
    assert saved["session_status"] == "completed"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", flow.session_id)
    assert stored["data"]["name"] == "Marjan Petrov"


def test_completed_phone_edit_can_be_cancelled(booking_ctx):
    flow = _complete_booking(booking_ctx)

    _send(booking_ctx.client, "__booking_edit__:phone", flow.session_id)
    cancelled = _send(booking_ctx.client, BOOKING_REJECT, flow.session_id)

    assert cancelled["session_status"] == "completed"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", flow.session_id)
    assert stored["data"]["phone"] == "070000000"


def test_completed_email_edit_rejects_invalid_replacement_before_resave(booking_ctx):
    flow = _complete_booking(booking_ctx)

    _send(booking_ctx.client, "__booking_edit__:email", flow.session_id)
    _send(booking_ctx.client, BOOKING_CONFIRM, flow.session_id)
    invalid = _send(booking_ctx.client, "broken@", flow.session_id)
    saved = _send(booking_ctx.client, "updated@test.mk", flow.session_id)

    assert invalid["session_status"] == "completed"
    assert saved["session_status"] == "completed"

    stored = booking_ctx.lead_store.load_lead_checkpoint("milena_dental", flow.session_id)
    assert stored["data"]["email"] == "updated@test.mk"


def test_save_lead_checkpoint_detects_missing_required_field_in_persisted_row(booking_ctx, monkeypatch):
    state = {
        "stage": "completed",
        "data": {"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    }

    original_fetch = booking_ctx.lead_store._fetch_persisted_lead

    def fake_fetch(connection, tenant, session_id):
        row = original_fetch(connection, tenant, session_id)
        return {
            "contact_name": row["contact_name"],
            "contact_phone": row["contact_phone"],
            "contact_email": None,
            "collected_data_json": row["collected_data_json"],
        }

    monkeypatch.setattr(booking_ctx.lead_store, "_fetch_persisted_lead", fake_fetch)

    result = booking_ctx.lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-missing-email",
        state,
        required_fields=["name", "phone", "email"],
    )

    assert result["success"] is False
    assert result["missing_required_fields"] == ["email"]


def test_save_lead_checkpoint_detects_mismatched_required_field_in_persisted_row(booking_ctx, monkeypatch):
    state = {
        "stage": "completed",
        "data": {"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    }

    original_fetch = booking_ctx.lead_store._fetch_persisted_lead

    def fake_fetch(connection, tenant, session_id):
        row = original_fetch(connection, tenant, session_id)
        return {
            "contact_name": row["contact_name"],
            "contact_phone": row["contact_phone"],
            "contact_email": "wrong@test.mk",
            "collected_data_json": row["collected_data_json"],
        }

    monkeypatch.setattr(booking_ctx.lead_store, "_fetch_persisted_lead", fake_fetch)

    result = booking_ctx.lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-mismatch-email",
        state,
        required_fields=["name", "phone", "email"],
    )

    assert result["success"] is False
    assert result["mismatched_fields"] == ["email"]


def test_save_lead_checkpoint_returns_error_result_on_sqlite_failure(booking_ctx, monkeypatch):
    monkeypatch.setattr(
        booking_ctx.lead_store,
        "_connect",
        lambda: (_ for _ in ()).throw(sqlite3.Error("boom")),
    )

    result = booking_ctx.lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-save-error",
        {"stage": "collecting_contact", "data": {}},
        required_fields=["name"],
    )

    assert result["success"] is False
    assert result["error_type"] == "Error"


def test_request_validation(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, session_trace_logger

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "validation.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.main as main_module

    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.post("/chat?tenant=milena_dental", json={"message": "   "})
    assert response.status_code == 422

    response = client.post(
        "/chat?tenant=milena_dental",
        json={"message": "ok", "session_id": "x" * 129},
    )
    assert response.status_code == 422
