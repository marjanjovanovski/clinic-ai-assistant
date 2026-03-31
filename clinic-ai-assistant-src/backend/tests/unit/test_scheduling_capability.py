# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
from datetime import date

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


def test_resolve_requested_operation_keeps_scheduling_entry_assessment_inside_boundary():
    assert scheduling_capability.resolve_requested_operation(
        allow_scheduling_first=True,
        state={"_availability_intent_pending": True},
    ) == scheduling_capability.OPERATION_AVAILABILITY
    assert scheduling_capability.resolve_requested_operation(
        allow_scheduling_first=True,
        state={"stage": "active"},
        availability_intent_requested=True,
    ) == scheduling_capability.OPERATION_AVAILABILITY
    assert scheduling_capability.resolve_requested_operation(
        allow_scheduling_first=False,
        state={"_availability_intent_pending": True},
        availability_intent_requested=True,
    ) is None


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


def test_execute_scheduling_turn_persists_availability_response_shape(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )
    session_state = {}

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
                    display_label="23 Mar 2026 vo 09:00",
                )
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    execution = scheduling_capability.execute_scheduling_turn(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            date_from="2026-03-23",
            date_to="2026-03-24",
            intro_message="Eve nekolku slobodni termini:",
        ),
        session_state=session_state,
        mark_availability_intent=True,
    )

    assert execution.result.assessment.status == "completed"
    assert execution.response_payload is not None
    assert "09:00" in execution.response_payload.reply_text
    assert execution.response_payload.widget_payload["type"] == "slot-list"
    assert execution.state["scheduling"]["booking_handoff_ready"] is True
    assert scheduling_capability.AVAILABILITY_INTENT_MARKER_KEY not in execution.state
    assert session_state["milena_dental:session-1"]["scheduling"]["status"] == "completed"


def test_availability_default_dates_uses_business_day_reach_window(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 27)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    date_from, date_to = scheduling_capability._availability_default_dates(
        _context(profile={"scheduling": {"default_availability_reach_days": 3}})
    )

    assert date_from == "2026-03-27"
    assert date_to == "2026-03-31"


def test_availability_default_dates_falls_back_to_existing_lookahead_behavior(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 24)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    date_from, date_to = scheduling_capability._availability_default_dates(
        _context(profile={"scheduling": {"lookahead_days": 14}})
    )

    assert date_from == "2026-03-24"
    assert date_to == "2026-03-25"


