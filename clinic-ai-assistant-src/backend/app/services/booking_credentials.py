"""Booking-credentials capability for confirmation and contact collection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from app.services.chat_session_state import SESSION_STATE, _recent_interactions


UNKNOWN_NAME_CONFIRM_MODE = "confirm_candidate"
UNKNOWN_NAME_REPEAT_MODE = "repeat_request"


@dataclass
class BookingPreparationResult:
    state: dict | None
    requested_edit_field: str | None
    final_response: tuple[str, str] | None = None


CAPABILITY_NEXT_CONTINUE = "continue"
CAPABILITY_NEXT_RETURN = "return_response"


@dataclass
class CapabilityContext:
    tenant: str
    session_id: str
    session_key: str
    message: str
    state: dict | None
    stage_before: str | None
    allow_booking: bool
    collect_fields: list[str]
    services: list[dict]
    profile: dict
    api_key: str | None
    requested_edit_field: str | None


@dataclass
class CapabilityResult:
    next_action: str
    state: dict | None
    final_response: tuple[str, str] | None = None


ProfileText = Callable[..., str | None]


def _appointment_summary_projection(state: dict) -> tuple[str, str, str | None, str]:
    scheduling_handoff = state.get("scheduling_handoff")
    selected_slot = scheduling_handoff.get("selected_slot") if isinstance(scheduling_handoff, dict) else None
    booking_result = state.get("booking_result") if isinstance(state.get("booking_result"), dict) else None
    appointment_display = ""
    appointment_status = "Привремен термин"
    appointment_source = None
    subtitle = "Подготвено за идно поврзување со календар и реален термин."

    if isinstance(selected_slot, dict):
        raw_display_label = selected_slot.get("display_label")
        if isinstance(raw_display_label, str) and raw_display_label.strip():
            appointment_display = raw_display_label.strip()
        appointment_source = "selected_slot"

    if isinstance(booking_result, dict):
        if booking_result.get("status") == "slot_unavailable":
            appointment_display = ""
            appointment_status = "Терминот не е достапен"
            appointment_source = None
        booked_display_label = booking_result.get("display_label")
        if isinstance(booked_display_label, str) and booked_display_label.strip():
            appointment_display = booked_display_label.strip()
        confirmation_message = booking_result.get("confirmation_message")
        if isinstance(confirmation_message, str) and confirmation_message.strip():
            subtitle = confirmation_message.strip()
        if booking_result.get("status") == "confirmed" or booking_result.get("booking_id"):
            appointment_status = "Потврден термин"
            appointment_source = "calendar_booking"

    return appointment_display, appointment_status, appointment_source, subtitle


def booking_summary_payload(
    profile: dict,
    state: dict,
    collect_fields: list[str],
    data: dict,
    services: list[dict],
    *,
    field_prompt: Callable[[dict, str], str],
    service_by_id: Callable[[list[dict], str | None], dict | None],
    consultation_service: Callable[[list[dict]], dict | None],
    service_display_name: Callable[[dict], str],
) -> dict | None:
    if state.get("stage") != "completed":
        return None

    service_id = state.get("service_id")
    service = service_by_id(services, service_id) or consultation_service(services)
    service_name = service_display_name(service) if isinstance(service, dict) else "Стоматолошка консултација"

    appointment_display, appointment_status, appointment_source, subtitle = _appointment_summary_projection(state)

    summary_fields = []
    for field_name in collect_fields:
        raw_value = data.get(field_name)
        if isinstance(raw_value, str) and raw_value.strip():
            summary_fields.append(
                {
                    "field": field_name,
                    "label": field_prompt(profile, field_name),
                    "value": raw_value.strip(),
                }
            )

    return {
        "title": "Резиме на барањето",
        "subtitle": subtitle,
        "service_name": service_name,
        "appointment_display": appointment_display,
        "appointment_status": appointment_status,
        "appointment_source": appointment_source,
        "fields": summary_fields,
    }


def scheduling_fallback_state_from_booking_result(
    state: dict,
    booking_result: dict | None,
) -> dict | None:
    if not isinstance(state, dict) or not isinstance(booking_result, dict):
        return None

    if booking_result.get("status") != "slot_unavailable":
        return None

    source_payload = booking_result.get("source_payload")
    if not isinstance(source_payload, dict):
        return None

    replacement_slots = source_payload.get("replacement_slots")
    if not isinstance(replacement_slots, list) or not replacement_slots:
        return None

    service_id = source_payload.get("service_id") or state.get("service_id")
    if not isinstance(service_id, str) or not service_id.strip():
        return None

    selected_slot = source_payload.get("selected_slot")
    fallback_date = source_payload.get("fallback_date")
    timezone_name = (
        selected_slot.get("timezone")
        if isinstance(selected_slot, dict) and isinstance(selected_slot.get("timezone"), str)
        else None
    )

    return {
        "operation": "availability_lookup",
        "status": "completed",
        "reason": "slot_conflict_same_day_fallback",
        "capability_state": {
            "capability": "scheduling",
            "operation": "availability_lookup",
            "status": "completed",
            "service_id": service_id.strip(),
            "slot_id": source_payload.get("slot_id"),
            "timezone": timezone_name,
            "missing_inputs": [],
        },
        "output_payload": {
            "capability": "scheduling",
            "operation": "availability_lookup",
            "provider": booking_result.get("provider"),
            "request": {
                "service_id": service_id.strip(),
                "date_from": fallback_date,
                "date_to": fallback_date,
                "timezone": timezone_name,
                "preferred_days": [],
                "preferred_time_range": None,
            },
            "result": {
                "provider": booking_result.get("provider"),
                "slots": [slot for slot in replacement_slots if isinstance(slot, dict)],
            },
            "reply_text": booking_result.get("confirmation_message"),
        },
        "booking_handoff_ready": True,
    }


def _complete_selected_slot_booking_if_ready(
    *,
    tenant: str,
    state: dict,
    data: dict,
) -> dict | None:
    scheduling_handoff = state.get("scheduling_handoff")
    if not isinstance(scheduling_handoff, dict):
        return None

    selected_slot = scheduling_handoff.get("selected_slot")
    if not isinstance(selected_slot, dict):
        return None

    existing_booking_result = state.get("booking_result")
    if isinstance(existing_booking_result, dict) and existing_booking_result.get("booking_id"):
        return existing_booking_result

    service_id = state.get("service_id") or scheduling_handoff.get("service_id")
    slot_id = selected_slot.get("slot_id")
    patient_name = data.get("name")
    if not isinstance(service_id, str) or not service_id.strip():
        return None
    if not isinstance(slot_id, str) or not slot_id.strip():
        return None
    if not isinstance(patient_name, str) or not patient_name.strip():
        return None

    from app.services import scheduling_capability
    from app.services.scheduling.service import SchedulingConfigError

    hold = scheduling_handoff.get("hold")
    try:
        booking_result = scheduling_capability.book_selected_slot(
            tenant=tenant,
            service_id=service_id.strip(),
            slot_id=slot_id.strip(),
            patient_name=patient_name.strip(),
            patient_phone=data.get("phone"),
            patient_email=data.get("email"),
            note="Booked from main chat scheduling flow",
            session_id=hold.get("session_id") if isinstance(hold, dict) else None,
            hold_id=hold.get("hold_id") if isinstance(hold, dict) else None,
            selected_slot=selected_slot,
        )
    except scheduling_capability.SchedulingSlotConflictError as exc:
        booking_payload = exc.to_booking_result_payload(slot_id=slot_id.strip())
        state["booking_result"] = booking_payload
        return booking_payload
    except SchedulingConfigError as exc:
        booking_payload = {
            "status": "slot_unavailable",
            "provider": "scheduling",
            "booking_id": "",
            "start_at": selected_slot.get("start_at"),
            "end_at": selected_slot.get("end_at"),
            "display_label": selected_slot.get("display_label", ""),
            "confirmation_message": str(exc),
            "source_payload": {
                "slot_id": slot_id.strip(),
                "reason": "slot_conflict",
            },
        }
        state["booking_result"] = booking_payload
        return booking_payload
    booking_payload = booking_result.to_dict()
    state["booking_result"] = booking_payload
    return booking_payload


def get_booking_progress(
    profile: dict,
    services: list[dict],
    collect_fields: list[str],
    state: dict | None,
    *,
    field_prompt: Callable[[dict, str], str],
    service_by_id: Callable[[list[dict], str | None], dict | None],
    consultation_service: Callable[[list[dict]], dict | None],
    service_display_name: Callable[[dict], str],
) -> dict | None:
    if not isinstance(state, dict):
        return None

    stage = state.get("stage")
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
                "label": field_prompt(profile, field_name),
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

    summary = booking_summary_payload(
        profile,
        state,
        collect_fields,
        data,
        services,
        field_prompt=field_prompt,
        service_by_id=service_by_id,
        consultation_service=consultation_service,
        service_display_name=service_display_name,
    )

    return {
        "visible": True,
        "booking_stage": stage,
        "collection_status": completed_count,
        "collection_total": len(collect_fields),
        "progress_percent": progress_percent,
        "reservation_status": "complete" if stage == "completed" else "pending",
        "next_field": state.get("next_field"),
        "fields": field_progress,
        "summary": summary,
    }


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


def has_active_booking_lock(state: dict | None) -> bool:
    return isinstance(state, dict) and state.get("stage") == "collecting_contact"


def _persisted_fields_match(save_result: dict | None, required_fields: list[str]) -> bool:
    if not isinstance(save_result, dict) or not save_result.get("success"):
        return False

    persisted_data = save_result.get("persisted_data")
    if not isinstance(persisted_data, dict):
        return False

    normalized_required_fields = [field_name for field_name in required_fields if field_name in {"name", "phone", "email"}]
    return all(
        isinstance(persisted_data.get(field_name), str) and persisted_data.get(field_name).strip()
        for field_name in normalized_required_fields
    )


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


def is_booking_confirmation(message: str, profile: dict, *, conversation_rule_list: Callable[[dict, str], list[str]]) -> bool:
    return message.strip().casefold() in {
        word.casefold()
        for word in conversation_rule_list(profile, "booking_confirm_words")
    }


def is_booking_rejection(message: str, *, normalize_lookup_text: Callable[[str], str]) -> bool:
    normalized_message = normalize_lookup_text(message)
    if not normalized_message:
        return False

    first_token = normalized_message.split(" ", 1)[0]
    return first_token in {"ne", "не", "no", "нет"}


def booking_edit_requested_field(message: str, allowed_fields: list[str]) -> str | None:
    normalized_message = message.strip()
    prefix = "__booking_edit__:"
    if not normalized_message.startswith(prefix):
        return None

    requested_field = normalized_message[len(prefix):].strip()
    return requested_field if requested_field in allowed_fields else None


def _clear_edit_state(state: dict) -> None:
    for key in ("edit_phase", "edit_field", "edit_return_stage", "edit_return_next_field"):
        state.pop(key, None)


def _extract_explicit_contact_name(
    message: str,
    *,
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
) -> str | None:
    normalized_message = normalize_lookup_text(message)
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
            return normalized_name_candidate(match.group(1))
    return None


def _recent_contact_name_hint(
    session_key: str,
    *,
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
) -> str | None:
    for item in reversed(_recent_interactions(session_key)):
        message = item.get("message")
        if not isinstance(message, str) or not message.strip():
            continue
        candidate_name = _extract_explicit_contact_name(
            message,
            normalize_lookup_text=normalize_lookup_text,
            normalized_name_candidate=normalized_name_candidate,
        )
        if candidate_name:
            return candidate_name
    return None


def _booking_start_reply(
    profile: dict,
    known_name: str | None,
    *,
    render_profile_text: Callable[..., str | None],
    field_prompt: Callable[[dict, str], str],
) -> str:
    if known_name:
        known_name_reply = render_profile_text(
            profile,
            ("reply_texts", "booking_known_name_confirmation"),
            known_name=known_name,
        )
        if known_name_reply:
            return known_name_reply
    return field_prompt(profile, "name")


def _normalize_freeform_name_value(value: str) -> str:
    cleaned_value = re.sub(r"\s+", " ", value.strip())
    return cleaned_value.strip("\"'„“")


def _clear_unknown_name_state(state: dict) -> None:
    for key in ("unknown_name_mode", "unknown_name_candidate"):
        state.pop(key, None)


def _should_offer_unknown_name_recovery(
    message: str,
    profile: dict,
    *,
    classify_booking_input: Callable[[str, dict], str],
    booking_input_field_value: str,
    is_conversational_filler_input: Callable[[str, dict], bool],
) -> bool:
    trimmed_message = message.strip()
    if not trimmed_message:
        return False

    if classify_booking_input(message, profile) != booking_input_field_value:
        return False

    if is_conversational_filler_input(message, profile):
        return False

    if any(char.isdigit() for char in trimmed_message):
        return False

    token_count = len(re.findall(r"\S+", trimmed_message))
    return token_count <= 4 and len(trimmed_message) <= 60


def _unknown_name_confirmation_reply(profile: dict, candidate: str, *, profile_text: ProfileText) -> str:
    template = profile_text(profile, "reply_texts", "unknown_name_confirmation")
    if template:
        return template.format(candidate_name=candidate)
    return f'Дали „{candidate}“ е вашето име?'


def _unknown_name_retry_reply(profile: dict, *, profile_text: ProfileText) -> str:
    template = profile_text(profile, "reply_texts", "unknown_name_retry")
    if template:
        return template
    return "Ве молам дали може повторно да го внесете вашето име."


def _start_unknown_name_recovery(
    state: dict,
    message: str,
    profile: dict,
    *,
    profile_text: ProfileText,
    random_choice: Callable[[tuple[str, str]], str],
) -> str:
    candidate = _normalize_freeform_name_value(message)
    recovery_mode = random_choice((UNKNOWN_NAME_CONFIRM_MODE, UNKNOWN_NAME_REPEAT_MODE))
    state["unknown_name_mode"] = recovery_mode

    if recovery_mode == UNKNOWN_NAME_CONFIRM_MODE:
        state["unknown_name_candidate"] = candidate
        return _unknown_name_confirmation_reply(profile, candidate, profile_text=profile_text)

    state.pop("unknown_name_candidate", None)
    return _unknown_name_retry_reply(profile, profile_text=profile_text)


def _invalid_phone_reply(
    profile: dict,
    message: str,
    *,
    field_error_prompt: Callable[..., str | None],
    field_prompt: Callable[[dict, str], str],
) -> str:
    digits_only = re.sub(r"\D+", "", message)
    missing_digits = max(0, 9 - len(digits_only))
    missing_digits_label = "цифра" if missing_digits == 1 else "цифри"
    missing_digits_verb = "недостига" if missing_digits == 1 else "недостигаат"
    invalid_reply = field_error_prompt(
        profile,
        "phone",
        missing_digits=missing_digits,
        missing_digits_label=missing_digits_label,
        missing_digits_verb=missing_digits_verb,
    )
    if invalid_reply:
        return invalid_reply
    return field_prompt(profile, "phone")


def _invalid_email_reply(
    profile: dict,
    *,
    field_error_prompt: Callable[..., str | None],
    field_prompt: Callable[[dict, str], str],
) -> str:
    invalid_reply = field_error_prompt(profile, "email")
    if invalid_reply:
        return invalid_reply
    return field_prompt(profile, "email")


def _extract_name_from_contact_bundle(
    message: str,
    *,
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
) -> str | None:
    normalized_message = normalize_lookup_text(message)
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
    return normalized_name_candidate(" ".join(candidate_tokens))


def extract_contact_fields_from_message(
    message: str,
    missing_fields: list[str],
    profile: dict,
    *,
    is_valid_contact_field_value: Callable[[str | None, str, dict], bool],
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
    is_plausible_contact_phone: Callable[[str], bool],
) -> dict[str, str]:
    extracted: dict[str, str] = {}
    remaining_text = message.strip()

    if "email" in missing_fields:
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", remaining_text)
        if email_match:
            candidate_email = email_match.group(0).strip()
            if is_valid_contact_field_value("email", candidate_email, profile):
                extracted["email"] = candidate_email
                remaining_text = remaining_text.replace(candidate_email, " ")

    if "phone" in missing_fields:
        phone_match = re.search(r"\+?\d[\d\s()./-]{6,}\d", remaining_text)
        if phone_match:
            raw_phone = phone_match.group(0).strip()
            candidate_phone = re.sub(r"\D+", "", raw_phone)
            if is_plausible_contact_phone(candidate_phone):
                extracted["phone"] = candidate_phone
                remaining_text = remaining_text.replace(raw_phone, " ", 1)

    if "name" in missing_fields:
        candidate_name = _extract_name_from_contact_bundle(
            remaining_text,
            normalize_lookup_text=normalize_lookup_text,
            normalized_name_candidate=normalized_name_candidate,
        )
        if candidate_name and is_valid_contact_field_value("name", candidate_name, profile):
            extracted["name"] = candidate_name

    return extracted


def should_attempt_contact_bundle_parse(
    message: str,
    missing_fields: list[str],
    profile: dict,
    *,
    is_valid_contact_field_value: Callable[[str | None, str, dict], bool],
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
    is_plausible_contact_phone: Callable[[str], bool],
) -> bool:
    if len(missing_fields) < 2:
        return False

    extracted = extract_contact_fields_from_message(
        message,
        missing_fields,
        profile,
        is_valid_contact_field_value=is_valid_contact_field_value,
        normalize_lookup_text=normalize_lookup_text,
        normalized_name_candidate=normalized_name_candidate,
        is_plausible_contact_phone=is_plausible_contact_phone,
    )
    if len(extracted) < 2:
        return False

    normalized_message = normalize_lookup_text(message)
    has_labeled_contact_hint = any(
        token in normalized_message
        for token in ("telefon", "tel", "broj", "kontakt", "email", "mail", "ime", "phone", "number")
    )

    explicit_email = "email" in extracted
    explicit_phone = "phone" in extracted

    return has_labeled_contact_hint or (explicit_email and explicit_phone)


def start_collecting_contact(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    service_id: str | None,
    collect_fields: list[str],
    profile: dict,
    scheduling_handoff: dict | None,
    save_lead_checkpoint: Callable[..., Any],
    render_profile_text: Callable[..., str | None],
    field_prompt: Callable[[dict, str], str],
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
) -> tuple[str, str]:
    known_name = _recent_contact_name_hint(
        session_key,
        normalize_lookup_text=normalize_lookup_text,
        normalized_name_candidate=normalized_name_candidate,
    )
    next_field = collect_fields[0]

    SESSION_STATE[session_key] = {
        "stage": "collecting_contact",
        "service_id": service_id,
        "next_field": next_field,
        "data": {},
    }
    if isinstance(scheduling_handoff, dict) and scheduling_handoff:
        SESSION_STATE[session_key]["scheduling_handoff"] = scheduling_handoff
    if known_name and "name" in collect_fields:
        SESSION_STATE[session_key]["pending_name_confirmation"] = known_name
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key], required_fields=[])
    return _booking_start_reply(
        profile,
        known_name,
        render_profile_text=render_profile_text,
        field_prompt=field_prompt,
    ), session_id


def mark_booking_confirmation_pending(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    service_id: str | None,
    collect_fields: list[str],
    save_lead_checkpoint: Callable[..., Any],
) -> None:
    SESSION_STATE[session_key] = {
        "stage": "awaiting_booking_confirmation",
        "service_id": service_id,
    }
    save_lead_checkpoint(tenant, session_id, SESSION_STATE[session_key], required_fields=collect_fields)


def prepare_booking_state(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    message: str,
    state: dict | None,
    collect_fields: list[str],
    requested_edit_field: str | None,
    services: list[dict],
    profile: dict,
    save_lead_checkpoint: Callable[..., Any],
    finalize_reply: Callable[..., str],
    log_chat_state: Callable[..., None],
) -> BookingPreparationResult:
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
            stage = state.get("stage")
            state["edit_phase"] = "confirm"
            state["edit_field"] = requested_edit_field
            state["edit_return_stage"] = state.get("stage")
            state["edit_return_next_field"] = state.get("next_field")
            save_lead_checkpoint(tenant, session_id, state, required_fields=[])
            log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage,
                stage_after=stage,
            )
            final_reply = finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply="Дали сакате да направите промена на записот?",
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=stage,
            )
            return BookingPreparationResult(
                state=state,
                requested_edit_field=requested_edit_field,
                final_response=(final_reply, session_id),
            )

    return BookingPreparationResult(state=state, requested_edit_field=requested_edit_field)


def maybe_handle_booking_turn(
    *,
    tenant: str,
    session_id: str,
    session_key: str,
    message: str,
    state: dict | None,
    stage_before: str | None,
    allow_booking: bool,
    collect_fields: list[str],
    services: list[dict],
    profile: dict,
    api_key: str | None,
    save_lead_checkpoint: Callable[..., Any],
    finalize_reply: Callable[..., str],
    trace_stage_transition: Callable[..., None],
    log_chat_state: Callable[..., None],
    field_prompt: Callable[[dict, str], str],
    field_error_prompt: Callable[..., str | None],
    render_profile_text: Callable[..., str | None],
    profile_text: ProfileText,
    booking_guidance_reply: Callable[..., str],
    is_valid_contact_field_value: Callable[[str | None, str, dict], bool],
    classify_booking_input: Callable[[str, dict], str],
    booking_input_field_value: str,
    booking_input_clarification: str,
    is_contact_ownership_style_clarification: Callable[[str, str | None], bool],
    is_catalog_reference_during_contact_collection: Callable[[str, list[dict], dict], bool],
    is_conversational_filler_input: Callable[[str, dict], bool],
    should_start_consultation_booking: Callable[[str, str, list[dict], dict], bool],
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
    is_plausible_contact_phone: Callable[[str], bool],
    conversation_rule_list: Callable[[dict, str], list[str]],
    random_choice: Callable[[tuple[str, str]], str],
    redirect_contact_message_to_availability: Callable[[str, dict | None, str], dict | None],
) -> tuple[str, str] | None:
    if state and state.get("stage") in {"collecting_contact", "completed"}:
        edit_phase = state.get("edit_phase")
        edit_field = state.get("edit_field")

        if edit_phase == "confirm" and edit_field in collect_fields:
            if is_booking_confirmation(message, profile, conversation_rule_list=conversation_rule_list):
                state["edit_phase"] = "value"
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                final_reply = finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply="Внесете ја промената",
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id
            if is_booking_rejection(message, normalize_lookup_text=normalize_lookup_text):
                _clear_edit_state(state)
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                final_reply = finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply="Во ред, записот останува ист.",
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id
            final_reply = finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply="Дали сакате да направите промена на записот?",
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=state.get("stage"),
            )
            return final_reply, session_id

        if edit_phase == "value" and edit_field in collect_fields:
            if not is_valid_contact_field_value(edit_field, message, profile):
                if (
                    edit_field == "phone"
                    and re.sub(r"\D+", "", message)
                    and not state.get("phone_length_guided")
                ):
                    state["phone_length_guided"] = True
                    reply = _invalid_phone_reply(
                        profile,
                        message,
                        field_error_prompt=field_error_prompt,
                        field_prompt=field_prompt,
                    )
                elif edit_field == "email" and "@" in message:
                    reply = _invalid_email_reply(
                        profile,
                        field_error_prompt=field_error_prompt,
                        field_prompt=field_prompt,
                    )
                else:
                    reply = "Внесете ја промената"
                final_reply = finalize_reply(
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
                final_reply = finalize_reply(
                    tenant=tenant,
                    session_id=session_id,
                    session_key=session_key,
                    message=message,
                    reply="Внесете ја промената",
                    response_type="collect_contact",
                    services=services,
                    profile=profile,
                    stage_after=state.get("stage"),
                )
                return final_reply, session_id

            final_reply = finalize_reply(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                message=message,
                reply="Промената е зачувана.",
                response_type="collect_contact",
                services=services,
                profile=profile,
                stage_after=state.get("stage"),
            )
            return final_reply, session_id

    if state and state.get("stage") == "awaiting_booking_confirmation" and allow_booking:
        contact_payload_detected = any(
            (
                should_attempt_contact_bundle_parse(
                    message,
                    collect_fields,
                    profile,
                    is_valid_contact_field_value=is_valid_contact_field_value,
                    normalize_lookup_text=normalize_lookup_text,
                    normalized_name_candidate=normalized_name_candidate,
                    is_plausible_contact_phone=is_plausible_contact_phone,
                ),
                is_valid_contact_field_value("name", message, profile),
                is_valid_contact_field_value("phone", message, profile),
                is_valid_contact_field_value("email", message, profile),
            )
        )
        if is_booking_confirmation(message, profile, conversation_rule_list=conversation_rule_list) or contact_payload_detected:
            reply, session_id = start_collecting_contact(
                tenant=tenant,
                session_id=session_id,
                session_key=session_key,
                service_id=state.get("service_id"),
                collect_fields=collect_fields,
                profile=profile,
                scheduling_handoff=state.get("scheduling_handoff") if isinstance(state, dict) else None,
                save_lead_checkpoint=save_lead_checkpoint,
                render_profile_text=render_profile_text,
                field_prompt=field_prompt,
                normalize_lookup_text=normalize_lookup_text,
                normalized_name_candidate=normalized_name_candidate,
            )
            trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason="backend_confirmation_word" if is_booking_confirmation(message, profile, conversation_rule_list=conversation_rule_list) else "backend_contact_payload_start",
            )
            log_chat_state(
                message=message,
                session_id=session_id,
                intent="confirm_booking",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            if not contact_payload_detected:
                final_reply = finalize_reply(
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

    if has_active_booking_lock(state):
        next_field = state.get("next_field")
        missing_fields = [field for field in collect_fields if field not in state.get("data", {})]
        pending_name_confirmation = state.get("pending_name_confirmation")
        force_accept_name = False

        redirected_state = redirect_contact_message_to_availability(message, state, session_key)
        if isinstance(redirected_state, dict):
            state.clear()
            state.update(redirected_state)
            return None

        if next_field == "name" and isinstance(pending_name_confirmation, str) and pending_name_confirmation.strip():
            explicit_name = _extract_explicit_contact_name(
                message,
                normalize_lookup_text=normalize_lookup_text,
                normalized_name_candidate=normalized_name_candidate,
            )
            if explicit_name:
                state.pop("pending_name_confirmation", None)
                message = explicit_name
            elif is_booking_confirmation(message, profile, conversation_rule_list=conversation_rule_list):
                state.pop("pending_name_confirmation", None)
                message = pending_name_confirmation
            elif is_booking_rejection(message, normalize_lookup_text=normalize_lookup_text):
                state.pop("pending_name_confirmation", None)
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                reply = field_prompt(profile, "name")
                final_reply = finalize_reply(
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
                if is_booking_confirmation(message, profile, conversation_rule_list=conversation_rule_list):
                    message = unknown_name_candidate
                    force_accept_name = True
                    _clear_unknown_name_state(state)
                elif is_booking_rejection(message, normalize_lookup_text=normalize_lookup_text):
                    state["unknown_name_mode"] = UNKNOWN_NAME_REPEAT_MODE
                    state.pop("unknown_name_candidate", None)
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_retry_reply(profile, profile_text=profile_text),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id
                else:
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_confirmation_reply(profile, unknown_name_candidate, profile_text=profile_text),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id

            elif unknown_name_mode == UNKNOWN_NAME_REPEAT_MODE:
                if classify_booking_input(message, profile) != booking_input_field_value or is_conversational_filler_input(message, profile):
                    save_lead_checkpoint(tenant, session_id, state, required_fields=[])
                    final_reply = finalize_reply(
                        tenant=tenant,
                        session_id=session_id,
                        session_key=session_key,
                        message=message,
                        reply=_unknown_name_retry_reply(profile, profile_text=profile_text),
                        response_type="collect_contact",
                        services=services,
                        profile=profile,
                        stage_after="collecting_contact",
                    )
                    return final_reply, session_id

                message = _normalize_freeform_name_value(message)
                force_accept_name = bool(message)
                _clear_unknown_name_state(state)

        booking_input_type = classify_booking_input(message, profile)
        if (
            booking_input_type != booking_input_clarification
            and is_contact_ownership_style_clarification(message, next_field)
            and not is_valid_contact_field_value(next_field, message, profile)
        ):
            booking_input_type = booking_input_clarification

        if booking_input_type == booking_input_clarification:
            reply = booking_guidance_reply(
                api_key=api_key,
                tenant=tenant,
                session_id=session_id,
                profile=profile,
                field_name=next_field,
                guidance_kind="field_clarification",
                user_message=message,
                services=services,
                state=state,
            )
            final_reply = finalize_reply(
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

        if next_field == "name" and is_catalog_reference_during_contact_collection(message, services, profile):
            reply = booking_guidance_reply(
                api_key=api_key,
                tenant=tenant,
                session_id=session_id,
                profile=profile,
                field_name=next_field,
                guidance_kind="catalog_redirect",
                user_message=message,
                services=services,
                state=state,
            )
            final_reply = finalize_reply(
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
        if should_attempt_contact_bundle_parse(
            message,
            missing_fields,
            profile,
            is_valid_contact_field_value=is_valid_contact_field_value,
            normalize_lookup_text=normalize_lookup_text,
            normalized_name_candidate=normalized_name_candidate,
            is_plausible_contact_phone=is_plausible_contact_phone,
        ):
            extracted_fields = extract_contact_fields_from_message(
                message,
                missing_fields,
                profile,
                is_valid_contact_field_value=is_valid_contact_field_value,
                normalize_lookup_text=normalize_lookup_text,
                normalized_name_candidate=normalized_name_candidate,
                is_plausible_contact_phone=is_plausible_contact_phone,
            )
        if extracted_fields:
            state["data"].update(extracted_fields)

            updated_missing_fields = [field for field in collect_fields if field not in state["data"]]
            if next_field in extracted_fields and not updated_missing_fields:
                state["stage"] = "completed"
                save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
                if not _persisted_fields_match(save_result, collect_fields):
                    retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                    SESSION_STATE[session_key] = state
                    trace_stage_transition(
                        tenant,
                        session_id,
                        stage_before,
                        "collecting_contact",
                        reason=f"persistence_retry_after_{next_field}_with_multi_field_parse",
                    )
                    log_chat_state(
                        message=message,
                        session_id=session_id,
                        intent="collect_contact",
                        stage_before=stage_before,
                        stage_after="collecting_contact",
                    )
                    reply = field_prompt(profile, retry_field)
                    final_reply = finalize_reply(
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
                trace_stage_transition(
                    tenant,
                    session_id,
                    stage_before,
                    "completed",
                    reason=f"collected_{next_field}_with_multi_field_parse",
                )
                log_chat_state(
                    message=message,
                    session_id=session_id,
                    intent="collect_contact",
                    stage_before=stage_before,
                    stage_after="completed",
                )
                reply = profile_text(profile, "reply_texts", "booking_completed")
                final_reply = finalize_reply(
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
                    reply = field_prompt(profile, retry_field)
                    final_reply = finalize_reply(
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
                reply = field_prompt(profile, next_field)
                final_reply = finalize_reply(
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
                reply = field_prompt(profile, retry_field)
                final_reply = finalize_reply(
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
            trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"multi_field_parse_after_{next_field}",
            )
            log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = field_prompt(profile, updated_missing_fields[0])
            final_reply = finalize_reply(
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

        if next_field == "name" and not force_accept_name and not is_valid_contact_field_value(next_field, message, profile):
            if _should_offer_unknown_name_recovery(
                message,
                profile,
                classify_booking_input=classify_booking_input,
                booking_input_field_value=booking_input_field_value,
                is_conversational_filler_input=is_conversational_filler_input,
            ):
                reply = _start_unknown_name_recovery(
                    state,
                    message,
                    profile,
                    profile_text=profile_text,
                    random_choice=random_choice,
                )
                save_lead_checkpoint(tenant, session_id, state, required_fields=[])
            else:
                reply = field_prompt(profile, next_field)
            final_reply = finalize_reply(
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

        if not force_accept_name and not is_valid_contact_field_value(next_field, message, profile):
            if next_field == "phone" and re.sub(r"\D+", "", message):
                reply = booking_guidance_reply(
                    api_key=api_key,
                    tenant=tenant,
                    session_id=session_id,
                    profile=profile,
                    field_name=next_field,
                    guidance_kind="phone_retry",
                    user_message=message,
                    services=services,
                    state=state,
                    missing_digits=max(0, 9 - len(re.sub(r"\D+", "", message))),
                )
            elif next_field == "email" and "@" in message:
                reply = _invalid_email_reply(
                    profile,
                    field_error_prompt=field_error_prompt,
                    field_prompt=field_prompt,
                )
            else:
                reply = field_prompt(profile, next_field)
            final_reply = finalize_reply(
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
        if next_field == "name":
            state.pop("pending_name_confirmation", None)

        remaining = [field for field in collect_fields if field not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            save_result = save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
            if not _persisted_fields_match(save_result, [next_field]):
                retry_field = _recover_from_persistence_failure(state, collect_fields, save_result, next_field)
                SESSION_STATE[session_key] = state
                reply = field_prompt(profile, retry_field)
                final_reply = finalize_reply(
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
            trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"collected_{next_field}",
            )
            log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = field_prompt(profile, remaining[0])
            final_reply = finalize_reply(
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
            trace_stage_transition(
                tenant,
                session_id,
                stage_before,
                "collecting_contact",
                reason=f"persistence_retry_after_{next_field}",
            )
            log_chat_state(
                message=message,
                session_id=session_id,
                intent="collect_contact",
                stage_before=stage_before,
                stage_after="collecting_contact",
            )
            reply = field_prompt(profile, retry_field)
            final_reply = finalize_reply(
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
        booking_result = _complete_selected_slot_booking_if_ready(
            tenant=tenant,
            state=state,
            data=state["data"],
        )
        if booking_result:
            save_lead_checkpoint(tenant, session_id, state, required_fields=collect_fields)
        fallback_scheduling_state = scheduling_fallback_state_from_booking_result(state, booking_result)
        if isinstance(fallback_scheduling_state, dict):
            state["scheduling"] = fallback_scheduling_state
            SESSION_STATE[session_key] = state
        else:
            SESSION_STATE.pop(session_key, None)
        trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "completed",
            reason=f"collected_{next_field}",
        )
        log_chat_state(
            message=message,
            session_id=session_id,
            intent="collect_contact",
            stage_before=stage_before,
            stage_after="completed",
        )
        reply = profile_text(profile, "reply_texts", "booking_completed")
        if isinstance(booking_result, dict):
            confirmation_message = booking_result.get("confirmation_message")
            if isinstance(confirmation_message, str) and confirmation_message.strip():
                reply = confirmation_message.strip()
        final_reply = finalize_reply(
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

    if not state and allow_booking and should_start_consultation_booking(message, session_key, services, profile):
        mark_booking_confirmation_pending(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            service_id="consultation",
            collect_fields=collect_fields,
            save_lead_checkpoint=save_lead_checkpoint,
        )
        trace_stage_transition(
            tenant,
            session_id,
            stage_before,
            "awaiting_booking_confirmation",
            reason="predicted_consultation_confirmation",
        )
        reply, session_id = start_collecting_contact(
            tenant=tenant,
            session_id=session_id,
            session_key=session_key,
            service_id="consultation",
            collect_fields=collect_fields,
            profile=profile,
            scheduling_handoff=None,
            save_lead_checkpoint=save_lead_checkpoint,
            render_profile_text=render_profile_text,
            field_prompt=field_prompt,
            normalize_lookup_text=normalize_lookup_text,
            normalized_name_candidate=normalized_name_candidate,
        )
        trace_stage_transition(
            tenant,
            session_id,
            "awaiting_booking_confirmation",
            "collecting_contact",
            reason="predicted_consultation_confirmation",
        )
        log_chat_state(
            message=message,
            session_id=session_id,
            intent="confirm_booking",
            stage_before=stage_before,
            stage_after="collecting_contact",
        )
        final_reply = finalize_reply(
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

    return None


def handle_booking_capability(
    context: CapabilityContext,
    *,
    save_lead_checkpoint: Callable[..., Any],
    finalize_reply: Callable[..., str],
    trace_stage_transition: Callable[..., None],
    log_chat_state: Callable[..., None],
    field_prompt: Callable[[dict, str], str],
    field_error_prompt: Callable[..., str | None],
    render_profile_text: Callable[..., str | None],
    profile_text: ProfileText,
    booking_guidance_reply: Callable[..., str],
    is_valid_contact_field_value: Callable[[str | None, str, dict], bool],
    classify_booking_input: Callable[[str, dict], str],
    booking_input_field_value: str,
    booking_input_clarification: str,
    is_contact_ownership_style_clarification: Callable[[str, str | None], bool],
    is_catalog_reference_during_contact_collection: Callable[[str, list[dict], dict], bool],
    is_conversational_filler_input: Callable[[str, dict], bool],
    should_start_consultation_booking: Callable[[str, str, list[dict], dict], bool],
    normalize_lookup_text: Callable[[str], str],
    normalized_name_candidate: Callable[[str], str | None],
    is_plausible_contact_phone: Callable[[str], bool],
    conversation_rule_list: Callable[[dict, str], list[str]],
    random_choice: Callable[[tuple[str, str]], str],
    redirect_contact_message_to_availability: Callable[[str, dict | None, str], dict | None],
) -> CapabilityResult:
    preparation = prepare_booking_state(
        tenant=context.tenant,
        session_id=context.session_id,
        session_key=context.session_key,
        message=context.message,
        state=context.state,
        collect_fields=context.collect_fields,
        requested_edit_field=context.requested_edit_field,
        services=context.services,
        profile=context.profile,
        save_lead_checkpoint=save_lead_checkpoint,
        finalize_reply=finalize_reply,
        log_chat_state=log_chat_state,
    )
    state = preparation.state
    if preparation.final_response:
        return CapabilityResult(
            next_action=CAPABILITY_NEXT_RETURN,
            state=state,
            final_response=preparation.final_response,
        )

    response = maybe_handle_booking_turn(
        tenant=context.tenant,
        session_id=context.session_id,
        session_key=context.session_key,
        message=context.message,
        state=state,
        stage_before=context.stage_before,
        allow_booking=context.allow_booking,
        collect_fields=context.collect_fields,
        services=context.services,
        profile=context.profile,
        api_key=context.api_key,
        save_lead_checkpoint=save_lead_checkpoint,
        finalize_reply=finalize_reply,
        trace_stage_transition=trace_stage_transition,
        log_chat_state=log_chat_state,
        field_prompt=field_prompt,
        field_error_prompt=field_error_prompt,
        render_profile_text=render_profile_text,
        profile_text=profile_text,
        booking_guidance_reply=booking_guidance_reply,
        is_valid_contact_field_value=is_valid_contact_field_value,
        classify_booking_input=classify_booking_input,
        booking_input_field_value=booking_input_field_value,
        booking_input_clarification=booking_input_clarification,
        is_contact_ownership_style_clarification=is_contact_ownership_style_clarification,
        is_catalog_reference_during_contact_collection=is_catalog_reference_during_contact_collection,
        is_conversational_filler_input=is_conversational_filler_input,
        should_start_consultation_booking=should_start_consultation_booking,
        normalize_lookup_text=normalize_lookup_text,
        normalized_name_candidate=normalized_name_candidate,
        is_plausible_contact_phone=is_plausible_contact_phone,
        conversation_rule_list=conversation_rule_list,
        random_choice=random_choice,
        redirect_contact_message_to_availability=redirect_contact_message_to_availability,
    )
    if response:
        return CapabilityResult(
            next_action=CAPABILITY_NEXT_RETURN,
            state=state,
            final_response=response,
        )

    return CapabilityResult(
        next_action=CAPABILITY_NEXT_CONTINUE,
        state=state,
    )
