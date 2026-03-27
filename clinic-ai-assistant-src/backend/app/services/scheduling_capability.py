"""Scheduling capability contract for orchestration-first integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta

from app.services.scheduling_hold_store import (
    HOLD_STATUS_ACTIVE,
    HOLD_STATUS_CONSUMED,
    HOLD_STATUS_EXPIRED,
    create_slot_hold,
    get_slot_hold,
    update_hold_status,
)
from app.services.session_trace_logger import trace_event
from app.services.scheduling.models import AvailabilityRequest, BookingRequest, BookingResult
from app.services.scheduling.service import (
    SchedulingConfigError,
    SchedulingDisabledError,
    SchedulingProviderError,
    book_slot,
    get_availability,
    get_scheduling_public_config,
)


CAPABILITY_NEXT_CONTINUE = "continue"
CAPABILITY_NEXT_RETURN = "return_response"
OPERATION_AVAILABILITY = "availability_lookup"
OPERATION_BOOK_SLOT = "book_selected_slot"
AVAILABILITY_INTENT_MARKER_KEY = "_availability_intent_pending"
SLOT_UNAVAILABLE_MESSAGE = "The selected slot is no longer available. I will show you other available slots for the same day."
SLOT_CONFLICT_NEXT_ACTION = "refresh_availability"
SLOT_CONFLICT_REASON = "slot_conflict"
SLOT_CONFLICT_SCOPE = "same_day"
NO_AVAILABILITY_MESSAGE = "Momentalno nema slobodni termini vo tekovniot period. Kazete drug datum ili drug period i ke proveram povtorno."


class SchedulingSlotConflictError(SchedulingConfigError):
    """Structured recoverable slot-conflict error for UI-safe fallback handling."""

    def __init__(
        self,
        message: str,
        *,
        service_id: str,
        selected_slot: dict | None,
        replacement_slots: list[dict] | None = None,
        next_action: str = SLOT_CONFLICT_NEXT_ACTION,
        reason: str = SLOT_CONFLICT_REASON,
        fallback_scope: str = SLOT_CONFLICT_SCOPE,
        fallback_date: str | None = None,
    ) -> None:
        super().__init__(message)
        self.service_id = service_id
        self.selected_slot = selected_slot if isinstance(selected_slot, dict) else None
        self.replacement_slots = replacement_slots if isinstance(replacement_slots, list) else []
        self.next_action = next_action
        self.reason = reason
        self.fallback_scope = fallback_scope
        self.fallback_date = fallback_date

    def to_booking_result_payload(self, *, slot_id: str) -> dict:
        selected_slot = self.selected_slot if isinstance(self.selected_slot, dict) else {}
        return {
            "status": "slot_unavailable",
            "provider": "scheduling",
            "booking_id": "",
            "start_at": selected_slot.get("start_at"),
            "end_at": selected_slot.get("end_at"),
            "display_label": "",
            "confirmation_message": str(self),
            "source_payload": {
                "slot_id": slot_id,
                "service_id": self.service_id,
                "reason": self.reason,
                "next_action": self.next_action,
                "fallback_scope": self.fallback_scope,
                "fallback_date": self.fallback_date,
                "selected_slot": dict(selected_slot) if isinstance(selected_slot, dict) else None,
                "replacement_slots": [slot for slot in self.replacement_slots if isinstance(slot, dict)],
            },
        }


@dataclass(slots=True)
class SchedulingCapabilitySnapshot:
    enabled: bool
    booking_enabled: bool
    provider: str
    timezone: str
    slot_duration_minutes: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CapabilityContext:
    tenant: str
    session_id: str
    session_key: str
    message: str
    state: dict | None
    profile: dict
    services: list[dict]
    requested_operation: str | None = None
    service_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    timezone: str | None = None
    preferred_days: list[str] = field(default_factory=list)
    preferred_time_range: str | None = None
    slot_id: str | None = None
    patient_name: str | None = None
    patient_phone: str | None = None
    patient_email: str | None = None
    note: str | None = None
    intro_message: str | None = None


@dataclass(slots=True)
class SchedulingCapabilityAssessment:
    can_handle: bool
    operation: str | None
    status: str
    reason: str
    missing_inputs: list[str]
    capability_state: dict | None
    output_payload: dict | None


@dataclass(slots=True)
class CapabilityResult:
    next_action: str
    state: dict | None
    assessment: SchedulingCapabilityAssessment
    final_response: tuple[str, str] | None = None


def get_capability_snapshot(tenant: str) -> SchedulingCapabilitySnapshot:
    config = get_scheduling_public_config(tenant)
    return SchedulingCapabilitySnapshot(
        enabled=config.enabled,
        booking_enabled=config.booking_enabled,
        provider=config.provider,
        timezone=config.timezone,
        slot_duration_minutes=config.slot_duration_minutes,
    )


def _normalized_operation(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def mark_availability_intent_pending(session_key: str, state: dict | None, session_state: dict) -> dict:
    next_state = dict(state) if isinstance(state, dict) else {}
    next_state[AVAILABILITY_INTENT_MARKER_KEY] = True
    session_state[session_key] = next_state
    return next_state


def has_pending_availability_intent(state: dict | None) -> bool:
    return isinstance(state, dict) and bool(state.get(AVAILABILITY_INTENT_MARKER_KEY))


def _slots_from_assessment(assessment: SchedulingCapabilityAssessment) -> list[dict]:
    output_payload = assessment.output_payload if isinstance(assessment.output_payload, dict) else None
    result_payload = output_payload.get("result") if isinstance(output_payload, dict) else None
    slots = result_payload.get("slots") if isinstance(result_payload, dict) else None
    return slots if isinstance(slots, list) else []


def store_scheduling_state(
    session_key: str,
    state: dict | None,
    *,
    assessment: SchedulingCapabilityAssessment,
    session_state: dict,
) -> dict:
    next_state = dict(state) if isinstance(state, dict) else {}
    next_state.pop(AVAILABILITY_INTENT_MARKER_KEY, None)

    scheduling_state = {
        "operation": assessment.operation,
        "status": assessment.status,
        "reason": assessment.reason,
        "capability_state": assessment.capability_state,
        "output_payload": assessment.output_payload,
        "booking_handoff_ready": bool(
            assessment.operation == OPERATION_AVAILABILITY
            and assessment.status == "completed"
            and bool(_slots_from_assessment(assessment))
        ),
    }
    next_state["scheduling"] = scheduling_state
    session_state[session_key] = next_state
    return next_state


def scheduling_handoff_ready(state: dict | None) -> bool:
    if not isinstance(state, dict):
        return False
    scheduling_state = state.get("scheduling")
    return bool(isinstance(scheduling_state, dict) and scheduling_state.get("booking_handoff_ready"))


def scheduling_handoff_payload(state: dict | None) -> dict | None:
    if not isinstance(state, dict):
        return None

    scheduling_state = state.get("scheduling")
    if not isinstance(scheduling_state, dict):
        return None

    capability_state = scheduling_state.get("capability_state")
    output_payload = scheduling_state.get("output_payload")
    result_payload = output_payload.get("result") if isinstance(output_payload, dict) else None
    slots = result_payload.get("slots") if isinstance(result_payload, dict) else []
    if not isinstance(slots, list):
        slots = []

    return {
        "source": "scheduling_availability",
        "reason": "confirmed_interest_after_availability",
        "service_id": capability_state.get("service_id") if isinstance(capability_state, dict) else None,
        "slot_count": len(slots),
        "selected_slot": None,
        "availability_result": {
            "provider": result_payload.get("provider") if isinstance(result_payload, dict) else None,
            "slots": slots,
        },
    }


def selected_slot_handoff_payload(
    state: dict | None,
    *,
    service_id: str,
    slot_id: str,
) -> dict:
    if not isinstance(state, dict):
        raise ValueError("Chat session was not found for slot selection")

    scheduling_state = state.get("scheduling")
    if not isinstance(scheduling_state, dict) or not scheduling_state.get("booking_handoff_ready"):
        raise ValueError("No active availability result is ready for slot selection in this chat session")

    capability_state = scheduling_state.get("capability_state")
    resolved_service_id = (
        capability_state.get("service_id")
        if isinstance(capability_state, dict) and isinstance(capability_state.get("service_id"), str)
        else None
    )
    if resolved_service_id and resolved_service_id != service_id:
        raise ValueError("Selected slot service_id does not match the active scheduling session")

    base_payload = scheduling_handoff_payload(state)
    if not isinstance(base_payload, dict):
        raise ValueError("Unable to build scheduling handoff payload for the selected slot")

    availability_result = base_payload.get("availability_result")
    slots = availability_result.get("slots") if isinstance(availability_result, dict) else None
    if not isinstance(slots, list) or not slots:
        raise ValueError("No authoritative slots are available for selection in this chat session")

    selected_slot = next(
        (
            slot for slot in slots
            if isinstance(slot, dict) and slot.get("slot_id") == slot_id
        ),
        None,
    )
    if not isinstance(selected_slot, dict):
        raise ValueError("Selected slot is not part of the active availability result")

    return {
        **base_payload,
        "reason": "selected_slot_from_main_chat",
        "service_id": resolved_service_id or service_id,
        "selected_slot": selected_slot,
    }


def assessment_reply_text(assessment: SchedulingCapabilityAssessment) -> str | None:
    output_payload = assessment.output_payload if isinstance(assessment.output_payload, dict) else None
    reply_text = output_payload.get("reply_text") if isinstance(output_payload, dict) else None
    return reply_text.strip() if isinstance(reply_text, str) and reply_text.strip() else None


def assessment_widget_payload(assessment: SchedulingCapabilityAssessment) -> dict | None:
    if assessment.operation != OPERATION_AVAILABILITY or assessment.status != "completed":
        return None

    output_payload = assessment.output_payload if isinstance(assessment.output_payload, dict) else None
    result_payload = output_payload.get("result") if isinstance(output_payload, dict) else None
    slots = result_payload.get("slots") if isinstance(result_payload, dict) else None
    capability_state = assessment.capability_state if isinstance(assessment.capability_state, dict) else None
    if not isinstance(slots, list) or not slots:
        return None

    title = output_payload.get("reply_text") if isinstance(output_payload, dict) else None
    if isinstance(title, str) and title.strip():
        title = title.split("\n\n", 1)[0].strip()

    return {
        "type": "slot-list",
        "title": title.strip() if isinstance(title, str) and title.strip() else None,
        "service_id": capability_state.get("service_id") if isinstance(capability_state, dict) else None,
        "provider": result_payload.get("provider") if isinstance(result_payload, dict) else None,
        "request": output_payload.get("request") if isinstance(output_payload, dict) else None,
        "slots": slots,
    }


def _resolved_timezone(context: CapabilityContext, snapshot: SchedulingCapabilitySnapshot) -> str:
    if isinstance(context.timezone, str) and context.timezone.strip():
        return context.timezone.strip()
    return snapshot.timezone


def _base_capability_state(
    *,
    context: CapabilityContext,
    snapshot: SchedulingCapabilitySnapshot,
    operation: str | None,
    status: str,
    missing_inputs: list[str],
) -> dict:
    return {
        "capability": "scheduling",
        "operation": operation,
        "status": status,
        "provider": snapshot.provider,
        "timezone": _resolved_timezone(context, snapshot),
        "booking_enabled": snapshot.booking_enabled,
        "service_id": context.service_id,
        "slot_id": context.slot_id,
        "missing_inputs": missing_inputs,
    }


def _availability_default_service_id(context: CapabilityContext) -> str | None:
    if isinstance(context.service_id, str) and context.service_id.strip() and context.service_id != "unknown":
        return context.service_id.strip()

    for service in context.services:
        if isinstance(service, dict) and service.get("id") == "consultation":
            return "consultation"

    for service in context.services:
        service_id = service.get("id") if isinstance(service, dict) else None
        if isinstance(service_id, str) and service_id.strip():
            return service_id.strip()

    return None


def _availability_default_dates(context: CapabilityContext) -> tuple[str, str]:
    today = date.today()
    scheduling = context.profile.get("scheduling") if isinstance(context.profile, dict) else {}
    reach_days = scheduling.get("default_availability_reach_days") if isinstance(scheduling, dict) else None
    if isinstance(reach_days, int) and reach_days > 1:
        counted_days = 1
        end_date = today
        while counted_days < reach_days:
            end_date += timedelta(days=1)
            if end_date.weekday() >= 5:
                continue
            counted_days += 1
        return today.isoformat(), end_date.isoformat()

    lookahead_days = scheduling.get("lookahead_days") if isinstance(scheduling, dict) else None
    end_date = today + timedelta(days=1) if isinstance(lookahead_days, int) and lookahead_days > 1 else today
    return today.isoformat(), end_date.isoformat()


def _with_availability_defaults(
    context: CapabilityContext,
    snapshot: SchedulingCapabilitySnapshot,
) -> CapabilityContext:
    if _normalized_operation(context.requested_operation) != OPERATION_AVAILABILITY:
        return context

    date_from, date_to = _availability_default_dates(context)
    return replace(
        context,
        service_id=_availability_default_service_id(context),
        date_from=context.date_from or date_from,
        date_to=context.date_to or date_to,
        timezone=_resolved_timezone(context, snapshot),
    )


def _availability_assessment(
    context: CapabilityContext,
    snapshot: SchedulingCapabilitySnapshot,
) -> SchedulingCapabilityAssessment:
    if not snapshot.enabled:
        state = _base_capability_state(
            context=context,
            snapshot=snapshot,
            operation=OPERATION_AVAILABILITY,
            status="disabled",
            missing_inputs=[],
        )
        return SchedulingCapabilityAssessment(
            can_handle=False,
            operation=OPERATION_AVAILABILITY,
            status="disabled",
            reason="scheduling_disabled",
            missing_inputs=[],
            capability_state=state,
            output_payload={
                "capability": "scheduling",
                "operation": OPERATION_AVAILABILITY,
                "provider": snapshot.provider,
                "enabled": False,
            },
        )

    timezone_name = _resolved_timezone(context, snapshot)
    missing_inputs = []
    if not context.service_id:
        missing_inputs.append("service_id")
    if not context.date_from:
        missing_inputs.append("date_from")
    if not context.date_to:
        missing_inputs.append("date_to")
    if not timezone_name:
        missing_inputs.append("timezone")

    status = "awaiting_input" if missing_inputs else "ready"
    request_payload = None
    if not missing_inputs:
        request_payload = AvailabilityRequest(
            tenant=context.tenant,
            service_id=str(context.service_id),
            date_from=str(context.date_from),
            date_to=str(context.date_to),
            timezone=timezone_name,
            preferred_days=list(context.preferred_days),
            preferred_time_range=context.preferred_time_range,
        ).to_dict()

    state = _base_capability_state(
        context=context,
        snapshot=snapshot,
        operation=OPERATION_AVAILABILITY,
        status=status,
        missing_inputs=missing_inputs,
    )
    return SchedulingCapabilityAssessment(
        can_handle=True,
        operation=OPERATION_AVAILABILITY,
        status=status,
        reason="availability_request_supported",
        missing_inputs=missing_inputs,
        capability_state=state,
        output_payload={
            "capability": "scheduling",
            "operation": OPERATION_AVAILABILITY,
            "provider": snapshot.provider,
            "request": request_payload,
            "missing_inputs": missing_inputs,
        },
    )


def _booking_assessment(
    context: CapabilityContext,
    snapshot: SchedulingCapabilitySnapshot,
) -> SchedulingCapabilityAssessment:
    if not snapshot.booking_enabled:
        state = _base_capability_state(
            context=context,
            snapshot=snapshot,
            operation=OPERATION_BOOK_SLOT,
            status="disabled",
            missing_inputs=[],
        )
        return SchedulingCapabilityAssessment(
            can_handle=False,
            operation=OPERATION_BOOK_SLOT,
            status="disabled",
            reason="scheduling_booking_disabled",
            missing_inputs=[],
            capability_state=state,
            output_payload={
                "capability": "scheduling",
                "operation": OPERATION_BOOK_SLOT,
                "provider": snapshot.provider,
                "enabled": False,
            },
        )

    missing_inputs = []
    if not context.service_id:
        missing_inputs.append("service_id")
    if not context.slot_id:
        missing_inputs.append("slot_id")
    if not context.patient_name:
        missing_inputs.append("patient_name")

    status = "awaiting_input" if missing_inputs else "ready"
    request_payload = None
    if not missing_inputs:
        request_payload = BookingRequest(
            tenant=context.tenant,
            service_id=str(context.service_id),
            slot_id=str(context.slot_id),
            patient_name=str(context.patient_name),
            patient_phone=context.patient_phone,
            patient_email=context.patient_email,
            note=context.note,
        ).to_dict()

    state = _base_capability_state(
        context=context,
        snapshot=snapshot,
        operation=OPERATION_BOOK_SLOT,
        status=status,
        missing_inputs=missing_inputs,
    )
    return SchedulingCapabilityAssessment(
        can_handle=True,
        operation=OPERATION_BOOK_SLOT,
        status=status,
        reason="slot_booking_supported",
        missing_inputs=missing_inputs,
        capability_state=state,
        output_payload={
            "capability": "scheduling",
            "operation": OPERATION_BOOK_SLOT,
            "provider": snapshot.provider,
            "request": request_payload,
            "missing_inputs": missing_inputs,
        },
    )


def assess_scheduling_capability(context: CapabilityContext) -> SchedulingCapabilityAssessment:
    snapshot = get_capability_snapshot(context.tenant)
    operation = _normalized_operation(context.requested_operation)

    if operation == OPERATION_AVAILABILITY:
        return _availability_assessment(context, snapshot)

    if operation == OPERATION_BOOK_SLOT:
        return _booking_assessment(context, snapshot)

    return SchedulingCapabilityAssessment(
        can_handle=False,
        operation=operation,
        status="idle",
        reason="no_scheduling_operation_requested",
        missing_inputs=[],
        capability_state=None,
        output_payload=None,
    )


def _availability_reply_text(context: CapabilityContext, slots_payload: list[dict]) -> str:
    intro_message = context.intro_message.strip() if isinstance(context.intro_message, str) and context.intro_message.strip() else ""
    slot_lines = [f"• {slot['display_label']}" for slot in slots_payload[:6] if isinstance(slot.get("display_label"), str)]
    if intro_message and slot_lines:
        return f"{intro_message}\n\n" + "\n".join(slot_lines)
    if not slot_lines:
        return NO_AVAILABILITY_MESSAGE
    if intro_message:
        return intro_message
    if slot_lines:
        return "\n".join(slot_lines)
    return ""


def handle_scheduling_capability(context: CapabilityContext) -> CapabilityResult:
    operation = _normalized_operation(context.requested_operation)
    snapshot = get_capability_snapshot(context.tenant)
    effective_context = _with_availability_defaults(context, snapshot)
    assessment = assess_scheduling_capability(effective_context)

    if operation == OPERATION_AVAILABILITY and assessment.can_handle and assessment.status == "ready":
        execution_context = replace(
            context,
            service_id=assessment.capability_state.get("service_id") if isinstance(assessment.capability_state, dict) else context.service_id,
            date_from=assessment.output_payload.get("request", {}).get("date_from") if isinstance(assessment.output_payload, dict) else context.date_from,
            date_to=assessment.output_payload.get("request", {}).get("date_to") if isinstance(assessment.output_payload, dict) else context.date_to,
            timezone=assessment.capability_state.get("timezone") if isinstance(assessment.capability_state, dict) else context.timezone,
        )
        try:
            availability = lookup_availability(
                tenant=execution_context.tenant,
                service_id=str(execution_context.service_id),
                date_from=str(execution_context.date_from),
                date_to=str(execution_context.date_to),
                timezone=str(execution_context.timezone),
                preferred_days=execution_context.preferred_days,
                preferred_time_range=execution_context.preferred_time_range,
            )
            result_payload = availability.to_dict()
            output_payload = {
                **(assessment.output_payload or {}),
                "result": result_payload,
                "reply_text": _availability_reply_text(execution_context, result_payload.get("slots", [])),
            }
            return CapabilityResult(
                next_action=CAPABILITY_NEXT_CONTINUE,
                state=context.state,
                assessment=SchedulingCapabilityAssessment(
                    can_handle=assessment.can_handle,
                    operation=assessment.operation,
                    status="completed",
                    reason="availability_lookup_completed",
                    missing_inputs=[],
                    capability_state=assessment.capability_state,
                    output_payload=output_payload,
                ),
            )
        except SchedulingDisabledError:
            pass
        except SchedulingConfigError:
            pass
        except SchedulingProviderError:
            pass

    return CapabilityResult(
        next_action=CAPABILITY_NEXT_CONTINUE,
        state=context.state,
        assessment=assessment,
    )


def lookup_availability(
    *,
    tenant: str,
    service_id: str,
    date_from: str,
    date_to: str,
    timezone: str,
    preferred_days: list[str] | None = None,
    preferred_time_range: str | None = None,
):
    request = AvailabilityRequest(
        tenant=tenant,
        service_id=service_id,
        date_from=date_from,
        date_to=date_to,
        timezone=timezone,
        preferred_days=list(preferred_days or []),
        preferred_time_range=preferred_time_range,
    )
    return get_availability(request)


def _slot_day_for_recheck(slot_id: str, selected_slot: dict | None) -> str | None:
    start_at = selected_slot.get("start_at") if isinstance(selected_slot, dict) else None
    if isinstance(start_at, str) and start_at.strip():
        try:
            return datetime.fromisoformat(start_at.strip()).date().isoformat()
        except ValueError:
            return None

    parts = slot_id.split("|")
    if len(parts) >= 2:
        candidate = parts[1].strip()
        if candidate:
            try:
                return datetime.fromisoformat(candidate).date().isoformat()
            except ValueError:
                return None
    return None


def _slot_timezone_for_recheck(tenant: str, selected_slot: dict | None) -> str:
    timezone_name = selected_slot.get("timezone") if isinstance(selected_slot, dict) else None
    if isinstance(timezone_name, str) and timezone_name.strip():
        return timezone_name.strip()
    return get_capability_snapshot(tenant).timezone


def _slot_is_still_available(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    selected_slot: dict | None,
) -> bool:
    slot_day = _slot_day_for_recheck(slot_id, selected_slot)
    if not slot_day:
        return False
    timezone_name = _slot_timezone_for_recheck(tenant, selected_slot)
    availability = lookup_availability(
        tenant=tenant,
        service_id=service_id,
        date_from=slot_day,
        date_to=slot_day,
        timezone=timezone_name,
    )
    availability_payload = availability.to_dict()
    slots = availability_payload.get("slots") if isinstance(availability_payload, dict) else None
    if not isinstance(slots, list):
        return False
    return any(isinstance(slot, dict) and slot.get("slot_id") == slot_id for slot in slots)


def _same_day_replacement_slots(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    selected_slot: dict | None,
) -> tuple[str | None, list[dict]]:
    slot_day = _slot_day_for_recheck(slot_id, selected_slot)
    if not slot_day:
        return None, []

    timezone_name = _slot_timezone_for_recheck(tenant, selected_slot)
    availability = lookup_availability(
        tenant=tenant,
        service_id=service_id,
        date_from=slot_day,
        date_to=slot_day,
        timezone=timezone_name,
    )
    availability_payload = availability.to_dict()
    slots = availability_payload.get("slots") if isinstance(availability_payload, dict) else None
    if not isinstance(slots, list):
        return slot_day, []
    replacement_slots = [
        dict(slot)
        for slot in slots
        if isinstance(slot, dict) and slot.get("slot_id") != slot_id
    ]
    return slot_day, replacement_slots[:6]


def _raise_slot_unavailable(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    selected_slot: dict | None,
    session_id: str | None = None,
) -> None:
    fallback_date, replacement_slots = _same_day_replacement_slots(
        tenant=tenant,
        service_id=service_id,
        slot_id=slot_id,
        selected_slot=selected_slot,
    )
    _trace_scheduling_decision(
        tenant,
        session_id,
        "SCHEDULING_SLOT_CONFLICT",
        service_id=service_id,
        slot_id=slot_id,
        reason=SLOT_CONFLICT_REASON,
        next_action=SLOT_CONFLICT_NEXT_ACTION,
        fallback_scope=SLOT_CONFLICT_SCOPE,
        fallback_date=fallback_date,
        replacement_count=len(replacement_slots),
    )
    raise SchedulingSlotConflictError(
        SLOT_UNAVAILABLE_MESSAGE,
        service_id=service_id,
        selected_slot=selected_slot,
        replacement_slots=replacement_slots,
        fallback_date=fallback_date,
    )


def slot_conflict_error(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    selected_slot: dict | None,
    message: str = SLOT_UNAVAILABLE_MESSAGE,
) -> SchedulingSlotConflictError:
    fallback_date, replacement_slots = _same_day_replacement_slots(
        tenant=tenant,
        service_id=service_id,
        slot_id=slot_id,
        selected_slot=selected_slot,
    )
    return SchedulingSlotConflictError(
        message,
        service_id=service_id,
        selected_slot=selected_slot,
        replacement_slots=replacement_slots,
        fallback_date=fallback_date,
    )


def _trace_scheduling_decision(
    tenant: str,
    session_id: str | None,
    event: str,
    **fields,
) -> None:
    if not isinstance(session_id, str) or not session_id.strip():
        return
    trace_event(tenant, session_id.strip(), event, **fields)


def book_selected_slot(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    patient_name: str,
    patient_phone: str | None = None,
    patient_email: str | None = None,
    note: str | None = None,
    session_id: str | None = None,
    hold_id: str | None = None,
    selected_slot: dict | None = None,
):
    recovery_applied = False
    if session_id or hold_id:
        hold = get_slot_hold(
            tenant=tenant,
            slot_id=slot_id,
            session_id=session_id,
            include_inactive=True,
        )
        hold_is_active = (
            isinstance(hold, dict)
            and (not hold_id or hold.get("hold_id") == hold_id)
            and (not session_id or hold.get("session_id") == session_id)
            and hold.get("status") == HOLD_STATUS_ACTIVE
        )
        if not hold_is_active:
            can_attempt_recovery = (
                isinstance(hold, dict)
                and hold.get("status") == HOLD_STATUS_EXPIRED
                and (not hold_id or hold.get("hold_id") == hold_id)
                and (not session_id or hold.get("session_id") == session_id)
            )
            if can_attempt_recovery and _slot_is_still_available(
                tenant=tenant,
                service_id=service_id,
                slot_id=slot_id,
                selected_slot=selected_slot,
            ):
                refreshed_hold = create_slot_hold(
                    tenant=tenant,
                    service_id=service_id,
                    slot_id=slot_id,
                    session_id=session_id or str(hold.get("session_id") or ""),
                )
                if isinstance(refreshed_hold, dict) and refreshed_hold.get("session_id") == (session_id or hold.get("session_id")):
                    hold = refreshed_hold
                    recovery_applied = True
                    _trace_scheduling_decision(
                        tenant,
                        session_id,
                        "SCHEDULING_HOLD_REFRESHED",
                        service_id=service_id,
                        slot_id=slot_id,
                        previous_hold_id=hold_id,
                        refreshed_hold_id=hold.get("hold_id"),
                    )
                else:
                    _raise_slot_unavailable(
                        tenant=tenant,
                        service_id=service_id,
                        slot_id=slot_id,
                        selected_slot=selected_slot,
                        session_id=session_id,
                    )
            else:
                _trace_scheduling_decision(
                    tenant,
                    session_id,
                    "SCHEDULING_BOOKING_MISMATCH",
                    service_id=service_id,
                    slot_id=slot_id,
                    hold_id=hold_id,
                    observed_hold_status=hold.get("status") if isinstance(hold, dict) else None,
                )
                _raise_slot_unavailable(
                    tenant=tenant,
                    service_id=service_id,
                    slot_id=slot_id,
                    selected_slot=selected_slot,
                    session_id=session_id,
                )
        if not isinstance(hold, dict) or hold.get("status") != HOLD_STATUS_ACTIVE:
            _trace_scheduling_decision(
                tenant,
                session_id,
                "SCHEDULING_BOOKING_MISMATCH",
                service_id=service_id,
                slot_id=slot_id,
                hold_id=hold_id,
                observed_hold_status=hold.get("status") if isinstance(hold, dict) else None,
            )
            _raise_slot_unavailable(
                tenant=tenant,
                service_id=service_id,
                slot_id=slot_id,
                selected_slot=selected_slot,
                session_id=session_id,
            )

    request = BookingRequest(
        tenant=tenant,
        service_id=service_id,
        slot_id=slot_id,
        patient_name=patient_name,
        patient_phone=patient_phone,
        patient_email=patient_email,
        note=note,
    )
    result = book_slot(request)
    if recovery_applied:
        source_payload = dict(result.source_payload or {})
        source_payload["recovery_applied"] = True
        result = BookingResult(
            status=result.status,
            provider=result.provider,
            booking_id=result.booking_id,
            start_at=result.start_at,
            end_at=result.end_at,
            display_label=result.display_label,
            confirmation_message=result.confirmation_message,
            source_payload=source_payload,
        )
    if session_id or hold_id:
        resolved_hold_id = hold_id or hold.get("hold_id")
        if isinstance(resolved_hold_id, str) and resolved_hold_id.strip():
            update_hold_status(
                hold_id=resolved_hold_id.strip(),
                status=HOLD_STATUS_CONSUMED,
            )
    _trace_scheduling_decision(
        tenant,
        session_id,
        "SCHEDULING_BOOKING_CONFIRMED",
        service_id=service_id,
        slot_id=slot_id,
        booking_id=result.booking_id,
        recovery_applied=recovery_applied,
    )
    return result
