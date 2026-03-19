import json
import logging
import os
import random
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
UNKNOWN_NAME_CONFIRM_MODE = "confirm_candidate"
UNKNOWN_NAME_REPEAT_MODE = "repeat_request"
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
    persisted_state = load_lead_checkpoint(tenant, session_id)

    if state is None:
        state = persisted_state
    elif isinstance(state, dict) and isinstance(persisted_state, dict):
        persisted_data = persisted_state.get("data")
        if isinstance(persisted_data, dict):
            authoritative_data = {}
            for field_name, value in persisted_data.items():
                if isinstance(value, str) and value.strip():
                    authoritative_data[field_name] = value
            state["data"] = authoritative_data

        persisted_stage = persisted_state.get("stage")
        if persisted_stage in {"awaiting_booking_confirmation", "collecting_contact", "completed"}:
            state["stage"] = persisted_stage

        if persisted_state.get("service_id"):
            state["service_id"] = persisted_state.get("service_id")

        if persisted_state.get("next_field") is not None:
            state["next_field"] = persisted_state.get("next_field")

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


def _field_error_prompt(profile: dict, field_name: str, **values) -> str | None:
    error_prompts = _profile_text_map(profile, "reply_texts", "field_error_prompts")
    template = error_prompts.get(field_name)
    if isinstance(template, str) and template.strip():
        return template.strip().format(**values)
    return None


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


def _transliterate_macedonian_text(value: str) -> str:
    transliteration_map = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
        "ѓ": "gj", "е": "e", "ж": "zh", "з": "z", "ѕ": "dz",
        "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj",
        "м": "m", "н": "n", "њ": "nj", "о": "o", "п": "p",
        "р": "r", "с": "s", "т": "t", "ќ": "kj", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "џ": "dj",
        "ш": "sh",
    }
    return "".join(transliteration_map.get(char, char) for char in value.casefold())


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
    return any(_contains_lookup_phrase(normalized_message, phrase) for phrase in phrases)


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


def _contains_lookup_phrase(normalized_message: str, phrase: str) -> bool:
    normalized_phrase = _normalize_lookup_text(phrase)
    if not normalized_message or not normalized_phrase:
        return False

    return f" {normalized_phrase} " in f" {normalized_message} "


def _field_clarification_with_resume(profile: dict, field_name: str) -> str:
    clarification_reply = _contact_clarification_reply(profile, field_name)
    field_prompt = _field_prompt(profile, field_name)

    if field_name != "phone":
        return clarification_reply

    if clarification_reply == field_prompt:
        return field_prompt

    return f"{clarification_reply}\n{field_prompt}"


def _contact_collection_redirect_reply(profile: dict, field_name: str | None) -> str:
    field_prompt = _field_prompt(profile, field_name or "name")
    redirect_reply = _render_profile_text(
        profile,
        ("reply_texts", "booking_interruption_redirect"),
        field_prompt=field_prompt,
    )
    return redirect_reply or field_prompt


def _has_contact_field_reference(message: str) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    contact_reference_tokens = (
        "име",
        "im",
        "бро",
        "bro",
        "тел",
        "tel",
        "контакт",
        "kontakt",
        "пошт",
        "mail",
        "email",
    )
    return any(token in normalized_message for token in contact_reference_tokens)


def _has_contact_ownership_clarification(message: str) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    ownership_tokens = (
        "moj", "moja", "moeto", "negov", "negova", "negovo",
        "nejzin", "nejzina", "nejzino", "tug", "tugjo",
        "мој", "моја", "моето", "негов", "негова", "негово",
        "нејзин", "нејзина", "нејзино", "туѓ", "туѓо",
    )
    return any(token in normalized_message for token in ownership_tokens)


def _is_field_level_clarification(message: str, field_name: str | None) -> bool:
    if field_name is None:
        return False

    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if field_name == "name":
        return any(token in normalized_message for token in ("име", "im")) or _has_contact_ownership_clarification(message)

    if field_name == "phone":
        return (
            any(token in normalized_message for token in ("бро", "bro", "тел", "tel", "контакт", "kontakt"))
            or _has_contact_ownership_clarification(message)
        )

    if field_name == "email":
        return any(token in normalized_message for token in ("пошт", "mail", "email")) or _has_contact_ownership_clarification(message)

    return False


