# Slot Overlap Conflict Handling Proposal

This document is a proposal and planning artifact only. It does not represent implemented behavior.

The purpose of this proposal is to define the most practical service-oriented way to prevent double booking when two users select the same time slot close together, while still preserving a smooth UX for users who take longer to finish the flow.

## Proposal Status

- `Proposal Only - Not Implemented`

## Workflow Authority

Execution of any future implementation based on this proposal must follow [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md).

## Why This Proposal Exists

The current system now supports:
- scheduling-first slot selection in the main chat
- direct sandbox booking in `cal.html`
- provider-backed booking through the scheduling subsystem

That means the overlap risk is now real:
- User A can view slot `26 Mar 2026 во 12:00`
- User B can view the same slot at nearly the same time
- both users may proceed believing the slot is still available
- only one booking should succeed authoritatively

Without an explicit strategy, the losing user may experience:
- a false booking success
- a stale summary still showing the old slot as if it were valid
- no guided recovery path back to fresh availability
- no operator-visible trace that this race happened at all

## Investigation Findings That Refined This Proposal

Runtime investigation on `2026-03-25` showed this is no longer theoretical.

Observed outcome:
- session `e1b02d0c-8d44-4dce-8d72-d5fb3c8ce690` booked `26 Mar 2026 во 12:00` for `marjan.jovanovski@gmail.com`
- session `c7b84d84-e06a-4b6f-baf8-d1f6a793c216` also booked `26 Mar 2026 во 12:00` for `marjan.j@gmail.com`
- both lead records were stored independently with correct contact data
- both sessions persisted `booking_result.status = confirmed`
- both sessions received separate Google Calendar booking ids
- Google Calendar later showed two overlapping events for the same slot
- the latest runtime traces showed no warning, no rejection, and no overlap-specific alert

Meaning:
- this does not currently look like a session data leak in the assistant DB
- it does look like a stale-slot / double-booking gap
- the current system has no built-in operator trace for this class of miss

## Current Risk Surfaces

### Main Chat

- the user selects a slot from `/scheduling/select-slot`
- the chosen slot is carried through contact collection
- the final booking occurs later during the `/chat` completion step
- a slot can become stale between selection time and final booking time

### Sandbox `cal.html`

- the user views availability and clicks a slot
- `cal.html` calls `/scheduling/book` directly
- a slot can become stale between the availability response and the booking request

## Proposal Goals

- prevent silent double booking
- leave a durable trace whenever slot contention or booking mismatch is detected
- establish a scheduling-owned temporary hold before final booking
- allow one silent recovery attempt when the hold expired but the same slot is still available
- return a clean recovery response only when the slot is actually no longer bookable

## Refined Proposed Strategy

### 1. Treat Availability As Advisory

Viewing availability must not reserve a slot permanently.

Implication:
- availability remains informational
- reservation starts only when the user actively selects a slot

### 2. Create A Short-Lived Scheduling Hold On Slot Selection

When the user selects a slot, scheduling should create a short-lived exclusive hold for that exact `tenant + slot_id`.

Recommended behavior:
- hold is created by scheduling, not by the frontend
- hold belongs to a single `session_id`
- only one active hold can exist for the same `tenant + slot_id`
- hold expiration window should be short, for example `3-5 minutes`
- hold is consumed on successful booking
- hold is released or expired automatically if the user does not complete in time

Recommended hold fields:
- `hold_id`
- `tenant`
- `service_id`
- `slot_id`
- `session_id`
- `status` such as `active`, `expired`, `released`, `consumed`
- `created_at`
- `expires_at`
- `released_reason`

### 3. Revalidate At Final Booking Time

Before the provider booking is executed, scheduling must validate that:
- the active hold still belongs to the same session
- the slot is still valid for booking
- the provider/calendar still allows the booking

This remains necessary even if a hold exists because external calendar changes can still happen outside our app.

### 4. Silent Recovery If The Hold Expired But The Slot Is Still Free

This is the key UX refinement.

If the user reaches the final booking step after the hold expired:
- do not immediately interrupt the user
- scheduling should make one dedicated backend re-check for the same selected slot
- if the same slot is still available:
  - recreate or refresh the hold internally
  - continue the booking flow without notifying the user
  - proceed to final provider booking normally
- if the slot is no longer available:
  - return a conflict / expiry response
  - keep the already collected patient details
  - offer fresh slots for the same selected day when possible

This gives the best balance between:
- protecting the calendar
- avoiding fake success
- not punishing a slow user unnecessarily

### 5. Return Dedicated Conflict Outcomes

