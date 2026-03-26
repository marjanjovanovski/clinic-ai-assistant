# Main Chat Booking Summary And Booking Completion Master Prompt

This document serves to guide, track, and coordinate the next iteration of the main chat scheduling flow after interactive slot selection was enabled.

The purpose of this work is to close the remaining gap between the main chat experience and the working sandbox flow by:
- removing dummy or placeholder booking-summary values from the main chat page
- ensuring the selected slot shown in chat and in the booking summary reflects the actual user choice
- restoring the real booking-completion transaction so the main chat flow reaches calendar booking like the sandbox flow
- preserving the service-oriented architecture where scheduling logic remains under scheduling-owned backend code
- ending with a proposal-only prompt for overlapping slot handling, not an implementation

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

Update rules:
- If only Prompt 1 is finished, the top summary must say: `Prompt 1 - Completed`
- If Prompt 1 and Prompt 2 are finished, the top summary must say: `Prompt 1, 2 - Completed`
- All prompts not yet executed must remain marked as `Pending`
- If a prompt cannot be completed, mark it as `Blocked` and add a short reason under that prompt

## Last Updated By

- `Kai - Codex`

## Last Updated On

- `2026-03-25`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Manual Verification / Merge`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Reuse existing scheduling and booking backend logic where possible instead of rebuilding flows from scratch.
- Keep final booking execution under scheduling-owned backend boundaries wherever practical.
- Do not turn `index.html` into a second booking engine.
- Keep `ai_agent.py` focused on orchestration and session state, not calendar-provider implementation details.
- Preserve current `/chat` compatibility for unrelated chat flows.
- Preserve the shared `slot-list` widget.
- Keep `cal.html` working as the sandbox/reference flow.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to avoid repo-local pytest temp folders.
- When running backend tests, use external `TMP` / `TEMP` and an external `--basetemp`.
- Add or update focused tests for any changed behavior.
- If a test cannot run because of environment permissions, document that clearly in the prompt completion note.
- Manual verification is allowed when the environment blocks full automated execution, but it must be described concretely.

## Commit And History Rules Reminder

- After each prompt is completed, stop and ask `Commit changes?`
- If the user approves, commit with a descriptive commit message.
- Then update the history database according to [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md).
- Every history DB entry created for this work must explicitly set `author_name` to `Kai - Codex`.

## Do Not Break

- current `cal.html` sandbox booking behavior
- current `/scheduling/book` booking path
- current `/scheduling/select-slot` session-aware selection path
- booking-first chat flow
- scheduling-first chat flow
- booking progress widget rendering
- booking summary widget rendering outside the dummy-value issue being fixed
- current `/chat` compatibility for non-booking flows

## Current Repo Truth

- The main chat now supports interactive slot selection through `/scheduling/select-slot`.
- The sandbox page `cal.html` still uses the working direct booking path through `/scheduling/book`.
- The current main chat can advance through slot selection and contact collection, but the final booking completion behavior is not yet matching the sandbox flow.
- The booking summary shown in the main chat currently displays at least one incorrect or dummy value instead of the user-selected slot.
- The browser network trace shows `select-slot` and `chat` requests in the main chat flow, while the sandbox flow reaches the working `book?tenant=...` request.

## Architecture Guidance

- If the main chat needs a final-booking backend step, prefer reusing the existing scheduling booking service and route behavior rather than duplicating booking logic.
- Any new bridging logic between selected-slot state and final booking should remain thin and explicit.
- Keep provider-specific booking behavior inside the scheduling subsystem.
- If proposal work is produced for overlapping slot conflicts, it must be documented in a separate new markdown file and must not silently expand into implementation.

## Prompt 1 - Completed

### Goal

Remove dummy booking-summary values from the main chat UI and ensure the displayed selected slot reflects the real user selection.

### Instructions

Inspect the current booking summary widget rendering in `index.html` and any shared widget/helper code that feeds it.

Requirements:
- identify every dummy, placeholder, hard-coded, or stale booking-summary value currently shown in the main chat flow
- remove those dummy values from `index.html` and from any booking-summary-related widget/helper used by the main chat
- ensure the selected slot shown in:
  - the transcript confirmation line
  - the booking summary widget
  uses the real selected slot chosen by the user in the active session
- preserve current summary layout and styling unless a small change is required to remove hard-coded data cleanly
- do not attempt final booking transaction fixes in this prompt unless they are strictly required to stop dummy-value rendering

### Required Outcome

The main chat no longer shows dummy booking-summary values, and the selected slot displayed to the user reflects the real slot they clicked.

### Prompt 1 Completion Note

What changed:
- removed the hard-coded appointment placeholder from the booking summary payload in `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- booking summaries now read the real selected slot from `state["scheduling_handoff"]["selected_slot"]` when the booking flow was started from scheduling-first slot selection
- removed hard-coded fallback service/date values from `clinic-ai-assistant-src/frontend/widgets/booking-summary/booking-summary.js` so the UI no longer invents dummy values when the payload is empty