def test_language_aware_hints_resolve_weekday_and_time_window_from_config(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    context = scheduling_capability._with_availability_defaults(
        _context(
            message="I need Tuesday afternoon availability",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            profile={
                "scheduling": {
                    "language_support": {
                        "weekday_terms": {
                            "tuesday": ["tuesday"],
                        },
                        "time_window_terms": {
                            "afternoon": ["afternoon"],
                        },
                    }
                }
            },
        ),
        _snapshot(),
    )

    assert context.date_from == "2026-03-31"
    assert context.date_to == "2026-03-31"
    assert context.preferred_time_range == "afternoon"


def test_language_aware_hints_resolve_relative_day_from_config(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    context = scheduling_capability._with_availability_defaults(
        _context(
            message="Сакам утре попладне термин",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            profile={
                "scheduling": {
                    "language_support": {
                        "relative_date_terms": {
                            "tomorrow": ["утре"],
                        },
                        "time_window_terms": {
                            "afternoon": ["попладне"],
                        },
                    }
                }
            },
        ),
        _snapshot(),
    )

    assert context.date_from == "2026-03-31"
    assert context.date_to == "2026-03-31"
    assert context.preferred_time_range == "afternoon"


def test_language_aware_hints_resolve_explicit_dotted_date_without_losing_it_to_normalization(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    context = scheduling_capability._with_availability_defaults(
        _context(
            message="check availability on 31.03.2026",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            profile={"scheduling": {"language_support": {}}},
        ),
        _snapshot(),
    )

    assert context.date_from == "2026-03-31"
    assert context.date_to == "2026-03-31"


def test_language_aware_hints_resolve_next_week_range_from_config(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    context = scheduling_capability._with_availability_defaults(
        _context(
            message="check availability next week",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            profile={
                "scheduling": {
                    "language_support": {
                        "relative_range_terms": {
                            "next_week": ["next week"],
                        },
                    }
                }
            },
        ),
        _snapshot(),
    )

    assert context.date_from == "2026-04-06"
    assert context.date_to == "2026-04-12"


def test_language_aware_hints_resolve_two_weeks_from_now_from_config(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)

    context = scheduling_capability._with_availability_defaults(
        _context(
            message="check availability in two weeks",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            profile={
                "scheduling": {
                    "language_support": {
                        "relative_date_terms": {
                            "in_two_weeks": ["in two weeks", "two weeks from now"],
                        },
                    }
                }
            },
        ),
        _snapshot(),
    )

    assert context.date_from == "2026-04-13"
    assert context.date_to == "2026-04-13"


def test_handle_scheduling_capability_filters_slots_by_requested_time_window(monkeypatch):
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
                    slot_id="slot-09",
                    start_at="2026-03-31T09:00:00+02:00",
                    end_at="2026-03-31T09:30:00+02:00",
                    timezone="Europe/Skopje",
                    display_label="31 Mar 2026 vo 09:00",
                ),
                AvailableSlot(
                    provider="mock",
                    slot_id="slot-14",
                    start_at="2026-03-31T14:00:00+02:00",
                    end_at="2026-03-31T14:30:00+02:00",
                    timezone="Europe/Skopje",
                    display_label="31 Mar 2026 vo 14:00",
                ),
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    result = scheduling_capability.handle_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            date_from="2026-03-31",
            date_to="2026-03-31",
            timezone="Europe/Skopje",
            preferred_time_range="afternoon",
        )
    )

    slots = result.assessment.output_payload["result"]["slots"]

    assert result.assessment.status == "completed"
    assert [slot["slot_id"] for slot in slots] == ["slot-14"]


def test_handle_scheduling_capability_preserves_language_derived_time_window(monkeypatch):
    class _FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 3, 30)

    monkeypatch.setattr(scheduling_capability, "date", _FakeDate)
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
                    slot_id="slot-09",
                    start_at="2026-03-31T09:00:00+02:00",
                    end_at="2026-03-31T09:30:00+02:00",
                    timezone="Europe/Skopje",
                    display_label="31 Mar 2026 vo 09:00",
                ),
                AvailableSlot(
                    provider="mock",
                    slot_id="slot-14",
                    start_at="2026-03-31T14:00:00+02:00",
                    end_at="2026-03-31T14:30:00+02:00",
                    timezone="Europe/Skopje",
                    display_label="31 Mar 2026 vo 14:00",
                ),
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    result = scheduling_capability.handle_scheduling_capability(
        _context(
            message="termin utre popladne",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            profile={
                "scheduling": {
                    "language_support": {
                        "relative_date_terms": {
                            "tomorrow": ["utre"],
                        },
                        "time_window_terms": {
                            "afternoon": ["popladne"],
                        },
                    }
                }
            },
        )
    )

    request = result.assessment.output_payload["request"]
    slots = result.assessment.output_payload["result"]["slots"]

    assert request["preferred_time_range"] == "afternoon"
    assert request["date_from"] == "2026-03-31"
    assert [slot["slot_id"] for slot in slots] == ["slot-14"]


def test_execute_scheduling_turn_suppresses_widget_and_booking_handoff_for_specific_day_inline_answers(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )
    session_state = {}

    def fake_lookup_availability(**kwargs):
        return AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|slot-1",
                    start_at="2026-03-31T09:00:00+01:00",
                    end_at="2026-03-31T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="31 Mar 2026 vo 09:00",
                )
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    execution = scheduling_capability.execute_scheduling_turn(
        _context(
            message="check availability on 31.03.2026",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            profile={"scheduling": {"language_support": {}}},
            intro_message="inline-availability",
        ),
        session_state=session_state,
        mark_availability_intent=True,
    )

    assert execution.result.assessment.output_payload["presentation"]["request_kind"] == "specific_day"
    assert execution.response_payload is not None
    assert execution.response_payload.widget_payload is None
    assert execution.state["scheduling"]["booking_handoff_ready"] is False


