# Main Chat Availability Slot Widget Master Prompt

This document serves to guide, track, and coordinate the implementation of inline availability widget rendering in the main chat page.

The purpose of this work is to evolve the current main-chat availability experience from plain text slot lines into a reusable shared widget flow by:
- reusing the existing shared `slot-list` widget
- rendering that widget inline inside the main chat transcript
- preserving the current booking-first and scheduling-first backend workflow rules
- keeping `cal.html` as the sandbox/integration surface while making the slot widget reusable in `index.html`

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

- `Prompt 2 - Pending`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Treat this feature as a shared widget integration task, not as a one-off `cal.html` hack.
- Reuse the existing `slot-list` widget instead of creating a second slot widget.
- Preserve current booking progress and booking summary widget behavior in the main chat page.
- Preserve current backend workflow ownership for booking and scheduling transitions.
- Keep reusable widget logic in shared frontend widget files, not duplicated in page-local code.
- Keep tenant wording/content and business workflow control in backend/config where those boundaries already exist.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Do Not Break

- booking-first chat flow
- scheduling-first chat flow
- booking progress widget rendering
- booking summary widget rendering
- current `cal.html` sandbox behavior
- current `/chat` response compatibility for non-availability flows

## Current Repo Truth

- The shared `slot-list` widget already exists under:
  - `clinic-ai-assistant-src/frontend/widgets/slot-list/slot-list.js`
  - `clinic-ai-assistant-src/frontend/widgets/slot-list/slot-list.css`
  - `clinic-ai-assistant-src/frontend/widgets/slot-list/demo.html`
- The shared widget registry already exists under:
  - `clinic-ai-assistant-src/frontend/widgets/widget-registry.js`
- `cal.html` already mounts the shared `slot-list` widget successfully and serves as the current sandbox/integration surface.
- The shared chat shell is used by both the main chat page and `cal.html`.
- The current problem is that the main chat page still surfaces availability results as plain text instead of rendering the shared `slot-list` widget inline in the transcript.

## Prompt 1 - Completed

### Goal

Understand the current end-to-end availability rendering path for the main chat page and produce a precise Change Map before implementation.

### Instructions

Inspect the repo and become fully up to speed with the current availability-to-chat rendering path before changing code.

You must understand:
- where the main chat page is served from
- how the main chat transcript is mounted and updated
- how frontend widget dispatch currently works in the main page
- how the shared `slot-list` widget is currently used in `cal.html`
- whether the backend currently returns structured availability payloads to `/chat`
- whether the frontend currently ignores widget-capable availability payloads or whether the backend only returns formatted text
- what exact response shape would allow the main chat page to mount the `slot-list` widget inline
- whether slot interaction in main chat should be display-only for now or interactive in a controlled way

You must then write one output:

**Output - Availability Widget Change Map**

A structured table listing every file that will likely need to change. For each file include:

| Field | Description |
|---|---|
| File path | Exact relative path from repo root |
| Why it matters | One sentence on its role in the current behavior |
| Functions / modules likely to change | Specific named functions/modules, not vague descriptions |
| Layer | One or more of: `backend`, `frontend`, `shared_contract`, `test` |
| Risk | `Low`, `Medium`, or `High` with a one-line reason |

### Required Outcome

A precise Change Map that later prompts can execute without re-exploring the whole repo. No code changes in this prompt.

---

### Output - Availability Widget Change Map

| File path | Why it matters | Functions / modules likely to change | Layer | Risk |
|---|---|---|---|---|
| `clinic-ai-assistant-src/backend/app/routes/chat.py` | Owns the public `/chat` response shape that the main frontend consumes. | `chat` route return payload | backend, shared_contract | **High** - any response-shape change affects the main chat page directly and must remain backward compatible for non-widget flows |
| `clinic-ai-assistant-src/backend/app/services/ai_agent.py` | Owns the main orchestration path and currently decides when availability replies are returned back to `/chat`. | `generate_reply`, scheduling-first availability branches, any final response payload shaping used by `/chat` | backend, shared_contract | **High** - this is the orchestration hotspot and availability behavior already passes through it |
| `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py` | Already produces structured slot data internally but currently exposes only reply text outward through the main chat path. | `handle_scheduling_capability`, `_availability_reply_text`, `assessment_reply_text`, `SchedulingCapabilityAssessment.output_payload` usage | backend, shared_contract | **High** - the slot data already exists here, so the contract likely needs to expose it safely without breaking current reply text behavior |
| `clinic-ai-assistant-src/frontend/index.html` | Owns the main chat page transcript behavior and currently always appends `data.reply` as plain text. | `performSend`, `conversationDispatcher` usage, widget mounting around availability replies | frontend | **High** - this is the page that must switch from plain text slot dumping to inline widget rendering |
| `clinic-ai-assistant-src/frontend/widgets/widget-registry.js` | Already registers the shared `slot-list` widget and defines the main widget dispatch contract. | `registerDefaultConversationWidgets`, `createConversationWidgetDispatcher`, possible helper shape expectations for widget payload mounting | frontend, shared_contract | **Medium** - the registry is already capable, but the main page may need a small extension or a cleaner shared helper path for response-driven widget insertion |
| `clinic-ai-assistant-src/frontend/widgets/slot-list/slot-list.js` | Provides the shared slot widget that should be reused in the main chat instead of text lines. | `createSlotListWidget` only if payload assumptions or interaction wiring need a minimal adjustment | frontend | **Low** - the widget already works in `cal.html`, so it likely needs reuse rather than redesign |
| `clinic-ai-assistant-src/frontend/cal.html` | Serves as the working reference implementation for inline `slot-list` widget rendering in a chat-like flow. | `conversationDispatcher.addWidget("slot-list", ...)`, `addSlotChoices`, any reuse-worthy mounting pattern | frontend | **Low** - likely no direct feature change required, but it is the strongest repo-truth reference for how the shared widget should be mounted |
| `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py` | Validates current availability behavior and shows that backend state already contains structured slot results while the reply remains plain text. | `test_availability_intent_triggers_scheduling_without_starting_booking` and related assertions | test | **Medium** - these tests may need extension to cover any new `/chat` contract fields while preserving current scheduling-first behavior |
| `clinic-ai-assistant-src/backend/tests/integration/test_frontend_booking_ui.py` | Covers the main chat page widget wiring and is the closest existing integration guard for transcript widget behavior in `index.html`. | main page HTML assertions and any new widget-rendering expectations | test | **Medium** - this suite already validates booking widgets and is the natural place to extend expectations for availability widget support |
| `clinic-ai-assistant-src/backend/tests/integration/test_cal_html.py` | Covers the sandbox/widget surface and helps preserve parity between the sandbox and shared widget infrastructure. | slot-list wiring assertions, existing brittle widget-registry expectation | test | **Low** - not the main feature target, but useful for protecting the shared widget path and avoiding regressions in the sandbox reference implementation |

### Prompt 1 Completion Note

Repo truth after inspection:
- the main chat page is served from `clinic-ai-assistant-src/frontend/index.html`
- `index.html` already uses the shared widget registry and dispatcher for booking progress and booking summary widgets
- the main chat page currently always appends only `data.reply` as plain text after `/chat`
- the `/chat` route currently returns only:
  - `received_message`
  - `tenant`
  - `session_id`
  - `session_status`
  - `booking_progress`
  - `reply`
- the backend already has structured slot data during availability handling inside `scheduling_capability.py` under `assessment.output_payload.result.slots`
- that structured slot data does not currently cross the `/chat` response boundary into `index.html`
- `cal.html` already demonstrates the correct shared-widget mounting pattern by calling `conversationDispatcher.addWidget("slot-list", ...)`
- the likely missing feature is a small shared contract addition plus main-page response handling, not a new slot widget

