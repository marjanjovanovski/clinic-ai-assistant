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