def test_handle_scheduling_capability_uses_config_owned_broad_range_narrowing_text(monkeypatch):
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
                    start_at="2026-04-06T09:00:00+01:00",
                    end_at="2026-04-06T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="06 Apr 2026 vo 09:00",
                )
            ],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    result = scheduling_capability.handle_scheduling_capability(
        _context(
            message="check availability next week",
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            profile={
                "scheduling": {
                    "language_support": {
                        "relative_range_terms": {
                            "next_week": ["next week"],
                        },
                    },
                    "contract_texts": {
                        "broad_range_narrowing": "Custom narrowing reply",
                    },
                }
            },
        )
    )

    assert result.assessment.status == "completed"
    assert result.assessment.output_payload["presentation"]["request_kind"] == "broad_range"
    assert result.assessment.output_payload["reply_text"] == "Custom narrowing reply"


def test_handle_scheduling_capability_returns_explicit_no_availability_message_when_slots_are_empty(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_scheduling_public_config",
        lambda tenant: _snapshot(),
    )

    def fake_lookup_availability(**kwargs):
        return AvailabilityResult(
            provider="mock",
            slots=[],
        )

    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)

    result = scheduling_capability.handle_scheduling_capability(
        _context(
            requested_operation=scheduling_capability.OPERATION_AVAILABILITY,
            service_id="consultation",
            date_from="2026-03-27",
            date_to="2026-03-28",
            intro_message="Za da proveram slobodni termini...",
        )
    )

    assert result.assessment.status == "completed"
    assert result.assessment.reason == "availability_lookup_completed"
    assert result.assessment.output_payload["result"]["slots"] == []
    assert result.assessment.output_payload["reply_text"] == scheduling_capability.NO_AVAILABILITY_MESSAGE


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
    trace_events = []
    monkeypatch.setattr(scheduling_capability, "get_slot_hold", lambda **kwargs: None)
    monkeypatch.setattr(
        scheduling_capability,
        "trace_event",
        lambda tenant, session_id, event, **fields: trace_events.append(
            {"tenant": tenant, "session_id": session_id, "event": event, "fields": fields}
        ),
    )

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
        assert any(item["event"] == "SCHEDULING_BOOKING_MISMATCH" for item in trace_events)
        assert any(item["event"] == "SCHEDULING_SLOT_CONFLICT" for item in trace_events)
    else:
        raise AssertionError("Expected active-hold validation to reject booking without a valid hold")


def test_book_selected_slot_returns_same_day_replacements_in_slot_conflict(monkeypatch):
    monkeypatch.setattr(
        scheduling_capability,
        "get_slot_hold",
        lambda **kwargs: {
            "hold_id": "hold-1",
            "slot_id": kwargs["slot_id"],
            "session_id": "session-1",
            "status": "expired",
        },
    )
    monkeypatch.setattr(
        scheduling_capability,
        "lookup_availability",
        lambda **kwargs: AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|2026-03-23T09:30:00|consultation|mock-provider",
                    start_at="2026-03-23T09:30:00+01:00",
                    end_at="2026-03-23T10:00:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 2026 во 09:30",
                ),
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|2026-03-23T10:00:00|consultation|mock-provider",
                    start_at="2026-03-23T10:00:00+01:00",
                    end_at="2026-03-23T10:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 2026 во 10:00",
                ),
            ],
        ),
    )

    try:
        scheduling_capability.book_selected_slot(
            tenant="milena_dental",
            service_id="consultation",
            slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
            patient_name="Marjan",
            session_id="session-1",
            hold_id="hold-1",
            selected_slot={
                "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
                "start_at": "2026-03-23T09:00:00+01:00",
                "end_at": "2026-03-23T09:30:00+01:00",
                "timezone": "Europe/Skopje",
                "display_label": "23 Mar 2026 во 09:00",
            },
        )
    except scheduling_capability.SchedulingSlotConflictError as exc:
        payload = exc.to_booking_result_payload(
            slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider"
        )
        assert payload["status"] == "slot_unavailable"
        assert payload["source_payload"]["next_action"] == "refresh_availability"
        assert payload["source_payload"]["fallback_scope"] == "same_day"
        assert payload["source_payload"]["fallback_date"] == "2026-03-23"
        assert len(payload["source_payload"]["replacement_slots"]) == 2
        assert payload["source_payload"]["replacement_slots"][0]["slot_id"].endswith("09:30:00|consultation|mock-provider")
    else:
        raise AssertionError("Expected a structured slot conflict with same-day replacements")


