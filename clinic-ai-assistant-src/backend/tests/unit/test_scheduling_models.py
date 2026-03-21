from app.services.scheduling.models import (
    AvailabilityRequest,
    AvailabilityResult,
    AvailableSlot,
    BookingRequest,
    BookingResult,
    SchedulingPublicConfig,
)


def test_availability_models_serialize_to_stable_dicts():
    request = AvailabilityRequest(
        tenant="milena_dental",
        service_id="consultation",
        date_from="2026-03-23",
        date_to="2026-03-24",
        timezone="Europe/Skopje",
        preferred_days=["monday"],
        preferred_time_range="morning",
    )
    slot = AvailableSlot(
        provider="mock",
        slot_id="mock|2026-03-23T09:00:00|consultation|seed",
        start_at="2026-03-23T09:00:00+01:00",
        end_at="2026-03-23T09:30:00+01:00",
        timezone="Europe/Skopje",
        display_label="23 Mar 2026 во 09:00",
        source_payload={"mock_seed": "seed"},
    )
    result = AvailabilityResult(provider="mock", slots=[slot])

    assert request.to_dict()["tenant"] == "milena_dental"
    assert request.to_dict()["preferred_days"] == ["monday"]
    assert result.to_dict()["provider"] == "mock"
    assert result.to_dict()["slots"][0]["display_label"] == "23 Mar 2026 во 09:00"


def test_booking_models_serialize_to_stable_dicts():
    request = BookingRequest(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|2026-03-23T09:00:00|consultation|seed",
        patient_name="Marjan",
        patient_phone="070000000",
        patient_email="mail@test.mk",
        note="Booked from sandbox",
    )
    result = BookingResult(
        status="confirmed",
        provider="mock",
        booking_id="mock-booking-123",
        start_at="2026-03-23T09:00:00+01:00",
        end_at="2026-03-23T09:30:00+01:00",
        display_label="23 Mar 2026 во 09:00",
        confirmation_message="Терминот е резервиран во mock режим.",
        source_payload={"slot_id": request.slot_id},
    )
    public_config = SchedulingPublicConfig(
        enabled=True,
        provider="mock",
        timezone="Europe/Skopje",
        slot_duration_minutes=30,
        booking_enabled=True,
    )

    assert request.to_dict()["patient_name"] == "Marjan"
    assert result.to_dict()["status"] == "confirmed"
    assert result.to_dict()["source_payload"]["slot_id"] == request.slot_id
    assert public_config.to_dict()["booking_enabled"] is True

