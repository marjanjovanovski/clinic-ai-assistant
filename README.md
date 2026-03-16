# Clinic AI Assistant

## Implemented

- FastAPI backend with `/chat`, `/config/{tenant}`, `/agent/{tenant}`, and `/health`
- OpenAI-powered response generation through `client.responses.create(...)`
- JSON tenant profiles loaded from `clinic-ai-assistant-src/backend/app/config/profiles/`
- Lightweight HTML/JS frontend served by the backend
- SQLite-based lead checkpoint persistence
- Booking state machine with these backend states:
  - `awaiting_booking_confirmation`
  - `collecting_contact`
  - `completed`
- Session-based booking continuity with completed-session rollover

## Prototype / In Progress

- Booking flow hardening through canonical intent normalization
- Multi-tenant support beyond the sample tenants
- Frontend session-status awareness
- Localized Macedonian shell text for the default frontend

## Planned

- Broader tenant-specific service catalogs and richer profile validation
- Additional observability and debug tooling
- More complete automated regression coverage
- Stronger deployment and environment hardening

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
