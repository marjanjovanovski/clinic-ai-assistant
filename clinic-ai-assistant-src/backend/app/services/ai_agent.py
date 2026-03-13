import json
import logging
import os
import uuid

from openai import OpenAI, OpenAIError, RateLimitError

from app.services.config_loader import load_profile_config
from app.services.lead_store import load_lead_checkpoint, save_lead_checkpoint
from app.services.session_trace_logger import trace_event


logger = logging.getLogger(__name__)
DEBUG_AI = os.getenv("DEBUG_AI", "").strip().lower() == "true"
SESSION_STATE = {}
BOOKING_CONFIRM_WORDS = {"да", "da", "yes", "ok", "okej", "okay"}
FIELD_PROMPTS = {
    "name": "Ве молам кажете ни го вашето име.",
    "phone": "Ве молам кажете ни го вашиот телефон.",
    "email": "Ве молам кажете ни ја вашата е-пошта.",
}
CANONICAL_INTENTS = {"greeting", "suggest_service", "confirm_booking", "collect_contact", "fallback"}
INTENT_ALIASES = {
    "greeting": "greeting",
    "hello": "greeting",
    "welcome": "greeting",
    "suggest_service": "suggest_service",
    "book_service": "suggest_service",
    "booking_inquiry": "suggest_service",
    "booking_request": "suggest_service",
    "list_services": "fallback",
    "confirm_booking": "confirm_booking",
    "booking_initiated": "confirm_booking",
    "booking_initiate": "confirm_booking",
    "booking_start": "confirm_booking",
    "collect_contact": "collect_contact",
    "clarify": "fallback",
    "clarification": "fallback",
    "out_of_scope": "fallback",
    "ask_services": "fallback",
    "fallback": "fallback",
}


class AIInferenceError(Exception):
    pass


def _fallback_reply(profile: dict) -> str:
    conversation = profile.get("conversation", {})
    fallback_message = conversation.get("fallback_message")

    if isinstance(fallback_message, str) and fallback_message.strip():
        return fallback_message

    return "I couldn't generate a valid response right now."


def _session_key(tenant: str, session_id: str) -> str:
    return f"{tenant}:{session_id}"


def _normalize_session_id(session_id: str | None) -> str:
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()

    return str(uuid.uuid4())


def _load_session_state(tenant: str, session_id: str) -> dict | None:
    session_key = _session_key(tenant, session_id)
    state = SESSION_STATE.get(session_key)

    if state is None:
        state = load_lead_checkpoint(tenant, session_id)
        if state:
            SESSION_STATE[session_key] = state

    return state


def _stage_name(state: dict | None) -> str | None:
    if not isinstance(state, dict):
        return None

    return state.get("stage")


def _log_chat_state(
    *,
    message: str,
    session_id: str,
    intent: str | None,
    stage_before: str | None,
    stage_after: str | None,
) -> None:
    logger.info(
        "chat_state message=%r session_id=%s intent=%s stage_before=%s stage_after=%s",
        message,
        session_id,
        intent,
        stage_before,
        stage_after,
    )


def _trace_stage_transition(
    tenant: str,
    session_id: str,
    from_stage: str | None,
    to_stage: str | None,
    *,
    reason: str,
):
    trace_event(
        tenant,
        session_id,
        "STAGE_TRANSITION",
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason,
    )


def _field_prompt(field_name: str) -> str:
    return FIELD_PROMPTS.get(field_name, field_name)


def _status_for_stage(stage: str | None) -> str:
    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def _trace_response(
    tenant: str,
    session_id: str,
    reply: str,
    stage_after: str | None,
):
    trace_event(
        tenant,
        session_id,
        "RESPONSE_RETURNED",
        reply=reply,
        session_status=_status_for_stage(stage_after),
        stage_after=stage_after,
    )


def _start_collecting_contact(
    tenant: str,
    session_id: str,
    session_key: str,
    service_id: str | None,
    collect_fields: list[str],
) -> tuple[str, str]:
    SESSION_STATE[session_key] = {
        "stage": "collecting_contact",
        "service_id": service_id,
        "next_field": collect_fields[0],
        "data": {}
    }
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key])
    return _field_prompt(collect_fields[0]), session_id


def _is_booking_confirmation(message: str) -> bool:
    return message.strip().casefold() in BOOKING_CONFIRM_WORDS


def _normalize_intent(intent: str | None) -> str:
    if not isinstance(intent, str):
        return "fallback"

    normalized_key = intent.strip().casefold()
    canonical_intent = INTENT_ALIASES.get(normalized_key, "fallback")

    if canonical_intent not in CANONICAL_INTENTS:
        return "fallback"

    return canonical_intent


