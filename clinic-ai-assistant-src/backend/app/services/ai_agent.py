"""Main chat orchestration.

Architecture manifest for this file:
- This file owns orchestration, workflow state, validation boundaries, and allowed transitions.
- The LLM interprets user wording; Python code must steer workflow and side effects.
- Tenant wording, conversational content, and tenant-specific knobs belong in config, not Python logic.
- Do not build or extend phrase dictionaries here for business semantics or tenant phrasing.
- If a change appears to require many wording variants, stop and move the boundary to config,
  normalized model output, or a capability contract instead of adding more phrases.
- Scheduling and booking side effects must be gated by backend contracts and state transitions,
  not by raw message phrasing.
"""

# region Imports and Shared Constants
# Module-level setup for orchestration-owned dependencies, shared constants, and intent aliases.

import json
import logging
import os
import random
import re

from openai import OpenAI, OpenAIError, RateLimitError

from app.services import booking_credentials, scheduling_capability
from app.services.agent_profile_helpers import (
    _conversation_rule_list,
    _conversation_rule_patterns,
    _field_error_prompt,
    _field_prompt,
    _profile_list,
    _profile_text,
    _profile_text_map,
    _render_profile_text,
)
from app.services.agent_service_helpers import (
    _business_overview_reply,
    _catalog_categories,
    _match_service_for_message,
    _normalize_lookup_text,
    _ordered_categories,
    _orientation_price_text,
    _service_by_id,
    _service_description_reply,
    _service_display_description,
    _service_display_name,
    _service_list_reply,
)
from app.services.chat_session_state import (
    INTERACTION_HISTORY,
    MAX_CONTEXT_INTERACTIONS,
    MAX_INTERACTION_HISTORY,
    SESSION_STATE,
    _last_interaction,
    _load_session_state,
    _normalize_session_id,
    _recent_interactions,
    _session_key,
    _stage_name,
    _status_for_stage,
)
from app.services.config_loader import load_profile_config
from app.services.lead_store import log_chat_message, save_lead_checkpoint
from app.services.session_trace_logger import trace_event


logger = logging.getLogger(__name__)
DEBUG_AI = os.getenv("DEBUG_AI", "").strip().lower() == "true"
CANONICAL_INTENTS = {"greeting", "suggest_service", "business_overview", "list_services", "quote_price", "confirm_booking", "collect_contact", "fallback"}
BOOKING_INPUT_FIELD_VALUE = "FIELD_VALUE"
BOOKING_INPUT_CLARIFICATION = "CLARIFICATION_QUESTION"
BOOKING_INPUT_FEEDBACK = "FEEDBACK_OR_META"
AVAILABILITY_INTENT_MARKER_KEY = scheduling_capability.AVAILABILITY_INTENT_MARKER_KEY
AVAILABILITY_INTENT_OUTPUT = "availability_lookup"
UNKNOWN_NAME_CONFIRM_MODE = booking_credentials.UNKNOWN_NAME_CONFIRM_MODE
UNKNOWN_NAME_REPEAT_MODE = booking_credentials.UNKNOWN_NAME_REPEAT_MODE
INTENT_ALIASES = {
    "greeting": "greeting",
    "hello": "greeting",
    "welcome": "greeting",
    "suggest_service": "suggest_service",
    "book_service": "suggest_service",
    "booking_inquiry": "suggest_service",
    "booking_request": "suggest_service",
    "business_overview": "business_overview",
    "ask_business": "business_overview",
    "what_do_you_do": "business_overview",
    "list_services": "list_services",
    "quote_price": "quote_price",
    "price_quote": "quote_price",
    "ask_price": "quote_price",
    "confirm_booking": "confirm_booking",
    "booking_initiated": "confirm_booking",
    "booking_initiate": "confirm_booking",
    "booking_start": "confirm_booking",
    "collect_contact": "collect_contact",
    "clarify": "fallback",
    "clarification": "fallback",
    "out_of_scope": "fallback",
    "ask_services": "list_services",
    "fallback": "fallback",
}


# endregion Imports and Shared Constants


# region Module Exceptions and Trace Helpers
# Lightweight orchestration-local exceptions and operational tracing helpers.

class AIInferenceError(Exception):
    pass


def _fallback_reply(profile: dict) -> str:
    conversation = profile.get("conversation", {})
    fallback_message = conversation.get("fallback_message")

    if isinstance(fallback_message, str) and fallback_message.strip():
        return fallback_message

    return ""


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


# endregion Module Exceptions and Trace Helpers