def test_book_selected_slot_silently_recovers_expired_hold_when_slot_is_still_available(monkeypatch):
    captured = {}

    def fake_get_slot_hold(**kwargs):
        captured["hold_lookup"] = kwargs
        return {
            "hold_id": "hold-1",
            "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
            "session_id": "session-1",
            "status": "expired",
        }

    def fake_lookup_availability(**kwargs):
        captured["availability_lookup"] = kwargs
        return AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
                    start_at="2026-03-23T09:00:00+01:00",
                    end_at="2026-03-23T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 2026 во 09:00",
                )
            ],
        )

    def fake_create_slot_hold(**kwargs):
        captured["hold_create"] = kwargs
        return {
            "hold_id": "hold-2",
            "slot_id": kwargs["slot_id"],
            "session_id": kwargs["session_id"],
            "status": "active",
        }

    def fake_book_slot(request):
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
        return {"hold_id": kwargs["hold_id"], "status": "consumed"}

    monkeypatch.setattr(scheduling_capability, "get_slot_hold", fake_get_slot_hold)
    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)
    monkeypatch.setattr(scheduling_capability, "create_slot_hold", fake_create_slot_hold)
    monkeypatch.setattr(scheduling_capability, "book_slot", fake_book_slot)
    monkeypatch.setattr(scheduling_capability, "update_hold_status", fake_update_hold_status)

    result = scheduling_capability.book_selected_slot(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
        patient_name="Marjan",
        session_id="session-1",
        hold_id="hold-1",
        selected_slot={
            "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
            "start_at": "2026-03-23T09:00:00+01:00",
            "timezone": "Europe/Skopje",
        },
    )

    assert result.status == "confirmed"
    assert captured["availability_lookup"]["date_from"] == "2026-03-23"
    assert captured["availability_lookup"]["date_to"] == "2026-03-23"
    assert captured["hold_create"]["session_id"] == "session-1"
    assert result.source_payload["recovery_applied"] is True
    assert captured["hold_update"] == {
        "hold_id": "hold-1",
        "status": "consumed",
    }


def test_book_selected_slot_rejects_when_expired_hold_recheck_fails(monkeypatch):
    captured = []
    monkeypatch.setattr(
        scheduling_capability,
        "get_slot_hold",
        lambda **kwargs: {
            "hold_id": "hold-1",
            "slot_id": kwargs["slot_id"],
            "session_id": "session-1",
            "status": "expired",
        },
    )
    monkeypatch.setattr(
        scheduling_capability,
        "lookup_availability",
        lambda **kwargs: AvailabilityResult(provider="mock", slots=[]),
    )
    monkeypatch.setattr(
        scheduling_capability,
        "trace_event",
        lambda tenant, session_id, event, **fields: captured.append(
            {"tenant": tenant, "session_id": session_id, "event": event, "fields": fields}
        ),
    )

    try:
        scheduling_capability.book_selected_slot(
            tenant="milena_dental",
            service_id="consultation",
            slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
            patient_name="Marjan",
            session_id="session-1",
            hold_id="hold-1",
            selected_slot={
                "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
                "start_at": "2026-03-23T09:00:00+01:00",
                "timezone": "Europe/Skopje",
            },
        )
    except scheduling_capability.SchedulingConfigError as exc:
        assert "no longer available" in str(exc)
        assert any(item["event"] == "SCHEDULING_SLOT_CONFLICT" for item in captured)
    else:
        raise AssertionError("Expected expired-hold recheck failure to reject booking")


