# Slot Overlap Conflict Handling Proposal

This document is a proposal and planning artifact only. It does not represent implemented behavior.

The purpose of this proposal is to define a simple, service-oriented way to handle overlapping slot selection and booking attempts when two users choose the same time slot close together and only one can complete the booking first.

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
- User A can view slot `26 Mar 2026 во 16:00`
- User B can view the same slot at nearly the same time
- both users may proceed believing the slot is still available
- only one booking should succeed authoritatively

Without an explicit strategy, the losing user may experience:
- a confusing failure late in the flow
- a stale summary still showing the old slot as if it were valid
- no guided recovery path back to fresh availability

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

## Proposal Goal

Reject stale slot claims at the final backend booking validation point and return a recovery response that is easy for both chat surfaces to handle.

## Proposed Strategy

### 1. Treat Availability As Advisory, Not Reserved

Viewing or selecting a slot must not lock it permanently by itself.

Implication:
- slot selection is a user intent signal
- final booking remains the authoritative moment

### 2. Validate Again At Final Booking Time

The scheduling-owned booking boundary must validate that the slot is still available immediately before the provider-backed booking attempt succeeds.

Recommended validation point:
- inside scheduling-owned booking execution, just before or during `book_selected_slot(...)` / `/scheduling/book`

This is the most reliable place because:
- both main chat and sandbox flows pass through scheduling
- the provider/backend remains the source of truth
- frontend timing cannot be trusted

### 3. Return A Dedicated Slot-Conflict Outcome

If the slot is no longer available, the backend should return an explicit conflict outcome instead of a generic failure.

Recommended response shape:
- `status`: `slot_unavailable`
- `reason`: `slot_conflict`
- `message`: clear user-facing explanation
- `selected_slot`: the stale slot the user attempted
- `next_action`: `refresh_availability`
- optional `replacement_slots`: fresh slots if cheap and safe to provide

### 4. UI Recovery Behavior

If the slot becomes unavailable:
- keep the transcript/history intact
- show a clear explanation that the slot was just taken
- invalidate the stale selected-slot summary state
- offer a fresh slot list or direct the user to refresh availability

### 5. Preserve Service-Oriented Ownership

The overlap check should not be implemented separately in each page.

Ownership split:
- frontend:
  - display conflict message
  - refresh the slot widget if fresh results are returned
- scheduling backend:
  - validate stale vs valid slot
  - return explicit conflict response
  - remain the single authoritative booking boundary

## Expected User Outcomes

### User Who Books First

- booking succeeds normally
- receives standard provider confirmation
- sees confirmed summary state

### User Who Loses The Race

- booking does not succeed
- receives a clear explanation that the slot is no longer available
- is guided back to refreshed availability without losing all context

## Proposed UI Response

Recommended wording pattern:
- `Овој термин во меѓувреме е резервиран од друг пациент. Ќе ви прикажам нови слободни термини.`

Recommended UX behavior:
- keep the selected service if known
- keep already collected contact fields when safe
- refresh only the stale slot portion of the flow

## Recommended Backend Validation Point

The backend validation point that should reject stale slot claims is:
- the scheduling-owned final booking path

For current architecture this likely means:
- shared validation inside scheduling booking execution
- reused by both:
  - main chat booking completion bridge
  - direct sandbox `/scheduling/book`

## Future Implementation Prompts

- Prompt 1 - Map stale-slot validation boundary across main chat and sandbox booking flows
- Prompt 2 - Add explicit scheduling conflict response contract for slot-unavailable outcomes
- Prompt 3 - Implement stale-slot rejection in the scheduling-owned booking path
- Prompt 4 - Update main chat UI to recover cleanly from slot conflict responses
- Prompt 5 - Update `cal.html` sandbox UI to recover cleanly from slot conflict responses
- Prompt 6 - Add regression coverage for simultaneous stale-slot booking scenarios

## Recommended Simplicity Principle

Do not build optimistic reservation locking first unless business requirements demand it.

Start with:
- authoritative final validation
- explicit conflict response
- clear UI recovery

Only introduce temporary holds or reservation windows later if real usage proves they are needed.
