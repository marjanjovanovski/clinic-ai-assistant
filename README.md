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
- Scheduling-capability orchestration inside `ai_agent.py` for availability-first requests
- Scheduling-first coexistence flags in tenant profiles, including `allow_scheduling_first` for `milena_dental`
- Scheduling service layer with normalized models, provider factory wiring, and tenant-driven scheduling config validation
- Deterministic mock scheduling provider for isolated slot and booking testing
- Google Calendar scheduling provider with live-validated availability lookup and booking event creation
- Scheduling-capability tests that verify orchestrator-safe availability and booking request handoff

## Prototype / In Progress

- Booking flow hardening through canonical intent normalization
- Multi-tenant support beyond the sample tenants
- Frontend session-status awareness
- Localized Macedonian shell text for the default frontend
- Safe end-to-end completion of scheduling-selected slots through the main chat flow
- Patient-facing confirmation delivery beyond direct Google Calendar event creation

## Planned

- Broader tenant-specific service catalogs and richer profile validation
- Additional observability and debug tooling
- More complete automated regression coverage
- Stronger deployment and environment hardening
- Future provider expansion beyond Google Calendar, such as Calendly

## Scheduling Notes

- The scheduling subsystem is no longer only an isolated backend sandbox.
- `ai_agent.py` now recognizes availability-first intent when tenant config enables scheduling-first coexistence.
- The current bridge is partial by design: availability assessment and slot surfacing can begin from chat, while final booking still stays behind the existing credential-collection safeguards.
- `clinic-ai-assistant-src/frontend/cal.html` is now both a sandbox and a scheduling-chat surface for exercising the live scheduling endpoints alongside chat UI state.
- `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json` currently uses `google_calendar` as the active scheduling provider.
- `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json` currently enables both `allow_booking` and `allow_scheduling_first`, so booking-first and availability-first paths can coexist for the main tenant.
- The Google provider currently uses service-account authentication.
- In this service-account mode, booking creates a Google Calendar event without attendee invites or Google email updates.
- That behavior is intentional because Google blocks attendee invites for service accounts without Domain-Wide Delegation.

## Test Execution Hygiene

- Do not use repo-local pytest temp folders such as `.pytest_*`, `_codex_pytest_tmp`, ad hoc `pytest_*` folders, or similar writable fallbacks under `clinic-ai-assistant-src/backend/`.
- Do not rely on Python bytecode caches inside the repo as a normal test side effect. Prefer running test commands with `PYTHONDONTWRITEBYTECODE=1` so repeated test runs do not keep generating `__pycache__/` trees in project folders.
- For backend pytest runs, always prefer an external temp root outside the repo and pin all temp behavior there with `TMP`, `TEMP`, and `--basetemp`.
- Known-good temp root for this workspace: `F:\temp\clinic-ai-assistant`
- Known-good backend integration command pattern:

```powershell
$env:TMP='F:\temp\clinic-ai-assistant'
$env:TEMP='F:\temp\clinic-ai-assistant'
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m pytest .\tests\integration\test_req_booking_flow.py .\tests\integration\test_frontend_booking_ui.py -vv --basetemp="F:\temp\clinic-ai-assistant\pytest-integration-codex"
```

- If an external temp path fails, do not fall back to creating new temp folders inside the repo. Stop, report the temp-path failure, and reuse or repair the external temp location instead.

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