def _is_booking_scope_clarification(message: str, field_name: str | None) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if _has_contact_field_reference(message):
        return False

    if "закаж" in normalized_message or "zakaz" in normalized_message:
        return True

    return "?" in message and not _is_field_level_clarification(message, field_name)


def _is_catalog_reference_during_contact_collection(message: str, services: list[dict], profile: dict) -> bool:
    if _match_service_for_message(message, services):
        return True

    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if _is_service_list_request(message, profile):
        return True

    transliterated_message = _normalize_lookup_text(_transliterate_macedonian_text(normalized_message))

    for category in _ordered_categories(profile, services):
        category_name = category.get("име") or category.get("name")
        if isinstance(category_name, str) and category_name.strip():
            normalized_category_name = _normalize_lookup_text(category_name)
            transliterated_category_name = _normalize_lookup_text(_transliterate_macedonian_text(category_name))
            if normalized_category_name == normalized_message or transliterated_category_name == transliterated_message:
                return True

        category_services = category.get("услуги") or category.get("services") or []
        for service in category_services:
            if not isinstance(service, dict):
                continue
            service_name = _service_display_name(service)
            if not service_name:
                continue
            normalized_service_name = _normalize_lookup_text(service_name)
            transliterated_service_name = _normalize_lookup_text(_transliterate_macedonian_text(service_name))
            if normalized_service_name == normalized_message or transliterated_service_name == transliterated_message:
                return True

    return False


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
    return len(digits_only) >= 9


def _is_plausible_contact_email(message: str) -> bool:
    trimmed_message = message.strip()
    if not trimmed_message or len(trimmed_message) > 254:
        return False

    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", trimmed_message):
        return False

    local_part, _, domain_part = trimmed_message.partition("@")
    if not local_part or not domain_part:
        return False

    if local_part.startswith(".") or local_part.endswith(".") or ".." in local_part:
        return False

    if domain_part.startswith(".") or domain_part.endswith(".") or ".." in domain_part:
        return False

    return True


def _is_conversational_filler_input(message: str, profile: dict) -> bool:
    if _is_acknowledgment_input(message, profile):
        return True

    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    return normalized_message in {"ajde", "ајде"}


def _is_valid_contact_field_value(field_name: str | None, message: str, profile: dict) -> bool:
    if field_name is None:
        return False

    trimmed_message = message.strip()
    normalized_message = _normalize_lookup_text(trimmed_message)
    if not normalized_message:
        return False

    if _classify_booking_input(message, profile) != BOOKING_INPUT_FIELD_VALUE:
        return False

    if _is_conversational_filler_input(message, profile):
        return False

    if field_name == "name":
        return _is_plausible_contact_name(trimmed_message)

    if field_name == "phone":
        return _is_plausible_contact_phone(trimmed_message)

    if field_name == "email":
        if not _is_plausible_contact_email(trimmed_message):
            return False

        confirmation_words = {
            word.casefold()
            for word in _conversation_rule_list(profile, "booking_confirm_words")
        }
        return normalized_message not in confirmation_words

    return True


def _normalized_name_candidate(value: str) -> str | None:
    cleaned_value = re.sub(r"[^\w\s\u0400-\u04FF-]", " ", value, flags=re.UNICODE)
    candidate_tokens = re.findall(r"[A-Za-z\u0400-\u04FF]+", cleaned_value)
    if not candidate_tokens:
        return None

    if len(candidate_tokens) > 3:
        return None

    candidate_name = " ".join(token.capitalize() for token in candidate_tokens)
    return candidate_name if _is_plausible_contact_name(candidate_name) else None


def _extract_name_from_contact_bundle(message: str) -> str | None:
    cleaned_message = re.sub(r"[^\w\s\u0400-\u04FF-]", " ", message, flags=re.UNICODE)
    normalized_message = _normalize_lookup_text(cleaned_message)
    if not normalized_message:
        return None

    normalized_message = re.sub(
        r"\b(moeto ime e|jas sum|ime e|moeto ime|ime mi e|моето име е|јас сум|името е|моето име|името ми е)\b",
        " ",
        normalized_message,
    )
    stopwords = {
        "moeto", "ime", "e", "jas", "sum", "moze", "ve", "kontakt", "email", "mail",
        "telefon", "phone", "number", "broj", "tel",
        "zdravo", "zdravoo", "hello", "hi", "mi",
        "моето", "име", "е", "јас", "сум", "може", "ве", "контакт", "пошта", "здраво", "ми",
    }
    candidate_tokens = [
        token
        for token in re.findall(r"[A-Za-z\u0400-\u04FF]+", normalized_message)
        if token not in stopwords
    ]
    return _normalized_name_candidate(" ".join(candidate_tokens))


