# Slot Overlap Conflict Handling Master Prompt

This document defines the execution-ready task plan for preventing double booking when two users compete for the same slot.

The purpose of this work is to:
- prevent silent double booking across main chat and sandbox flows
- keep scheduling as the authority for slot reservation, revalidation, and final booking
- preserve a smooth UX for slower users through one silent same-slot recovery attempt
- return explicit, recoverable conflict outcomes when a selected slot is no longer bookable
- leave durable operator-visible traces for overlap, stale-slot, and booking-mismatch incidents

This file replaces the older proposal-style structure with an implementation-ready master prompt format aligned to the current task guide.

## Execution Tracking Instructions

Before executing any prompt in this document, the implementing AI agent must first read this file and understand the current status.

Execution of this feature must follow [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md).
After each completed prompt, stop, update prompt status in this file, and ask `Commit changes?`
Do not auto-advance to the next prompt.

As soon as a prompt is executed, this file must be updated in two places:
- at the very top of the document in the global status summary
- in the corresponding prompt section header

Status values allowed in this document:
- `Pending`
- `Completed`
- `Blocked`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-27`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 4`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Pending
- Prompt 5 - Pending
- Prompt 6 - Pending
- Prompt 7 - Pending
- Prompt 8 - Pending
- Prompt 9 - Pending
- Prompt 10 - Pending
- Prompt 11 - Pending
- Prompt 12 - Pending

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Treat scheduling-owned backend code as the authority for slot holds, slot revalidation, and provider booking.
- Reuse existing scheduling and booking services where possible instead of building a parallel reservation flow.
- Keep `ai_agent.py` orchestration-focused rather than pushing provider-specific booking logic into agent orchestration.
- Keep `index.html` and `cal.html` thin clients that render backend-owned state and conflict responses.
- Preserve both current entry points:
  - main chat scheduling-first flow through `/chat`
  - sandbox booking flow through `/scheduling/book`
- Prefer one focused prompt per engineering boundary so each prompt has a clear verification target and natural commit point.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to keep test artifacts out of the repository.
- When running pytest, use external `TMP` / `TEMP` and an external `--basetemp`.
- Add or update focused automated coverage for any changed hold, conflict, booking, or UI behavior.
- If cleanup is required after verification, document it in the prompt completion note.
- If a test cannot run because of environment permissions, document that clearly in the prompt completion note.
- Manual verification is allowed when the environment blocks full automated execution, but it must be described concretely.

## Do Not Break

- current `cal.html` sandbox booking behavior outside the intentional overlap-hardening change
- current `/scheduling/select-slot` selection flow
- current `/scheduling/book` provider-backed booking authority
- booking-first chat flow
- scheduling-first chat flow
- booking summary widget rendering
- slot-list widget rendering
- persisted contact collection and existing lead/session ownership behavior

## Current Repo Truth

- The system currently supports scheduling-first slot selection in the main chat.
- The sandbox page `cal.html` can book directly through `/scheduling/book`.
- A selected slot can remain visible to a user for some time before final booking is attempted.
- Runtime investigation on `2026-03-25` showed that the same exact slot could be booked twice in close succession.
- The overlap issue currently behaves like a stale-slot / double-booking gap rather than a session-state leak.
- The current system has no dedicated hold lifecycle, no conflict-specific backend contract, and no overlap-focused operator trace event set.

Observed investigation outcome:
- session `e1b02d0c-8d44-4dce-8d72-d5fb3c8ce690` booked `26 Mar 2026 at 12:00` for `marjan.jovanovski@gmail.com`
- session `c7b84d84-e06a-4b6f-baf8-d1f6a793c216` also booked `26 Mar 2026 at 12:00` for `marjan.j@gmail.com`
- both lead records were stored independently with correct contact data
- both sessions persisted `booking_result.status = confirmed`
- both sessions received separate Google Calendar booking ids
- Google Calendar later showed overlapping events for the same slot
- the latest runtime traces showed no warning, rejection, or overlap-specific alert