# region LLM Input Shaping and Internal Intent Markers
# Prompt-bounding, interaction-history shaping, and model-output normalization helpers.

def _is_availability_intent_output(intent: str | None) -> bool:
    if not isinstance(intent, str):
        return False
    return intent.strip().casefold() == AVAILABILITY_INTENT_OUTPUT


def _booking_summary_payload(profile: dict, state: dict, collect_fields: list[str], data: dict, services: list[dict]) -> dict | None:
    if state.get("stage") != "completed":
        return None

    service_id = state.get("service_id")
    service = _service_by_id(services, service_id) or _consultation_service(services)
    service_name = _service_display_name(service) if isinstance(service, dict) else "Стоматолошка консултација"

    summary_fields = []
    for field_name in collect_fields:
        raw_value = data.get(field_name)
        if isinstance(raw_value, str) and raw_value.strip():
            summary_fields.append(
                {
                    "field": field_name,
                    "label": _field_prompt(profile, field_name),
                    "value": raw_value.strip(),
                }
            )

    return {
        "title": "Резиме на барањето",
        "subtitle": "Подготвено за идно поврзување со календар и реален термин.",
        "service_name": service_name,
        "appointment_display": "21 MAR 2026 \u0432\u043e 14:00",
        "appointment_status": "Привремен термин",
        "appointment_source": "placeholder",
        "fields": summary_fields,
    }


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


# endregion LLM Input Shaping and Internal Intent Markers


# region Contact Collection and Booking Guidance Kept Local
# These helpers still live here because orchestration depends on their exact guidance and gating behavior.

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


def _ownership_clarification_reply(profile: dict, field_name: str) -> str | None:
    field_prompt = _field_prompt(profile, field_name)
    ownership_replies = _profile_text_map(profile, "reply_texts", "contact_ownership_clarification_replies")
    template = ownership_replies.get(field_name) or ownership_replies.get("default")
    if isinstance(template, str) and template.strip():
        return template.strip().format(field_prompt=field_prompt)
    return None


def _contains_lookup_phrase(normalized_message: str, phrase: str) -> bool:
    sanitized_message = re.sub(r"[^\w\s\u0400-\u04FF]+", " ", normalized_message)
    sanitized_message = re.sub(r"\s+", " ", sanitized_message).strip()
    normalized_phrase = _normalize_lookup_text(phrase)
    normalized_phrase = re.sub(r"[^\w\s\u0400-\u04FF]+", " ", normalized_phrase)
    normalized_phrase = re.sub(r"\s+", " ", normalized_phrase).strip()
    if not sanitized_message or not normalized_phrase:
        return False

    return f" {normalized_phrase} " in f" {sanitized_message} "


def _field_clarification_with_resume(profile: dict, field_name: str) -> str:
    clarification_reply = _contact_clarification_reply(profile, field_name)
    field_prompt = _field_prompt(profile, field_name)
    ownership_reply = _ownership_clarification_reply(profile, field_name)

    if ownership_reply:
        return ownership_reply

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


def _is_contact_ownership_style_clarification(message: str, field_name: str | None) -> bool:
    if field_name is None or not _is_field_level_clarification(message, field_name):
        return False

    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return False

    if _has_contact_ownership_clarification(message):
        return True

    return normalized_message.startswith("na ") or normalized_message.startswith("Ð½Ð° ")


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
    missing_digits_verb = "недостига" if missing_digits == 1 else "недостигаат"
    invalid_reply = _field_error_prompt(
        profile,
        "phone",
        missing_digits=missing_digits,
        missing_digits_label=missing_digits_label,
        missing_digits_verb=missing_digits_verb,
    )
    if invalid_reply:
        return invalid_reply
    return _field_prompt(profile, "phone")


def _invalid_email_reply(profile: dict) -> str:
    invalid_reply = _field_error_prompt(profile, "email")
    if invalid_reply:
        return invalid_reply
    return _field_prompt(profile, "email")


def _booking_guidance_fallback(
    *,
    profile: dict,
    field_name: str | None,
    guidance_kind: str,
    user_message: str,
    services: list[dict],
    state: dict | None = None,
    missing_digits: int | None = None,
) -> str:
    if guidance_kind == "field_clarification":
        if _is_field_level_clarification(user_message, field_name):
            return _field_clarification_with_resume(profile, field_name)
        return _contact_collection_redirect_reply(profile, field_name)

    if guidance_kind == "phone_retry":
        return _invalid_phone_reply(profile, user_message)

    if guidance_kind == "catalog_redirect":
        return _contact_collection_redirect_reply(profile, field_name)

    if guidance_kind == "scope_clarification":
        if isinstance(state, dict):
            return _booking_scope_clarification_reply(state, services, profile)
        return _contact_collection_redirect_reply(profile, field_name)

    return _field_prompt(profile, field_name or "name")