def _extract_explicit_contact_name(message: str) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return None

    explicit_name_patterns = (
        r"\bjas sum\s+(.+)$",
        r"\bmoeto ime e\s+(.+)$",
        r"\bime mi e\s+(.+)$",
        r"\bime e\s+(.+)$",
        r"\bјас сум\s+(.+)$",
        r"\bмоето име е\s+(.+)$",
        r"\bимето ми е\s+(.+)$",
        r"\bимето е\s+(.+)$",
    )
    for pattern in explicit_name_patterns:
        match = re.search(pattern, normalized_message)
        if match:
            return _normalized_name_candidate(match.group(1))
    return None


def _recent_contact_name_hint(session_key: str) -> str | None:
    for item in reversed(_recent_interactions(session_key)):
        message = item.get("message")
        if not isinstance(message, str) or not message.strip():
            continue
        candidate_name = _extract_explicit_contact_name(message)
        if candidate_name:
            return candidate_name
    return None


def _booking_start_reply(profile: dict, known_name: str | None = None) -> str:
    if known_name:
        known_name_reply = _render_profile_text(
            profile,
            ("reply_texts", "booking_known_name_confirmation"),
            known_name=known_name,
        )
        if known_name_reply:
            return known_name_reply
    return _field_prompt(profile, "name")


def _normalize_freeform_name_value(value: str) -> str:
    cleaned_value = re.sub(r"\s+", " ", value.strip())
    return cleaned_value.strip("\"'„”")


def _clear_unknown_name_state(state: dict) -> None:
    for key in ("unknown_name_mode", "unknown_name_candidate"):
        state.pop(key, None)


def _should_offer_unknown_name_recovery(message: str, profile: dict) -> bool:
    trimmed_message = message.strip()
    if not trimmed_message:
        return False

    if _classify_booking_input(message, profile) != BOOKING_INPUT_FIELD_VALUE:
        return False

    if _is_conversational_filler_input(message, profile):
        return False

    if any(char.isdigit() for char in trimmed_message):
        return False

    token_count = len(re.findall(r"\S+", trimmed_message))
    return token_count <= 4 and len(trimmed_message) <= 60


def _unknown_name_confirmation_reply(profile: dict, candidate: str) -> str:
    template = _profile_text(profile, "reply_texts", "unknown_name_confirmation")
    if template:
        return template.format(candidate_name=candidate)
    return f'Дали „{candidate}“ е вашето име?'


def _unknown_name_retry_reply(profile: dict) -> str:
    template = _profile_text(profile, "reply_texts", "unknown_name_retry")
    if template:
        return template
    return "Ве молам дали може повторно да го внесете вашето име."


def _start_unknown_name_recovery(state: dict, message: str, profile: dict) -> str:
    candidate = _normalize_freeform_name_value(message)
    recovery_mode = random.choice((UNKNOWN_NAME_CONFIRM_MODE, UNKNOWN_NAME_REPEAT_MODE))
    state["unknown_name_mode"] = recovery_mode

    if recovery_mode == UNKNOWN_NAME_CONFIRM_MODE:
        state["unknown_name_candidate"] = candidate
        return _unknown_name_confirmation_reply(profile, candidate)

    state.pop("unknown_name_candidate", None)
    return _unknown_name_retry_reply(profile)


def _invalid_phone_reply(profile: dict, message: str) -> str:
    digits_only = re.sub(r"\D+", "", message)
    missing_digits = max(0, 9 - len(digits_only))
    missing_digits_label = "цифра" if missing_digits == 1 else "цифри"
    invalid_reply = _field_error_prompt(
        profile,
        "phone",
        missing_digits=missing_digits,
        missing_digits_label=missing_digits_label,
    )
    if invalid_reply:
        return invalid_reply
    return _field_prompt(profile, "phone")


