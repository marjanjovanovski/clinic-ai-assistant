from app.services.ai_agent import (
    get_runtime_session_state,
    start_contact_collection_from_scheduling_handoff,
)
from app.services.config_loader import TenantConfigError, TenantNotFoundError
from app.services.scheduling.models import AvailabilityRequest, BookingRequest
from app.services.scheduling.service import (
    SchedulingConfigError,
    SchedulingDisabledError,
    SchedulingProviderError,
    book_slot,
    get_availability,
    get_scheduling_public_config,
)
from app.services.scheduling_capability import (
    SchedulingSlotConflictError,
    book_selected_slot,
    prepare_selected_slot_handoff,
    slot_conflict_error,
)
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

router = APIRouter()


class AvailabilityLookupRequest(BaseModel):
    service_id: str = Field(..., max_length=128)
    date_from: str = Field(..., max_length=32)
    date_to: str = Field(..., max_length=32)
    timezone: str = Field(..., max_length=64)

    @field_validator("service_id", "date_from", "date_to", "timezone")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field must not be empty")
        return trimmed


class SlotBookingRequest(BaseModel):
    service_id: str = Field(..., max_length=128)
    slot_id: str = Field(..., max_length=256)
    patient_name: str = Field(..., max_length=200)
    patient_phone: str | None = Field(default=None, max_length=64)
    patient_email: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    session_id: str | None = Field(default=None, max_length=128)
    selected_slot: dict | None = None

    @field_validator("service_id", "slot_id", "patient_name")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field must not be empty")
        return trimmed

    @field_validator("patient_phone", "patient_email", "note", "session_id")
    @classmethod
    def validate_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class SessionSlotSelectionRequest(BaseModel):
    session_id: str = Field(..., max_length=128)
    service_id: str = Field(..., max_length=128)
    slot_id: str = Field(..., max_length=256)

    @field_validator("session_id", "service_id", "slot_id")
    @classmethod
    def validate_selection_fields(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field must not be empty")
        return trimmed


@router.get("/scheduling/config/{tenant}")
def scheduling_config(tenant: str):
    try:
        return get_scheduling_public_config(tenant).to_dict()
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/scheduling/availability")
def scheduling_availability(payload: AvailabilityLookupRequest, tenant: str = Query(...)):
    try:
        result = get_availability(
            AvailabilityRequest(
                tenant=tenant,
                service_id=payload.service_id,
                date_from=payload.date_from,
                date_to=payload.date_to,
                timezone=payload.timezone,
            )
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return result.to_dict()


@router.post("/scheduling/book")
def scheduling_book(payload: SlotBookingRequest, tenant: str = Query(...)):
    try:
        if payload.session_id:
            hold = create_slot_hold(
                tenant=tenant,
                service_id=payload.service_id,
                slot_id=payload.slot_id,
                session_id=payload.session_id,
            )
            if not isinstance(hold, dict) or hold.get("session_id") != payload.session_id:
                conflict = slot_conflict_error(
                    tenant=tenant,
                    service_id=payload.service_id,
                    slot_id=payload.slot_id,
                    selected_slot=payload.selected_slot,
                )
                return JSONResponse(
                    status_code=409,
                    content=conflict.to_booking_result_payload(slot_id=payload.slot_id),
                )
            result = book_selected_slot(
                tenant=tenant,
                service_id=payload.service_id,
                slot_id=payload.slot_id,
                patient_name=payload.patient_name,
                patient_phone=payload.patient_phone,
                patient_email=payload.patient_email,
                note=payload.note,
                session_id=payload.session_id,
                hold_id=hold.get("hold_id"),
                selected_slot=payload.selected_slot,
            )
        else:
            result = book_slot(
                BookingRequest(
                    tenant=tenant,
                    service_id=payload.service_id,
                    slot_id=payload.slot_id,
                    patient_name=payload.patient_name,
                    patient_phone=payload.patient_phone,
                    patient_email=payload.patient_email,
                    note=payload.note,
                )
            )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchedulingSlotConflictError as exc:
        return JSONResponse(
            status_code=409,
            content=exc.to_booking_result_payload(slot_id=payload.slot_id),
        )
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return result.to_dict()


@router.post("/scheduling/select-slot")
def scheduling_select_slot(payload: SessionSlotSelectionRequest, tenant: str = Query(...)):
    try:
        state = get_runtime_session_state(tenant, payload.session_id)
        scheduling_handoff = prepare_selected_slot_handoff(
            tenant=tenant,
            session_id=payload.session_id,
            state=state,
            service_id=payload.service_id,
            slot_id=payload.slot_id,
        )
        return start_contact_collection_from_scheduling_handoff(
            tenant,
            payload.session_id,
            scheduling_handoff,
        )
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
