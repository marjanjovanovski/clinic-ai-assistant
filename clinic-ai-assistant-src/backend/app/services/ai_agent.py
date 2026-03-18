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
INTERACTION_HISTORY = {}
MAX_INTERACTION_HISTORY = 6
MAX_CONTEXT_INTERACTIONS = 1
CANONICAL_INTENTS = {"greeting", "suggest_service", "confirm_booking", "collect_contact", "fallback"}
BOOKING_INPUT_FIELD_VALUE = "FIELD_VALUE"
BOOKING_INPUT_CLARIFICATION = "CLARIFICATION_QUESTION"
BOOKING_INPUT_FEEDBACK = "FEEDBACK_OR_META"
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

    return ""


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


def _profile_text(profile: dict, *path: str) -> str | None:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _profile_text_map(profile: dict, *path: str) -> dict:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(key)

    return value if isinstance(value, dict) else {}


def _profile_list(profile: dict, *path: str) -> list[str]:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return []
        value = value.get(key)

    if not isinstance(value, list):
        return []

    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _render_profile_text(profile: dict, path: tuple[str, ...], **values) -> str | None:
    template = _profile_text(profile, *path)
    if not template:
        return None

    return template.format(**values)


def _field_prompt(profile: dict, field_name: str) -> str:
    field_prompts = _profile_text_map(profile, "reply_texts", "field_prompts")
    value = field_prompts.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return field_name


def _conversation_rule_list(profile: dict, rule_name: str) -> list[str]:
    return _profile_list(profile, "conversation_rules", rule_name)


def _conversation_rule_patterns(profile: dict) -> list[tuple[list[str], str]]:
    patterns = profile.get("conversation_rules", {}).get("casual_reply_patterns", [])
    if not isinstance(patterns, list):
        return []

    normalized_patterns: list[tuple[list[str], str]] = []
    for item in patterns:
        if not isinstance(item, dict):
            continue

        triggers = item.get("triggers")
        reply_key = item.get("reply_key")
        if not isinstance(triggers, list) or not isinstance(reply_key, str) or not reply_key.strip():
            continue

        clean_triggers = [trigger.strip() for trigger in triggers if isinstance(trigger, str) and trigger.strip()]
        if clean_triggers:
            normalized_patterns.append((clean_triggers, reply_key.strip()))

    return normalized_patterns


def _status_for_stage(stage: str | None) -> str:
    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def _message_tokens(value: str) -> set[str]:
    normalized = _normalize_lookup_text(value)
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9\u0400-\u04FF]+", normalized)
        if token
    }


def _messages_are_similar(left: str, right: str) -> bool:
    left_normalized = _normalize_lookup_text(left)
    right_normalized = _normalize_lookup_text(right)

    if not left_normalized or not right_normalized:
        return False

    if left_normalized == right_normalized:
        return True

    if left_normalized in right_normalized or right_normalized in left_normalized:
        return True

    left_tokens = _message_tokens(left_normalized)
    right_tokens = _message_tokens(right_normalized)
    if not left_tokens or not right_tokens:
        return False

    overlap = len(left_tokens & right_tokens)
    smallest = min(len(left_tokens), len(right_tokens))
    return smallest > 0 and (overlap / smallest) >= 0.75


def _recent_interactions(session_key: str) -> list[dict]:
    return INTERACTION_HISTORY.get(session_key, [])


def _last_interaction(session_key: str) -> dict | None:
    history = _recent_interactions(session_key)
    if not history:
        return None

    return history[-1]


def _record_interaction(session_key: str, message: str, reply: str, response_type: str | None) -> None:
    history = INTERACTION_HISTORY.setdefault(session_key, [])
    history.append(
        {
            "message": _normalize_lookup_text(message),
            "reply": reply,
            "response_type": response_type,
        }
    )
    if len(history) > MAX_INTERACTION_HISTORY:
        del history[:-MAX_INTERACTION_HISTORY]


