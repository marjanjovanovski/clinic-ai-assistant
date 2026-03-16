import json
import logging
import os
import re
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
SERVICE_LIST_TRIGGERS = (
    "\u0448\u0442\u043e \u0443\u0441\u043b\u0443\u0433\u0438",
    "\u043a\u043e\u0438 \u0443\u0441\u043b\u0443\u0433\u0438",
    "\u0443\u0441\u043b\u0443\u0433\u0438 \u043d\u0443\u0434\u0438\u0442\u0435",
    "\u0448\u0442\u043e \u043d\u0443\u0434\u0438\u0442\u0435",
    "koi uslugi",
    "shto uslugi",
    "uslugi nudite",
    "sto nudite",
)
PRICE_TRIGGERS = (
    "\u0446\u0435\u043d\u0430",
    "\u043a\u043e\u043b\u043a\u0443 \u0447\u0438\u043d\u0438",
    "\u043a\u043e\u043b\u043a\u0430\u0432\u0430 \u0435 \u0446\u0435\u043d\u0430\u0442\u0430",
    "cena",
    "kolku chini",
    "kolku cini",
    "price",
)
CASUAL_REPLY_PATTERNS = (
    (
        (
            "\u0444\u0430\u043b\u0430",
            "\u0431\u043b\u0430\u0433\u043e\u0434\u0430\u0440\u0430\u043c",
            "fala",
            "blagodaram",
            "thanks",
            "thank you",
        ),
        "\u0412\u0438 \u0431\u043b\u0430\u0433\u043e\u0434\u0430\u0440\u0430\u043c. \u0410\u043a\u043e \u0441\u0430\u043a\u0430\u0442\u0435, \u0441\u043b\u043e\u0431\u043e\u0434\u043d\u043e \u043a\u0430\u0436\u0435\u0442\u0435 \u0448\u0442\u043e \u0432\u0435 \u0438\u043d\u0442\u0435\u0440\u0435\u0441\u0438\u0440\u0430.",
    ),
    (
        (
            "wow",
            "\u0432\u0430\u0443",
            "\u043b\u0435\u043b\u0435",
        ),
        "\u0412\u0438 \u0431\u043b\u0430\u0433\u043e\u0434\u0430\u0440\u0430\u043c, \u0434\u0440\u0430\u0433\u043e \u043c\u0438 \u0435 \u0448\u0442\u043e \u043f\u043e\u043c\u043e\u0433\u043d\u0430\u0432. \u0410\u043a\u043e \u0441\u0430\u043a\u0430\u0442\u0435, \u043c\u043e\u0436\u0430\u043c \u0438 \u0434\u0430 \u0432\u0435 \u043d\u0430\u0441\u043e\u0447\u0430\u043c \u043a\u043e\u043d \u0441\u043e\u043e\u0434\u0432\u0435\u0442\u043d\u0430 \u0443\u0441\u043b\u0443\u0433\u0430 \u0438\u043b\u0438 \u043a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430.",
    ),
    (
        (
            "\u0441\u0443\u043f\u0435\u0440",
            "\u043e\u0434\u043b\u0438\u0447\u043d\u043e",
            "super",
            "odlichno",
            "odlicno",
            "great",
        ),
        "\u0414\u0440\u0430\u0433\u043e \u043c\u0438 \u0435. \u041a\u0430\u0436\u0435\u0442\u0435 \u0430\u043a\u043e \u0441\u0430\u043a\u0430\u0442\u0435 \u0434\u0430 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u043c\u0435 \u0443\u0441\u043b\u0443\u0433\u0430 \u0438\u043b\u0438 \u0434\u0430 \u0437\u0430\u043a\u0430\u0436\u0435\u043c\u0435 \u043a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430.",
    ),
)


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


def _normalize_lookup_text(value: str) -> str:
    lowered = value.casefold()
    normalized = re.sub(r"\s+", " ", lowered)
    return normalized.strip()


