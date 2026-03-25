# Main Chat Interactive Slot Selection Master Prompt

This document serves to guide, track, and coordinate the implementation of safe interactive slot selection in the main chat page.

The purpose of this work is to evolve the current main-chat availability widget from read-only browsing into a backend-authoritative interactive scheduling flow by:
- enabling slot buttons in the main chat transcript
- preserving reuse of the shared `slot-list` widget
- moving slot-selection behavior into the scheduling subsystem instead of bloating `ai_agent.py`
- keeping `cal.html` and the main chat aligned where shared widget behavior makes sense
- preserving current booking-first and scheduling-first workflow boundaries while introducing a safe selection handoff

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

## Current Active Prompt

- `None - Feature Completed`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed
- Prompt 5 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Reuse the existing shared `slot-list` widget instead of creating a second widget.
- Treat main-chat slot interaction as a scheduling feature, not a page-local hack.
- Keep slot-selection state transitions backend-authoritative.
- Prefer placing new slot-selection logic in the scheduling subsystem or scheduling-facing contracts rather than expanding `ai_agent.py` with page-specific branching.
- Keep `ai_agent.py` focused on orchestration and routing, not direct slot-booking mechanics.
- Preserve current booking progress and booking summary widget behavior in the main chat page.
- Preserve current `/chat` compatibility for non-availability flows.
- Keep reusable frontend interaction behavior in shared widget/frontend helpers when possible.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Do Not Break

- booking-first chat flow
- scheduling-first chat flow
- booking progress widget rendering
- booking summary widget rendering
- current `cal.html` sandbox booking behavior
- current `/chat` response compatibility for non-availability flows
- current availability widget rendering in the main chat page

## Current Repo Truth

- The shared `slot-list` widget already exists and is reused by both `cal.html` and the main chat page.
- The main chat page currently renders the slot widget inline in `clinic-ai-assistant-src/frontend/index.html`.
- The main chat page currently mounts that widget with `readOnly: true`, so slot buttons are visually present but disabled.
- `cal.html` already demonstrates an interactive slot-selection path, but it is a sandbox/integration surface and should not be copied blindly into the main chat flow.
- Current slot widget payloads for `/chat` availability replies come from scheduling capability output and already include `service_id`, `title`, and `slots`.
- There is not yet a dedicated backend-authoritative main-chat slot-selection contract for choosing one of those returned slots from the transcript.

## Architecture Guidance

- The slot-selection backend path for this feature should live under scheduling-oriented code and contracts.
- `ai_agent.py` may orchestrate or hand off, but it should not become the long-term home for slot-selection execution details.
- If new request/response shapes are needed, keep them explicit and minimal.
- If a new route or service helper is needed, prefer a scheduling-owned boundary over embedding booking side effects directly into frontend-only logic.

## Prompt 1 - Completed

### Goal

Enable slot buttons in the main chat window so the widget is interactive at the UI layer instead of disabled.

### Instructions

Work only on the minimum frontend/shared-widget changes required to make the slot buttons enabled in the main chat transcript.

Requirements:
- remove the current read-only behavior for main-chat slot widgets
- keep using the shared `slot-list` widget
- preserve current inline transcript rendering in `index.html`
- do not implement booking completion or authoritative scheduling state changes in this prompt
- if a click handler is required, keep it lightweight and isolated so later prompts can attach backend-authoritative logic cleanly
- do not break `cal.html`

Expected behavior after this prompt:
- availability widget appears in the main chat transcript
- slot buttons are enabled and clickable in the main chat window
- no final booking state is invented yet

### Required Outcome

Main-chat slot buttons are enabled and ready for controlled interaction, with the implementation kept clean enough for backend-authoritative follow-up prompts.

### Prompt 1 Completion Note

What changed:
- removed the main-chat `readOnly: true` slot-widget wiring in `clinic-ai-assistant-src/frontend/index.html`
- the shared `slot-list` widget is still reused, but the main chat now mounts it with enabled buttons
- no backend slot-selection contract or booking side effects were introduced in this prompt

Behavior after Prompt 1:
- availability widgets in the main chat still render inline in the transcript
- slot buttons in the main chat are now enabled and clickable
- current clicks remain UI-local and ready for a later backend-authoritative selection flow

Files changed for Prompt 1:
- `clinic-ai-assistant-src/frontend/index.html`
- `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py`

Verification completed for Prompt 1:
- updated focused frontend integration assertions for main-chat slot widget enablement

## Prompt 2 - Completed

### Goal

Map the safe backend architecture for main-chat slot selection and define the minimum contract needed for authoritative slot-choice handling.

### Instructions

Inspect the existing scheduling subsystem, current availability payload shape, `cal.html` interaction flow, and any current booking handoff behavior before implementing backend selection logic.