def _bounded_ai_input(
    *,
    system_prompt: str,
    session_key: str,
    message: str,
    stage: str | None,
    stage_context_template: str | None,
) -> list[dict]:
    prompt_input: list[dict] = [{"role": "system", "content": system_prompt}]

    if stage and isinstance(stage_context_template, str) and stage_context_template.strip():
        prompt_input.append(
            {
                "role": "system",
                "content": stage_context_template.format(stage=stage),
            }
        )

    recent_context = _recent_interactions(session_key)[-MAX_CONTEXT_INTERACTIONS:]
    for item in recent_context:
        previous_user_message = item.get("message")
        previous_assistant_reply = item.get("reply")

        if isinstance(previous_user_message, str) and previous_user_message.strip():
            prompt_input.append({"role": "user", "content": previous_user_message.strip()})

        if isinstance(previous_assistant_reply, str) and previous_assistant_reply.strip():
            prompt_input.append({"role": "assistant", "content": previous_assistant_reply.strip()})

    prompt_input.append({"role": "user", "content": message})
    return prompt_input


def _is_broad_pricing_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    price_terms = _conversation_rule_list(profile, "broad_pricing_price_terms")
    has_price_language = any(
        token in normalized_message
        for token in price_terms
    )
    service_terms = _conversation_rule_list(profile, "broad_pricing_service_terms")
    has_service_language = any(
        token in normalized_message
        for token in service_terms
    )
    return has_price_language and has_service_language and not _is_price_request(message, profile)


def _is_consultation_explanation_request(message: str, services: list[dict], profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    consultation_service = _match_service_for_message(message, services)
    if not consultation_service or consultation_service.get("id") != "consultation":
        return False

    return any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "consultation_explanation_triggers")
    )


def _consultation_service(services: list[dict]) -> dict | None:
    for service in services:
        if service.get("id") == "consultation":
            return service
    return None


def _should_start_consultation_booking(message: str, session_key: str, services: list[dict], profile: dict) -> bool:
    if not _is_booking_confirmation(message, profile):
        return False

    last_item = _last_interaction(session_key)
    if not last_item:
        return False

    if last_item.get("response_type") == "service_list":
        return False

    consultation_service = _consultation_service(services)
    if not consultation_service:
        return False

    last_reply = last_item.get("reply", "")
    matched_service = _match_service_for_message(last_reply, services) if isinstance(last_reply, str) else None
    return bool(matched_service and matched_service.get("id") == consultation_service.get("id"))