def _service_variants(service: dict) -> set[str]:
    variants = set()
    for field_name in ("name", "\u0438\u043c\u0435", "description", "\u043e\u043f\u0438\u0441"):
        value = service.get(field_name)
        if isinstance(value, str) and value.strip():
            variants.add(_normalize_lookup_text(value))

    for field_name in ("aliases", "keywords", "symptoms", "\u043f\u0440\u0435\u043f\u043e\u0440\u0430\u0447\u0430\u043d\u043e_\u0437\u0430"):
        values = service.get(field_name) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    variants.add(_normalize_lookup_text(item))

    return variants


def _match_service_for_message(message: str, services: list[dict]) -> dict | None:
    normalized_message = _normalize_lookup_text(message)
    best_match = None
    best_score = 0

    for service in services:
        for variant in _service_variants(service):
            if not variant:
                continue
            if variant in normalized_message:
                score = len(variant)
                if score > best_score:
                    best_score = score
                    best_match = service

    return best_match


def _is_service_list_request(message: str) -> bool:
    normalized_message = _normalize_lookup_text(message)
    return any(trigger in normalized_message for trigger in SERVICE_LIST_TRIGGERS)


def _is_price_request(message: str) -> bool:
    normalized_message = _normalize_lookup_text(message)
    return any(trigger in normalized_message for trigger in PRICE_TRIGGERS)


def _casual_reply(message: str) -> str | None:
    normalized_message = _normalize_lookup_text(message)

    for triggers, reply in CASUAL_REPLY_PATTERNS:
        if any(trigger in normalized_message for trigger in triggers):
            return reply

    return None


def _catalog_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = profile.get("\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438")
    if isinstance(categories, list) and categories:
        return categories

    grouped: dict[str, list[dict]] = {}
    for service in services:
        category_name = service.get("category") or "\u0423\u0441\u043b\u0443\u0433\u0438"
        grouped.setdefault(category_name, []).append(service)

    return [
        {
            "\u0438\u043c\u0435": category_name,
            "\u0443\u0441\u043b\u0443\u0433\u0438": category_services,
        }
        for category_name, category_services in grouped.items()
    ]


def _ordered_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = list(_catalog_categories(profile, services))
    consultation_name = _normalize_lookup_text("\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430")

    consultation_categories = []
    other_categories = []
    for category in categories:
        category_name = category.get("\u0438\u043c\u0435") or category.get("name") or ""
        if _normalize_lookup_text(category_name) == consultation_name:
            consultation_categories.append(category)
        else:
            other_categories.append(category)

    return consultation_categories + other_categories


def _service_display_name(service: dict) -> str:
    return service.get("\u0438\u043c\u0435") or service.get("name") or service.get("id", "")


def _service_display_description(service: dict) -> str | None:
    description = service.get("\u043e\u043f\u0438\u0441") or service.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _service_list_reply(profile: dict, services: list[dict]) -> str:
    lines: list[str] = []

    for category in _ordered_categories(profile, services):
        category_name = category.get("\u0438\u043c\u0435") or category.get("name")
        if not isinstance(category_name, str) or not category_name.strip():
            continue

        lines.append(f"\u2022 {category_name.strip()}")
        category_services = category.get("\u0443\u0441\u043b\u0443\u0433\u0438") or category.get("services") or []

        for service in category_services:
            if not isinstance(service, dict):
                continue

            service_name = _service_display_name(service)
            if not service_name:
                continue

            description = _service_display_description(service)
            if description and category_name == "\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430":
                lines.append(f"  \u2013 {service_name} \u2014 {description}")
            else:
                lines.append(f"  \u2013 {service_name}")

        lines.append("")

    return "\n".join(lines).strip()