Behavior after Prompt 1:
- the transcript confirmation line still shows the exact clicked slot label from the widget selection
- a completed scheduling-first booking summary now shows the same real selected slot instead of the previous placeholder date
- booking-first flows no longer show a fake appointment time in the summary when no real slot has been selected yet

Files changed for Prompt 1:
- `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- `clinic-ai-assistant-src/frontend/widgets/booking-summary/booking-summary.js`
- `clinic-ai-assistant-src/backend/tests/integration/test_req_booking_flow.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`

Verification completed for Prompt 1:
- `tests/integration/test_availability_intent_gating.py` passed
- `tests/integration/test_req_booking_flow.py` passed
- `tests/integration/test_frontend_booking_ui.py` passed

## Prompt 2 - Completed

### Goal

Trace and restore the missing final booking transaction in the main chat flow so the selected slot can actually reach the working booking backend path.

### Instructions

Inspect the current main chat booking flow end to end and compare it against the sandbox `cal.html` booking flow.

You must identify:
- which frontend action currently happens after contact collection completes in the main chat
- whether the main chat ever reaches `/scheduling/book`
- what request payload the sandbox sends to `book?tenant=...`
- what data is missing or disconnected in the main chat flow
- whether the fix should call `/scheduling/book` directly or use a new small scheduling-owned bridge that reuses the same booking service logic

Requirements:
- reuse existing backend scheduling booking logic where possible
- do not duplicate Google Calendar provider logic
- keep the architecture service-oriented, with booking execution under scheduling
- make the main chat complete the booking flow all the way through the authoritative booking transaction
- make sure the resulting selected slot and booking summary stay consistent with the actual booked slot

### Required Outcome

The main chat completes the real booking transaction through scheduling-owned backend logic instead of stopping after contact collection.

### Prompt 2 Completion Note

What changed:
- restored the missing scheduling-first booking transaction inside `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- when the final contact field completes a main-chat scheduling flow, the backend now detects `scheduling_handoff.selected_slot` and internally calls the existing scheduling booking service through `scheduling_capability.book_selected_slot(...)`
- the completed session now stores `booking_result` in state, which feeds the booking summary with:
  - confirmed appointment label
  - confirmed badge state
  - provider confirmation subtitle
- the final assistant reply for scheduling-first completion now uses the provider confirmation message when booking succeeds

Architecture outcome:
- the browser still finishes the conversation through `/chat`
- `index.html` does not rebuild booking requests on its own
- the real booking execution remains in scheduling-owned backend logic and still reuses the existing provider-backed booking path behind `book_selected_slot(...)`
- `cal.html` continues to use the explicit `/scheduling/book` sandbox flow

Files changed for Prompt 2:
- `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_req_booking_flow.py`

Verification completed for Prompt 2:
- `tests/integration/test_availability_intent_gating.py` passed
- `tests/integration/test_req_booking_flow.py` passed
- `tests/integration/test_frontend_booking_ui.py` passed
- `tests/integration/test_scheduling_api.py` passed
- `tests/integration/test_cal_html.py` passed