def _invalid_email_reply(profile: dict) -> str:
    invalid_reply = _field_error_prompt(profile, "email")
    if invalid_reply:
        return invalid_reply
    return _field_prompt(profile, "email")


def _edit_record_confirmation_reply() -> str:
    return "Дали сакате да направите промена на записот?"


def _edit_record_value_reply() -> str:
    return "Внесете ја промената"


def _edit_record_saved_reply() -> str:
    return "Промената е зачувана."


def _edit_record_cancelled_reply() -> str:
    return "Во ред, записот останува ист."


def _extract_contact_fields_from_message(
    message: str,
    missing_fields: list[str],
    profile: dict,
) -> dict[str, str]:
    extracted: dict[str, str] = {}
    remaining_text = message.strip()

    if "email" in missing_fields:
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", remaining_text)
        if email_match:
            candidate_email = email_match.group(0).strip()
            if _is_valid_contact_field_value("email", candidate_email, profile):
                extracted["email"] = candidate_email
                remaining_text = remaining_text.replace(candidate_email, " ")

    if "phone" in missing_fields:
        phone_match = re.search(r"\+?\d[\d\s()./-]{6,}\d", remaining_text)
        if phone_match:
            raw_phone = phone_match.group(0).strip()
            candidate_phone = re.sub(r"\D+", "", raw_phone)
            if _is_plausible_contact_phone(candidate_phone):
                extracted["phone"] = candidate_phone
                remaining_text = remaining_text.replace(raw_phone, " ", 1)

    if "name" in missing_fields:
        candidate_name = _extract_name_from_contact_bundle(remaining_text)
        if candidate_name and _is_valid_contact_field_value("name", candidate_name, profile):
            extracted["name"] = candidate_name

    return extracted


def _should_attempt_contact_bundle_parse(
    message: str,
    missing_fields: list[str],
    profile: dict,
) -> bool:
    if len(missing_fields) < 2:
        return False

    extracted = _extract_contact_fields_from_message(message, missing_fields, profile)
    if len(extracted) < 2:
        return False

    normalized_message = _normalize_lookup_text(message)
    has_labeled_contact_hint = any(
        token in normalized_message
        for token in (
            "telefon",
            "tel",
            "broj",
            "kontakt",
            "email",
            "mail",
            "ime",
            "phone",
            "number",
        )
    )

    explicit_email = "email" in extracted
    explicit_phone = "phone" in extracted

    return has_labeled_contact_hint or (explicit_email and explicit_phone)


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
    known_name = _recent_contact_name_hint(session_key)
    initial_data = {}
    next_field = collect_fields[0]

    SESSION_STATE[session_key] = {
        "stage": "collecting_contact",
        "service_id": service_id,
        "next_field": next_field,
        "data": initial_data,
    }
    if known_name and "name" in collect_fields:
        SESSION_STATE[session_key]["pending_name_confirmation"] = known_name
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key], required_fields=[])
    return _booking_start_reply(profile, known_name), session_id


def _normalize_collecting_contact_state(state: dict, collect_fields: list[str]) -> tuple[dict, list[str], bool]:
    changed = False

    data = state.get("data")
    if not isinstance(data, dict):
        state["data"] = {}
        data = state["data"]
        changed = True

    missing_fields = [field for field in collect_fields if field not in data]
    expected_next_field = missing_fields[0] if missing_fields else None

    if state.get("next_field") != expected_next_field:
        state["next_field"] = expected_next_field
        changed = True

    return state, missing_fields, changed


def _has_active_booking_lock(state: dict | None) -> bool:
    if not isinstance(state, dict):
        return False

    return state.get("stage") == "collecting_contact"


def _persisted_fields_match(save_result: dict | None, required_fields: list[str]) -> bool:
    if not isinstance(save_result, dict) or not save_result.get("success"):
        return False

    persisted_data = save_result.get("persisted_data")
    if not isinstance(persisted_data, dict):
        return False

    normalized_required_fields = [field_name for field_name in required_fields if field_name in {"name", "phone", "email"}]
    return all(isinstance(persisted_data.get(field_name), str) and persisted_data.get(field_name).strip() for field_name in normalized_required_fields)