You must determine:
- where main-chat slot selection should enter the backend
- whether selection should go through `/chat`, a scheduling route, or a new minimal endpoint
- what request payload is required to identify the selected slot safely
- how selected-slot data should be validated against the scheduling result already shown to the user
- where the handoff from scheduling into booking/contact collection should occur
- what should remain in `ai_agent.py` versus what should move into scheduling-owned code

You must then write one output:

**Output - Main Chat Slot Selection Change Map**

A structured table listing every file likely to change for the backend-authoritative selection flow. For each file include:

| Field | Description |
|---|---|
| File path | Exact relative path from repo root |
| Why it matters | One sentence on its role in the future slot-selection behavior |
| Functions / modules likely to change | Specific named functions/modules |
| Layer | One or more of: `frontend`, `backend`, `shared_contract`, `test` |
| Risk | `Low`, `Medium`, or `High` with a one-line reason |

### Required Outcome

A precise change map for authoritative main-chat slot selection, with clear architecture guidance that keeps slot-selection execution under scheduling-owned boundaries where appropriate.

---

### Output - Main Chat Slot Selection Change Map

| File path | Why it matters | Functions / modules likely to change | Layer | Risk |
|---|---|---|---|---|
| `clinic-ai-assistant-src/backend/app/routes/scheduling.py` | Owns the existing scheduling HTTP boundary and is the most natural place for a new session-aware slot-selection endpoint that does not immediately book a calendar event. | `SlotBookingRequest` reuse or sibling request model, new route such as `POST /scheduling/select-slot`, request validation | backend, shared_contract | **High** - this is the public contract boundary and the wrong endpoint shape could blur the distinction between slot selection and final booking |
| `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py` | Already owns scheduling-oriented availability state, handoff payload shaping, and a thin booking wrapper, making it the best place to add slot-selection validation and next-step payload logic. | `store_scheduling_state`, `scheduling_handoff_payload`, new slot-selection validator/helper, possible new assessment/output helpers for selected slot state | backend, shared_contract | **High** - this is the scheduling-owned layer that should validate selected slots against authoritative prior availability results |
| `clinic-ai-assistant-src/backend/app/services/ai_agent.py` | Currently owns session orchestration and the in-memory session state that stores the last scheduling result, but should remain a thin coordinator rather than becoming the slot-selection execution layer. | `SESSION_STATE` access path, possible new helper(s) to fetch/update per-session scheduling state safely for routes, minimal orchestration hooks only | backend | **Medium** - it already owns session state, but pushing too much slot-selection logic here would weaken the service-oriented layout |
| `clinic-ai-assistant-src/backend/app/services/booking_credentials.py` | Owns contact-collection progression after booking intent/handoff and will likely receive the next-step state once a slot is authoritatively selected. | booking handoff entry points such as `start_collecting_contact`, any summary/handoff fields that should include the selected slot | backend | **Medium** - it should consume a validated selected-slot handoff, but should not be responsible for slot validation itself |
| `clinic-ai-assistant-src/backend/app/routes/chat.py` | May need no direct behavior change, but it defines current main-chat response shape and remains relevant if selected-slot outcomes need to stay compatible with existing chat responses. | route response compatibility review only, possibly no code change | backend, shared_contract | **Low** - likely not the primary execution boundary if slot clicks go through a scheduling-owned endpoint |
| `clinic-ai-assistant-src/frontend/index.html` | Owns main-chat widget mounting and is where slot clicks should send a lightweight authoritative selection request instead of only changing UI locally. | `addResponseWidget`, new slot click handler, request submission for selected slot, transcript/status updates after response | frontend | **High** - this is the user-facing integration point and must stay coherent with booking progress and transcript behavior |
| `clinic-ai-assistant-src/frontend/widgets/widget-registry.js` | Provides the shared conversation widget mounting helper that may need a small shared hook path for slot selection callbacks across chat surfaces. | `addSlotListConversationWidget` usage expectations, possible callback/context normalization | frontend | **Low** - shared helper likely needs only light reuse support, not a redesign |
| `clinic-ai-assistant-src/frontend/widgets/slot-list/slot-list.js` | Already emits `onSelect(slot, api)` for interactive usage and is likely reusable as-is for main chat. | likely no major change; only minor payload/callback support if needed | frontend | **Low** - click support already exists and is proven by `cal.html` |
| `clinic-ai-assistant-src/frontend/cal.html` | Demonstrates the current interactive sandbox path and is the strongest reference for widget click behavior, but its direct booking flow should not be copied verbatim into main chat. | `addSlotChoices`, `bookSelectedSlot`, comparison/reference only unless shared helpers are extracted | frontend | **Low** - useful reference, but the main-chat flow should diverge because it needs session-aware selection and booking handoff rather than immediate booking |
| `clinic-ai-assistant-src/backend/tests/integration/test_scheduling_api.py` | Already covers `/scheduling/availability` and `/scheduling/book`, and is the natural home for a new authoritative slot-selection endpoint test. | new integration coverage for selected-slot request/validation/response behavior | test | **High** - this will be the main contract guard for the new backend boundary |
| `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py` | Already verifies scheduling-first availability state and handoff readiness in main chat, which will need extension once a concrete slot can be selected from returned availability results. | scheduling-first handoff assertions, selected-slot state assertions, next-step contract assertions | test | **Medium** - current tests already prove the pre-selection state and can naturally extend to post-selection behavior |
| `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py` | Guards `index.html` transcript/widget wiring and should verify that main-chat slot clicks call the authoritative backend path instead of remaining UI-local. | frontend HTML assertions for click wiring, selected-slot request path, loading/status feedback | test | **Medium** - main frontend wiring needs focused protection but likely only light additions |

