# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
from app.services import scheduling_capability
from app.services.scheduling.models import (
    AvailabilityResult,
    AvailableSlot,
    BookingResult,
    SchedulingPublicConfig,
)


def _snapshot(*, enabled=True, booking_enabled=True, provider="mock", timezone="Europe/Skopje"):
    return SchedulingPublicConfig(
        enabled=enabled,
        provider=provider,
        timezone=timezone,
        slot_duration_minutes=30,
        booking_enabled=booking_enabled,
    )


def _context(**overrides):
    base = {
        "tenant": "milena_dental",
        "session_id": "session-1",
        "session_key": "milena_dental:session-1",
        "message": "test",
        "state": {"stage": "active"},
        "profile": {},
        "services": [],
    }
    base.update(overrides)
    return scheduling_capability.CapabilityContext(**base)


def test_get_capability_snapshot_returns_orchestration_safe_public_state(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    snapshot = scheduling_capability.get_capability_snapshot("milena_dental")

    assert snapshot.to_dict() == {
        "enabled": True,
        "booking_enabled": True,
        "provider": "mock",
        "timezone": "Europe/Skopje",
        "slot_duration_minutes": 30,
    }


def test_assess_scheduling_capability_returns_idle_without_requested_operation(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    assessment = scheduling_capability.assess_scheduling_capability(_context())

    assert assessment.can_handle is False
    assert assessment.status == "idle"
    assert assessment.reason == "no_scheduling_operation_requested"
    assert assessment.capability_state is None
    assert assessment.output_payload is None


def test_assess_availability_request_returns_awaiting_input_state_when_fields_missing(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    assessment = scheduling_capability.assess_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
        )
    )

    assert assessment.can_handle is True
    assert assessment.status == "awaiting_input"
    assert assessment.missing_inputs == ["date_from", "date_to"]
    assert assessment.capability_state["capability"] == "scheduling"
    assert assessment.capability_state["operation"] == scheduling_capability.OPERATION_AVAILABILITY
    assert assessment.output_payload["request"] is None


def test_assess_availability_request_returns_ready_request_payload(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    assessment = scheduling_capability.assess_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            date_from="2026-03-23",
            date_to="2026-03-24",
        )
    )

    assert assessment.can_handle is True
    assert assessment.status == "ready"
    assert assessment.missing_inputs == []
    assert assessment.output_payload["request"] == {
        "tenant": "milena_dental",
        "service_id": "consultation",
        "date_from": "2026-03-23",
        "date_to": "2026-03-24",
        "timezone": "Europe/Skopje",
        "preferred_days": [],
        "preferred_time_range": None,
    }


def test_assess_booking_request_respects_booking_enabled_boundary(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(enabled=True, booking_enabled=False),
    )

    assessment = scheduling_capability.assess_scheduling_capability(
        _context(requested_operation=scheduling_capability.OPERATION_BOOK_SLOT)
    )

    assert assessment.can_handle is False
    assert assessment.status == "disabled"
    assert assessment.reason == "scheduling_booking_disabled"


def test_assess_booking_request_returns_ready_request_payload(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    assessment = scheduling_capability.assess_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_BOOK_SLOT,
            service_id="consultation",
            slot_id="mock|slot-1",
            patient_name="Marjan",
            patient_phone="070000000",
            patient_email="mail@test.mk",
            note="Booked from orchestrator",
        )
    )

    assert assessment.can_handle is True
    assert assessment.status == "ready"
    assert assessment.output_payload["request"] == {
        "tenant": "milena_dental",
        "service_id": "consultation",
        "slot_id": "mock|slot-1",
        "patient_name": "Marjan",
        "patient_phone": "070000000",
        "patient_email": "mail@test.mk",
        "note": "Booked from orchestrator",
    }


def test_handle_scheduling_capability_preserves_runtime_behavior_when_unused(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )
    context = _context(state={"stage": "collecting_contact"})

    result = scheduling_capability.handle_scheduling_capability(context)

    assert result.next_action == scheduling_capability.CAPABILITY_NEXT_CONTINUE
    assert result.state == {"stage": "collecting_contact"}
    assert result.assessment.reason == "no_scheduling_operation_requested"


def test_handle_scheduling_capability_executes_availability_lookup_when_ready(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    def fake_lookup_availability(**kwargs):
        return AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|slot-1",
                    start_at="2026-03-23T09:00:00+01:00",
                    end_at="2026-03-23T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 2026 во 09:00",
                )
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    result = scheduling_capability.handle_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            date_from="2026-03-23",
            date_to="2026-03-24",
            intro_message="Еве неколку слободни термини:",
        )
    )

    assert result.assessment.status == "completed"
    assert result.assessment.reason == "availability_lookup_completed"
    assert result.assessment.output_payload["result"]["provider"] == "mock"
    assert "09:00" in result.assessment.output_payload["reply_text"]


def test_lookup_availability_builds_scheduling_request_and_delegates(monkeypatch):
    captured = {}

    def fake_get_availability(request):
        captured["request"] = request
        return AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|slot-1",
                    start_at="2026-03-23T09:00:00+01:00",
                    end_at="2026-03-23T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 09:00",
                )
            ],
        )

    monkeypatch.setattr(scheduling_capability, "get_availability", fake_get_availability)

    result = scheduling_capability.lookup_availability(
        tenant="milena_dental",
        service_id="consultation",
        date_from="2026-03-23",
        date_to="2026-03-24",
        timezone="Europe/Skopje",
        preferred_days=["monday"],
        preferred_time_range="morning",
    )

    assert result.provider == "mock"
    assert len(result.slots) == 1
    assert captured["request"].tenant == "milena_dental"
    assert captured["request"].service_id == "consultation"
    assert captured["request"].preferred_days == ["monday"]
    assert captured["request"].preferred_time_range == "morning"


