"""Scheduling capability contract for orchestration-first integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta

from app.services.scheduling.models import AvailabilityRequest, BookingRequest
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


def assessment_reply_text(assessment: SchedulingCapabilityAssessment) -> str | None:
    output_payload = assessment.output_payload if isinstance(assessment.output_payload, dict) else None
    reply_text = output_payload.get("reply_text") if isinstance(output_payload, dict) else None
    return reply_text.strip() if isinstance(reply_text, str) and reply_text.strip() else None


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
    lookahead_days = scheduling.get("lookahead_days") if isinstance(scheduling, dict) else None
    if isinstance(lookahead_days, int) and lookahead_days > 1:
        end_date = today + timedelta(days=1)
    else:
        end_date = today
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


def book_selected_slot(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    patient_name: str,
    patient_phone: str | None = None,
    patient_email: str | None = None,
    note: str | None = None,
):
    request = BookingRequest(
        tenant=tenant,
        service_id=service_id,
        slot_id=slot_id,
        patient_name=patient_name,
        patient_phone=patient_phone,
        patient_email=patient_email,
        note=note,
    )
    return book_slot(request)