## Why This Feature Exists

Without explicit overlap handling, the losing user may experience:
- a false booking success
- a stale booking summary that still looks valid
- no guided recovery path back to fresh availability
- no operator-visible evidence that slot contention happened

The target outcome is a simple, service-oriented reservation model:
- availability remains advisory
- slot selection acquires a short-lived hold
- final booking revalidates the hold and provider availability
- one silent same-slot recovery attempt is allowed if the hold expired but the slot is still free
- explicit recovery responses are returned when the slot is no longer available

## Target Architecture

### Reservation Model

- Viewing availability does not reserve a slot.
- Reservation starts only when the user actively selects a slot.
- Scheduling creates and owns a short-lived exclusive hold for exact `tenant + slot_id`.
- The hold belongs to one `session_id`.
- Only one active hold may exist for the same `tenant + slot_id`.
- Successful booking consumes the hold.
- Inactive holds must expire or be released automatically.

### Hold Fields

- `hold_id`
- `tenant`
- `service_id`
- `slot_id`
- `session_id`
- `status`
- `created_at`
- `expires_at`
- `released_reason`

### Booking Boundary

Before provider booking executes, scheduling must verify:
- the active hold still belongs to the same session, or can be silently refreshed under the approved recovery rule
- the slot is still valid for booking
- the provider or calendar still accepts the booking

### Silent Recovery Rule

If the user reaches final booking after the hold expired:
- do not interrupt the user immediately
- perform one backend re-check for the same exact selected slot
- if the slot is still available:
  - recreate or refresh the hold internally
  - continue booking without notifying the user
- if the slot is no longer available:
  - return an explicit conflict outcome
  - preserve already collected contact data
  - return fresh same-day alternatives when possible

### Conflict Contract Direction

Recommended status and reason values:
- `status = hold_rejected`
- `status = hold_expired`
- `status = slot_unavailable`
- `reason = slot_conflict`
- `reason = hold_expired_recheck_failed`
- `next_action = refresh_availability`

Recommended response payload fields:
- `message`
- `selected_slot`
- `selected_date`
- optional `replacement_slots`
- optional `service_id`

Recommended user-facing conflict messages:
- User B immediate hold rejection at slot click:
  - `This slot was just taken by another booking. I will show available slots for the same day.`
- User A late failure at final booking after losing the slot:
  - `The selected slot is no longer available. I will show you other available slots for the same day.`

Messaging intent:
- use the first message when the user tried to claim the slot but never obtained the hold
- use the second message when the user had progressed further and the slot was lost before final booking
- avoid generic error wording such as `booking failed`
- avoid false-confirmation language
- immediately pair the message with same-day replacement slots when available

### Trace Events

Minimum recommended event set:
- `SLOT_HOLD_CREATED`
- `SLOT_HOLD_REJECTED`
- `SLOT_HOLD_EXPIRED`
- `SLOT_HOLD_REFRESHED`
- `BOOKING_PRECHECK_CONFLICT`
- `BOOKING_PROVIDER_CONFLICT`
- `BOOKING_CONFIRMATION_MISMATCH`
- `BOOKING_DOUBLE_SUCCESS_SAME_SLOT`
- `HOLD_EXPIRED_RECHECK_SUCCEEDED`
- `HOLD_EXPIRED_RECHECK_FAILED`

Each trace should include:
- `tenant`
- `session_id`
- `service_id`
- `slot_id`
- `selected_slot.display_label`
- `selected_date`
- `calendar_id` when known
- `booking_id` when one exists
- `hold_id` when a reservation is involved
- a short machine-readable `reason`

## User Outcome Expectations

### User Who Books First

- hold is created
- booking succeeds normally
- user receives the usual confirmation

### User Who Is Delayed But The Slot Is Still Free

- original hold may expire
- backend silently rechecks the same slot
- hold is refreshed internally
- booking continues without interruption

### User Who Loses The Race

- booking does not succeed
- user receives a clear explanation
- already entered patient details remain usable
- same-day replacement slots are offered when possible

Recommended user-facing wording when the slot is no longer available:
- `This slot is no longer available. I will show available slots for the same day.`

## Prompt Strategy

This feature should be implemented in small prompt units because it spans contracts, persistence, backend flow control, two UI surfaces, logging, and concurrency-oriented tests.

The prompts below are intentionally split so the implementing agent can:
- keep context windows smaller
- verify each boundary independently
- reduce the chance of mixing API, UI, and test work in one oversized step
- stop cleanly after every meaningful checkpoint

## Prompt 1 - Completed

### Goal

Trace the exact current slot-selection and final-booking flow across main chat and sandbox paths, then confirm the precise overlap failure boundaries.

### Instructions

Inspect the repo end to end before changing code.

Requirements:
- identify where slot selection currently becomes durable state
- identify where booking authority actually executes for:
  - main chat
  - `cal.html`
- map where a stale slot can survive between selection and booking
- identify existing persistence, service, or route boundaries that should own the hold lifecycle
- document the recommended insertion points for hold creation, hold validation, hold consumption, and hold release

### Required Outcome

A precise architecture map exists in this file or in prompt notes, and the exact integration points for the hold model are clear before implementation starts.

### Prompt 1 Completion Note

Current flow map:
- main chat availability lookup runs through scheduling capability assessment and stores the availability result in runtime session state under `state["scheduling"]`
- main chat slot selection calls `/scheduling/select-slot`, which reads the existing chat session state and uses `selected_slot_handoff_payload(...)` to confirm that the chosen `slot_id` exists in the active availability snapshot
- successful main chat slot selection then starts contact collection through `start_contact_collection_from_scheduling_handoff(...)`, which stores `scheduling_handoff.selected_slot` in session state for later booking completion
- final main chat booking does not book at slot-click time; it happens later inside `booking_credentials._complete_selected_slot_booking_if_ready(...)`, which calls `scheduling_capability.book_selected_slot(...)`
- `scheduling_capability.book_selected_slot(...)` currently builds a `BookingRequest` and delegates directly to `scheduling.service.book_slot(...)`
- `scheduling.service.book_slot(...)` currently validates required booking inputs and delegates directly to the configured provider's `book_slot(...)`
- sandbox `cal.html` does not use the chat-session handoff path; it calls `/scheduling/book` directly, which also delegates straight to `scheduling.service.book_slot(...)`

Confirmed overlap failure boundaries:
- slot selection in main chat is only validated against the current in-session availability snapshot, not against a cross-session reservation or hold record
- direct sandbox booking has no reservation layer between availability display and provider booking
- final booking for both entry points currently reaches provider booking without an app-level short-lived hold, hold ownership check, or explicit stale-slot conflict contract
- this means the system can accept two near-simultaneous users as long as the provider layer does not reject the second booking first

Recommended insertion points:
- hold creation boundary:
  - main chat: in `/scheduling/select-slot` immediately after authoritative slot validation and before contact collection begins
  - sandbox: at the point where the selected slot is claimed for booking, ideally through the same scheduling-owned hold API rather than frontend-only state
- hold persistence owner:
  - scheduling-owned backend service or scheduling persistence module, not frontend and not `ai_agent.py`
- hold validation boundary:
  - inside the scheduling-owned final booking path before provider booking executes
- hold consumption boundary:
  - immediately after successful provider booking confirmation
- hold release or expiry boundary:
  - scheduling-owned expiration logic with timestamp-based invalidation, plus explicit release where appropriate
- silent expired-hold recovery boundary:
  - inside the final booking path after hold lookup fails due to expiry but before returning a user-facing conflict