### Prompt 2 Completion Note

Architecture conclusion after inspection:
- `cal.html` currently uses the shared widget interactively, but it books immediately through `POST /scheduling/book`
- that direct booking route is not the right backend boundary for the main chat flow because it requires `patient_name` and represents final slot booking rather than intermediate slot selection
- the main chat already has scheduling-first state stored under `ai_agent.SESSION_STATE[session_key]["scheduling"]`
- that stored scheduling state already contains the authoritative availability result needed to validate whether a clicked `slot_id` actually came from the most recent scheduling response

Recommended backend entry point:
- prefer a new minimal scheduling-owned endpoint for main-chat slot selection, rather than sending slot clicks back through normal `/chat` text turns
- that endpoint should accept explicit structured inputs such as:
  - `session_id`
  - `service_id`
  - `slot_id`
- the endpoint should validate the selected slot against the stored scheduling availability result for that chat session
- on success, it should return a next-step response that prepares the booking/contact-collection handoff instead of immediately creating the calendar booking

Recommended ownership split:
- scheduling route/service/capability layer:
  - validate selected slot against authoritative scheduling state
  - shape the selected-slot handoff payload
  - decide whether the selection is acceptable
- `ai_agent.py`:
  - remain the owner of session state storage/orchestration
  - expose only minimal helper access if needed for session-bound scheduling state retrieval/update
  - avoid growing into the direct slot-selection execution layer
- booking/contact layer:
  - continue owning contact collection after a valid selected-slot handoff exists

Most likely implementation direction for later prompts:
- keep `/scheduling/book` for sandbox/direct booking use cases like `cal.html`
- add a separate main-chat slot-selection backend contract under scheduling ownership
- validate slot clicks against the session’s stored availability result before any booking/contact transition
- only after a valid slot selection, hand off into the existing booking/contact collection path

## Prompt 3 - Completed

### Goal

Implement the minimum backend contract and scheduling-owned logic required to accept a slot selection from the main chat safely.

### Instructions

Reference the Change Map from Prompt 2.

Requirements:
- keep slot-selection execution in scheduling-oriented code or routes wherever practical
- avoid growing `ai_agent.py` into a slot-booking implementation layer
- validate the selected slot against authoritative backend state or cached scheduling context
- keep the contract explicit and minimal
- ensure the response clearly tells the frontend what happened next
- preserve non-slot and non-availability chat behavior

The contract should be explicit enough to carry:
- selected slot identity
- related service identity
- session or conversation context required for validation
- resulting next-step state for the frontend

### Required Outcome

The backend can safely accept a selected main-chat slot and respond with an authoritative next-step result without frontend-invented workflow state.

### Prompt 3 Completion Note

Implemented the minimum backend contract and scheduling-owned selection logic for main-chat slot clicks:
- added a new scheduling-owned `POST /scheduling/select-slot` endpoint
- the new endpoint accepts explicit structured inputs:
  - `session_id`
  - `service_id`
  - `slot_id`
- slot selection is validated against the authoritative availability result already stored in the chat session's scheduling state
- on successful validation, the backend now starts the existing booking/contact collection flow and returns an authoritative next-step response instead of relying on frontend-invented workflow state

Architecture outcome after implementation:
- `/scheduling/book` remains the direct final-booking path used by sandbox-style flows like `cal.html`
- `/scheduling/select-slot` becomes the session-aware selection path for the main chat flow
- slot validation lives in `scheduling_capability.py`
- `ai_agent.py` only exposes minimal public helpers for runtime session access and for reusing the existing contact-collection start path