def get_session_status(tenant: str, session_id: str | None) -> str:
    if not session_id:
        return "active"

    state = _load_session_state(tenant, session_id)
    stage = _stage_name(state)

    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def generate_reply(tenant: str, message: str, session_id: str | None = None) -> tuple[str, str]:
    original_session_id = session_id
    profile = load_profile_config(tenant)
    api_key = os.getenv("OPENAI_API_KEY")
    session_id = _normalize_session_id(session_id)

    if not original_session_id:
        trace_event(
            tenant,
            session_id,
            "SESSION_CREATED",
            reason="request_without_session_id",
        )

    trace_event(
        tenant,
        session_id,
        "REQUEST_RECEIVED",
        incoming_session_id=original_session_id,
        message=message,
    )

    business = profile.get("business", {})
    conversation = profile.get("conversation", {})
    prompt_template = profile.get("prompt_template", {})
    services = profile.get("services", [])
    actions = profile.get("actions", {})
    output_contract = profile.get("output_contract", {})

    business_name = business.get("name", "Assistant")
    language = business.get("language", "en")
    goal = conversation.get("goal", "")
    rules = conversation.get("rules", [])

    allow_booking = actions.get("allow_booking", False)
    collect_fields = actions.get("collect_contact_fields", [])

    template = prompt_template.get(
        "system",
        "You are an AI assistant for {{business_name}}. Your goal: {{goal}}."
    )

    service_catalog = [
        {
            "id": service.get("id"),
            "name": service.get("name"),
            "description": service.get("description"),
            "keywords": service.get("keywords", []),
            "symptoms": service.get("symptoms", []),
            "bookable": service.get("bookable", False)
        }
        for service in services
    ]

    services_json = json.dumps(service_catalog, ensure_ascii=False, indent=2)
    rules_text = "\n".join(f"- {rule}" for rule in rules)

    system_prompt = (
        template.replace("{{business_name}}", business_name)
        .replace("{{goal}}", goal)
    )

    if rules_text:
        system_prompt += f"\n\nRules:\n{rules_text}"

    system_prompt += f"\n\nAlways respond in this language: {language}"
    system_prompt += f"\n\nAllowed services catalog:\n{services_json}"

    if allow_booking:
        system_prompt += (
            "\n\nBooking capability: enabled."
            "\nCanonical intents: greeting, suggest_service, confirm_booking, fallback."
            "\nIf the user confirms booking, return confirm_booking."
            f"\nCollect these fields in order: {collect_fields}"
        )

    if output_contract:
        system_prompt += (
            "\n\nReturn ONLY a JSON object with this structure:\n"
            + json.dumps(output_contract.get("response_format", {}), ensure_ascii=False, indent=2)
        )

    session_key = _session_key(tenant, session_id)
    state = _load_session_state(tenant, session_id)
    stage_before = _stage_name(state)

    trace_event(
        tenant,
        session_id,
        "SESSION_LOADED",
        stage_before=stage_before,
        state=state,
    )

    if state and state.get("stage") == "completed":
        old_session_id = session_id
        SESSION_STATE.pop(session_key, None)
        session_id = _normalize_session_id(None)
        session_key = _session_key(tenant, session_id)
        state = None
        stage_before = None
        trace_event(
            tenant,
            old_session_id,
            "SESSION_RESET_AFTER_COMPLETION",
            old_session_id=old_session_id,
            new_session_id=session_id,
        )
        trace_event(
            tenant,
            session_id,
            "SESSION_CREATED",
            reason="post_completion_rollover",
            previous_session_id=old_session_id,
        )

    # Booking state 1: waiting for the user to confirm a suggested service.
    if (
        state
        and state.get("stage") == "awaiting_booking_confirmation"
        and allow_booking
        and _is_booking_confirmation(message)
    ):
        reply, session_id = _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            state.get("service_id"),
            collect_fields,
        )
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "collecting_contact",
            reason="backend_confirmation_word",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="confirm_booking",
            stage_before=stage_before,
            stage_after="collecting_contact",
        )
        _trace_response(tenant, session_id, reply, "collecting_contact")
        return reply, session_id

    # Booking state 2: backend owns the contact collection prompts until completion.
    if state and state.get("stage") == "collecting_contact":
        next_field = state.get("next_field")
        state["data"][next_field] = message

        remaining = [field for field in collect_fields if field not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            save_lead_checkpoint(tenant, session_id, state)
            _trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"collected_{next_field}",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = _field_prompt(remaining[0])
            _trace_response(tenant, session_id, reply, "collecting_contact")
            return reply, session_id

        SESSION_STATE.pop(session_key, None)
        state["stage"] = "completed"
        save_lead_checkpoint(tenant, session_id, state)
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "completed",
            reason=f"collected_{next_field}",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="collect_contact",
            stage_before=stage_before,
            stage_after="completed",
        )
        reply = "Ви благодарам. Вашето барање за термин е примено. Клиниката ќе ве контактира."
        _trace_response(tenant, session_id, reply, "completed")
        return reply, session_id

    try:
        client = OpenAI(api_key=api_key)

        if DEBUG_AI:
            logger.debug("OPENAI CALL START tenant=%s session_id=%s", tenant, session_id)

        trace_event(tenant, session_id, "AI_CALL_START")
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        trace_event(tenant, session_id, "AI_CALL_END")

        if DEBUG_AI:
            logger.debug("OPENAI CALL END tenant=%s session_id=%s", tenant, session_id)
            logger.debug("OPENAI RESPONSE TEXT %s", (response.output_text or "").strip())

        raw_output = (response.output_text or "").strip()
        trace_event(tenant, session_id, "AI_RAW_OUTPUT", raw_output=raw_output)

        try:
            parsed = json.loads(raw_output)
            if not isinstance(parsed, dict):
                trace_event(
                    tenant,
                    session_id,
                    "FALLBACK_USED",
                    reason="parsed_output_not_object",
                )
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent="fallback",
                    stage_before=stage_before,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                reply = _fallback_reply(profile)
                _trace_response(tenant, session_id, reply, _stage_name(SESSION_STATE.get(session_key)))
                return reply, session_id

            raw_intent = parsed.get("intent")
            intent = _normalize_intent(raw_intent)
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")

            trace_event(
                tenant,
                session_id,
                "INTENT_NORMALIZED",
                raw_intent=raw_intent,
                normalized_intent=intent,
                service_id=service_id,
            )

            if intent == "confirm_booking" and allow_booking:
                reply, session_id = _start_collecting_contact(
                    tenant,
                    session_id,
                    session_key,
                    service_id,
                    collect_fields,
                )
                _trace_stage_transition(
                    tenant,
                    session_id,
                    stage_before,
                    "collecting_contact",
                    reason="model_confirm_booking",
                )
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent=intent,
                    stage_before=stage_before,
                    stage_after="collecting_contact",
                )
                _trace_response(tenant, session_id, reply, "collecting_contact")
                return reply, session_id

            if intent == "suggest_service" and allow_booking and service_id and service_id != "unknown":
                bookable_service_ids = {
                    service.get("id")
                    for service in services
                    if service.get("bookable")
                }
                if service_id in bookable_service_ids:
                    SESSION_STATE[session_key] = {
                        "stage": "awaiting_booking_confirmation",
                        "service_id": service_id,
                    }
                    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key])
                    _trace_stage_transition(
                        tenant,
                        session_id,
                        stage_before,
                        "awaiting_booking_confirmation",
                        reason="model_suggest_service",
                    )

            if intent not in {"greeting", "suggest_service", "fallback"}:
                intent = "fallback"

            if isinstance(message_text, str) and message_text.strip():
                _log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent=intent,
                    stage_before=stage_before,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                _trace_response(
                    tenant,
                    session_id,
                    message_text,
                    _stage_name(SESSION_STATE.get(session_key)),
                )
                return message_text, session_id

            trace_event(
                tenant,
                session_id,
                "FALLBACK_USED",
                reason="empty_message_text_after_normalization",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent=intent,
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            reply = _fallback_reply(profile)
            _trace_response(tenant, session_id, reply, _stage_name(SESSION_STATE.get(session_key)))
            return reply, session_id

        except json.JSONDecodeError:
            trace_event(
                tenant,
                session_id,
                "FALLBACK_USED",
                reason="json_decode_error",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="fallback",
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            reply = raw_output or _fallback_reply(profile)
            _trace_response(tenant, session_id, reply, _stage_name(SESSION_STATE.get(session_key)))
            return reply, session_id

    except RateLimitError as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AIInferenceError(
            "The AI service is temporarily unavailable because the API quota is not active yet."
        )

    except OpenAIError as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise AIInferenceError(
            "The AI service is temporarily unavailable right now. Please try again shortly."
        )

    except Exception as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="ai_agent.generate_reply",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise
