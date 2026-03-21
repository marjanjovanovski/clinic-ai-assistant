# Scheduling Architecture Plan

## How To Use This Document

This document should be treated as the source of truth for the isolated scheduling work.

Recommended working rule:

- before each new work session, read this file first
- pick the first task that is not `completed`
- implement only the intended scope for that task
- when the task is done, update its status here immediately
- if work stops mid-task, mark it `in_progress` or `blocked` with a short note

### Recommended Status Values

Use only these statuses for consistency:

- `not_started`
- `in_progress`
- `blocked`
- `completed`

### Recommended Improvement

Yes, your approach is good.

My improvement recommendation is:

1. Keep the architecture section at the top
2. Add a task board with small enough tasks that each session can complete one or more cleanly
3. Add a prompt board at the end for restart continuity
4. Add a short progress summary near the top so we can see completion state quickly

This is better than a single long plan because it gives us:

- clear execution order
- visible state across resets
- less re-analysis on every restart
- a safer way to keep unfinished work isolated

## Progress Summary

- Overall status: `phase_1_to_5_planning_complete`
- Booking-flow integration status: `designed_not_implemented`
- Current provider target: `google_calendar`
- Future provider target: `calendly`
- Current implementation phase: `phase_5_design_closeout`
- Tasks completed: `14 / 14`

## Execution Log

Add one short line here whenever a task changes state in a meaningful way.

- `2026-03-21`: Planning tracker expanded into task board, phase mapping, prompt board, and restart workflow.
- `2026-03-21`: Task 01 completed. Added isolated scheduling package scaffold under `backend/app/services/scheduling/`.
- `2026-03-21`: Task 02 completed. Added normalized internal scheduling models for availability, slot, booking, and public config payloads.
- `2026-03-21`: Task 03 completed. Added the stable scheduling provider interface and adapter contract.
- `2026-03-21`: Task 04 completed. Extended tenant profile JSON with isolated scheduling configuration and provider blocks.
- `2026-03-21`: Task 05 completed. Added scheduling config validation and safe public scheduling metadata in the config loader.
- `2026-03-21`: Task 06 completed. Added the deterministic mock scheduling provider, provider factory wiring, and scheduling service entry points.
- `2026-03-21`: Task 07 completed. Added isolated scheduling API endpoints for config, availability, and booking and wired them into `main.py`.
- `2026-03-21`: Task 08 completed. Added `frontend/cal.html` as a separate scheduling sandbox page that loads config and prints availability responses in a chat-like panel.
- `2026-03-21`: Task 09 completed. Updated `cal.html` to render available slots as clickable actions and trigger isolated booking requests on selection.
- `2026-03-21`: Task 10 completed. Added focused unit and integration test files for scheduling models, factory, API, and `cal.html`.
- `2026-03-21`: Task 11 completed. Added the Google Calendar availability adapter, factory support, dependency declarations, shared-config merge logic, and timezone fallback handling for local development.
- `2026-03-21`: Task 12 completed. Added Google Calendar booking event creation, normalized booking results, and focused unit coverage for booking payload creation.
- `2026-03-21`: Task 13 completed. Hardened scheduling validation, disabled-provider behavior, provider/config error mapping, and added focused tests for these edge cases.
- `2026-03-21`: Task 14 completed. Added the future booking-flow integration design so the scheduling subsystem can be hooked into chat later without breaking provider separation.

## Goal

Add a separate scheduling subsystem for calendar-based availability lookup and booking without modifying the current booking flow until the calendar runtime is stable.

This plan is intentionally staged so we can:

- build and test scheduling in isolation
- keep the current booking/chat flow untouched
- keep provider-specific logic separate from the core runtime
- keep provider configuration in JSON rather than embedding tenant/provider settings in Python
- support future providers like Calendly after Google Calendar

## Task Board

This task board is intentionally granular so we can resume cleanly after resets.

### Task 01

