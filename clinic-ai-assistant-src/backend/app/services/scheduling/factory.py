"""Scheduling provider factory."""

from __future__ import annotations

from app.services.scheduling.base import SchedulingProvider
from app.services.scheduling.providers.google_calendar import GoogleCalendarSchedulingProvider
from app.services.scheduling.providers.mock_provider import MockSchedulingProvider


def build_provider(provider_name: str, provider_config: dict) -> SchedulingProvider:
    normalized_name = str(provider_name or "").strip()
    if normalized_name == "mock":
        return MockSchedulingProvider(provider_config)
    if normalized_name == "google_calendar":
        return GoogleCalendarSchedulingProvider(provider_config)
    raise ValueError(f"Unsupported scheduling provider: {provider_name}")
