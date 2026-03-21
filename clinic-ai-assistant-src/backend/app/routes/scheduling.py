from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.services.config_loader import TenantConfigError, TenantNotFoundError
from app.services.scheduling.models import AvailabilityRequest, BookingRequest
from app.services.scheduling.service import (
    book_slot,
    get_availability,
    get_scheduling_public_config,
    SchedulingConfigError,
    SchedulingDisabledError,
    SchedulingProviderError,
)

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

    @field_validator("service_id", "slot_id", "patient_name")
    @classmethod
    def validate_required_fields(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field must not be empty")
        return trimmed

    @field_validator("patient_phone", "patient_email", "note")
    @classmethod
    def validate_optional_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


@router.get("/scheduling/config/{tenant}")
def scheduling_config(tenant: str):
    try:
        return get_scheduling_public_config(tenant).to_dict()
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


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
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return result.to_dict()


@router.post("/scheduling/book")
def scheduling_book(payload: SlotBookingRequest, tenant: str = Query(...)):
    try:
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
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
    except SchedulingDisabledError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except SchedulingConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except SchedulingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return result.to_dict()