def test_book_selected_slot_builds_booking_request_and_delegates(monkeypatch):
    captured = {}

    def fake_book_slot(request):
        captured["request"] = request
        return BookingResult(
            status="confirmed",
            provider="mock",
            booking_id="mock-booking-1",
            start_at="2026-03-23T09:00:00+01:00",
            end_at="2026-03-23T09:30:00+01:00",
            display_label="23 Mar 09:00",
            confirmation_message="Confirmed",
            source_payload={"slot_id": request.slot_id},
        )

    monkeypatch.setattr(scheduling_capability, "book_slot", fake_book_slot)

    result = scheduling_capability.book_selected_slot(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        patient_name="Marjan",
        patient_phone="070000000",
        patient_email="mail@test.mk",
        note="Booked from orchestration bridge",
    )

    assert result.status == "confirmed"
    assert result.provider == "mock"
    assert captured["request"].tenant == "milena_dental"
    assert captured["request"].patient_name == "Marjan"
    assert captured["request"].patient_phone == "070000000"
    assert captured["request"].patient_email == "mail@test.mk"
    assert captured["request"].note == "Booked from orchestration bridge"


def test_book_selected_slot_validates_active_hold_and_consumes_it(monkeypatch):
    captured = {}

    def fake_get_slot_hold(**kwargs):
        captured["hold_lookup"] = kwargs
        return {
            "hold_id": "hold-1",
            "slot_id": "mock|slot-1",
            "session_id": "session-1",
            "status": "active",
        }

    def fake_book_slot(request):
        captured["request"] = request
        return BookingResult(
            status="confirmed",
            provider="mock",
            booking_id="mock-booking-1",
            start_at="2026-03-23T09:00:00+01:00",
            end_at="2026-03-23T09:30:00+01:00",
            display_label="23 Mar 09:00",
            confirmation_message="Confirmed",
            source_payload={"slot_id": request.slot_id},
        )

    def fake_update_hold_status(**kwargs):
        captured["hold_update"] = kwargs
        return {
            "hold_id": "hold-1",
            "status": "consumed",
        }

    monkeypatch.setattr(scheduling_capability, "get_slot_hold", fake_get_slot_hold)
    monkeypatch.setattr(scheduling_capability, "book_slot", fake_book_slot)
    monkeypatch.setattr(scheduling_capability, "update_hold_status", fake_update_hold_status)

    result = scheduling_capability.book_selected_slot(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        patient_name="Marjan",
        patient_phone="070000000",
        patient_email="mail@test.mk",
        note="Booked from orchestration bridge",
        session_id="session-1",
        hold_id="hold-1",
    )

    assert result.status == "confirmed"
    assert captured["hold_lookup"] == {
        "tenant": "milena_dental",
        "slot_id": "mock|slot-1",
        "session_id": "session-1",
        "include_inactive": True,
    }
    assert captured["request"].slot_id == "mock|slot-1"
    assert captured["hold_update"] == {
        "hold_id": "hold-1",
        "status": "consumed",
    }


def test_book_selected_slot_rejects_booking_when_hold_is_missing_or_invalid(monkeypatch):
    monkeypatch.setattr(scheduling_capability, "get_slot_hold", lambda **kwargs: None)

    try:
        scheduling_capability.book_selected_slot(
            tenant="milena_dental",
            service_id="consultation",
            slot_id="mock|slot-1",
            patient_name="Marjan",
            session_id="session-1",
            hold_id="hold-1",
        )
    except scheduling_capability.SchedulingConfigError as exc:
        assert "no longer available" in str(exc)
    else:
        raise AssertionError("Expected active-hold validation to reject booking without a valid hold")


def test_selected_slot_handoff_payload_uses_authoritative_scheduling_state():
    state = {
        "stage": "active",
        "scheduling": {
            "operation": scheduling_capability.OPERATION_AVAILABILITY,
            "status": "completed",
            "reason": "availability_lookup_completed",
            "capability_state": {
                "service_id": "consultation",
            },
            "output_payload": {
                "result": {
                    "provider": "mock",
                    "slots": [
                        {
                            "slot_id": "mock|slot-1",
                            "display_label": "23 Mar 2026 во 09:00",
                        },
                        {
                            "slot_id": "mock|slot-2",
                            "display_label": "23 Mar 2026 во 09:30",
                        },
                    ],
                },
            },
            "booking_handoff_ready": True,
        },
    }

    payload = scheduling_capability.selected_slot_handoff_payload(
        state,
        service_id="consultation",
        slot_id="mock|slot-2",
    )

    assert payload["reason"] == "selected_slot_from_main_chat"
    assert payload["service_id"] == "consultation"
    assert payload["slot_count"] == 2
    assert payload["selected_slot"]["slot_id"] == "mock|slot-2"


def test_selected_slot_handoff_payload_rejects_slot_not_in_active_result():
    state = {
        "scheduling": {
            "capability_state": {
                "service_id": "consultation",
            },
            "output_payload": {
                "result": {
                    "provider": "mock",
                    "slots": [{"slot_id": "mock|slot-1"}],
                },
            },
            "booking_handoff_ready": True,
        },
    }

    try:
        scheduling_capability.selected_slot_handoff_payload(
            state,
            service_id="consultation",
            slot_id="mock|slot-9",
        )
    except ValueError as exc:
        assert "Selected slot is not part of the active availability result" in str(exc)
    else:
        raise AssertionError("Expected selected_slot_handoff_payload to reject an unknown slot_id")