Files and functions that define the current critical path:
- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/service.py`

Architecture conclusion after Prompt 1:
- scheduling backend is the correct owner for the overlap solution
- `ai_agent.py` should remain orchestration-focused and should not own reservation logic
- the cleanest design is to introduce a shared scheduling-owned hold lifecycle that both main chat and sandbox booking paths must pass through before final provider booking

## Prompt 2 - Completed

### Goal

Define the backend contract for hold lifecycle and conflict outcomes before runtime changes are introduced.

### Instructions

Design the scheduling-owned API and service contract for:
- hold creation on slot selection
- hold validation at booking time
- expired-hold same-slot recheck
- explicit conflict and fallback responses

Requirements:
- keep the contract compatible with both main chat and sandbox flows
- prefer explicit machine-readable statuses over vague failure strings
- define which fields are required versus optional in success, conflict, and fallback responses
- define which response fields the frontend may safely rely on

### Required Outcome

The booking and conflict contract is explicit enough that backend, UI, and tests can be implemented without guessing response shape.

### Prompt 2 Completion Note

Contract design direction:
- keep scheduling as the contract owner for hold creation, hold validation, silent recheck, and conflict responses
- preserve the current distinction between:
  - slot selection / handoff response
  - final booking response
- add machine-readable hold and conflict fields rather than overloading generic provider errors or plain-text `detail` messages

Recommended contract families:

1. Slot selection response contract:
- used by `/scheduling/select-slot` and by any future sandbox hold-claim path
- returns whether the slot was successfully claimed for the current session
- if claim succeeds, contact collection or next booking step may continue
- if claim fails, return a structured conflict response rather than only an HTTP error string

2. Final booking response contract:
- used by the scheduling-owned final booking path before and after provider booking
- distinguishes:
  - booking confirmed
  - hold expired but silently recovered
  - hold rejected
  - slot unavailable after recheck
  - provider conflict or provider failure

Recommended hold payload fields:
- `hold_id`
- `hold_status`
- `hold_expires_at`
- `session_id`
- `service_id`
- `slot_id`

Recommended slot-selection success shape:
- `status = hold_acquired`
- `next_action = collect_contact` for main chat, or a booking-ready equivalent for sandbox
- required payload fields:
  - `message`
  - `service_id`
  - `selected_slot`
  - `hold`
- optional payload fields:
  - `booking_progress`
  - `session_status`
  - `inspector_payload`

Recommended slot-selection conflict shape:
- `status = hold_rejected`
- `reason = slot_conflict`
- `next_action = refresh_availability`
- required payload fields:
  - `message`
  - `service_id`
  - `selected_slot`
- optional payload fields:
  - `selected_date`
  - `replacement_slots`
  - `conflict_slot_id`

Recommended final-booking success shape:
- `status = confirmed`
- retain current booking result fields for compatibility:
  - `provider`
  - `booking_id`
  - `start_at`
  - `end_at`
  - `display_label`
  - `confirmation_message`
- add optional overlap-related fields:
  - `hold_id`
  - `hold_status = consumed`
  - `recovery_applied = true|false`

Recommended final-booking conflict shape:
- `status = hold_expired` or `status = slot_unavailable`
- `reason = hold_expired_recheck_failed` or `reason = slot_conflict`
- `next_action = refresh_availability`
- required payload fields:
  - `message`
  - `service_id`
  - `selected_slot`
  - `selected_date`
- optional payload fields:
  - `replacement_slots`
  - `hold_id`
  - `hold_status`

Recommended provider-conflict shape:
- `status = slot_unavailable`
- `reason = provider_conflict`
- `next_action = refresh_availability`
- required payload fields:
  - `message`
  - `service_id`
  - `selected_slot`
- optional payload fields:
  - `selected_date`
  - `replacement_slots`
  - `provider`

Recommended fallback and frontend-safe rules:
- frontend may always rely on:
  - `status`
  - `message`
  - `service_id` when the booking flow is service-bound
- frontend should treat these as optional:
  - `replacement_slots`
  - `hold`
  - `selected_date`
  - `provider`
- if `next_action = refresh_availability`, UI should treat the selected slot as lost and render returned same-day alternatives when present
- if `recovery_applied = true`, UI should behave as a normal success path and must not show a conflict banner

Recommended HTTP semantics:
- keep `200` for confirmed booking and successful silent recovery
- use `409` for hold rejection, expired-hold failure, and slot-conflict outcomes
- reserve `503` for real provider unavailability where the system cannot safely determine a user-recoverable slot conflict

Compatibility guidance:
- preserve current `BookingResult` success fields so existing booking summary rendering remains compatible during the migration
- introduce overlap-specific fields additively rather than replacing current booking result structure in one step
- for selection conflicts, move from plain `HTTPException(detail=...)` responses toward structured JSON payloads that the frontend can render consistently

## Prompt 3 - Completed

### Goal

Add scheduling-owned persistence or equivalent state support for slot holds.

### Instructions

Implement the minimal persistence layer needed for short-lived holds.

Requirements:
- store exact hold ownership by `tenant + slot_id + session_id`
- support statuses such as `active`, `expired`, `released`, and `consumed`
- support deterministic expiration checks
- keep the implementation simple and maintainable
- avoid introducing distributed-lock complexity unless the existing architecture truly requires it

### Required Outcome

A minimal scheduling-owned hold store exists and can represent the required hold lifecycle safely.

### Prompt 3 Completion Note

What changed:
- added a new scheduling-owned persistence module:
  - `clinic-ai-assistant-src/backend/app/services/scheduling_hold_store.py`
- added startup initialization for the new hold table in:
  - `clinic-ai-assistant-src/backend/app/main.py`
- added a focused unit test suite for the persistence lifecycle in:
  - `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_hold_store.py`

Persistence design chosen for the first version:
- use the existing backend SQLite database rather than introducing a second database
- keep hold ownership in a separate scheduling-owned table instead of mixing it into lead/session rows
- reuse the existing tenant table through backend service helpers so holds remain tenant-scoped
- keep the implementation small and deterministic while preserving room for later scheduling-specific expansion

Hold store capabilities now represented:
- create an active hold for exact `tenant + slot_id + session_id`
- detect and return an already-active hold for the same exact slot
- mark stale active holds as expired based on timestamp
- update holds into `released` and `consumed` terminal states
- read holds with active-vs-inactive awareness for later booking-path integration

Current table intent:
- one row per hold lifecycle instance
- `hold_id` is the durable external identifier
- `status` supports:
  - `active`
  - `expired`
  - `released`
  - `consumed`
- `expires_at` is the deterministic expiration boundary
- `released_reason`, `released_at`, and `consumed_at` preserve lifecycle traceability

Verification completed for Prompt 3:
- automated test run:
  - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\unit\\test_scheduling_hold_store.py -q --basetemp="F:\\temp\\clinic-ai-assistant\\pytest-slot-hold-store"`