def _booking_guidance_reply(
    *,
    api_key: str | None,
    tenant: str,
    session_id: str,
    profile: dict,
    field_name: str | None,
    guidance_kind: str,
    user_message: str,
    services: list[dict],
    state: dict | None = None,
    missing_digits: int | None = None,
) -> str:
    fallback_reply = _booking_guidance_fallback(
        profile=profile,
        field_name=field_name,
        guidance_kind=guidance_kind,
        user_message=user_message,
        services=services,
        state=state,
        missing_digits=missing_digits,
    )

    if not api_key:
        return fallback_reply

    if guidance_kind == "field_clarification" and _is_contact_ownership_style_clarification(user_message, field_name):
        return fallback_reply

    field_prompt = _field_prompt(profile, field_name or "name")
    business_name = profile.get("business", {}).get("name", "Ординацијата")
    guidance_payload = {
        "kind": guidance_kind,
        "field_name": field_name,
        "field_prompt": field_prompt,
        "user_message": user_message,
        "missing_digits": missing_digits,
        "service_id": state.get("service_id") if isinstance(state, dict) else None,
    }
    system_prompt = (
        f"You are writing a short booking-guidance reply for {business_name}. "
        "Always reply in Macedonian Cyrillic. "
        "The backend already knows which contact field is being collected; do not change the field. "
        "Answer the user's clarification or guide the retry naturally in 1-2 sentences. "
        "Keep the tone warm and direct, avoid diagnosis, avoid markdown, and end by guiding the user back to the same field."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "BOOKING_GUIDANCE\n" + json.dumps(guidance_payload, ensure_ascii=False),
                },
            ],
        )
        reply = (response.output_text or "").strip()
        if reply:
            trace_event(
                tenant,
                session_id,
                "BOOKING_GUIDANCE_USED",
                guidance_kind=guidance_kind,
                field_name=field_name,
            )
            return reply
    except (OpenAIError, RateLimitError, json.JSONDecodeError):
        pass

    return fallback_reply


# endregion Contact Collection and Booking Guidance Kept Local


# region Reply Quality and Response Finalization
# Final reply shaping, repetition control, interaction recording, and response tracing.

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
    return booking_credentials.extract_contact_fields_from_message(
        message,
        missing_fields,
        profile,
        is_valid_contact_field_value=_is_valid_contact_field_value,
        normalize_lookup_text=_normalize_lookup_text,
        normalized_name_candidate=_normalized_name_candidate,
        is_plausible_contact_phone=_is_plausible_contact_phone,
    )


def _should_attempt_contact_bundle_parse(
    message: str,
    missing_fields: list[str],
    profile: dict,
) -> bool:
    return booking_credentials.should_attempt_contact_bundle_parse(
        message,
        missing_fields,
        profile,
        is_valid_contact_field_value=_is_valid_contact_field_value,
        normalize_lookup_text=_normalize_lookup_text,
        normalized_name_candidate=_normalized_name_candidate,
        is_plausible_contact_phone=_is_plausible_contact_phone,
    )


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
    widget_payload: dict | None = None,
) -> dict:
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
    log_chat_message(tenant, session_id, "assistant", final_reply)
    _trace_response(tenant, session_id, final_reply, stage_after)
    return {
        "reply": final_reply,
        "widget_payload": widget_payload,
    }


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


# endregion Reply Quality and Response Finalization


# region Booking Capability Adapters
# Thin wrappers that keep orchestration readable while delegating workflow details to booking_credentials.

def _start_collecting_contact(
    tenant: str,
    session_id: str,
    session_key: str,
    service_id: str | None,
    collect_fields: list[str],
    profile: dict,
    scheduling_handoff: dict | None = None,
) -> tuple[str, str]:
    return booking_credentials.start_collecting_contact(
        tenant=tenant,
        session_id=session_id,
        session_key=session_key,
        service_id=service_id,
        collect_fields=collect_fields,
        profile=profile,
        scheduling_handoff=scheduling_handoff,
        save_lead_checkpoint=save_lead_checkpoint,
        render_profile_text=_render_profile_text,
        field_prompt=_field_prompt,
        normalize_lookup_text=_normalize_lookup_text,
        normalized_name_candidate=_normalized_name_candidate,
    )