Files changed for Prompt 3:
- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/tests/unit/test_scheduling_capability.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_scheduling_api.py`
- `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`

Verification completed for Prompt 3:
- added unit coverage for authoritative selected-slot handoff validation
- added integration coverage for the new scheduling endpoint
- added integration coverage proving a chat availability session can hand off into contact collection through selected-slot submission

## Prompt 4 - Completed

### Goal

Connect the main chat frontend to the new backend-authoritative slot-selection path.

### Instructions

Reference the Prompt 1 UI changes and the backend contract from Prompt 3.

Requirements:
- wire slot clicks in `index.html` through the new authoritative backend path
- preserve shared widget reuse
- keep transcript behavior coherent and conversational
- surface loading, success, and failure states clearly
- do not let the frontend claim booking success unless the backend confirms it
- preserve booking progress and summary widget behavior
- keep `cal.html` behavior intact unless the shared helper genuinely benefits from safe reuse

Expected behavior:
- user clicks a slot in the main chat widget
- the frontend sends an authoritative selection request
- the transcript and any widgets update based on the backend response

### Required Outcome

Main-chat slot clicks are wired into the authoritative backend flow and the UI reflects the backend-owned next state cleanly.

### Prompt 4 Completion Note

Implemented the main-chat frontend wiring for authoritative slot selection:
- `index.html` now defines a dedicated main-chat slot-selection request path using `POST /scheduling/select-slot`
- shared slot widget clicks now call a page-local `handleSlotSelection(...)` helper instead of remaining UI-local only
- the frontend sends:
  - `session_id`
  - `service_id`
  - `slot_id`
- the selected slot widget is disabled while the backend request is in flight
- on successful backend response, the main chat now:
  - updates booking progress
  - appends the backend-provided reply
  - updates status text based on the returned session state
- on failure, the widget is re-enabled and the transcript shows an error message instead of claiming success

Behavior after Prompt 4:
- user clicks a slot in the main chat widget
- the frontend sends an authoritative slot-selection request to scheduling
- the backend response controls the next transcript and booking-progress state
- the main chat does not claim booking success unless the backend explicitly responds

Files changed for Prompt 4:
- `clinic-ai-assistant-src/frontend/index.html`
- `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py`

Verification completed for Prompt 4:
- updated focused frontend integration assertions for main-chat slot-selection request wiring and backend-driven response handling

## Prompt 5 - Completed

### Goal

Harden the interactive slot-selection flow with focused tests, cleanup, and final verification.

### Instructions

Reference the earlier prompts and finish the feature in a maintainable way.

Requirements:
- remove any safe-to-remove duplication introduced during the implementation
- keep reusable interaction logic in shared frontend or scheduling-owned layers where appropriate
- update or add focused tests for:
  - main chat interactive slot behavior
  - backend slot-selection validation and handoff behavior
  - any updated shared widget expectations
  - any affected `cal.html` or scheduling integration expectations
- read and follow repo test execution instructions
- never generate repo-local pytest temp folders or similar temp artifacts under the repo tree
- use external `TMP` / `TEMP` plus `--basetemp` when running backend tests

Final summary for this prompt must cover:
- what changed
- what was verified
- what remains intentionally different between `cal.html` and the main chat usage
- any follow-up cleanup candidates discovered during implementation

### Required Outcome

The main-chat interactive slot-selection flow is verified, maintainable, and ready for continued iteration under the project’s commit and history rules.

### Prompt 5 Completion Note

What changed:
- cleaned up `index.html` by extracting shared backend-response handling into reusable page-local helpers:
  - `syncSessionId(...)`
  - `updateStatusFromSessionStatus(...)`
  - `applyBackendConversationUpdate(...)`
- reused that shared response path for both:
  - normal `/chat` responses
  - authoritative `/scheduling/select-slot` responses
- kept reusable slot-selection execution in scheduling-owned backend layers while leaving `cal.html` direct-booking flow untouched
- updated focused frontend integration assertions so the main chat page now documents:
  - the new slot-selection endpoint wiring
  - the shared backend-response helper path
  - the shared widget click callback path

What was verified:
- `tests/unit/test_scheduling_capability.py` passes
- lightweight manual app verification confirms `/agent/milena_dental` serves the new main-chat slot-selection wiring
- lightweight manual app verification confirms `/scheduling/select-slot` can move a session into `collecting_contact` with a validated selected slot
- pytest integration suites for frontend and scheduling could not be fully rerun because external temp-path creation/cleanup is currently blocked by Windows permission errors in the environment

What remains intentionally different between `cal.html` and the main chat usage:
- `cal.html` still performs direct sandbox booking through `/scheduling/book`
- the main chat now performs session-aware slot selection through `/scheduling/select-slot`
- both paths reuse the shared `slot-list` widget, but `cal.html` remains a direct-booking sandbox while the main chat follows a session-bound contact-collection handoff

Follow-up cleanup candidates discovered during implementation:
- if the repo’s Windows temp-path permissions are stabilized, rerun the full focused integration suites for:
  - `test_frontend_booking_ui.py`
  - `test_scheduling_api.py`
  - `test_availability_intent_gating.py`
- if session trace logging continues to hit write-permission issues in local verification, align trace output configuration with the same external-temp strategy already used for tests
