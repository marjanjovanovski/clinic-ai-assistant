"""Scheduling capability contract for orchestration-first integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.services.scheduling.models import AvailabilityRequest, BookingRequest
from app.services.scheduling.service import (
    book_slot,
    get_availability,
    get_scheduling_public_config,
)


CAPABILITY_NEXT_CONTINUE = "continue"
CAPABILITY_NEXT_RETURN = "return_response"
OPERATION_AVAILABILITY = "availability_lookup"
OPERATION_BOOK_SLOT = "book_selected_slot"


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


def handle_scheduling_capability(context: CapabilityContext) -> CapabilityResult:
    assessment = assess_scheduling_capability(context)
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