def test_book_selected_slot_traces_recovery_refresh_and_confirmation(monkeypatch):
    captured = {}
    trace_events = []

    def fake_get_slot_hold(**kwargs):
        return {
            "hold_id": "hold-1",
            "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
            "session_id": "session-1",
            "status": "expired",
        }

    def fake_lookup_availability(**kwargs):
        return AvailabilityResult(
            provider="mock",
            slots=[
                AvailableSlot(
                    provider="mock",
                    slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
                    start_at="2026-03-23T09:00:00+01:00",
                    end_at="2026-03-23T09:30:00+01:00",
                    timezone="Europe/Skopje",
                    display_label="23 Mar 2026 во 09:00",
                )
            ],
        )

    def fake_create_slot_hold(**kwargs):
        return {
            "hold_id": "hold-2",
            "slot_id": kwargs["slot_id"],
            "session_id": kwargs["session_id"],
            "status": "active",
        }

    def fake_book_slot(request):
        captured["slot_id"] = request.slot_id
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

    monkeypatch.setattr(scheduling_capability, "get_slot_hold", fake_get_slot_hold)
    monkeypatch.setattr(scheduling_capability, "lookup_availability", fake_lookup_availability)
    monkeypatch.setattr(scheduling_capability, "create_slot_hold", fake_create_slot_hold)
    monkeypatch.setattr(scheduling_capability, "book_slot", fake_book_slot)
    monkeypatch.setattr(scheduling_capability, "update_hold_status", lambda **kwargs: {"hold_id": kwargs["hold_id"]})
    monkeypatch.setattr(
        scheduling_capability,
        "trace_event",
        lambda tenant, session_id, event, **fields: trace_events.append(
            {"tenant": tenant, "session_id": session_id, "event": event, "fields": fields}
        ),
    )

    scheduling_capability.book_selected_slot(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|2026-03-23T09:00:00|consultation|mock-provider",
        patient_name="Marjan",
        session_id="session-1",
        hold_id="hold-1",
        selected_slot={
            "slot_id": "mock|2026-03-23T09:00:00|consultation|mock-provider",
            "start_at": "2026-03-23T09:00:00+01:00",
            "timezone": "Europe/Skopje",
        },
    )

    event_names = [item["event"] for item in trace_events]
    assert "SCHEDULING_HOLD_REFRESHED" in event_names
    assert "SCHEDULING_BOOKING_CONFIRMED" in event_names


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


def test_handoff_response_payload_preserves_selected_slot_and_hold_for_contact_collection():
    response_payload = scheduling_capability.handoff_response_payload(
        {
            "selected_slot": {"slot_id": "mock|slot-2"},
            "hold": {"hold_id": "hold-1"},
        },
        fallback_service_id="consultation",
        next_action="collect_contact",
    )

    assert response_payload == {
        "selected_slot": {"slot_id": "mock|slot-2"},
        "hold": {"hold_id": "hold-1"},
        "widget_payload": None,
        "next_action": "collect_contact",
    }


def test_handoff_response_payload_reuses_conflict_widget_and_refresh_action():
    response_payload = scheduling_capability.handoff_response_payload(
        {
            "selected_slot": {"slot_id": "mock|slot-1"},
            "hold": {"hold_id": "hold-1"},
        },
        booking_result={
            "status": "slot_unavailable",
            "provider": "mock",
            "confirmation_message": "The selected slot is no longer available.",
            "source_payload": {
                "service_id": "consultation",
                "fallback_date": "2026-03-23",
                "selected_slot": {
                    "slot_id": "mock|slot-1",
                    "timezone": "Europe/Skopje",
                },
                "replacement_slots": [
                    {"slot_id": "mock|slot-2"},
                    {"slot_id": "mock|slot-3"},
                ],
            },
        },
        fallback_service_id="consultation",
        next_action="booking_completed",
    )

    assert response_payload["selected_slot"]["slot_id"] == "mock|slot-1"
    assert response_payload["hold"]["hold_id"] == "hold-1"
    assert response_payload["next_action"] == "refresh_availability"
    assert response_payload["widget_payload"]["type"] == "slot-list"
    assert len(response_payload["widget_payload"]["slots"]) == 2
