import pytest
# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
from app.services.scheduling.factory import build_provider
from app.services.scheduling.models import AvailabilityRequest, BookingRequest
from app.services.scheduling.providers.google_calendar import GoogleCalendarSchedulingProvider


class _FakeEventsResource:
    def __init__(self, items):
        self._items = items
        self.insert_body = None
        self.insert_send_updates = None
        self.insert_calendar_id = None

    def list(self, **kwargs):
        self._kwargs = kwargs
        return self

    def insert(self, *, calendarId, body, sendUpdates):
        self.insert_calendar_id = calendarId
        self.insert_body = body
        self.insert_send_updates = sendUpdates
        return self

    def execute(self):
        if self.insert_body is not None:
            return {
                "id": "google-event-123",
                "status": "confirmed",
                "htmlLink": "https://calendar.google.test/event",
                "start": self.insert_body["start"],
                "end": self.insert_body["end"],
            }
        return {"items": self._items}


class _FakeCalendarService:
    def __init__(self, items):
        self._items = items

    def events(self):
        return _FakeEventsResource(self._items)


def test_factory_builds_google_calendar_provider():
    provider = build_provider(
        "google_calendar",
        {
            "calendar_id": "primary",
            "credentials": {
                "auth_type": "service_account",
                "service_account_file": "backend/app/config/secrets/google-service-account.json",
            },
        },
    )

    assert isinstance(provider, GoogleCalendarSchedulingProvider)


def test_google_provider_returns_open_slots_around_busy_events(monkeypatch):
    target_date = "2026-04-20"
    provider = GoogleCalendarSchedulingProvider(
        {
            "calendar_id": "primary",
            "slot_duration_minutes": 30,
            "slot_interval_minutes": 30,
            "minimum_notice_minutes": 0,
            "business_hours": {
                "monday": [["09:00", "12:00"]],
            },
            "credentials": {
                "auth_type": "service_account",
                "service_account_file": "backend/app/config/secrets/google-service-account.json",
            },
        }
    )

    monkeypatch.setattr(
        provider,
        "_calendar_service",
        lambda: _FakeCalendarService(
            [
                {
                    "start": {"dateTime": f"{target_date}T10:00:00+01:00"},
                    "end": {"dateTime": f"{target_date}T10:30:00+01:00"},
                }
            ]
        ),
    )

    result = provider.get_availability(
        AvailabilityRequest(
            tenant="milena_dental",
            service_id="consultation",
            date_from=target_date,
            date_to=target_date,
            timezone="Europe/Skopje",
        )
    )

    slot_starts = [slot["start_at"] for slot in result.to_dict()["slots"]]
    assert f"{target_date}T10:00:00+01:00" not in slot_starts
    assert f"{target_date}T09:00:00+01:00" in slot_starts
    assert f"{target_date}T11:00:00+01:00" in slot_starts


def test_google_provider_books_selected_slot_and_normalizes_result(monkeypatch):
    provider = GoogleCalendarSchedulingProvider(
        {
            "calendar_id": "primary",
            "timezone": "Europe/Skopje",
            "business_name": "Milena Dental",
            "credentials": {
                "auth_type": "service_account",
                "service_account_file": "backend/app/config/secrets/google-service-account.json",
            },
        }
    )
    fake_service = _FakeCalendarService([])
    monkeypatch.setattr(provider, "_calendar_service", lambda: fake_service)

    result = provider.book_slot(
        BookingRequest(
            tenant="milena_dental",
            service_id="consultation",
            slot_id="google|2026-03-23T09:00:00+01:00|2026-03-23T09:30:00+01:00|primary",
            patient_name="Marjan",
            patient_phone="070000000",
            patient_email="mail@test.mk",
            note="Booked from sandbox",
        )
    )

    payload = result.to_dict()
    assert payload["status"] == "confirmed"
    assert payload["provider"] == "google_calendar"
    assert payload["booking_id"] == "google-event-123"
    assert payload["source_payload"]["html_link"] == "https://calendar.google.test/event"


def test_google_provider_rejects_slot_from_other_calendar():
    provider = GoogleCalendarSchedulingProvider(
        {
            "calendar_id": "primary",
            "credentials": {
                "auth_type": "service_account",
                "service_account_file": "backend/app/config/secrets/google-service-account.json",
            },
        }
    )

    try:
        provider.book_slot(
            BookingRequest(
                tenant="milena_dental",
                service_id="consultation",
                slot_id="google|2026-03-23T09:00:00+01:00|2026-03-23T09:30:00+01:00|other-calendar",
                patient_name="Marjan",
            )
        )
    except ValueError as exc:
        assert "does not match configured calendar_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError for mismatched calendar id")


def test_google_provider_resolves_backend_prefixed_relative_credentials_path():
    resolved = GoogleCalendarSchedulingProvider._service_account_path(
        "backend/app/config/secrets/google-service-account.json"
    )

    assert resolved.as_posix().endswith("backend/app/config/secrets/google-service-account.json")

def test_google_provider_rejects_unknown_timezone_without_local_fallback():
    with pytest.raises(ValueError, match="Unsupported timezone without local tzdata: Mars/Olympus"):
        GoogleCalendarSchedulingProvider._timezone_for_name("Mars/Olympus")