- Title: Create scheduling module scaffold
- Status: `completed`
- Scope:
  - add the scheduling package structure
  - add empty module entry files
  - keep behavior isolated from booking flow
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/__init__.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/models.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/base.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/factory.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`
- Done when:
  - imports resolve cleanly
  - no booking flow code is modified

### Task 02

- Title: Define scheduling request and response models
- Status: `completed`
- Scope:
  - add internal availability, slot, and booking models
  - define stable normalized payload shape
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/models.py`
- Done when:
  - mock and real providers can share one internal contract

### Task 03

- Title: Define provider interface and adapter contract
- Status: `completed`
- Scope:
  - add abstract provider interface
  - define required adapter methods
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/base.py`
- Done when:
  - provider implementations can be swapped without route changes

### Task 04

- Title: Extend tenant JSON config schema for scheduling
- Status: `completed`
- Scope:
  - add scheduling section to tenant profiles
  - keep provider configuration in JSON
- Target files:
  - `clinic-ai-assistant-src/backend/app/config/profiles/generic.json`
  - `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json`
  - `clinic-ai-assistant-src/backend/app/config/profiles/risto.json`
- Done when:
  - scheduling config exists in tenant JSON
  - booking flow behavior remains unchanged

### Task 05

- Title: Add scheduling config validation and public-config support
- Status: `completed`
- Scope:
  - validate scheduling config in the config loader
  - expose safe public scheduling config for frontend usage
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/config_loader.py`
- Done when:
  - invalid scheduling config fails fast
  - secrets are not exposed in public config

### Task 06

- Title: Build mock scheduling provider
- Status: `completed`
- Scope:
  - add deterministic fake slot generation
  - add deterministic booking confirmation behavior
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/providers/mock_provider.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/factory.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`
- Done when:
  - isolated frontend work can proceed without live calendar integration

### Task 07

- Title: Add standalone scheduling API route
- Status: `completed`
- Scope:
  - create scheduling route models and endpoints
  - add endpoints for config, availability, and booking
- Target files:
  - `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
  - `clinic-ai-assistant-src/backend/app/main.py`
- Done when:
  - scheduling API works independently of chat API

### Task 08

- Title: Create isolated scheduling test page
- Status: `completed`
- Scope:
  - add `cal.html`
  - keep it separate from `index.html`
- Target files:
  - `clinic-ai-assistant-src/frontend/cal.html`
- Done when:
  - page loads independently and can call scheduling endpoints

### Task 09

- Title: Render available slots as clickable chat actions
- Status: `completed`
- Scope:
  - show returned slots in chat-like UI
  - render slots as buttons
  - clicking a slot sends booking request
- Target files:
  - `clinic-ai-assistant-src/frontend/cal.html`
- Done when:
  - one-click slot selection works through the isolated runtime

### Task 10

- Title: Add focused tests for mock scheduling runtime
- Status: `completed`
- Scope:
  - add unit tests for models and provider wiring
  - add integration tests for scheduling endpoints and `cal.html`
- Target files:
  - `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_models.py`
  - `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_factory.py`
  - `clinic-ai-assistant-src/backend/tests/integration/test_scheduling_api.py`
  - `clinic-ai-assistant-src/backend/tests/integration/test_cal_html.py`
- Done when:
  - isolated scheduling mock runtime is covered by focused tests

### Task 11

- Title: Implement Google Calendar availability adapter
- Status: `completed`
- Scope:
  - add Google provider
  - retrieve available slots
  - normalize into internal slot model
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/factory.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`
- Done when:
  - live Google availability can replace the mock provider through config

### Task 12

- Title: Add Google Calendar booking action
- Status: `completed`
- Scope:
  - create booking event flow for selected slot
  - normalize booking response
- Target files:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`
  - `clinic-ai-assistant-src/frontend/cal.html`
- Done when:
  - selecting a slot can create a booking through Google Calendar

### Task 13