def _is_contact_clarification(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if "?" in message:
        return True

    prefixes = _conversation_rule_list(profile, "contact_clarification_prefixes")
    if any(normalized_message.startswith(prefix) for prefix in prefixes):
        return True

    phrases = _conversation_rule_list(profile, "contact_clarification_phrases")
    return any(phrase in normalized_message for phrase in phrases)


def _contact_clarification_reply(profile: dict, field_name: str) -> str:
    field_label = _field_prompt(profile, field_name)
    contact_replies = _profile_text_map(profile, "reply_texts", "contact_clarification_replies")
    template = contact_replies.get(field_name) or contact_replies.get("default")
    if isinstance(template, str) and template.strip():
        normalized_template = template.strip()
        if "{field_prompt}" in normalized_template:
            static_text = normalized_template.replace("{field_prompt}", "").strip()
            if static_text:
                return " ".join(static_text.split())
        return normalized_template.format(field_prompt=field_label)
    return field_label


def _is_field_level_clarification(message: str, field_name: str | None) -> bool:
    if field_name is None:
        return False

    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if field_name == "name":
        return any(token in normalized_message for token in ("име", "im"))

    if field_name == "phone":
        return any(token in normalized_message for token in ("бро", "bro", "тел", "tel", "контакт", "kontakt"))

    if field_name == "email":
        return any(token in normalized_message for token in ("пошт", "mail", "email"))

    return False


def _is_booking_scope_clarification(message: str, field_name: str | None) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if "закаж" in normalized_message or "zakaz" in normalized_message:
        return True

    return "?" in message and not _is_field_level_clarification(message, field_name)


def _classify_booking_input(message: str, profile: dict) -> str:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return BOOKING_INPUT_FEEDBACK

    if "?" in message or _is_contact_clarification(message, profile):
        return BOOKING_INPUT_CLARIFICATION

    return BOOKING_INPUT_FIELD_VALUE


def _booking_scope_clarification_reply(state: dict, services: list[dict], profile: dict) -> str:
    service_id = state.get("service_id")
    if service_id == "consultation":
        consultation_reply = _profile_text(profile, "repetition_responses", "consultation_explanation")
        if consultation_reply:
            return consultation_reply

    service = next(
        (item for item in services if item.get("id") == service_id),
        None,
    )
    if not isinstance(service, dict):
        return _fallback_reply(profile)

    service_name = _service_display_name(service)
    description = _service_display_description(service)
    if not service_name or not description:
        return _fallback_reply(profile)

    article_name = service.get("article_name") or service_name
    sentence_description = description[0].lower() + description[1:] if description else description
    followup = _profile_text(profile, "reply_texts", "service_description_followup")
    reply = _render_profile_text(
        profile,
        ("reply_texts", "service_description_template"),
        article_name=article_name,
        service_name=service_name,
        description=sentence_description,
        followup=followup or "",
    )
    return reply or _fallback_reply(profile)


def _is_plausible_contact_name(message: str) -> bool:
    if any(char.isdigit() for char in message):
        return False

    name_tokens = re.findall(r"[A-Za-z\u0400-\u04FF]+", message)
    if not name_tokens:
        return False

    if len(name_tokens) > 4:
        return False

    return all(len(token) >= 2 for token in name_tokens)


def _is_plausible_contact_phone(message: str) -> bool:
    digits_only = re.sub(r"\D+", "", message)
    return len(digits_only) >= 6


def _is_valid_contact_field_value(field_name: str | None, message: str, profile: dict) -> bool:
    if field_name is None:
        return False

    trimmed_message = message.strip()
    normalized_message = _normalize_lookup_text(trimmed_message)
    if not normalized_message:
        return False

    if _classify_booking_input(message, profile) != BOOKING_INPUT_FIELD_VALUE:
        return False

    if field_name == "name":
        return _is_plausible_contact_name(trimmed_message)

    if field_name == "phone":
        return _is_plausible_contact_phone(trimmed_message)

    if field_name == "email":
        if "@" not in trimmed_message:
            return False

        confirmation_words = {
            word.casefold()
            for word in _conversation_rule_list(profile, "booking_confirm_words")
        }
        return normalized_message not in confirmation_words

    return True


def _unknown_service_detail_reply(message: str, services: list[dict], profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    detail_triggers = _conversation_rule_list(profile, "service_detail_triggers")
    if not any(trigger in normalized_message for trigger in detail_triggers):
        return None

    service = _match_service_for_message(message, services)
    if not service:
        return None

    known_text_parts: list[str] = []
    for field_name in ("name", "име", "description", "опис", "article_name", "category"):
        value = service.get(field_name)
        if isinstance(value, str) and value.strip():
            known_text_parts.append(_normalize_lookup_text(value))

    for field_name in ("aliases", "keywords", "symptoms", "препорачано_за"):
        values = service.get(field_name) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    known_text_parts.append(_normalize_lookup_text(item))

    if any(trigger in " ".join(known_text_parts) for trigger in detail_triggers):
        return None

    return _profile_text(profile, "conversation_rules", "safe_detail_fallback")


def _repetition_reformulation(
    *,
    message: str,
    session_key: str,
    services: list[dict],
    profile: dict,
) -> str | None:
    history = _recent_interactions(session_key)
    if not history:
        return None

    repeated = any(_messages_are_similar(message, item.get("message", "")) for item in reversed(history))
    if not repeated:
        return None

    if _is_broad_pricing_request(message, profile):
        return _profile_text(profile, "repetition_responses", "broad_pricing")

    if _is_service_list_request(message, profile):
        return _service_list_reply(profile, services)

    if _is_consultation_explanation_request(message, services, profile):
        return _profile_text(profile, "repetition_responses", "consultation_explanation")

    return None


def _finalize_reply(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    message: str,
    reply: str,
    response_type: str | None,
    services: list[dict],
    profile: dict,
    stage_after: str | None,
) -> str:
    final_reply = reply
    reformulated = _repetition_reformulation(
        message=message,
        session_key=session_key,
        services=services,
        profile=profile,
    )
    if reformulated:
        final_reply = reformulated

    _record_interaction(session_key, message, final_reply, response_type)
    _trace_response(tenant, session_id, final_reply, stage_after)
    return final_reply


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
    profile: dict,
) -> tuple[str, str]:
    SESSION_STATE[session_key] = {
        "stage": "collecting_contact",
        "service_id": service_id,
        "next_field": collect_fields[0],
        "data": {}
    }
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key])
    return _field_prompt(profile, collect_fields[0]), session_id


