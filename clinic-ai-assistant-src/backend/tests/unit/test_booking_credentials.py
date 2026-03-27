# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
from app.services import booking_credentials


def test_appointment_summary_projection_uses_selected_slot_before_calendar_booking():
    state = {
        "stage": "completed",
        "scheduling_handoff": {
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
            }
        },
    }

    appointment_display, appointment_status, appointment_source, subtitle = (
        booking_credentials._appointment_summary_projection(state)
    )

    assert appointment_display == "26 Mar 2026 во 16:00"
    assert appointment_status == "Привремен термин"
    assert appointment_source == "selected_slot"
    assert subtitle == "Подготвено за идно поврзување со календар и реален термин."


def test_appointment_summary_projection_prefers_confirmed_booking_result():
    state = {
        "stage": "completed",
        "scheduling_handoff": {
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
            }
        },
        "booking_result": {
            "booking_id": "mock-booking-1",
            "display_label": "26 Mar 2026 во 16:00",
            "confirmation_message": "Терминот е резервиран во mock режим.",
        },
    }

    appointment_display, appointment_status, appointment_source, subtitle = (
        booking_credentials._appointment_summary_projection(state)
    )

    assert appointment_display == "26 Mar 2026 во 16:00"
    assert appointment_status == "Потврден термин"
    assert appointment_source == "calendar_booking"
    assert subtitle == "Терминот е резервиран во mock режим."


def test_appointment_summary_projection_clears_stale_slot_display_when_booking_conflicts():
    state = {
        "stage": "completed",
        "scheduling_handoff": {
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
            }
        },
        "booking_result": {
            "status": "slot_unavailable",
            "booking_id": "",
            "display_label": "",
            "confirmation_message": "The selected slot is no longer available. I will show you other available slots for the same day.",
        },
    }

    appointment_display, appointment_status, appointment_source, subtitle = (
        booking_credentials._appointment_summary_projection(state)
    )

    assert appointment_display == ""
    assert appointment_status == "Терминот не е достапен"
    assert appointment_source is None
    assert "no longer available" in subtitle


def test_complete_selected_slot_booking_if_ready_returns_none_without_selected_slot():
    result = booking_credentials._complete_selected_slot_booking_if_ready(
        tenant="milena_dental",
        state={"stage": "completed"},
        data={"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    )

    assert result is None


def test_complete_selected_slot_booking_if_ready_books_once_and_stores_payload(monkeypatch):
    captured = {}

    class FakeBookingResult:
        def to_dict(self):
            return {
                "status": "confirmed",
                "provider": "mock",
                "booking_id": "mock-booking-1",
                "display_label": "26 Mar 2026 во 16:00",
                "confirmation_message": "Терминот е резервиран во mock режим.",
            }

    def fake_book_selected_slot(**kwargs):
        captured.update(kwargs)
        return FakeBookingResult()

    monkeypatch.setattr(
        "app.services.scheduling_capability.book_selected_slot",
        fake_book_selected_slot,
    )

    state = {
        "stage": "completed",
        "service_id": "consultation",
        "scheduling_handoff": {
            "service_id": "consultation",
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
            },
        },
    }

    result = booking_credentials._complete_selected_slot_booking_if_ready(
        tenant="milena_dental",
        state=state,
        data={"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    )

    assert result["booking_id"] == "mock-booking-1"
    assert state["booking_result"]["booking_id"] == "mock-booking-1"
    assert captured == {
        "tenant": "milena_dental",
        "service_id": "consultation",
        "slot_id": "mock|slot-1",
        "patient_name": "Marjan",
        "patient_phone": "070000000",
        "patient_email": "mail@test.mk",
        "note": "Booked from main chat scheduling flow",
        "session_id": None,
        "hold_id": None,
        "selected_slot": {
            "slot_id": "mock|slot-1",
            "display_label": "26 Mar 2026 во 16:00",
        },
    }


def test_complete_selected_slot_booking_if_ready_passes_hold_identity_and_returns_conflict_payload(monkeypatch):
    from app.services.scheduling_capability import SchedulingSlotConflictError

    def fake_book_selected_slot(**kwargs):
        assert kwargs["session_id"] == "session-1"
        assert kwargs["hold_id"] == "hold-1"
        raise SchedulingSlotConflictError(
            "The selected slot is no longer available. I will show you other available slots for the same day.",
            service_id="consultation",
            selected_slot=kwargs["selected_slot"],
            fallback_date="2026-03-26",
            replacement_slots=[
                {
                    "slot_id": "mock|slot-2",
                    "display_label": "26 Mar 2026 во 16:30",
                    "start_at": "2026-03-26T16:30:00+01:00",
                    "end_at": "2026-03-26T17:00:00+01:00",
                    "timezone": "Europe/Skopje",
                }
            ],
        )

    monkeypatch.setattr(
        "app.services.scheduling_capability.book_selected_slot",
        fake_book_selected_slot,
    )

    state = {
        "stage": "completed",
        "service_id": "consultation",
        "scheduling_handoff": {
            "service_id": "consultation",
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
                "start_at": "2026-03-26T16:00:00+01:00",
                "end_at": "2026-03-26T16:30:00+01:00",
            },
            "hold": {
                "hold_id": "hold-1",
                "session_id": "session-1",
            },
        },
    }

    result = booking_credentials._complete_selected_slot_booking_if_ready(
        tenant="milena_dental",
        state=state,
        data={"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    )

    assert result["status"] == "slot_unavailable"
    assert result["provider"] == "scheduling"
    assert result["booking_id"] == ""
    assert "no longer available" in result["confirmation_message"]
    assert result["source_payload"]["reason"] == "slot_conflict"
    assert result["source_payload"]["next_action"] == "refresh_availability"
    assert result["source_payload"]["fallback_scope"] == "same_day"
    assert result["source_payload"]["fallback_date"] == "2026-03-26"
    assert result["source_payload"]["service_id"] == "consultation"
    assert result["source_payload"]["selected_slot"]["slot_id"] == "mock|slot-1"
    assert result["source_payload"]["replacement_slots"][0]["slot_id"] == "mock|slot-2"


def test_complete_selected_slot_booking_if_ready_preserves_recovery_success_payload(monkeypatch):
    class FakeBookingResult:
        def to_dict(self):
            return {
                "status": "confirmed",
                "provider": "mock",
                "booking_id": "mock-booking-1",
                "display_label": "26 Mar 2026 во 16:00",
                "confirmation_message": "Терминот е резервиран во mock режим.",
                "source_payload": {
                    "slot_id": "mock|slot-1",
                    "recovery_applied": True,
                },
            }

    monkeypatch.setattr(
        "app.services.scheduling_capability.book_selected_slot",
        lambda **kwargs: FakeBookingResult(),
    )

    state = {
        "stage": "completed",
        "service_id": "consultation",
        "scheduling_handoff": {
            "service_id": "consultation",
            "selected_slot": {
                "slot_id": "mock|slot-1",
                "display_label": "26 Mar 2026 во 16:00",
                "start_at": "2026-03-26T16:00:00+01:00",
                "end_at": "2026-03-26T16:30:00+01:00",
                "timezone": "Europe/Skopje",
            },
            "hold": {
                "hold_id": "hold-1",
                "session_id": "session-1",
            },
        },
    }

    result = booking_credentials._complete_selected_slot_booking_if_ready(
        tenant="milena_dental",
        state=state,
        data={"name": "Marjan", "phone": "070000000", "email": "mail@test.mk"},
    )

    assert result["status"] == "confirmed"
    assert result["source_payload"]["recovery_applied"] is True
    assert state["booking_result"]["source_payload"]["recovery_applied"] is True
