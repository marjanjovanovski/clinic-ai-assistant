# Clinic AI Assistant

## Implemented

- FastAPI backend with `/chat`, `/config/{tenant}`, `/agent/{tenant}`, and `/health`
- Isolated scheduling backend with `/scheduling/config/{tenant}`, `/scheduling/availability`, and `/scheduling/book`
- OpenAI-powered response generation through `client.responses.create(...)`
- JSON tenant profiles loaded from `clinic-ai-assistant-src/backend/app/config/profiles/`
- Lightweight HTML/JS frontend served by the backend
- Isolated scheduling sandbox served from `clinic-ai-assistant-src/frontend/cal.html`
- SQLite-based lead checkpoint persistence
- Booking state machine with these backend states:
  - `awaiting_booking_confirmation`
  - `collecting_contact`
  - `completed`
- Session-based booking continuity with completed-session rollover
- Scheduling service layer with normalized models, provider factory wiring, and tenant-driven scheduling config validation
- Deterministic mock scheduling provider for isolated slot and booking testing
- Google Calendar scheduling provider with live-validated availability lookup and booking event creation

## Prototype / In Progress

- Booking flow hardening through canonical intent normalization
- Multi-tenant support beyond the sample tenants
- Frontend session-status awareness
- Localized Macedonian shell text for the default frontend
- Booking-flow integration with the isolated scheduling subsystem
- Patient-facing confirmation delivery beyond direct Google Calendar event creation

## Planned

- Broader tenant-specific service catalogs and richer profile validation
- Additional observability and debug tooling
- More complete automated regression coverage
- Stronger deployment and environment hardening
- Future provider expansion beyond Google Calendar, such as Calendly

## Scheduling Notes

- The scheduling subsystem is intentionally separate from the current booking/chat flow.
- `clinic-ai-assistant-src/frontend/cal.html` is the current sandbox for isolated scheduling validation.
- `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json` currently uses `google_calendar` as the active scheduling provider.
- The Google provider currently uses service-account authentication.
- In this service-account mode, booking creates a Google Calendar event without attendee invites or Google email updates.
- That behavior is intentional because Google blocks attendee invites for service accounts without Domain-Wide Delegation.

## Architecture Rule

### ARCHITECTURE RULE - CONFIGURATION SEPARATION

1. Python files must never contain:
   - trigger phrases
   - language patterns
   - business wording
   - booking confirmation words
   - fallback texts
2. All such content must exist only inside tenant profile JSON.
3. Onboarding a new business must require only creating a new JSON configuration file.

The backend Python layer is reserved for:
- logic
- routing
- state machine behavior
- orchestration

The tenant profile layer is reserved for:
- reply wording
- trigger lists
- conversation rules
- catalog content
- booking/contact prompts

## Day 4.4

### DAY 4.4 ARCHITECTURE RULE CONFIRMATION

- Configuration has been extracted from `ai_agent.py` into tenant profile JSON.
- Python now loads conversation rules dynamically from profile JSON.
- The rule `NO CONFIGURATION IN PYTHON` is active and should be reviewed before any future backend change.
