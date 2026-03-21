"""Internal scheduling models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(slots=True)
class AvailabilityRequest:
    tenant: str
    service_id: str
    date_from: str
    date_to: str
    timezone: str
    preferred_days: list[str] = field(default_factory=list)
    preferred_time_range: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class AvailableSlot:
    provider: str
    slot_id: str
    start_at: str
    end_at: str
    timezone: str
    display_label: str
    source_payload: JsonDict | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class AvailabilityResult:
    provider: str
    slots: list[AvailableSlot] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "provider": self.provider,
            "slots": [slot.to_dict() for slot in self.slots],
        }


@dataclass(slots=True)
class BookingRequest:
    tenant: str
    service_id: str
    slot_id: str
    patient_name: str
    patient_phone: str | None = None
    patient_email: str | None = None
    note: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class BookingResult:
    status: str
    provider: str
    booking_id: str
    start_at: str
    end_at: str
    display_label: str
    confirmation_message: str
    source_payload: JsonDict | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(slots=True)
class SchedulingPublicConfig:
    enabled: bool
    provider: str
    timezone: str
    slot_duration_minutes: int
    booking_enabled: bool

    def to_dict(self) -> JsonDict:
        return asdict(self)
