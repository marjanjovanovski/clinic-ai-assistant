"""Scheduling provider base contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.scheduling.models import (
    AvailabilityRequest,
    AvailabilityResult,
    BookingRequest,
    BookingResult,
)


class SchedulingProvider(ABC):
    """Stable adapter contract for scheduling providers."""

    provider_name: str

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def get_availability(self, request: AvailabilityRequest) -> AvailabilityResult:
        """Return normalized available slots for the requested range."""

    @abstractmethod
    def book_slot(self, request: BookingRequest) -> BookingResult:
        """Create a booking for a previously selected slot."""

    @abstractmethod
    def healthcheck(self) -> dict:
        """Return a lightweight provider health payload."""