If the slot can no longer be booked, the backend should return an explicit outcome instead of a generic failure.

Recommended response shapes:
- `status = hold_rejected`
- `status = hold_expired`
- `status = slot_unavailable`
- `reason = slot_conflict`
- `reason = hold_expired_recheck_failed`
- `next_action = refresh_availability`

Recommended payload fields:
- `message`
- `selected_slot`
- `selected_date`
- optional `replacement_slots`
- optional `service_id`

### 6. Same-Day Recovery UX

If the slot is no longer available:
- keep the transcript intact
- keep already collected name/phone/email when safe
- do not restart the whole booking flow
- show a clear message that the selected slot is no longer available
- show fresh slots for the same day the user had already selected

Recommended user-facing wording:
- `Овој термин повеќе не е достапен. Ќе ви прикажам слободни термини за истиот ден.`

If the hold expired but silent re-check succeeds:
- do not notify the user
- continue as if the reservation had remained valid

### 7. Add Conflict And Anomaly Trace Logging

Scheduling must emit explicit trace events for overlap-related misses and suspicious outcomes.

Minimum recommended trace events:
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

Purpose:
- leave operator evidence when a stale-slot race occurs
- make post-incident debugging possible without digging only through chat text
- surface possible leak-like symptoms early, even when the real issue is slot contention

### 8. Preserve Service-Oriented Ownership

The overlap solution should not be implemented separately in each page.

Ownership split:
- frontend:
  - display selected slots
  - show recovery messages
  - render same-day replacement slots when returned
- scheduling backend:
  - own hold creation, expiration, refresh, and release
  - own final revalidation
  - own provider booking authority
  - own overlap and anomaly trace logging
  - return explicit recovery contracts

## Expected User Outcomes

### User Who Books First

- slot hold is created
- booking succeeds normally
- user receives standard confirmation

### User Who Is Slightly Delayed But Slot Is Still Free

- original hold may expire
- backend silently rechecks the same slot
- hold is refreshed internally
- booking continues without interruption

### User Who Loses The Race

- booking does not succeed
- user receives a clear explanation
- user keeps already entered patient details
- user is offered fresh slots for the same day when possible

## Recommended Backend Validation Point

The authoritative booking boundary remains the scheduling-owned booking path.

For current architecture this likely means:
- hold creation or refresh in the slot-selection path
- final hold validation and provider booking in scheduling execution
- reuse for both:
  - main chat booking completion bridge
  - direct sandbox booking flow

## Reservation Feasibility

An application-level reservation mechanism is feasible.

Recommended first version:
- create a lightweight DB-backed hold table or scheduling module
- enforce one active hold per exact `tenant + slot_id`
- expire holds automatically by timestamp
- allow one silent same-slot recheck when the hold expired
- require final booking to confirm hold ownership or refreshed hold ownership

Important limitation:
- a hold only protects against races inside this application
- final provider validation is still required because external calendar changes can happen outside our app

Therefore the safest architecture is:
- hold on selection
- revalidate at booking time
- if hold expired, try one silent same-slot recovery
- if recovery fails, return same-day alternatives
- then create the provider event
- log any mismatch or conflict at each boundary

## Refined Future Implementation Prompts

- Prompt 1 - Map the exact hold lifecycle, expired-hold recovery path, and same-day fallback contract across main chat and sandbox flows
- Prompt 2 - Add scheduling-owned hold persistence, expiration handling, and overlap trace events
- Prompt 3 - Add response contracts for hold rejection, hold expiry, silent same-slot recheck, and slot-unavailable outcomes
- Prompt 4 - Implement hold acquisition on selection plus final booking revalidation in the scheduling-owned booking path
- Prompt 5 - Implement silent expired-hold recheck for the same slot and same-day fallback slot generation when recovery fails
- Prompt 6 - Update main chat UI to support silent recovery, same-day replacement slots, and preserved contact data
- Prompt 7 - Update `cal.html` sandbox UI to support the same scheduling-owned recovery and conflict responses
- Prompt 8 - Add regression coverage for simultaneous booking, hold expiry, silent recheck success, silent recheck failure, and duplicate-booking anomaly traces

## Recommended Simplicity Principle

Do not jump straight to complex distributed locking or provider-specific reservation tricks.

Start with:
- application-level short hold
- final scheduling revalidation
- one silent same-slot recovery attempt after expired hold
- same-day replacement slot response when recovery fails
- overlap/anomaly trace logging

Only introduce more advanced reservation behavior later if real usage proves the simple hold-plus-recheck model is insufficient.