- Title: Harden error handling and provider runtime behavior
- Status: `completed`
- Scope:
  - handle bad config
  - handle no-slot scenarios
  - handle provider errors and timeouts
  - verify timezone behavior
- Target files:
  - scheduling service files
  - scheduling route files
  - scheduling tests
- Done when:
  - isolated runtime is stable enough for real-world testing

### Task 14

- Title: Prepare integration design for future booking-flow hookup
- Status: `completed`
- Scope:
  - define how booking flow will consume scheduling later
  - do not implement integration yet
- Target files:
  - this document
  - optional follow-up design note if needed
- Done when:
  - future booking-flow integration path is clear but still untouched

## Current Repo Anchors

The current repo structure suggests these integration points:

- Backend app entry: `clinic-ai-assistant-src/backend/app/main.py`
- Existing API route pattern: `clinic-ai-assistant-src/backend/app/routes/chat.py`
- Existing config loader: `clinic-ai-assistant-src/backend/app/services/config_loader.py`
- Existing tenant JSON config directory: `clinic-ai-assistant-src/backend/app/config/profiles/`
- Existing frontend runtime page: `clinic-ai-assistant-src/frontend/index.html`
- Existing backend test layout:
  - `clinic-ai-assistant-src/backend/tests/unit/`
  - `clinic-ai-assistant-src/backend/tests/integration/`

## Architectural Recommendation

Create a scheduling subsystem with three layers:

1. Stable scheduling core
2. Provider adapters
3. Standalone scheduling API and test UI

This keeps the scheduling runtime independent from the current booking collection logic.

### Layer 1: Stable Scheduling Core

Create a new backend service package:

- `clinic-ai-assistant-src/backend/app/services/scheduling/__init__.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/models.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/base.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/factory.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`

Responsibilities:

- define internal request/response models
- define the provider interface
- build provider instances from tenant JSON config
- expose stable application-facing functions such as:
  - `get_availability(...)`
  - `book_slot(...)`
  - `get_scheduling_public_config(...)`

### Layer 2: Provider Adapters

Start with Google Calendar as the first provider.

Planned adapter files:

- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/mock_provider.py`

Future adapter:

- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/calendly.py`

Responsibilities:

- map provider-specific config into runtime behavior
- call the provider API
- normalize provider responses into internal slot models
- normalize booking results into internal booking result models

The `mock_provider.py` file is important because it lets us stabilize:

- frontend wiring
- API contract
- button selection behavior
- booking action shape

before real provider integration is complete.

### Layer 3: Standalone Scheduling API and Test UI

Add a separate route file:

- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`

Expose isolated endpoints such as:

- `GET /scheduling/config/{tenant}`
- `POST /scheduling/availability?tenant=...`
- `POST /scheduling/book?tenant=...`

Add a separate frontend test page:

- `clinic-ai-assistant-src/frontend/cal.html`

This page should not replace or alter `index.html`.

Its purpose is to:

- test scheduling retrieval independently
- render available slots in a chat-like panel
- let a user click a slot button
- send a booking request for the selected slot
- print returned success/failure data into the same panel

## Configuration Strategy

The repo already uses tenant JSON profiles. We should extend that shape rather than invent a second config source.

Recommended new profile section:

```json
{
  "scheduling": {
    "enabled": true,
    "provider": "google_calendar",
    "timezone": "Europe/Skopje",
    "slot_duration_minutes": 30,
    "slot_interval_minutes": 30,
    "minimum_notice_minutes": 120,
    "lookahead_days": 14,
    "business_hours": {
      "monday": [["09:00", "17:00"]],
      "tuesday": [["09:00", "17:00"]],
      "wednesday": [["09:00", "17:00"]],
      "thursday": [["09:00", "17:00"]],
      "friday": [["09:00", "17:00"]]
    },
    "providers": {
      "google_calendar": {
        "calendar_id": "primary",
        "credentials": {
          "auth_type": "service_account",
          "service_account_file": "backend/app/config/secrets/google-service-account.json"
        }
      },
      "calendly": {
        "organization_uri": "",
        "event_type_uri": "",
        "credentials": {
          "access_token_env": "CALENDLY_ACCESS_TOKEN"
        }
      }
    }
  }
}
```

### Important Separation Rule

Tenant/provider settings belong in JSON.

Python should only:

- validate the config
- choose the configured provider
- execute the provider adapter

Provider credentials should preferably be referenced by JSON, not hardcoded in Python.

Best practical pattern:

- JSON stores config structure and secret references
- secret values come from env vars or secret files

That still satisfies the separation you want, while avoiding fragile hardcoded Python values.

## Stable Internal Contract

The Python core should stay stable by normalizing providers behind shared models.

### Availability Request

- tenant
- service_id
- date_from
- date_to
- timezone
- preferred_days optional
- preferred_time_range optional

### Slot Model

- provider
- slot_id
- start_at
- end_at
- timezone
- display_label
- source_payload optional

### Booking Request

- tenant
- service_id
- slot_id
- patient_name
- patient_phone optional
- patient_email optional
- note optional

### Booking Result

- status
- provider
- booking_id
- start_at
- end_at
- display_label
- confirmation_message
- source_payload optional

This lets the rest of the app consume one stable format even if Google and Calendly behave differently underneath.

## Recommended Implementation Phases

### Phase 1: Core Contract and Mock Runtime

Deliverables:

- scheduling package scaffold
- models and provider interface
- config validation extensions
- mock provider
- scheduling API endpoints
- `cal.html`

This phase should use fake or deterministic slot data so the UI and API settle first.

### Phase 2: Google Calendar Availability Retrieval

Deliverables:

- Google provider adapter
- availability retrieval path
- provider config validation
- focused unit and integration tests

This phase should focus only on:

- querying availability
- slot normalization
- returning stable API responses

No booking-flow integration yet.

### Phase 3: Google Calendar Booking Action

Deliverables:

- booking request path
- slot selection in `cal.html`
- booking response rendering
- booking tests

Still separate from the current booking flow.

### Phase 4: Runtime Hardening

Deliverables:

- provider failure handling
- timeout behavior
- invalid config handling
- no-slot scenarios
- timezone correctness checks
- minimal logging/traceability

### Phase 5: Booking Flow Integration

Only after the isolated runtime is stable.

Deliverables:

- controlled integration into the booking flow
- replacement of placeholder appointment text
- flow updates to retrieve slots and confirm selections

This phase remains explicitly off limits for now.

## Future Booking-Flow Integration Design

This section closes Task 14. It defines how the current booking flow should consume the scheduling subsystem later, without implementing that integration now.

### Integration Principle

Do not make the booking flow talk directly to Google Calendar or Calendly.

The booking flow should talk only to the internal scheduling service layer:

- `get_availability(...)`
- `book_slot(...)`
- `get_scheduling_public_config(...)`

That keeps:

- provider logic out of the booking flow
- JSON-driven provider selection intact
- future provider swapping low-risk

### Current Booking Flow Boundary

Today the booking flow lives primarily in:

- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/frontend/index.html`

That flow should remain responsible for:

- user intent and conversation management
- collecting name, phone, and email
- chat-history rendering
- summary-card lifecycle

It should not become responsible for:

- provider authentication
- calendar API calls
- slot collision logic
- event payload generation

Those stay inside the scheduling subsystem.

### Recommended Future Backend Flow

When the booking flow is opened for integration later, the backend sequence should be:

1. user reaches the completed contact-data stage
2. booking flow calls `get_availability(...)` through the scheduling service
3. scheduling service returns normalized slots
4. booking flow stores the proposed slot list in session state
5. user selects one slot
6. booking flow calls `book_slot(...)`
7. scheduling service creates the booking with the configured provider
8. booking flow receives normalized booking result
9. booking flow updates chat summary and final confirmation copy