- result:
  - `4 passed`

Architecture result after Prompt 3:
- the repo now has the minimal persistence layer needed for the hold model
- runtime selection and booking flows do not use it yet; that integration remains for the next prompts

## Prompt 4 - Pending

### Goal

Acquire or reject a hold when a user selects a slot.

### Instructions

Update the slot-selection path so scheduling attempts to create the hold at selection time.

Requirements:
- only one active hold may exist per exact `tenant + slot_id`
- if another active hold already owns the slot, return a clear conflict outcome
- persist enough hold metadata for later booking validation
- keep the slot-selection flow compatible with existing selection payloads where possible

### Required Outcome

Slot selection becomes the point where reservation starts, and stale advisory availability no longer behaves like a claim of ownership by itself.

## Prompt 5 - Pending

### Goal

Enforce hold ownership and provider revalidation at final booking time.

### Instructions

Update the scheduling-owned booking execution path so final booking requires a valid hold or an approved silent-refresh path.

Requirements:
- verify hold ownership against the current session
- verify the slot is still valid before provider booking
- consume the hold on successful booking
- reject booking cleanly if the hold belongs to another session or the slot is no longer bookable
- keep provider-booking authority inside scheduling-owned code

### Required Outcome

Final booking becomes an authoritative guarded boundary rather than a best-effort attempt based only on earlier slot display.

