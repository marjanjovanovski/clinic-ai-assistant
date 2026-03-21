from app.services.scheduling.factory import build_provider
from app.services.scheduling.models import AvailabilityRequest
from app.services.scheduling.providers.mock_provider import MockSchedulingProvider
from app.services.scheduling.service import (
    SchedulingConfigError,
    SchedulingDisabledError,
    get_availability,
)


def test_factory_builds_mock_provider():
    provider = build_provider("mock", {"seed": "tenant-seed"})

    assert isinstance(provider, MockSchedulingProvider)
    assert provider.healthcheck()["status"] == "ok"
    assert provider.healthcheck()["seed"] == "tenant-seed"


def test_factory_rejects_unknown_provider():
    try:
        build_provider("unsupported_provider", {})
    except ValueError as exc:
        assert "Unsupported scheduling provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unsupported provider")


def test_service_rejects_reversed_dates_before_provider_lookup():
    try:
        get_availability(
            AvailabilityRequest(
                tenant="milena_dental",
                service_id="consultation",
                date_from="2026-03-24",
                date_to="2026-03-23",
                timezone="Europe/Skopje",
            )
        )
    except SchedulingConfigError as exc:
        assert "date_from must be on or before date_to" in str(exc)
    else:
        raise AssertionError("Expected SchedulingConfigError for reversed dates")


def test_service_rejects_disabled_tenant_scheduling():
    try:
        get_availability(
            AvailabilityRequest(
                tenant="generic",
                service_id="consultation",
                date_from="2026-03-23",
                date_to="2026-03-24",
                timezone="Europe/Skopje",
            )
        )
    except SchedulingDisabledError as exc:
        assert "Scheduling is disabled" in str(exc)
    else:
        raise AssertionError("Expected SchedulingDisabledError for disabled scheduling")
