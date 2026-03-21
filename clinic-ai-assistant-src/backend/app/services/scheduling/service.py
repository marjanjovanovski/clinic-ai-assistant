"""Scheduling service entry points."""

from __future__ import annotations

from datetime import date

from app.services.config_loader import load_profile_config
from app.services.scheduling.factory import build_provider
from app.services.scheduling.models import (
    AvailabilityRequest,
    AvailabilityResult,
    BookingRequest,
    BookingResult,
    SchedulingPublicConfig,
)


class SchedulingError(Exception):
    """Base scheduling runtime error."""


class SchedulingConfigError(SchedulingError):
    """Scheduling configuration is invalid for the requested action."""


class SchedulingDisabledError(SchedulingError):
    """Scheduling is disabled for the tenant."""


class SchedulingProviderError(SchedulingError):
    """Provider interaction failed or is unavailable."""


def _scheduling_config_for_tenant(tenant: str) -> dict:
    profile = load_profile_config(tenant)
    scheduling = profile.get("scheduling") or {}
    if not isinstance(scheduling, dict):
        raise SchedulingConfigError(f"Tenant '{tenant}' scheduling config is invalid")
    return scheduling


def _provider_for_tenant(tenant: str):
    profile = load_profile_config(tenant)
    scheduling = _scheduling_config_for_tenant(tenant)
    if not scheduling.get("enabled", False):
        raise SchedulingDisabledError(f"Scheduling is disabled for tenant '{tenant}'")
    provider_name = scheduling.get("provider")
    if not isinstance(provider_name, str) or not provider_name.strip():
        raise SchedulingConfigError(f"Tenant '{tenant}' scheduling provider is missing")
    providers = scheduling.get("providers") or {}
    provider_config = providers.get(provider_name) or {}
    if not isinstance(provider_config, dict):
        raise SchedulingConfigError(f"Tenant '{tenant}' scheduling provider config is invalid")
    shared_config = {
        key: value
        for key, value in scheduling.items()
        if key != "providers"
    }
    shared_config["business_name"] = profile.get("business", {}).get("name") or tenant
    merged_config = {
        **shared_config,
        **provider_config,
    }
    try:
        return build_provider(provider_name, merged_config)
    except ValueError as exc:
        raise SchedulingConfigError(str(exc)) from exc


def get_scheduling_public_config(tenant: str) -> SchedulingPublicConfig:
    scheduling = _scheduling_config_for_tenant(tenant)
    profile = load_profile_config(tenant)
    return SchedulingPublicConfig(
        enabled=bool(scheduling.get("enabled", False)),
        provider=str(scheduling.get("provider") or ""),
        timezone=str(scheduling.get("timezone") or ""),
        slot_duration_minutes=int(scheduling.get("slot_duration_minutes") or 0),
        booking_enabled=bool(
            scheduling.get("enabled", False) and profile.get("actions", {}).get("allow_booking", False)
        ),
    )


def _validate_availability_request(request: AvailabilityRequest, scheduling: dict) -> None:
    try:
        start_date = date.fromisoformat(request.date_from)
        end_date = date.fromisoformat(request.date_to)
    except ValueError as exc:
        raise SchedulingConfigError("date_from and date_to must be valid ISO dates") from exc

    if start_date > end_date:
        raise SchedulingConfigError("date_from must be on or before date_to")

    lookahead_days = int(scheduling.get("lookahead_days") or 0)
    if lookahead_days > 0 and (end_date - start_date).days >= lookahead_days:
        raise SchedulingConfigError(
            f"Requested date range exceeds configured lookahead window of {lookahead_days} days"
        )


def _validate_booking_request(request: BookingRequest) -> None:
    if not request.patient_name.strip():
        raise SchedulingConfigError("patient_name is required")
    if not request.slot_id.strip():
        raise SchedulingConfigError("slot_id is required")


def get_availability(request: AvailabilityRequest) -> AvailabilityResult:
    scheduling = _scheduling_config_for_tenant(request.tenant)
    _validate_availability_request(request, scheduling)
    provider = _provider_for_tenant(request.tenant)
    try:
        return provider.get_availability(request)
    except SchedulingError:
        raise
    except ValueError as exc:
        raise SchedulingConfigError(str(exc)) from exc
    except Exception as exc:
        raise SchedulingProviderError(f"Scheduling availability lookup failed: {exc}") from exc


def book_slot(request: BookingRequest) -> BookingResult:
    _validate_booking_request(request)
    provider = _provider_for_tenant(request.tenant)
    try:
        return provider.book_slot(request)
    except SchedulingError:
        raise
    except ValueError as exc:
        raise SchedulingConfigError(str(exc)) from exc
    except Exception as exc:
        raise SchedulingProviderError(f"Scheduling booking failed: {exc}") from exc