## Prompt 6 - Pending

### Goal

Implement one silent same-slot recovery attempt when the hold expired but the slot is still free.

### Instructions

Add the expired-hold recheck behavior to the final booking path.

Requirements:
- perform at most one silent recheck per booking attempt
- recreate or refresh the hold only if the same slot is still available
- continue booking without user-facing interruption when recheck succeeds
- return the explicit expired-hold conflict contract when recheck fails

### Required Outcome

Slow users are not penalized unnecessarily, while stale-slot conflicts still fail safely when the slot was actually lost.

## Prompt 7 - Pending

### Goal

Return same-day fallback options and preserve collected user data when a selected slot is lost.

### Instructions

Extend the conflict response path so the user can recover without restarting the whole booking flow.

Requirements:
- keep transcript and already collected contact details intact where safe
- return fresh same-day replacement slots when possible
- include enough metadata for the UI to explain the issue and render the alternatives
- do not fake success or preserve stale booking-summary state

### Required Outcome

The backend can respond to lost-slot conflicts with a recoverable same-day fallback contract instead of a generic failure.

## Prompt 8 - Pending

### Goal

Adapt the main chat flow to the new scheduling-owned hold and conflict contract.

### Instructions

Update the main chat surface and any supporting backend bridge logic to respect the new overlap-handling behavior.

Requirements:
- preserve the `/chat` driven interaction model
- support silent recovery with no user-facing noise when recheck succeeds
- show clear lost-slot messaging when recheck fails
- preserve already collected patient details where the backend contract allows it
- keep booking summary and transcript state consistent with actual booking outcome

### Required Outcome

The main chat flow remains smooth for valid bookings and recovers cleanly when a selected slot is lost.

## Prompt 9 - Pending

### Goal

Adapt `cal.html` to the same scheduling-owned hold and conflict contract.

### Instructions

Update the sandbox booking surface so it no longer assumes a direct book request can succeed purely from stale availability display.

Requirements:
- support the new explicit conflict responses
- render same-day fallback slots when returned
- preserve the sandbox's value as a clear backend reference flow
- avoid adding duplicate hold logic in frontend code

### Required Outcome

`cal.html` remains usable as a sandbox flow while following the same authoritative overlap rules as the main chat.

## Prompt 10 - Pending

### Goal

Add overlap-focused trace logging and anomaly detection hooks.

### Instructions

Implement the recommended hold and conflict trace events in scheduling-owned code.

Requirements:
- emit trace events at hold creation, rejection, expiration, refresh, conflict, and booking mismatch boundaries
- include stable machine-readable identifiers in each event
- make post-incident debugging possible without relying only on transcript text
- keep log volume focused on meaningful state transitions and anomalies

### Required Outcome

Operators have durable evidence when overlap, stale-slot conflict, or suspicious booking outcomes occur.

## Prompt 11 - Pending

### Goal

Add focused regression coverage for overlap handling across backend and UI boundaries.

### Instructions

Create or update automated tests for the new behavior.

Requirements:
- cover simultaneous booking or equivalent contention scenarios
- cover hold rejection on selection
- cover final booking success with a valid hold
- cover expired-hold silent recheck success
- cover expired-hold silent recheck failure
- cover same-day fallback responses
- cover overlap trace emission where practical
- follow repo-clean temp-path rules for all test execution

### Required Outcome

Automated coverage exists for the critical overlap-control paths and helps prevent silent regression.

## Prompt 12 - Pending

### Goal

Perform final verification, tighten any rough edges, and document the completed behavior in this file.

### Instructions

After implementation prompts are complete, perform the final pass.

