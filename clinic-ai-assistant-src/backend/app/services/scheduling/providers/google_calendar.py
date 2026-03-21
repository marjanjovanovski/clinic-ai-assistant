"""Google Calendar scheduling provider."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.scheduling.base import SchedulingProvider
from app.services.scheduling.models import (
    AvailabilityRequest,
    AvailabilityResult,
    AvailableSlot,
    BookingRequest,
    BookingResult,
)


class GoogleCalendarSchedulingProvider(SchedulingProvider):
    provider_name = "google_calendar"
    _CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
    _TIMEZONE_FALLBACKS = {
        "Europe/Skopje": timezone(timedelta(hours=1)),
        "UTC": timezone.utc,
    }

    def get_availability(self, request: AvailabilityRequest) -> AvailabilityResult:
        calendar_service = self._calendar_service()
        calendar_id = self._calendar_id()
        timezone_name = request.timezone or self.config.get("timezone") or "UTC"
        tz = self._timezone_for_name(timezone_name)

        start_date = datetime.fromisoformat(request.date_from).date()
        end_date = datetime.fromisoformat(request.date_to).date()
        slot_minutes = int(self.config.get("slot_duration_minutes") or 30)
        interval_minutes = int(self.config.get("slot_interval_minutes") or slot_minutes)
        minimum_notice_minutes = int(self.config.get("minimum_notice_minutes") or 0)
        business_hours = self.config.get("business_hours") or {}

        window_start = datetime.combine(start_date, time.min, tzinfo=tz)
        window_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
        busy_ranges = self._busy_ranges(
            calendar_service=calendar_service,
            calendar_id=calendar_id,
            time_min=window_start,
            time_max=window_end,
            timezone_name=timezone_name,
        )

        notice_cutoff = datetime.now(tz) + timedelta(minutes=minimum_notice_minutes)
        slots: list[AvailableSlot] = []
        current_date = start_date
        while current_date <= end_date:
            weekday_name = current_date.strftime("%A").lower()
            day_ranges = business_hours.get(weekday_name, [])
            for start_text, end_text in day_ranges:
                range_start = self._combine_day_and_time(current_date, start_text, tz)
                range_end = self._combine_day_and_time(current_date, end_text, tz)
                cursor = range_start
                while cursor + timedelta(minutes=slot_minutes) <= range_end:
                    slot_end = cursor + timedelta(minutes=slot_minutes)
                    if cursor >= notice_cutoff and not self._overlaps_busy(cursor, slot_end, busy_ranges):
                        slots.append(
                            AvailableSlot(
                                provider=self.provider_name,
                                slot_id=f"google|{cursor.isoformat()}|{slot_end.isoformat()}|{calendar_id}",
                                start_at=cursor.isoformat(),
                                end_at=slot_end.isoformat(),
                                timezone=timezone_name,
                                display_label=cursor.strftime("%d %b %Y во %H:%M"),
                                source_payload={
                                    "calendar_id": calendar_id,
                                },
                            )
                        )
                    cursor += timedelta(minutes=interval_minutes)
            current_date += timedelta(days=1)

        return AvailabilityResult(provider=self.provider_name, slots=slots)

    def book_slot(self, request: BookingRequest) -> BookingResult:
        calendar_id = self._calendar_id()
        start_at, end_at, slot_calendar_id = self._parse_slot_id(request.slot_id)
        if slot_calendar_id != calendar_id:
            raise ValueError("Selected Google Calendar slot does not match configured calendar_id")
        calendar_service = self._calendar_service()

        event_payload = self._booking_event_payload(
            request=request,
            start_at=start_at,
            end_at=end_at,
            calendar_id=calendar_id,
        )
        response = (
            calendar_service.events()
            .insert(
                calendarId=calendar_id,
                body=event_payload,
                sendUpdates="none",
            )
            .execute()
        )

        confirmed_start = (response.get("start") or {}).get("dateTime") or start_at
        confirmed_end = (response.get("end") or {}).get("dateTime") or end_at
        booking_id = response.get("id") or "google-calendar-booking"
        start_dt = datetime.fromisoformat(confirmed_start)
        return BookingResult(
            status="confirmed",
            provider=self.provider_name,
            booking_id=booking_id,
            start_at=confirmed_start,
            end_at=confirmed_end,
            display_label=start_dt.strftime("%d %b %Y во %H:%M"),
            confirmation_message="Терминот е резервиран во Google Calendar.",
            source_payload={
                "calendar_id": calendar_id,
                "html_link": response.get("htmlLink"),
                "event_status": response.get("status"),
            },
        )

    def healthcheck(self) -> dict:
        return {
            "provider": self.provider_name,
            "status": "configured" if self._calendar_id() else "missing_calendar_id",
        }

    def _calendar_id(self) -> str:
        calendar_id = self.config.get("calendar_id")
        if not isinstance(calendar_id, str) or not calendar_id.strip():
            raise ValueError("Google Calendar provider requires a calendar_id")
        return calendar_id.strip()

    def _calendar_service(self):
        credentials = self._credentials()
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise ValueError(
                "Google Calendar dependencies are not installed. Add google-api-python-client and google-auth."
            ) from exc
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def _credentials(self):
        credentials_config = self.config.get("credentials") or {}
        auth_type = credentials_config.get("auth_type")
        if auth_type != "service_account":
            raise ValueError("Google Calendar currently supports only service_account auth_type")

        service_account_file = credentials_config.get("service_account_file")
        if not isinstance(service_account_file, str) or not service_account_file.strip():
            raise ValueError("Google Calendar service_account_file is required")

        secrets_path = self._service_account_path(service_account_file)
        if not secrets_path.exists():
            raise ValueError(f"Google Calendar service account file was not found: {secrets_path}")

        try:
            from google.oauth2.service_account import Credentials
        except ImportError as exc:
            raise ValueError(
                "Google auth dependencies are not installed. Add google-api-python-client and google-auth."
            ) from exc

        return Credentials.from_service_account_file(
            str(secrets_path),
            scopes=[self._CALENDAR_SCOPE],
        )

    @classmethod
    def _service_account_path(cls, service_account_file: str) -> Path:
        raw_path = Path(service_account_file)
        if raw_path.is_absolute():
            return raw_path

        backend_root = Path(__file__).resolve().parents[4]
        project_root = backend_root.parent
        candidates = [backend_root / raw_path, project_root / raw_path]

        if raw_path.parts and raw_path.parts[0] == "backend":
            candidates.append(backend_root / Path(*raw_path.parts[1:]))

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return candidates[-1]

    def _busy_ranges(self, *, calendar_service, calendar_id: str, time_min: datetime, time_max: datetime, timezone_name: str):
        response = (
            calendar_service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                timeZone=timezone_name,
            )
            .execute()
        )
        busy_ranges: list[tuple[datetime, datetime]] = []
        for item in response.get("items", []):
            start_payload = item.get("start") or {}
            end_payload = item.get("end") or {}
            start_raw = start_payload.get("dateTime")
            end_raw = end_payload.get("dateTime")
            if not start_raw or not end_raw:
                continue
            busy_ranges.append(
                (
                    datetime.fromisoformat(start_raw),
                    datetime.fromisoformat(end_raw),
                )
            )
        return busy_ranges

    @staticmethod
    def _combine_day_and_time(day_value, time_text: str, tz: ZoneInfo) -> datetime:
        hour_text, minute_text = time_text.split(":", 1)
        return datetime.combine(
            day_value,
            time(int(hour_text), int(minute_text)),
            tzinfo=tz,
        )

    @classmethod
    def _timezone_for_name(cls, timezone_name: str):
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            fallback = cls._TIMEZONE_FALLBACKS.get(timezone_name)
            if fallback is None:
                raise ValueError(f"Unsupported timezone without local tzdata: {timezone_name}")
            return fallback

    @staticmethod
    def _overlaps_busy(slot_start: datetime, slot_end: datetime, busy_ranges: list[tuple[datetime, datetime]]) -> bool:
        for busy_start, busy_end in busy_ranges:
            if slot_start < busy_end and slot_end > busy_start:
                return True
        return False

    @staticmethod
    def _parse_slot_id(slot_id: str) -> tuple[str, str, str]:
        try:
            provider_name, start_at, end_at, calendar_id = slot_id.split("|", 3)
        except ValueError as exc:
            raise ValueError("Invalid Google Calendar slot_id format") from exc
        if provider_name != "google":
            raise ValueError("Invalid Google Calendar slot_id provider prefix")
        return start_at, end_at, calendar_id

    def _booking_event_payload(self, *, request: BookingRequest, start_at: str, end_at: str, calendar_id: str) -> dict:
        timezone_name = self.config.get("timezone") or "UTC"
        business_name = self.config.get("business_name") or "Clinic appointment"
        event_payload = {
            "summary": f"{business_name}: {request.service_id}",
            "description": self._booking_description(request, calendar_id),
            "start": {
                "dateTime": start_at,
                "timeZone": timezone_name,
            },
            "end": {
                "dateTime": end_at,
                "timeZone": timezone_name,
            },
        }
        return event_payload

    @staticmethod
    def _booking_description(request: BookingRequest, calendar_id: str) -> str:
        lines = [
            "Clinic AI Assistant booking",
            f"Calendar: {calendar_id}",
            f"Service: {request.service_id}",
            f"Patient: {request.patient_name}",
        ]
        if request.patient_phone:
            lines.append(f"Phone: {request.patient_phone}")
        if request.patient_email:
            lines.append(f"Email: {request.patient_email}")
        if request.note:
            lines.append(f"Note: {request.note}")
        return "\n".join(lines)