def _orientation_price_text(service: dict) -> str | None:
    service_name = _service_display_name(service)
    price = service.get("price", service.get("\u0446\u0435\u043d\u0430"))
    currency = service.get("\u0432\u0430\u043b\u0443\u0442\u0430")
    price_range = service.get("price_range", service.get("\u0446\u0435\u043d\u043e\u0432\u0435\u043d_\u043e\u043f\u0441\u0435\u0433"))
    description = _service_display_description(service)

    if isinstance(price, (int, float)):
        currency_text = f" {currency}" if isinstance(currency, str) and currency.strip() else ""
        first_line = f"{service_name} \u0435 \u043e\u043a\u043e\u043b\u0443 {price:g}{currency_text}."
    elif isinstance(price, str) and price.strip():
        first_line = f"{service_name} \u0435 {price.strip()}."
    elif isinstance(price_range, str) and price_range.strip():
        first_line = f"\u0417\u0430 {service_name.lower()} \u043e\u0440\u0438\u0435\u043d\u0442\u0430\u0446\u0438\u0441\u043a\u0438\u043e\u0442 \u0446\u0435\u043d\u043e\u0432\u0435\u043d \u043e\u043f\u0441\u0435\u0433 \u0435 {price_range.strip()}."
    else:
        return None

    lines = [first_line]
    if description:
        lines.append(description)
    lines.append("")
    lines.append("\u0417\u0430 \u0442\u043e\u0447\u043d\u0430 \u043f\u0440\u043e\u0446\u0435\u043d\u043a\u0430 \u043d\u0430\u0458\u0434\u043e\u0431\u0440\u043e \u0435 \u0434\u0430 \u0441\u0435 \u043d\u0430\u043f\u0440\u0430\u0432\u0438 \u043a\u0440\u0430\u0442\u043a\u0430 \u043a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430.")
    return "\n".join(lines)


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
    communication_rules = profile.get("\u043a\u043e\u043c\u0443\u043d\u0438\u043a\u0430\u0446\u0438\u0441\u043a\u0438_\u043f\u0440\u0430\u0432\u0438\u043b\u0430", [])
    categories = _catalog_categories(profile, services)

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
            "aliases": service.get("aliases", []),
            "category": service.get("category"),
            "price": service.get("price", service.get("\u0446\u0435\u043d\u0430")),
            "price_range": service.get("price_range", service.get("\u0446\u0435\u043d\u043e\u0432\u0435\u043d_\u043e\u043f\u0441\u0435\u0433")),
            "bookable": service.get("bookable", False)
        }
        for service in services
    ]

    services_json = json.dumps(service_catalog, ensure_ascii=False, indent=2)
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    communication_rules_text = "\n".join(f"- {rule}" for rule in communication_rules if isinstance(rule, str))
    categories_json = json.dumps(categories, ensure_ascii=False, indent=2)

    system_prompt = (
        template.replace("{{business_name}}", business_name)
        .replace("{{goal}}", goal)
    )

    if rules_text:
        system_prompt += f"\n\nRules:\n{rules_text}"

    system_prompt += f"\n\nAlways respond in this language: {language}"
    system_prompt += f"\n\nAllowed services catalog:\n{services_json}"
    system_prompt += f"\n\nClinical category catalog:\n{categories_json}"

    if communication_rules_text:
        system_prompt += f"\n\nCommunication rules:\n{communication_rules_text}"

    if allow_booking:
        system_prompt += (
            "\n\nBooking capability: enabled."
            "\nCanonical intents: greeting, suggest_service, confirm_booking, fallback."
            "\nIf the user confirms booking, return confirm_booking."
            "\nIf the user asks for a price and the catalog includes price or price_range, mention that orientation price and then recommend consultation."
            "\nIf the user asks what services are available, present them grouped by category."
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

    if _is_service_list_request(message):
        reply = _service_list_reply(profile, services)
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        _trace_response(
            tenant,
            session_id,
            reply,
            _stage_name(SESSION_STATE.get(session_key)),
        )
        return reply, session_id

    if _is_price_request(message):
        matched_service = _match_service_for_message(message, services)
        price_reply = _orientation_price_text(matched_service) if matched_service else None
        if price_reply:
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="suggest_service",
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            _trace_response(
                tenant,
                session_id,
                price_reply,
                _stage_name(SESSION_STATE.get(session_key)),
            )
            return price_reply, session_id

    casual_reply = _casual_reply(message)
    if casual_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        _trace_response(
            tenant,
            session_id,
            casual_reply,
            _stage_name(SESSION_STATE.get(session_key)),
        )
        return casual_reply, session_id

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