Requirements:
- re-check that both main chat and sandbox flows still work under their intended interaction models
- verify no repo-local junk was left behind by testing
- document automated and manual verification clearly
- list any accepted limitations or follow-up ideas without silently expanding scope

### Required Outcome

The overlap-handling feature is verified, documented, and ready for user review and eventual merge approval.

---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is for archive, handoff, and manual-verification guidance only.

Execution rule for future implementing agents:
- do not treat this appendix as additional implementation scope
- do not create extra prompts from this appendix unless the user explicitly asks for that
- use it only to understand expected runtime behavior and manual verification outcomes
- once the implementation reaches the matching prompt stages above, this appendix should not consume further context planning time

### Main Logic

The system treats availability as view-only until a user actually selects a slot.

When a user clicks a slot:
1. The backend tries to create a short hold for that exact slot.
2. If no one else holds it, the hold is assigned to that user session for a few minutes.
3. The user continues entering contact details.
4. At final booking, the backend checks:
   - does this session still own the hold?
   - is the slot still valid?
   - does the provider or calendar still allow booking?
5. If yes, booking is created and the hold is consumed.
6. If the hold expired, the backend tries one silent re-check for the same slot.
7. If the slot is still free, it refreshes the hold and continues.
8. If the slot is gone, booking is rejected cleanly and fresh same-day slots are returned.

### Practical Use Case

Two users see the same available slot: `12:00`.

| Step | User A | User B | Backend result |
|---|---|---|---|
| 1 | Opens availability | Opens availability | Both can see `12:00` because viewing does not reserve |
| 2 | Clicks `12:00` first | Still looking at list | Hold for `12:00` is created for User A |
| 3 | Enters details | Clicks `12:00` too | User B hold is rejected because User A already owns the active hold |
| 4 | Completes booking | Sees conflict response plus fresh same-day slots | User A booking succeeds |
| 5 | Gets confirmation | Chooses another slot | No double booking |

### Scenarios

#### Scenario A - User B loses immediately at slot selection

Runtime:
1. User A clicks `12:00` first.
2. The backend creates the hold for User A.
3. User B clicks `12:00` while that hold is still active.
4. The backend rejects User B's hold request.
5. User B sees:
   - `This slot was just taken by another booking. I will show available slots for the same day.`
6. The UI refreshes with same-day alternatives.

#### Scenario B - User A loses later at final booking

Runtime:
1. User A clicked `12:00` earlier and had a valid hold.
2. User A takes too long and the hold expires.
3. User B then clicks `12:00` and gets the new active hold.
4. User B completes booking successfully.
5. User A later tries to finish booking.
6. The backend checks the hold and sees User A no longer owns the slot.
7. The backend performs one silent same-slot re-check.
8. The slot is no longer free because User B already secured it.
9. User A sees:
   - `The selected slot is no longer available. I will show you other available slots for the same day.`
10. The UI returns same-day replacement slots without forcing the user to restart from scratch.

#### Scenario C - User A is delayed but silent recovery succeeds

Runtime:
1. User A clicked `12:00`.
2. User A's hold expires before final confirmation.
3. No one else has taken the slot.
4. User A finishes booking.
5. The backend performs one silent re-check.
6. The slot is still free, so the backend refreshes the hold and completes booking.
7. User A sees normal booking confirmation only.
8. No conflict message is shown because recovery succeeded silently.

### Simple Flow Chart

```text
User clicks slot
   |
   v
Create short hold?
   |
   +-- No --> Return conflict + replacement slots
   |
   +-- Yes --> Continue booking flow
                 |
                 v
          Final booking attempt
                 |
                 v
      Hold still valid for this session?
                 |
        +--------+--------+
        |                 |
       Yes               No
        |                 |
        v                 v
 Provider recheck     Silent same-slot recheck
        |                 |
   +----+----+       +----+----+
   |         |       |         |
 Success    Fail   Success     Fail
   |         |       |         |
   v         v       v         v
Confirm   Conflict  Confirm   Conflict +
booking   response  booking   replacement slots
```