def _is_booking_confirmation(message: str, profile: dict) -> bool:
    return message.strip().casefold() in {
        word.casefold()
        for word in _conversation_rule_list(profile, "booking_confirm_words")
    }


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


def _is_service_list_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_list_triggers")
    ):
        return True

    return "katalog" in normalized_message or "каталог" in normalized_message


def _is_price_request(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    return any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "price_triggers")
    )


def _greeting_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if normalized_message not in {
        trigger.casefold()
        for trigger in _conversation_rule_list(profile, "greeting_triggers")
    }:
        return None

    return _profile_text(profile, "reply_texts", "greeting_short")


def _service_clarification_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)

    if normalized_message in {
        trigger.casefold()
        for trigger in _conversation_rule_list(profile, "service_clarification_specific_triggers")
    }:
        return _profile_text(profile, "reply_texts", "service_clarification_specific", "koja_usluga_mi_treba")

    if any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_clarification_triggers")
    ):
        return _profile_text(profile, "reply_texts", "service_clarification")

    return None


def _casual_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    casual_replies = _profile_text_map(profile, "reply_texts", "casual_replies")

    for triggers, reply_key in _conversation_rule_patterns(profile):
        if any(trigger in normalized_message for trigger in triggers):
            reply = casual_replies.get(reply_key)
            if isinstance(reply, str) and reply.strip():
                return reply.strip()

    return None


def _is_acknowledgment_input(message: str, profile: dict) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if normalized_message in {
        word.casefold()
        for word in _conversation_rule_list(profile, "booking_confirm_words")
    }:
        return True

    for triggers, _reply_key in _conversation_rule_patterns(profile):
        if any(trigger in normalized_message for trigger in triggers):
            return True

    return False


def _has_active_topic_context(session_key: str, services: list[dict]) -> bool:
    last_item = _last_interaction(session_key)
    if not last_item:
        return False

    response_type = last_item.get("response_type")
    if response_type in {"greeting", "casual"}:
        return False

    last_message = last_item.get("message", "")
    if isinstance(last_message, str) and _match_service_for_message(last_message, services):
        return True

    last_reply = last_item.get("reply", "")
    if isinstance(last_reply, str) and _match_service_for_message(last_reply, services):
        return True

    return response_type in {"suggest_service", "service_description", "explicit_price"}


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


def _orientation_price_text(service: dict, profile: dict) -> str | None:
    service_name = _service_display_name(service)
    price = service.get("price", service.get("\u0446\u0435\u043d\u0430"))
    currency = service.get("\u0432\u0430\u043b\u0443\u0442\u0430")
    price_range = service.get("price_range", service.get("\u0446\u0435\u043d\u043e\u0432\u0435\u043d_\u043e\u043f\u0441\u0435\u0433"))
    description = _service_display_description(service)

    if isinstance(price, (int, float)):
        currency_text = f" {currency}" if isinstance(currency, str) and currency.strip() else ""
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "numeric"),
            service_name=service_name,
            price=f"{price:g}",
            currency=currency_text,
        )
    elif isinstance(price, str) and price.strip():
        if price.strip().casefold() == "\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e":
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "free"),
                service_name=service_name,
            )
        else:
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "text"),
                service_name=service_name,
                price=price.strip(),
            )
    elif isinstance(price_range, str) and price_range.strip():
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "range"),
            service_name=service_name,
            service_name_lower=service_name.lower(),
            price_range=price_range.strip(),
        )
    else:
        return None

    if not first_line:
        return None

    lines = [first_line]
    if description:
        lines.append(description)
    lines.append("")
    followup = _profile_text(profile, "reply_texts", "price_followup")
    if followup:
        lines.append(followup)
    return "\n".join(lines)