### Recommended Session-State Extension

Do not mix raw provider payloads into the existing session state unless they are needed.

If scheduling is integrated into the booking flow later, add only minimal fields such as:

- `scheduling_status`
- `availability_request`
- `available_slots`
- `selected_slot_id`
- `booking_result`

Recommended meanings:

- `scheduling_status = idle`
- `scheduling_status = awaiting_slot_selection`
- `scheduling_status = booking_in_progress`
- `scheduling_status = booked`
- `scheduling_status = booking_failed`

### Recommended Frontend Integration Pattern

The current `cal.html` sandbox should be treated as the prototype for future slot selection behavior.

When slot selection moves into `index.html`, reuse these ideas:

- render returned slots as bot-side clickable actions
- keep slot choice visible in chat history
- after selection, append a short user-side confirmation bubble
- after successful booking, append a bot-side booking confirmation

Do not initially replace the entire booking summary card with slot buttons.

Instead:

- keep the summary card as the patient-info checkpoint
- render slot-choice actions as the next conversational step
- after booking success, update the summary payload from placeholder appointment text to confirmed appointment text

### Recommended Summary Transition

The current summary uses a placeholder appointment string.

Future integration should move summary timing through these stages:

1. placeholder stage:
   - current behavior
   - summary shows provisional appointment text
2. slot-selection stage:
   - summary can remain provisional
   - available slots appear in chat as actions
3. confirmed-booking stage:
   - summary should use the confirmed slot from `BookingResult`
   - appointment status should change from provisional to confirmed

### Recommended Data Mapping For Booking Flow

The booking flow should pass only normalized values into scheduling:

- `service_id`
- `patient_name`
- `patient_phone`
- `patient_email`
- optional `note`
- selected slot id

The scheduling layer should return only normalized values back:

- `booking_id`
- `provider`
- `start_at`
- `end_at`
- `display_label`
- `confirmation_message`

### Error Handling Recommendation For Future Integration

When scheduling is integrated into the chat flow later:

- validation/config issues should produce a short human-safe fallback
- provider downtime should not collapse the rest of the chat flow
- booking failure should preserve collected patient data
- slot-selection failure should allow retry without restarting contact collection

Recommended user-facing behavior:

- if availability lookup fails:
  - keep booking data
  - tell the user scheduling is temporarily unavailable
  - offer retry later
- if booking fails after slot selection:
  - keep the selected slot visible if useful
  - offer another slot selection or later retry

### Migration Order For Actual Integration

When we eventually start real booking-flow integration, the safest sequence is:

1. add backend session-state fields for scheduling
2. retrieve availability after contact collection completes
3. show slots in chat while keeping the rest of the booking flow intact
4. add confirmed-slot booking action
5. update booking summary payload to use confirmed appointment data
6. remove placeholder appointment text only after confirmed booking is stable

### What Must Stay Unchanged During Early Integration

Until the scheduling integration is proven stable:

- do not remove the existing contact collection flow
- do not remove completed summary chat-history behavior
- do not collapse the provider boundary into `ai_agent.py`
- do not move provider config into Python code

### Definition Of Done For Future Integration

Future booking-flow integration should only be considered complete when:

- booking flow still preserves chat-history summary behavior
- patient data collection still works unchanged
- available slots render reliably in the main chat UI
- selected slot can be booked through the configured provider
- confirmed booking updates the summary card and chat history
- retry/error behavior does not force a full flow restart

## Phase Mapping

This maps the tasks above into phases so we can see both the detailed and high-level view.

- Phase 1: Tasks 01-10
- Phase 2: Task 11
- Phase 3: Task 12
- Phase 4: Task 13
- Phase 5: Task 14

## Exact File Plan

### New Backend Files

- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/__init__.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/base.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/models.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/factory.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/mock_provider.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`

### Existing Backend Files To Extend

- `clinic-ai-assistant-src/backend/app/main.py`
- `clinic-ai-assistant-src/backend/app/services/config_loader.py`
- `clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json`
- `clinic-ai-assistant-src/backend/app/config/profiles/generic.json`
- `clinic-ai-assistant-src/backend/app/config/profiles/risto.json`

### New Frontend File

- `clinic-ai-assistant-src/frontend/cal.html`

### New Tests

- `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_models.py`
- `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_factory.py`
- `clinic-ai-assistant-src/backend/tests/unit/test_google_calendar_provider.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_scheduling_api.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_cal_html.py`

## API Sketch

### `GET /scheduling/config/{tenant}`

Returns public scheduling config needed by the test page:

- enabled
- provider
- timezone
- slot duration
- whether booking is enabled

### `POST /scheduling/availability?tenant=...`

Request:

```json
{
  "service_id": "consultation",
  "date_from": "2026-03-25",
  "date_to": "2026-03-31",
  "timezone": "Europe/Skopje"
}
```

Response:

```json
{
  "provider": "google_calendar",
  "slots": [
    {
      "slot_id": "google:2026-03-25T09:00:00+01:00",
      "start_at": "2026-03-25T09:00:00+01:00",
      "end_at": "2026-03-25T09:30:00+01:00",
      "timezone": "Europe/Skopje",
      "display_label": "25 Mar 2026 во 09:00"
    }
  ]
}
```

### `POST /scheduling/book?tenant=...`

Request:

```json
{
  "service_id": "consultation",
  "slot_id": "google:2026-03-25T09:00:00+01:00",
  "patient_name": "Marjan",
  "patient_phone": "070000000",
  "patient_email": "mail@test.mk",
  "note": "Initial consultation"
}
```

Response:

```json
{
  "status": "confirmed",
  "provider": "google_calendar",
  "booking_id": "gc-event-123",
  "start_at": "2026-03-25T09:00:00+01:00",
  "end_at": "2026-03-25T09:30:00+01:00",
  "display_label": "25 Mar 2026 во 09:00",
  "confirmation_message": "Терминот е резервиран."
}
```

## `cal.html` Recommendation

Use a lightweight chat-like shell that is intentionally separate from the production chat page.

Minimal first version:

- a small header
- date range inputs
- a button to load availability
- a message list area
- slot buttons rendered inside bot-style messages
- a booking result message after selection

Suggested behavior:

1. User opens `cal.html`
2. Clicks "Load slots"
3. Backend returns slots
4. Slots render as clickable buttons
5. Clicking a button sends booking request
6. Result prints in the same chat log

## Risks To Design Around

- Google Calendar auth complexity
- timezone drift
- provider-specific availability semantics
- double booking/race conditions
- config validation gaps
- exposing secrets to the frontend

## First Implementation Prompt

Use this prompt to start implementation:

```text
Continue from repo truth only.

Goal:
Build a separate scheduling subsystem for calendar integration without modifying the existing booking flow yet.

Requirements:
- Create a clearly separated scheduling service architecture in the backend.
- Keep provider-specific logic isolated behind a common interface.
- Start with Google Calendar as the first provider.
- Design the system so future providers like Calendly can be added with minimal Python-core changes.
- Keep configuration outside Python logic and in JSON-driven tenant/provider config.
- Do not integrate scheduling into the current booking flow yet.
- Add standalone scheduling endpoints for availability lookup and booking.
- Add a minimal frontend test page `clinic-ai-assistant-src/frontend/cal.html`.
- The test page should be independent from the current production chat page.
- The page should display returned available time slots in a chat-like UI, ideally as clickable buttons.
- Clicking a slot should trigger a booking request and render the result in the page.
- Prefer stable internal contracts and adapter boundaries over quick one-off coupling.
- Preserve current product behavior outside this isolated scheduling work.