def _normalize_collecting_contact_state(state: dict, collect_fields: list[str]) -> tuple[dict, list[str], bool]:
    return booking_credentials._normalize_collecting_contact_state(state, collect_fields)


def _has_active_booking_lock(state: dict | None) -> bool:
    return booking_credentials.has_active_booking_lock(state)


def _persisted_fields_match(save_result: dict | None, required_fields: list[str]) -> bool:
    return booking_credentials._persisted_fields_match(save_result, required_fields)


def _recover_from_persistence_failure(
    state: dict,
    collect_fields: list[str],
    save_result: dict | None,
    fallback_field: str | None,
) -> str:
    return booking_credentials._recover_from_persistence_failure(state, collect_fields, save_result, fallback_field)


# endregion Booking Capability Adapters


# region Intent Normalization and Deterministic Routing Shortcuts
# Backend-safe intent collapsing plus rule-based shortcuts that can answer before the main LLM path.

def _is_booking_confirmation(message: str, profile: dict) -> bool:
    return booking_credentials.is_booking_confirmation(
        message,
        profile,
        conversation_rule_list=_conversation_rule_list,
    )


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


def _goal_redirect_reply(message: str, profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not normalized_message:
        return None

    redirect_replies = _profile_text_map(profile, "reply_texts", "goal_redirect_replies")

    for triggers, reply_key in _conversation_rule_patterns(profile, "goal_redirect_reply_patterns"):
        if any(_contains_lookup_phrase(normalized_message, trigger) for trigger in triggers):
            reply = redirect_replies.get(reply_key)
            if isinstance(reply, str) and reply.strip():
                return reply.strip()

    return None


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
        if any(_contains_lookup_phrase(normalized_message, trigger) for trigger in triggers):
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
        if any(_contains_lookup_phrase(normalized_message, trigger) for trigger in triggers):
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


def _is_global_service_intent(message: str, services: list[dict], profile: dict) -> bool:
    return any(
        (
            _is_service_list_request(message, profile),
            _is_price_request(message, profile),
            bool(_service_clarification_reply(message, profile)),
            bool(_service_description_reply(message, services, profile)),
        )
    )


# endregion Intent Normalization and Deterministic Routing Shortcuts


# region Session Status and Progress Projections
# Public helpers used by the chat surface to summarize current session and booking state.

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
    services = profile.get("services", [])
    collect_fields = _profile_list(profile, "actions", "collect_contact_fields")
    if not collect_fields:
        collect_fields = ["name", "phone", "email"]

    state = _load_session_state(tenant, session_id)
    if not isinstance(state, dict):
        return None

    return booking_credentials.get_booking_progress(
        profile,
        services,
        collect_fields,
        state,
        field_prompt=_field_prompt,
        service_by_id=_service_by_id,
        consultation_service=_consultation_service,
        service_display_name=_service_display_name,
    )


# endregion Session Status and Progress Projections


# region Main Orchestration Entry Point
# The request lifecycle coordinator: bootstrap, deterministic gates, model call, and capability routing.

def generate_reply(tenant: str, message: str, session_id: str | None = None) -> tuple[dict, str]:
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
    allow_scheduling_first = actions.get("allow_scheduling_first") is True
    require_credentials_before_confirm = actions.get("require_credentials_before_confirm") is True
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
            "\nCanonical intents: greeting, suggest_service, business_overview, list_services, quote_price, confirm_booking, fallback."
            "\nIf the user confirms booking, return confirm_booking."
            "\nIf the user asks what the clinic does or asks about the business in general, return business_overview."
            "\nIf the user asks what services are available or asks generally what the clinic offers, return list_services."
            "\nIf the user asks for the price of a specific catalog service, return quote_price and set service_id to that service."
            "\nDo not volunteer prices in general descriptive answers."
            f"\nCollect these fields in order: {collect_fields}"
        )
        if allow_scheduling_first:
            system_prompt += (
                f"\nUse {AVAILABILITY_INTENT_OUTPUT} when the user is primarily asking about appointment availability, free slots, or opening-time availability."
                f"\n{AVAILABILITY_INTENT_OUTPUT} is an internal orchestration signal, not a booking confirmation."
            )

    # Task 7C keeps the existing booking safeguard path intact. We only read this normalized
    # coexistence flag here so orchestration can continue to require credentials before any final
    # completion until there is an explicit safe branch to change that behavior.
    _ = require_credentials_before_confirm

    if output_contract:
        system_prompt += (
            "\n\nReturn ONLY a JSON object with this structure:\n"
            + json.dumps(output_contract.get("response_format", {}), ensure_ascii=False, indent=2)
        )

    session_key = _session_key(tenant, session_id)
    state = _load_session_state(tenant, session_id)
    stage_before = _stage_name(state)
    requested_edit_field = booking_credentials.booking_edit_requested_field(message, collect_fields)

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

    log_chat_message(tenant, session_id, "user", message)

    if (
        allow_booking
        and allow_scheduling_first
        and scheduling_capability.scheduling_handoff_ready(state)
        and booking_credentials.is_booking_confirmation(
            message,
            profile,
            conversation_rule_list=_conversation_rule_list,
        )
    ):
        scheduling_handoff = scheduling_capability.scheduling_handoff_payload(state)
        handoff_service_id = (
            scheduling_handoff.get("service_id")
            if isinstance(scheduling_handoff, dict)
            else None
        )
        reply, session_id = _start_collecting_contact(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            service_id=handoff_service_id,
            collect_fields=collect_fields,
            profile=profile,
            scheduling_handoff=scheduling_handoff,
        )
        _trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "collecting_contact",
            reason="scheduling_availability_interest_confirmed",
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

    booking_context = booking_credentials.CapabilityContext(
        tenant=tenant,
        session_id=session_id,
        session_key=session_key,
        message=message,
        state=state,
        stage_before=stage_before,
        allow_booking=allow_booking,
        collect_fields=collect_fields,
        services=services,
        profile=profile,
        api_key=api_key,
        requested_edit_field=requested_edit_field,
    )
    booking_result = booking_credentials.handle_booking_capability(
        booking_context,
        save_lead_checkpoint=save_lead_checkpoint,
        finalize_reply=_finalize_reply,
        trace_stage_transition=_trace_stage_transition,
        log_chat_state=_log_chat_state,
        field_prompt=_field_prompt,
        field_error_prompt=_field_error_prompt,
        render_profile_text=_render_profile_text,
        profile_text=_profile_text,
        booking_guidance_reply=_booking_guidance_reply,
        is_valid_contact_field_value=_is_valid_contact_field_value,
        classify_booking_input=_classify_booking_input,
        booking_input_field_value=BOOKING_INPUT_FIELD_VALUE,
        booking_input_clarification=BOOKING_INPUT_CLARIFICATION,
        is_contact_ownership_style_clarification=_is_contact_ownership_style_clarification,
        is_catalog_reference_during_contact_collection=_is_catalog_reference_during_contact_collection,
        is_conversational_filler_input=_is_conversational_filler_input,
        should_start_consultation_booking=_should_start_consultation_booking,
        normalize_lookup_text=_normalize_lookup_text,
        normalized_name_candidate=_normalized_name_candidate,
        is_plausible_contact_phone=_is_plausible_contact_phone,
        conversation_rule_list=_conversation_rule_list,
        random_choice=random.choice,
    )
    state = booking_result.state
    if booking_result.next_action == booking_credentials.CAPABILITY_NEXT_RETURN:
        return booking_result.final_response

    scheduling_context = scheduling_capability.CapabilityContext(
        tenant=tenant,
        session_id=session_id,
        session_key=session_key,
        message=message,
        state=state,
        profile=profile,
        services=services,
        requested_operation=(
            scheduling_capability.OPERATION_AVAILABILITY
            if allow_scheduling_first and scheduling_capability.has_pending_availability_intent(state)
            else None
        ),
    )
    scheduling_result = scheduling_capability.handle_scheduling_capability(
        scheduling_context,
    )
    state = scheduling_result.state
    if scheduling_result.assessment.operation == scheduling_capability.OPERATION_AVAILABILITY:
        state = scheduling_capability.store_scheduling_state(
            session_key,
            state,
            assessment=scheduling_result.assessment,
            session_state=SESSION_STATE,
        )
        scheduling_reply = scheduling_capability.assessment_reply_text(
            scheduling_result.assessment
        )
        if isinstance(scheduling_reply, str) and scheduling_reply.strip():
            _log_chat_state(
                message=message,
                session_id=session_id,
                intent=AVAILABILITY_INTENT_OUTPUT,
                stage_before=stage_before,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
            )
            final_reply = _finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply=scheduling_reply.strip(),
                response_type=AVAILABILITY_INTENT_OUTPUT,
                services=services,
                profile=profile,
                stage_after=_stage_name(SESSION_STATE.get(session_key)),
                widget_payload=scheduling_capability.assessment_widget_payload(
                    scheduling_result.assessment,
                ),
            )
            return final_reply, session_id
    if scheduling_result.next_action == scheduling_capability.CAPABILITY_NEXT_RETURN:
        return scheduling_result.final_response

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

    goal_redirect_reply = _goal_redirect_reply(message, profile)
    if goal_redirect_reply:
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
            reply=goal_redirect_reply,
            response_type="casual",
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
            availability_intent_requested = _is_availability_intent_output(raw_intent)
            intent = _normalize_intent(raw_intent)
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")
            booking_input_type = _classify_booking_input(message, profile)

            if availability_intent_requested and allow_scheduling_first:
                state = scheduling_capability.mark_availability_intent_pending(
                    session_key,
                    state,
                    SESSION_STATE,
                )
                scheduling_context = scheduling_capability.CapabilityContext(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    state=state,
                    profile=profile,
                    services=services,
                    requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
                    service_id=service_id if isinstance(service_id, str) and service_id.strip() else None,
                    intro_message=message_text,
                )
                scheduling_result = scheduling_capability.handle_scheduling_capability(
                    scheduling_context,
                )
                state = scheduling_capability.store_scheduling_state(
                    session_key,
                    scheduling_result.state,
                    assessment=scheduling_result.assessment,
                    session_state=SESSION_STATE,
                )
                scheduling_reply = scheduling_capability.assessment_reply_text(
                    scheduling_result.assessment
                )
                if isinstance(scheduling_reply, str) and scheduling_reply.strip():
                    _log_chat_state(
                        message=message,
                        session_id=session_id,
                        intent=AVAILABILITY_INTENT_OUTPUT,
                        stage_before=stage_before,
                        stage_after=_stage_name(SESSION_STATE.get(session_key)),
                    )
                    final_reply = _finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=scheduling_reply.strip(),
                        response_type=AVAILABILITY_INTENT_OUTPUT,
                        services=services,
                        profile=profile,
                        stage_after=_stage_name(SESSION_STATE.get(session_key)),
                        widget_payload=scheduling_capability.assessment_widget_payload(
                            scheduling_result.assessment,
                        ),
                    )
                    return final_reply, session_id

            trace_event(
                tenant,
                session_id,
                "INTENT_NORMALIZED",
                raw_intent=raw_intent,
                normalized_intent=intent,
                service_id=service_id,
                availability_intent_requested=availability_intent_requested,
            )

            if intent == "confirm_booking" and allow_booking and not availability_intent_requested:
                reply, session_id = booking_credentials.start_collecting_contact(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    service_id=service_id,
                    collect_fields=collect_fields,
                    profile=profile,
                    scheduling_handoff=None,
                    save_lead_checkpoint=save_lead_checkpoint,
                    render_profile_text=_render_profile_text,
                    field_prompt=_field_prompt,
                    normalize_lookup_text=_normalize_lookup_text,
                    normalized_name_candidate=_normalized_name_candidate,
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

            if intent == "suggest_service" and allow_booking and not availability_intent_requested and service_id and service_id != "unknown":
                bookable_service_ids = {
                    service.get("id")
                    for service in services
                    if service.get("bookable")
                }
                if service_id in bookable_service_ids:
                    booking_credentials.mark_booking_confirmation_pending(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        service_id=service_id,
                        collect_fields=collect_fields,
                        save_lead_checkpoint=save_lead_checkpoint,
                    )
                    _trace_stage_transition(
                        tenant,
                        session_id,
                        stage_before,
                        "awaiting_booking_confirmation",
                        reason="model_suggest_service",
                    )

            if intent == "list_services":
                reply = _service_list_reply(profile, services)
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
                    reply=reply,
                    response_type="service_list",
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

            if intent == "business_overview":
                reply = _business_overview_reply(profile, services)
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
                    reply=reply,
                    response_type="business_overview",
                    services=services,
                    profile=profile,
                    stage_after=_stage_name(SESSION_STATE.get(session_key)),
                )
                return final_reply, session_id

            if intent == "quote_price":
                priced_service = _service_by_id(services, service_id) or _match_service_for_message(message, services)
                price_reply = _orientation_price_text(priced_service, profile) if priced_service else None
                if price_reply:
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
                        reply=price_reply,
                        response_type="explicit_price",
                        services=services,
                        profile=profile,
                        stage_after=_stage_name(SESSION_STATE.get(session_key)),
                    )
                    return final_reply, session_id

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


# endregion Main Orchestration Entry Point