def _service_description_reply(message: str, services: list[dict], profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_description_triggers")
    ):
        return None

    service = _match_service_for_message(message, services)
    if not service:
        return None

    service_name = _service_display_name(service)
    description = _service_display_description(service)
    if not description:
        return None

    article_name = service.get("article_name") or service_name
    sentence_description = description[0].lower() + description[1:] if description else description
    followup = _profile_text(profile, "reply_texts", "service_description_followup")
    return _render_profile_text(
        profile,
        ("reply_texts", "service_description_template"),
        article_name=article_name,
        service_name=service_name,
        description=sentence_description,
        followup=followup or "",
    )


def _is_global_service_intent(message: str, services: list[dict], profile: dict) -> bool:
    return any(
        (
            _is_service_list_request(message, profile),
            _is_price_request(message, profile),
            bool(_service_clarification_reply(message, profile)),
            bool(_service_description_reply(message, services, profile)),
        )
    )


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
            "bookable": service.get("bookable", False)
        }
        for service in services
    ]

    services_json = json.dumps(service_catalog, ensure_ascii=False, indent=2)
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    communication_rules_text = "\n".join(f"- {rule}" for rule in communication_rules if isinstance(rule, str))
    categories_json = json.dumps(categories, ensure_ascii=False, indent=2)
    conversation_behavior = profile.get("conversation_behavior", {})
    context_carry = conversation_behavior.get("context_carry", {}) if isinstance(conversation_behavior, dict) else {}
    stage_context_template = context_carry.get("stage_context_template")

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
            "\nIf the user asks what services are available, present them grouped by category."
            "\nDo not volunteer prices in general descriptive answers."
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
        INTERACTION_HISTORY.pop(session_key, None)
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
        and _is_booking_confirmation(message, profile)
    ):
        reply, session_id = _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            state.get("service_id"),
            collect_fields,
            profile,
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
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="confirm_booking",
            services=services,
            profile=profile,
            stage_after="collecting_contact",
        )
        return final_reply, session_id

    if (
        state
        and state.get("stage") == "collecting_contact"
        and _is_global_service_intent(message, services, profile)
    ):
        old_session_id = session_id
        SESSION_STATE.pop(session_key, None)
        INTERACTION_HISTORY.pop(session_key, None)
        session_id = _normalize_session_id(None)
        session_key = _session_key(tenant, session_id)
        state = None
        stage_before = None
        trace_event(
            tenant,
            old_session_id,
            "SESSION_RESET_FOR_GLOBAL_INTENT",
            old_session_id=old_session_id,
            new_session_id=session_id,
            reason="stale_collecting_contact_global_intent",
        )
        trace_event(
            tenant,
            session_id,
            "SESSION_CREATED",
            reason="stale_collecting_contact_global_intent",
            previous_session_id=old_session_id,
        )

    # Booking state 2: backend owns the contact collection prompts until completion.
    if state and state.get("stage") == "collecting_contact":
        next_field = state.get("next_field")

        booking_input_type = _classify_booking_input(message, profile)

        if booking_input_type == BOOKING_INPUT_CLARIFICATION:
            if _is_booking_scope_clarification(message, next_field):
                reply = _booking_scope_clarification_reply(state, services, profile)
            else:
                reply = _contact_clarification_reply(profile, next_field)
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after="collecting_contact",
            )
            return final_reply, session_id

        if not _is_valid_contact_field_value(next_field, message, profile):
            reply = _field_prompt(profile, next_field)
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after="collecting_contact",
            )
            return final_reply, session_id

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
            reply = _field_prompt(profile, remaining[0])
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after="collecting_contact",
            )
            return final_reply, session_id

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
        reply = _profile_text(profile, "reply_texts", "booking_completed")
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="collect_contact",
            services=services,
            profile=profile,
            stage_after="completed",
        )
        return final_reply, session_id

    if not state and allow_booking and _should_start_consultation_booking(message, session_key, services, profile):
        SESSION_STATE[session_key] = {
            "stage": "awaiting_booking_confirmation",
            "service_id": "consultation",
        }
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "awaiting_booking_confirmation",
            reason="predicted_consultation_confirmation",
        )
        reply, session_id = _start_collecting_contact(
            tenant,
            session_id,
            session_key,
            "consultation",
            collect_fields,
            profile,
        )
        _trace_stage_transition(
            tenant,
            session_id,
            "awaiting_booking_confirmation",
            "collecting_contact",
            reason="predicted_consultation_confirmation",
        )
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="confirm_booking",
            stage_before=stage_before,
            stage_after="collecting_contact",
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="confirm_booking",
            services=services,
            profile=profile,
            stage_after="collecting_contact",
        )
        return final_reply, session_id

    greeting_reply = _greeting_reply(message, profile)
    if greeting_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="greeting",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=greeting_reply,
            response_type="greeting",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    clarification_reply = _service_clarification_reply(message, profile)
    if clarification_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=clarification_reply,
            response_type="service_clarification",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    if _is_service_list_request(message, profile):
        reply = _service_list_reply(profile, services)
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=reply,
            response_type="service_list",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    if _is_price_request(message, profile):
        matched_service = _match_service_for_message(message, services)
        price_reply = _orientation_price_text(matched_service, profile) if matched_service else None
        if price_reply:
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="suggest_service",
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=price_reply,
                response_type="explicit_price",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

    description_reply = _service_description_reply(message, services, profile)
    if description_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="suggest_service",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=description_reply,
            response_type="service_description",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    casual_reply = _casual_reply(message, profile)
    if casual_reply and not (
        _is_acknowledgment_input(message, profile)
        and _has_active_topic_context(session_key, services)
    ):
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=casual_reply,
            response_type="casual",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    cautious_detail_reply = _unknown_service_detail_reply(message, services, profile)
    if cautious_detail_reply:
        _log_chat_state(
            message=message,
            session_id=session_id,
            intent="fallback",
            stage_before=stage_before,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        final_reply = _finalize_reply(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            message=message,
            reply=cautious_detail_reply,
            response_type="fallback",
            services=services,
            profile=profile,
            stage_after=_stage_name(SESSION_STATE.get(session_key)),
        )
        return final_reply, session_id

    try:
        client = OpenAI(api_key=api_key)

        if DEBUG_AI:
            logger.debug("OPENAI CALL START tenant=%s session_id=%s", tenant, session_id)

        trace_event(tenant, session_id, "AI_CALL_START")
        ai_input = _bounded_ai_input(
            system_prompt=system_prompt,
            session_key=session_key,
            message=message,
            stage=stage_before,
            stage_context_template=stage_context_template,
        )
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=ai_input
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
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=reply,
                    response_type="fallback",
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

            raw_intent = parsed.get("intent")
            intent = _normalize_intent(raw_intent)
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")
            booking_input_type = _classify_booking_input(message, profile)

            trace_event(
                tenant,
                session_id,
                "INTENT_NORMALIZED",
                raw_intent=raw_intent,
                normalized_intent=intent,
                service_id=service_id,
            )

            if (
                intent == "confirm_booking"
                and allow_booking
                and booking_input_type == BOOKING_INPUT_FIELD_VALUE
                and _is_booking_confirmation(message, profile)
            ):
                reply, session_id = _start_collecting_contact(
                    tenant,
                    session_id,
                    session_key,
                    service_id,
                    collect_fields,
                    profile,
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
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=reply,
                    response_type="confirm_booking",
                    services=services,
                    profile=profile,
                    stage_after="collecting_contact",
                )
                return final_reply, session_id

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
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=message_text,
                    response_type=intent,
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

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
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="fallback",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

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
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=reply,
                response_type="fallback",
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            return final_reply, session_id

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