## Prompt 3 - Completed

### Goal

Harden the repaired main chat booking-completion flow with focused tests, cleanup, and explicit behavioral verification.

### Instructions

After the main-chat booking transaction is restored, clean up any safe-to-remove duplication and add focused coverage.

Requirements:
- add or update focused tests for:
  - selected slot display in the booking summary
  - main chat transition from selected slot to final booking submission
  - backend booking contract reuse or bridge behavior
  - any impacted sandbox-vs-main-chat expectations
- follow repo temp-path rules for pytest execution
- document what was verified automatically and what was verified manually
- note any intentionally preserved differences between `cal.html` and `index.html`

### Required Outcome

The repaired main-chat booking completion flow is verified, maintainable, and clearly documented in this file.

### Prompt 3 Completion Note

What changed:
- cleaned up `clinic-ai-assistant-src/backend/app/services/booking_credentials.py` by extracting appointment-summary state projection into a focused helper so the logic for:
  - selected slot display
  - confirmed booking display
  - badge state
  - summary subtitle
  now lives in one place
- added a new focused unit suite in `clinic-ai-assistant-src/backend/tests/unit/test_booking_credentials.py`
- tightened the frontend integration assertions in `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py` so the summary widget contract explicitly covers appointment status display handling

What was verified:
- `tests/unit/test_booking_credentials.py` passed
- `tests/integration/test_availability_intent_gating.py` passed
- `tests/integration/test_req_booking_flow.py` passed
- `tests/integration/test_frontend_booking_ui.py` passed

What remains intentionally different between `cal.html` and `index.html`:
- `cal.html` still performs direct explicit booking through `/scheduling/book`
- `index.html` still completes booking through the chat session flow and lets the backend bridge into scheduling-owned booking logic internally
- both surfaces now converge on the same provider-backed booking behavior, but they still use different frontend interaction models by design

Follow-up cleanup result:
- no additional safe refactor was necessary in `index.html` for this prompt because the main maintainability hotspot was in backend summary/booking projection logic

## Prompt 4 - Completed

### Goal

Produce a proposal-only follow-up document describing a safe and simple approach for overlapping slot selection conflicts.

### Instructions

This prompt is documentation and proposal work only. Do not implement overlap handling in code in this prompt.

Create a new markdown file in `clinic-ai-assistant docs/ProjectTasks_Pending` that proposes how the system should handle the case where two users select the same slot nearly simultaneously and one user reaches the final booking step first.

The new proposal file must:
- follow the project task-file naming rules
- reference [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md)
- clearly state that it is a proposal/planning document, not implemented behavior
- explain the current conflict risk in both main chat and sandbox-style flows
- describe an easy-to-adopt conflict-handling strategy
- explain what happens for:
  - the user who books first
  - the user who loses the race
  - the UI response shown after a slot becomes unavailable
  - the backend validation point that should reject stale slot claims
- include several prompts for future implementation, but do not execute them in this prompt

Final note for this prompt:
- update this master file to reference the new proposal file that was created

### Required Outcome

A separate new markdown proposal task file exists for overlapping slot handling, and this master file references it without implementing the proposal.

### Prompt 4 Completion Note

What changed:
- created the proposal-only follow-up task file [API - Slot Overlap Conflict Handling Proposal.md](./API%20-%20Slot%20Overlap%20Conflict%20Handling%20Proposal.md)
- the new file documents:
  - current overlap risk in main chat and `cal.html`
  - a simple backend-authoritative stale-slot rejection strategy
  - expected outcomes for the winning and losing user
  - recommended UI recovery behavior
  - future implementation prompts without executing them

Proposal outcome:
- overlap handling remains unimplemented in code
- the repo now has a dedicated pending proposal artifact that can be implemented later under normal task-branch workflow

Files changed for Prompt 4:
- `clinic-ai-assistant docs/ProjectTasks_Pending/API - Slot Overlap Conflict Handling Proposal.md`
- `clinic-ai-assistant docs/ProjectTasks_Pending/UI - Main Chat Booking Summary And Booking Completion.md`