Most likely implementation direction for later prompts:
- keep human-readable `reply`
- add a small structured widget payload to `/chat` for availability-capable responses
- let `index.html` mount the existing shared `slot-list` widget inline when that payload is present
- keep slot interaction minimal/safe until backend workflow boundaries are confirmed in later prompts

## Prompt 2 - Pending

### Goal

Add the minimum safe backend/frontend response contract needed so availability-capable chat replies can carry widget-ready slot data.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions required to establish the shared contract.

Requirements:
- Preserve the existing `/chat` reply shape for non-widget flows as much as possible.
- Continue returning human-readable reply text.
- Add a structured payload that the frontend can use to mount the shared `slot-list` widget inline.
- Reuse the existing widget type name and shared widget registry approach where appropriate.
- Do not embed HTML in backend responses.
- Do not build a large speculative widget protocol if a small explicit structure is enough.
- Keep backend workflow control deterministic and state-aware.

The contract must be explicit enough to carry:
- widget type
- slot list
- service id if needed
- optional widget title or display metadata

### Required Outcome

Availability-related chat responses can carry structured widget-ready slot data without breaking existing non-availability chat flows.

## Prompt 3 - Pending

### Goal

Render the shared `slot-list` widget inline in the main chat page so availability is shown as a real conversational widget rather than a plain text slot dump.

### Instructions

Reference the Change Map from Prompt 1 and the shared contract from Prompt 2.

Requirements:
- Use the existing shared `slot-list` widget.
- Use the existing widget registry / widget dispatcher pattern.
- Mount the widget inline in the transcript at the correct conversation point.
- Preserve existing booking progress and booking summary widget rendering.
- Keep normal text chat rendering intact.
- Do not pull `cal.html` sandbox-only controls into the main chat page.
- Keep page-local code clean and reuse shared widget infrastructure where possible.

Expected behavior:
- user asks for available/free slots in main chat
- assistant reply appears
- shared `slot-list` widget appears inline in the transcript at the point where the assistant discusses the slots

### Required Outcome

The main chat page uses the shared `slot-list` widget for availability results instead of plain text slot lines.

## Prompt 4 - Pending

### Goal

Add the smallest safe slot interaction behavior for the inline widget in the main chat page.

### Instructions

Reference the implementation from Prompt 3.

Implement the safest current interaction level that fits the existing backend architecture. Engineering judgment may choose between:
- display-only widget if current workflow boundaries are not ready for safe interaction
- controlled interaction where clicking a slot produces a safe structured follow-up action consistent with backend workflow rules

Requirements:
- Do not bypass required booking/contact collection rules.
- Do not let the frontend invent workflow transitions.
- Keep the backend authoritative for scheduling/booking state transitions.
- Preserve current booking-first and scheduling-first coexistence rules.
- Keep this implementation minimal and safe; do not overbuild.

### Required Outcome

The inline slot widget in the main chat is either safely interactive or intentionally display-only with a documented reason, based on current backend boundaries.

## Prompt 5 - Pending

### Goal

Clean up the shared path so the `slot-list` widget is maintainable across both `cal.html` and the main chat page, then verify the feature with focused tests.

### Instructions

Reference the earlier prompts and finish the feature in a reuse-friendly way.

Requirements:
- remove any safe-to-remove duplication introduced while integrating the widget
- keep `cal.html` as the sandbox/integration surface
- keep reusable slot rendering behavior in the shared widget layer
- update or add focused tests for:
  - shared widget contract where applicable
  - main chat widget rendering path
  - any affected frontend integration expectations
- read and follow repo test execution instructions
- never generate repo-local pytest temp folders or similar temp artifacts under the repo tree
- use external `TMP` / `TEMP` plus `--basetemp` when running backend tests

Final summary for this prompt must cover:
- what changed
- what was verified
- what remains intentionally different between `cal.html` and the main chat usage
- any follow-up cleanup candidates discovered during implementation

### Required Outcome

The shared `slot-list` widget is cleanly integrated into the main chat page, the relevant tests are updated or added, and the feature is ready for later reuse and iteration.