def _recover_from_persistence_failure(
    state: dict,
    collect_fields: list[str],
    save_result: dict | None,
    fallback_field: str | None,
) -> str:
    persisted_data = save_result.get("persisted_data") if isinstance(save_result, dict) else {}
    if not isinstance(persisted_data, dict):
        persisted_data = {}

    missing_fields = [field_name for field_name in collect_fields if not persisted_data.get(field_name)]
    retry_field = missing_fields[0] if missing_fields else fallback_field or collect_fields[0]

    state["stage"] = "collecting_contact"
    state["next_field"] = retry_field
    state.setdefault("data", {}).pop(retry_field, None)
    return retry_field


def _is_booking_confirmation(message: str, profile: dict) -> bool:
    return message.strip().casefold() in {
        word.casefold()
        for word in _conversation_rule_list(profile, "booking_confirm_words")
    }


def _is_booking_rejection(message: str) -> bool:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    first_token = normalized_message.split(" ", 1)[0]
    return first_token in {"ne", "не", "no", "нет"}


def _booking_edit_requested_field(message: str, allowed_fields: list[str]) -> str | None:
    normalized_message = message.strip()
    prefix = "__booking_edit__:"
    if not normalized_message.startswith(prefix):
        return None

    requested_field = normalized_message[len(prefix):].strip()
    return requested_field if requested_field in allowed_fields else None


def _clear_edit_state(state: dict) -> None:
    for key in ("edit_phase", "edit_field", "edit_return_stage", "edit_return_next_field"):
        state.pop(key, None)


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


