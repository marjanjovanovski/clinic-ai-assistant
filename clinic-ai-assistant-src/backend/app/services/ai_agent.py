import json
import os
import uuid

from openai import OpenAI, OpenAIError, RateLimitError

from app.services.config_loader import load_profile_config
from app.services.lead_store import load_lead_checkpoint, save_lead_checkpoint


SESSION_STATE = {}
BOOKING_CONFIRM_WORDS = {"да", "da", "yes", "ok", "okej", "okay"}
INTENT_ALIASES = {
    "book_service": "suggest_service",
    "booking_inquiry": "suggest_service",
    "booking_initiated": "confirm_booking",
    "booking_start": "confirm_booking",
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
    return f"Ве молам кажете го вашето {collect_fields[0]}.", session_id


def _is_booking_confirmation(message: str) -> bool:
    return message.strip().casefold() in BOOKING_CONFIRM_WORDS


def _normalize_intent(intent: str | None) -> str | None:
    if not isinstance(intent, str):
        return None

    normalized_intent = intent.strip()
    normalized_key = normalized_intent.casefold()

    if normalized_key in INTENT_ALIASES:
        return INTENT_ALIASES[normalized_key]

    if "booking" in normalized_key or "book" in normalized_key:
        if any(keyword in normalized_key for keyword in ("start", "initiate", "initiated", "confirm")):
            return "confirm_booking"
        return "suggest_service"

    return normalized_intent


def generate_reply(tenant: str, message: str, session_id: str | None = None) -> tuple[str, str]:
    profile = load_profile_config(tenant)
    api_key = os.getenv("OPENAI_API_KEY")
    session_id = _normalize_session_id(session_id)

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
            "\nIf the user confirms booking (yes/da/ok), start collecting contact details."
            f"\nCollect these fields in order: {collect_fields}"
        )

    if output_contract:
        system_prompt += (
            "\n\nReturn ONLY a JSON object with this structure:\n"
            + json.dumps(output_contract.get("response_format", {}), ensure_ascii=False, indent=2)
        )

    session_key = _session_key(tenant, session_id)
    state = SESSION_STATE.get(session_key)

    if state is None:
        state = load_lead_checkpoint(tenant, session_id)
        if state:
            SESSION_STATE[session_key] = state

    if (
        state
        and state.get("stage") == "awaiting_booking_confirmation"
        and allow_booking
        and _is_booking_confirmation(message)
    ):
        return _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            state.get("service_id"),
            collect_fields,
        )

    if state and state.get("stage") == "collecting_contact":
        next_field = state.get("next_field")
        state["data"][next_field] = message

        remaining = [field for field in collect_fields if field not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            save_lead_checkpoint(tenant, session_id, state)
            return f"Ве молам кажете го вашето {remaining[0]}.", session_id

        SESSION_STATE.pop(session_key, None)
        state["stage"] = "completed"
        save_lead_checkpoint(tenant, session_id, state)
        return "Ви благодарам. Вашето барање за термин е примено. Клиниката ќе ве контактира.", session_id

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )

        raw_output = (response.output_text or "").strip()

        try:
            parsed = json.loads(raw_output)
            if not isinstance(parsed, dict):
                return _fallback_reply(profile), session_id

            intent = _normalize_intent(parsed.get("intent"))
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")

            if intent == "confirm_booking" and allow_booking:
                return _start_collecting_contact(
                    tenant,
                    session_id,
                    session_key,
                    service_id,
                    collect_fields,
                )

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

            if isinstance(message_text, str) and message_text.strip():
                return message_text, session_id

            return _fallback_reply(profile), session_id

        except json.JSONDecodeError:
            if raw_output:
                return raw_output, session_id

            return _fallback_reply(profile), session_id

    except RateLimitError:
        raise AIInferenceError(
            "The AI service is temporarily unavailable because the API quota is not active yet."
        )

    except OpenAIError:
        raise AIInferenceError(
            "The AI service is temporarily unavailable right now. Please try again shortly."
        )