Deliverables:
1. Scheduling architecture and file structure
2. Backend scheduling service/factory/provider implementation
3. JSON config additions for scheduling
4. Standalone scheduling API endpoints
5. Minimal `cal.html` test UI
6. Focused tests
7. Summary of what was built, what is verified, and what remains intentionally not integrated
```

## Restart Sync Prompt

Use this whenever work resumes after context reset:

```text
Re-anchor from repo truth and continue the isolated scheduling subsystem work.

Scope:
- scheduling service only
- Google Calendar provider first
- JSON config driven
- standalone scheduling endpoints
- `frontend/cal.html` test page
- no booking-flow integration yet

Before changing code, inspect:
- latest git state
- frontend/cal.html if present
- backend scheduling-related files if present
- tenant JSON config files
- scheduling tests if present

Then continue implementation from the current repo state without redoing completed work.
Return:
1. what you changed
2. what you verified
3. what remains for next step
```

## Prompt Board

These prompts are meant to be reused across sessions. They should also carry status so we know whether a prompt has already been executed.

### Prompt P1

- Title: Build isolated scheduling scaffold and mock runtime
- Status: `not_started`
- Use when:
  - we are starting the implementation
  - no scheduling subsystem exists yet
- Prompt:

```text
Re-anchor from repo truth and begin Phase 1 of the isolated scheduling subsystem.

Scope:
- scheduling scaffold
- internal models
- provider interface
- scheduling config validation support
- mock provider
- standalone scheduling API
- `frontend/cal.html`
- no booking-flow integration

Update the task board statuses in `clinic-ai-assistant docs/scheduling_architecture_plan.md` as you complete work.
Return:
1. what you changed
2. what you verified
3. which task IDs are now completed
4. what remains next
```

### Prompt P2

- Title: Replace mock availability with Google Calendar retrieval
- Status: `not_started`
- Use when:
  - Phase 1 is complete
  - mock scheduling runtime is stable
- Prompt:

```text
Re-anchor from repo truth and continue the isolated scheduling subsystem with Google Calendar availability retrieval.

Scope:
- Google Calendar provider implementation
- provider config validation
- slot normalization
- focused tests
- keep booking flow untouched

Update task statuses in `clinic-ai-assistant docs/scheduling_architecture_plan.md` during the work.
Return:
1. what you changed
2. what you verified
3. which task IDs are now completed
4. remaining risks
```

### Prompt P3

- Title: Add Google Calendar booking action
- Status: `not_started`
- Use when:
  - Google availability retrieval is stable
- Prompt:

```text
Re-anchor from repo truth and continue the isolated scheduling subsystem with Google Calendar booking support.

Scope:
- slot booking action
- normalized booking result
- `cal.html` booking interaction
- focused tests
- no booking-flow integration yet

Update task statuses in `clinic-ai-assistant docs/scheduling_architecture_plan.md` during the work.
Return:
1. what you changed
2. what you verified
3. which task IDs are now completed
4. what remains before integration readiness
```

### Prompt P4

- Title: Harden scheduling runtime for pre-integration stability
- Status: `not_started`
- Use when:
  - booking action exists
  - runtime needs hardening before integration planning closes
- Prompt:

```text
Re-anchor from repo truth and harden the isolated scheduling subsystem before any booking-flow integration.

Scope:
- provider/runtime error handling
- no-slot scenarios
- timeout behavior
- timezone correctness
- config edge cases
- focused tests

Update task statuses in `clinic-ai-assistant docs/scheduling_architecture_plan.md` during the work.
Return:
1. what you changed
2. what you verified
3. which task IDs are now completed
4. remaining blockers
```

## Suggested Execution Order

1. Add scheduling models, base interface, factory, and mock provider
2. Add scheduling config validation support
3. Add isolated scheduling API route and wire it in `main.py`
4. Add `cal.html` against the mock provider
5. Replace mock availability with Google Calendar retrieval
6. Add booking action for Google Calendar
7. Harden tests and error handling
8. Only then discuss booking-flow integration