def get_booking_progress(tenant: str, session_id: str | None) -> dict | None:
    if not session_id:
        return None

    profile = load_profile_config(tenant)
    collect_fields = _profile_list(profile, "actions", "collect_contact_fields")
    if not collect_fields:
        collect_fields = ["name", "phone", "email"]

    state = _load_session_state(tenant, session_id)
    if not isinstance(state, dict):
        return None

    stage = _stage_name(state)
    if stage not in {"collecting_contact", "completed"}:
        return None

    data = state.get("data")
    if not isinstance(data, dict):
        data = {}

    field_progress = []
    completed_count = 0
    for field_name in collect_fields:
        raw_value = data.get(field_name)
        is_done = isinstance(raw_value, str) and raw_value.strip()
        if is_done:
            completed_count += 1
        field_progress.append(
            {
                "field": field_name,
                "label": _field_prompt(profile, field_name),
                "value": raw_value.strip() if is_done else None,
                "done": bool(is_done),
            }
        )

    progress_percent = 0
    if completed_count == 1:
        progress_percent = 30
    elif completed_count == 2:
        progress_percent = 60
    elif completed_count >= 3:
        progress_percent = 100

    return {
        "visible": True,
        "booking_stage": stage,
        "collection_status": completed_count,
        "collection_total": len(collect_fields),
        "progress_percent": progress_percent,
        "reservation_status": "complete" if stage == "completed" else "pending",
        "next_field": state.get("next_field"),
        "fields": field_progress,
    }


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
    requested_edit_field = _booking_edit_requested_field(message, collect_fields)

    trace_event(
        tenant,
        session_id,
        "SESSION_LOADED",
        stage_before=stage_before,
        state=state,
    )

    if (
        state
        and state.get("stage") == "completed"
        and not requested_edit_field
        and not state.get("edit_phase")
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

    if state and state.get("stage") == "collecting_contact":
        state, missing_fields, state_changed = _normalize_collecting_contact_state(state, collect_fields)
        if state_changed:
            save_lead_checkpoint(tenant, session_id, state, required_fields=[])
        if state.get("next_field") is None and missing_fields:
            state["next_field"] = missing_fields[0]
            save_lead_checkpoint(tenant, session_id, state, required_fields=[])

    if state and state.get("stage") in {"collecting_contact", "completed"} and requested_edit_field:
        existing_value = state.get("data", {}).get(requested_edit_field)
        if isinstance(existing_value, str) and existing_value.strip():
            state["edit_phase"] = "confirm"
            state["edit_field"] = requested_edit_field
            state["edit_return_stage"] = state.get("stage")
            state["edit_return_next_field"] = state.get("next_field")
            save_lead_checkpoint(tenant, session_id, state, required_fields=[])
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=_edit_record_confirmation_reply(),
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=state.get("stage"),
            )
            return final_reply, session_id

    if state and state.get("stage") in {"collecting_contact", "completed"}:
        edit_phase = state.get("edit_phase")
        edit_field = state.get("edit_field")

        if edit_phase == "confirm" and edit_field in collect_fields:
            if _is_booking_confirmation(message, profile):
                state["edit_phase"] = "value"
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=_edit_record_value_reply(),
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id
            if _is_booking_rejection(message):
                _clear_edit_state(state)
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=_edit_record_cancelled_reply(),
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=_edit_record_confirmation_reply(),
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=state.get("stage"),
            )
            return final_reply, session_id

        if edit_phase == "value" and edit_field in collect_fields:
            if not _is_valid_contact_field_value(edit_field, message, profile):
                if (
                    edit_field == "phone"
                    and re.sub(r"\D+", "", message)
                    and not state.get("phone_length_guided")
                ):
                    state["phone_length_guided"] = True
                    reply = _invalid_phone_reply(profile, message)
                elif edit_field == "email" and "@" in message:
                    reply = _invalid_email_reply(profile)
                else:
                    reply = _edit_record_value_reply()
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=reply,
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id

            state.setdefault("data", {})[edit_field] = message
            if edit_field == "phone":
                state.pop("phone_length_guided", None)

            state["stage"] = state.get("edit_return_stage") or state.get("stage")
            state["next_field"] = state.get("edit_return_next_field")
            _clear_edit_state(state)
            required_fields = collect_fields if state.get("stage") == "completed" else [edit_field]
            save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=required_fields)
            if not _persisted_fields_match(save_result, required_fields):
                final_reply = _finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply=_edit_record_value_reply(),
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id

            stage_after = state.get("stage")
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=_edit_record_saved_reply(),
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=stage_after,
            )
            return final_reply, session_id

    # Booking state 1: waiting for the user to confirm a suggested service.
    if state and state.get("stage") == "awaiting_booking_confirmation" and allow_booking:
        contact_payload_detected = any(
            (
                _should_attempt_contact_bundle_parse(message, collect_fields, profile),
                _is_valid_contact_field_value("name", message, profile),
                _is_valid_contact_field_value("phone", message, profile),
                _is_valid_contact_field_value("email", message, profile),
            )
        )
        if _is_booking_confirmation(message, profile) or contact_payload_detected:
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
                reason="backend_confirmation_word" if _is_booking_confirmation(message, profile) else "backend_contact_payload_start",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="confirm_booking",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            if not contact_payload_detected:
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
            state = SESSION_STATE.get(session_key)

    # Booking state 2: backend owns the contact collection prompts until completion.
    if _has_active_booking_lock(state):
        next_field = state.get("next_field")
        missing_fields = [field for field in collect_fields if field not in state.get("data", {})]
        pending_name_confirmation = state.get("pending_name_confirmation")
        force_accept_name = False

        if next_field == "name" and isinstance(pending_name_confirmation, str) and pending_name_confirmation.strip():
            explicit_name = _extract_explicit_contact_name(message)
            if explicit_name:
                state.pop("pending_name_confirmation", None)
                message = explicit_name
            elif _is_booking_confirmation(message, profile):
                state.pop("pending_name_confirmation", None)
                message = pending_name_confirmation
            elif _is_booking_rejection(message):
                state.pop("pending_name_confirmation", None)
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                reply = _field_prompt(profile, "name")
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

        if next_field == "name":
            unknown_name_mode = state.get("unknown_name_mode")
            unknown_name_candidate = state.get("unknown_name_candidate")

            if unknown_name_mode == UNKNOWN_NAME_CONFIRM_MODE and isinstance(unknown_name_candidate, str) and unknown_name_candidate.strip():
                if _is_booking_confirmation(message, profile):
                    message = unknown_name_candidate
                    force_accept_name = True
                    _clear_unknown_name_state(state)
                elif _is_booking_rejection(message):
                    state["unknown_name_mode"] = UNKNOWN_NAME_REPEAT_MODE
                    state.pop("unknown_name_candidate", None)
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = _finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_retry_reply(profile),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id
                else:
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = _finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_confirmation_reply(profile, unknown_name_candidate),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id

            elif unknown_name_mode == UNKNOWN_NAME_REPEAT_MODE:
                if _classify_booking_input(message, profile) != BOOKING_INPUT_FIELD_VALUE or _is_conversational_filler_input(message, profile):
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = _finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_retry_reply(profile),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id

                message = _normalize_freeform_name_value(message)
                force_accept_name = bool(message)
                _clear_unknown_name_state(state)

        booking_input_type = _classify_booking_input(message, profile)

        if booking_input_type == BOOKING_INPUT_CLARIFICATION:
            if _is_field_level_clarification(message, next_field):
                reply = _field_clarification_with_resume(profile, next_field)
            else:
                reply = _contact_collection_redirect_reply(profile, next_field)
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

        if next_field == "name" and _is_catalog_reference_during_contact_collection(message, services, profile):
            reply = _contact_collection_redirect_reply(profile, next_field)
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

        extracted_fields = {}
        if _should_attempt_contact_bundle_parse(message, missing_fields, profile):
            extracted_fields = _extract_contact_fields_from_message(message, missing_fields, profile)
        if extracted_fields:
            state["data"].update(extracted_fields)

            updated_missing_fields = [field for field in collect_fields if field not in state["data"]]
            if next_field in extracted_fields and not updated_missing_fields:
                state["stage"] = "completed"
                save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
                if not _persisted_fields_match(save_result, collect_fields):
                    retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                    SESSION_STATE[session_key] = state
                    _trace_stage_transition(
                        tenant,
                        session_id,
                        stage_before,
                        "collecting_contact",
                        reason=f"persistence_retry_after_{next_field}_with_multi_field_parse",
                    )
                    _log_chat_state(
                        message=message,
                        session_id=session_id,
                        intent="collect_contact",
                        stage_before=stage_before,
                        stage_after="collecting_contact",
                    )
                    reply = _field_prompt(profile, retry_field)
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
                _trace_stage_transition(
                    tenant,
                    session_id,
                    stage_before,
                    "completed",
                    reason=f"collected_{next_field}_with_multi_field_parse",
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

            if next_field not in extracted_fields:
                state["next_field"] = next_field
                save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
                if not _persisted_fields_match(save_result, list(extracted_fields.keys())):
                    retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                    SESSION_STATE[session_key] = state
                    reply = _field_prompt(profile, retry_field)
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

            state["next_field"] = updated_missing_fields[0]
            save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
            if not _persisted_fields_match(save_result, list(extracted_fields.keys())):
                retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                SESSION_STATE[session_key] = state
                reply = _field_prompt(profile, retry_field)
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
            _trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"multi_field_parse_after_{next_field}",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = _field_prompt(profile, updated_missing_fields[0])
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

        if next_field == "name" and not force_accept_name and not _is_valid_contact_field_value(next_field, message, profile):
            if _should_offer_unknown_name_recovery(message, profile):
                reply = _start_unknown_name_recovery(state, message, profile)
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
            else:
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

        if not force_accept_name and not _is_valid_contact_field_value(next_field, message, profile):
            if (
                next_field == "phone"
                and re.sub(r"\D+", "", message)
                and not state.get("phone_length_guided")
            ):
                state["phone_length_guided"] = True
                reply = _invalid_phone_reply(profile, message)
            elif next_field == "email" and "@" in message:
                reply = _invalid_email_reply(profile)
            else:
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
        if next_field == "phone":
            state.pop("phone_length_guided", None)
        if next_field == "name":
            state.pop("pending_name_confirmation", None)

        remaining = [field for field in collect_fields if field not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
            if not _persisted_fields_match(save_result, [next_field]):
                retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                SESSION_STATE[session_key] = state
                reply = _field_prompt(profile, retry_field)
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

        state["stage"] = "completed"
        save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
        if not _persisted_fields_match(save_result, collect_fields):
            retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
            SESSION_STATE[session_key] = state
            _trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"persistence_retry_after_{next_field}",
            )
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = _field_prompt(profile, retry_field)
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

            if intent == "confirm_booking" and allow_booking:
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
                    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key], required_fields=collect_fields)
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
