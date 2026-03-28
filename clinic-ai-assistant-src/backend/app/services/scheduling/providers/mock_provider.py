"""Deterministic mock scheduling provider for isolated runtime work."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from app.services.scheduling.base import SchedulingProvider
from app.services.scheduling.models import (
    AvailabilityRequest,
    AvailabilityResult,
    AvailableSlot,
    BookingRequest,
    BookingResult,
)


class MockSchedulingProvider(SchedulingProvider):
    provider_name = "mock"

    def _seed(self) -> str:
        return str(self.config.get("seed") or "mock-provider")

    def get_availability(self, request: AvailabilityRequest) -> AvailabilityResult:
        start_date = date.fromisoformat(request.date_from)
        end_date = date.fromisoformat(request.date_to)
        slots: list[AvailableSlot] = []

        current_day = start_date
        while current_day <= end_date and len(slots) < 12:
            for hour in (9, 11, 14):
                start_at = datetime(
                    current_day.year,
                    current_day.month,
                    current_day.day,
                    hour,
                    0,
                )
                end_at = start_at + timedelta(minutes=30)
                slot_id = self._slot_id(request.service_id, start_at.isoformat())
                slots.append(
                    AvailableSlot(
                        provider=self.provider_name,
                        slot_id=slot_id,
                        start_at=f"{start_at.isoformat()}+01:00",
                        end_at=f"{end_at.isoformat()}+01:00",
                        timezone=request.timezone,
                        display_label=start_at.strftime("%d %b %Y во %H:%M"),
                        source_payload={
                            "mock_seed": self._seed(),
                            "service_id": request.service_id,
                        },
                    )
                )
            current_day += timedelta(days=1)

        return AvailabilityResult(provider=self.provider_name, slots=slots)

    def book_slot(self, request: BookingRequest) -> BookingResult:
        _, start_at, _, _ = request.slot_id.split("|", 3)
        start_dt = datetime.fromisoformat(start_at)
        end_dt = start_dt + timedelta(minutes=30)
        booking_hash = hashlib.sha256(
            f"{self._seed()}:{request.service_id}:{request.slot_id}:{request.patient_name}".encode()
        ).hexdigest()[:12]
        return BookingResult(
            status="confirmed",
            provider=self.provider_name,
            booking_id=f"mock-booking-{booking_hash}",
            start_at=f"{start_dt.isoformat()}+01:00",
            end_at=f"{end_dt.isoformat()}+01:00",
            display_label=start_dt.strftime("%d %b %Y во %H:%M"),
            confirmation_message="Терминот е резервиран во mock режим.",
            source_payload={
                "slot_id": request.slot_id,
                "patient_name": request.patient_name,
            },
        )

    def healthcheck(self) -> dict:
        return {
            "provider": self.provider_name,
            "status": "ok",
            "seed": self._seed(),
        }

    def _slot_id(self, service_id: str, start_at: str) -> str:
        return f"mock|{start_at}|{service_id}|{self._seed()}"
