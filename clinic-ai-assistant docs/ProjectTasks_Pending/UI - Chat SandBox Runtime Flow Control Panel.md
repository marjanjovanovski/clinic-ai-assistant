# Chat SandBox Runtime Flow Control Panel Master Prompt

This document defines a future UI task for creating a Chat SandBox page that mirrors the production main chat while exposing runtime flow variables in a minimal side panel for testing and debugging.

The purpose of this work is to:
- create a `ChatSandBox` page as a duplicate-style companion to the production `index.html`
- preserve the production main chat interaction model while adding an optional inspector panel similar in spirit to `cal.html`
- expose important runtime variables from the booking, scheduling, and catalog-assisted flow in a grouped, readable form
- let testers uncover the panel only when needed
- preview relevant JSON config content at the bottom of the panel
- keep the feature useful for debugging without turning the production page into a sandbox or admin tool

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

- `Kai - Codex`

## Last Updated On

- `2026-03-26`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Manual Verification / Merge`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed
- Prompt 5 - Completed
- Prompt 6 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Keep `index.html` production-oriented; do not add the debug panel there.
- Create a dedicated sandbox-style page for this work rather than turning the main chat into a diagnostics surface.
- Preserve shared chat widgets and avoid duplicating widget logic unnecessarily.
- Prefer reusing backend response payloads and existing session state projections before inventing new frontend-only state.
- Runtime variables shown in the panel must be grouped by concern and easy to scan.
- The side panel should stay minimalistic and hidden/collapsible by default if possible.
- Only expose variables useful for flow debugging, especially values derived from user interaction and backend flow decisions.
- Include relevant config JSON previews in the panel, but avoid dumping unrelated internal state if it does not help testing.
- Keep any new runtime-inspector contracts explicit and stable enough for future debugging use.

## Testing And Verification Rules

- Follow the repo rule to avoid repo-local pytest temp folders.
- When running backend or frontend-related tests, use external `TMP` / `TEMP` and an external `--basetemp`.
- Do not create temporary junk folders or temp artifacts inside the repo.
- Add or update focused tests only for the behaviors changed by the implementation prompts.
- Manual verification is allowed when a prompt is mainly UI-focused, but it must be described concretely.

## Branching And Repo-State Rules

- This task file may be authored on the current branch as documentation-only work.
- Actual feature implementation for this task must start later on its own dedicated branch, preferably from `main`, following [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md).
- If the repo still contains unmerged branch work when implementation begins, the implementing agent must pause and call out merge/conflict risks before coding.

## Do Not Break

- current production `index.html` chat behavior
- current `cal.html` scheduling sandbox behavior
- current `/chat` response shape
- current `/scheduling/select-slot` main chat handoff
- current booking progress widget rendering
- current booking summary widget rendering
- current scheduling-first and booking-first flows

## Current Repo Truth

- `index.html` is the production-style main chat surface.
- `cal.html` already has a side-panel-oriented sandbox/testing layout.
- scheduling availability currently uses a thin default request shape with values such as:
  - `service_id`
  - `date_from`
  - `date_to`
  - `timezone`
  - `preferred_days`
  - `preferred_time_range`
- many of those values currently exist in code but are not yet exposed in a tester-facing runtime control panel.
- the orchestration anchor still lives mainly in `backend/app/services/ai_agent.py`, while booking and scheduling details are delegated to dedicated service modules.

## Desired Outcome

After all prompts are complete, the repo should have:
- a new `ChatSandBox` page that visually mimics the production main chat
- a minimal side panel that can be uncovered during testing
- grouped runtime variables for the complete flow
- textbox-style controls or displays for important flow variables
- bottom-panel previews for relevant config JSON files
- focused verification for the new page and its runtime data display

## Prompt 1 - Completed

### Goal

Define the exact runtime variables, groupings, and data sources for the Chat SandBox inspector panel before implementation begins.

### Instructions

Inspect the current production chat flow and determine which runtime values are important enough to expose for testing.

The output of this prompt must identify grouped categories such as:
- session / routing
- booking flow
- scheduling request criteria
- selected slot / booking result
- config preview sources

Requirements:
- focus on variables that are part of the actual runtime flow and are influenced by user interaction or backend decisions
- do not expose arbitrary internal noise that would clutter the panel
- clearly distinguish:
  - editable control values
  - read-only observed values
  - config-preview-only content

### Required Outcome

A clear variable inventory exists for the future Chat SandBox panel, grouped by concern and mapped to likely data sources.

### Prompt 1 Completion Note

What was identified:

- the current runtime already exposes enough stable flow state to build a first useful inspector without inventing a second booking engine
- the most important sandbox panel values should be grouped into:
  - `Session And Routing`
  - `Catalog / Intent Resolution`
  - `Booking Flow`
  - `Scheduling Criteria`
  - `Selected Slot And Booking Result`
  - `Widget / Response Payload`
  - `Config Preview`

Variable inventory for the future panel:

`Session And Routing`
- `tenant`
  - type: read-only observed value
  - likely source: frontend tenant resolution from page path
- `session_id`
  - type: read-only observed value
  - likely source: `/chat` and `/scheduling/select-slot` response payloads plus local storage
- `session_status`
  - type: read-only observed value
  - likely source: `/chat` response payload
- `last_user_message`
  - type: read-only observed value
  - likely source: frontend chat send flow
- `last_response_type`
  - type: read-only observed value
  - likely source: frontend response handling, potentially derived from widget and session updates unless a small backend field is later added

`Catalog / Intent Resolution`
- `resolved_service_id`
  - type: read-only observed value, with future optional editable override for testing
  - likely source: `booking_progress.summary`, scheduling widget payload, or future explicit inspector contract
- `allow_booking`
  - type: config-preview-only content
  - likely source: tenant profile JSON
- `allow_scheduling_first`
  - type: config-preview-only content
  - likely source: tenant profile JSON

`Booking Flow`
- `booking_stage`
  - type: read-only observed value
  - likely source: `booking_progress.booking_stage`
- `reservation_status`
  - type: read-only observed value
  - likely source: `booking_progress.reservation_status`
- `collection_status`
  - type: read-only observed value
  - likely source: `booking_progress.collection_status`
- `collection_total`
  - type: read-only observed value
  - likely source: `booking_progress.collection_total`
- `progress_percent`
  - type: read-only observed value
  - likely source: `booking_progress.progress_percent`
- `next_field`
  - type: read-only observed value
  - likely source: `booking_progress.next_field`
- collected field values:
  - `name`
  - `phone`
  - `email`
  - type: read-only observed values in the first implementation; possible future editable controls only if that helps testing
  - likely source: `booking_progress.fields` and `booking_progress.summary.fields`

`Scheduling Criteria`
- `service_id`
  - type: editable control value
  - likely source: sandbox panel state, seeded from scheduling defaults or latest runtime context
- `date_from`
  - type: editable control value
  - likely source: sandbox panel state
- `date_to`
  - type: editable control value
  - likely source: sandbox panel state
- `timezone`
  - type: editable control value
  - likely source: sandbox panel state seeded from scheduling config
- `preferred_days`
  - type: editable control value
  - likely source: sandbox panel state
- `preferred_time_range`
  - type: editable control value
  - likely source: sandbox panel state
- resolved/defaulted scheduling request snapshot:
  - type: read-only observed value
  - likely source: future explicit inspector payload or a focused backend debug contract

`Selected Slot And Booking Result`
- `selected_slot.display_label`
  - type: read-only observed value
  - likely source: `/scheduling/select-slot` response and booking summary state
- `selected_slot.slot_id`
  - type: read-only observed value
  - likely source: slot widget payload / selected-slot response payload
- `selected_slot.start_at`
  - type: read-only observed value
  - likely source: slot widget payload / selected-slot response payload
- `selected_slot.end_at`
  - type: read-only observed value
  - likely source: slot widget payload / selected-slot response payload
- `selected_slot.provider`
  - type: read-only observed value
  - likely source: slot widget payload / selected-slot response payload
- `booking_result.status`
  - type: read-only observed value
  - likely source: booking completion state projected through booking summary or future inspector payload
- `booking_result.display_label`
  - type: read-only observed value
  - likely source: booking completion summary state
- `booking_result.booking_id`
  - type: read-only observed value
  - likely source: future explicit inspector payload if exposed safely
- `booking_result.confirmation_message`
  - type: read-only observed value
  - likely source: booking summary subtitle / future inspector payload

`Widget / Response Payload`
- `widget_payload.type`
  - type: read-only observed value
  - likely source: `/chat` response payload
- `widget_payload.service_id`
  - type: read-only observed value
  - likely source: slot-list widget payload
- `widget_payload.slots.length`
  - type: read-only observed value
  - likely source: slot-list widget payload
- `last_reply`
  - type: read-only observed value
  - likely source: `/chat` response payload
- raw payload preview:
  - type: read-only observed value
  - likely source: latest `/chat`, `/scheduling/select-slot`, and optional scheduling-config payload snapshots

`Config Preview`
- tenant profile JSON preview
  - type: config-preview-only content
  - likely source: `backend/app/config/profiles/<tenant>.json`
- scheduling public config preview
  - type: config-preview-only content
  - likely source: `/scheduling/config/{tenant}`
- optional prompt/output contract preview if later deemed useful
  - type: config-preview-only content
  - likely source: tenant profile JSON sections already driving model behavior

Implementation guidance locked in after Prompt 1:

- the first useful Chat SandBox version should avoid exposing raw full backend session state
- the panel should mix:
  - editable scheduling criteria controls
  - read-only live flow observations
  - config previews at the bottom
- if a value cannot be derived reliably from existing frontend payloads, the preferred next step is a small explicit backend inspector contract rather than fragile DOM inference

## Prompt 2 - Completed

### Goal

Create the new Chat SandBox page as a production-chat-style duplicate surface with a minimal side panel layout.

### Instructions

Add a new frontend page named `ChatSandBox` that mirrors the production `index.html` chat experience closely enough for realistic flow testing.

Requirements:
- the page must feel like the production chat, not like `cal.html`
- the page must include a side panel similar in spirit to `cal.html`
- the panel should be minimalistic and not dominate the chat UI
- the panel should be uncoverable/toggleable for testing use
- reuse existing shared chat and widget infrastructure where practical

### Required Outcome

A new Chat SandBox page exists with production-like chat behavior and a sandbox inspector side panel shell.

### Prompt 2 Completion Note

What changed:

- created a new frontend page at `clinic-ai-assistant-src/frontend/ChatSandBox.html`
- kept the main chat runtime behavior production-like by reusing the same:
  - `/chat` interaction model
  - booking progress widget
  - booking summary history behavior
  - slot-list widget flow
  - `/scheduling/select-slot` handoff path
- added a minimal inspector-side layout shell without turning the page into a scheduling-first sandbox like `cal.html`
- made the inspector shell toggleable through a `Show Inspector` / `Hide Inspector` control
- added reserved grouped inspector cards for:
  - `Session And Routing`
  - `Booking Flow`
  - `Scheduling Criteria`
  - `Selected Slot And Booking Result`
  - `Config Preview`

Prompt 2 intentionally does not yet implement:

- live runtime variable rendering in the panel
- editable scheduling controls inside the panel
- config JSON previews
- focused inspector payload wiring

Why this prompt stops here:

- Prompt 2 was limited to establishing the new page and the minimal side-panel shell
- the grouped panel content and runtime wiring are deferred to Prompts 3, 4, and 5 so the work stays staged and reviewable

## Prompt 3 - Completed

### Goal

Populate the side panel with grouped runtime flow variables for observation and controlled testing.

### Instructions

Implement grouped sections in the side panel that show the most important variables in textbox-style fields.

Suggested categories:
- Session And Routing
- Booking Flow
- Scheduling Criteria
- Selected Slot And Booking Result
- Widget / Payload Snapshot

Requirements:
- each important variable should have a label and textbox-style value display
- editable fields should be used only when the runtime should allow controlled overrides for testing
- read-only fields should still use the same minimal textbox visual language where that improves scanning
- prefer grouped clarity over maximal completeness

### Required Outcome

The Chat SandBox panel displays the important runtime flow variables in a categorized and readable way.

### Prompt 3 Completion Note

What changed:

- replaced the remaining panel shell with textbox-style runtime fields for:
  - `Session And Routing`
  - `Booking Flow`
  - `Scheduling Criteria`
  - `Selected Slot And Booking Result`
  - `Widget / Payload Snapshot`
- wired the inspector to current frontend runtime values already available from:
  - session state
  - booking progress payloads
  - selected slot state
  - latest widget / response payload handling
- finished the `Scheduling Criteria` section as editable inspector state instead of static placeholder values by:
  - seeding defaults from tenant config where available
  - seeding a readable default date window for sandbox inspection
  - syncing values from runtime payload data when scheduling-related request context is present
  - allowing local textbox edits for controlled tester prep without yet changing the live chat contract

Prompt 3 intentionally still does not yet implement:

- config JSON preview rendering at the bottom of the panel
- a dedicated backend inspector contract for values not already exposed in current runtime payloads
- guaranteed request-override behavior from edited scheduling criteria values into the live flow

Why this prompt stops here:

- Prompt 3 is complete as the categorized runtime-variable display pass
- config previews are reserved for Prompt 4
- deeper runtime-contract or override behavior belongs to Prompt 5

## Prompt 4 - Completed

### Goal

Add config-preview sections at the bottom of the panel for relevant JSON-based configuration.

### Instructions

Show previews for the config JSON artifacts most relevant to this flow.

Likely sources may include:
- tenant profile JSON
- scheduling public config or equivalent derived config payload
- any other config artifact directly needed to debug runtime criteria

Requirements:
- previews must be clearly separated from live runtime variables
- use a minimal inspector-style presentation
- avoid turning the panel into a full file browser

### Required Outcome

The Chat SandBox panel includes useful config JSON previews at the bottom.

### Prompt 4 Completion Note

What changed:

- replaced the reserved `Config Preview` placeholder with real read-only preview fields at the bottom of `ChatSandBox`
- added a focused `tenant_profile_preview` JSON view sourced from the existing `/config/{tenant}` endpoint
- added a `scheduling_public_config_preview` JSON view sourced from the existing `/scheduling/config/{tenant}` endpoint
- added a lightweight `preview_status` field so testers can see whether each preview loaded successfully or failed independently
- kept the preview content scoped to flow-relevant configuration rather than turning the panel into a broad config/file browser

Prompt 4 intentionally still does not yet implement:

- any new backend inspector payload beyond existing config endpoints
- deeper live-flow runtime synchronization for values that are not already available in the current frontend/runtime contract
- verification coverage for the new preview sections

Why this prompt stops here:

- Prompt 4 is complete as the config-preview pass
- any additional live runtime contract work belongs to Prompt 5
- focused verification belongs to Prompt 6

## Prompt 5 - Completed

### Goal

Wire the Chat SandBox page to the current runtime so the displayed variables reflect the actual live flow.

### Instructions

Connect the panel to the complete chat flow so values update as the tester interacts with the page.

Requirements:
- reflect the state transitions that matter across:
  - initial chat
  - service suggestion
  - scheduling availability lookup
  - slot selection
  - contact collection
  - booking completion
- prefer explicit backend-fed values where possible instead of fragile frontend inference
- if additional backend payload is needed, keep the contract focused and stable

### Required Outcome

The Chat SandBox panel shows live, relevant flow data rather than static placeholders.

### Prompt 5 Completion Note

What changed:

- added a focused backend `inspector_payload` contract to chat-flow responses so the sandbox can read live flow state from a stable payload instead of relying only on frontend inference
- extended the scheduling availability widget payload with backend-fed request details so the inspector can display:
  - `service_id`
  - `date_from`
  - `date_to`
  - `timezone`
  - `preferred_days`
  - `preferred_time_range`
- wired the Chat SandBox frontend to prefer the new inspector payload for:
  - session / routing state
  - response type
  - scheduling criteria snapshot
  - selected slot carry-forward
  - widget snapshot slot count / service metadata
- kept the contract narrow and runtime-focused rather than exposing broad internal state

Prompt 5 intentionally still does not yet implement:

- final verification coverage for the new inspector contract and page behavior
- broader inspector sections beyond the currently scoped runtime groups

Why this prompt stops here:

- Prompt 5 is complete as the live runtime wiring pass
- verification and non-regression checks belong to Prompt 6

## Prompt 6 - Completed

### Goal

Verify the new Chat SandBox flow, runtime inspector behavior, and non-regression of existing chat surfaces.

### Instructions

Add or update focused tests and perform manual verification as needed.

Requirements:
- verify the new page loads correctly
- verify the panel can be uncovered or used during testing
- verify grouped runtime variables render meaningfully
- verify config preview sections render
- verify existing `index.html` and `cal.html` behavior is not unintentionally broken
- follow repo temp-path rules during any test execution

### Required Outcome

The Chat SandBox page and its runtime inspector behavior are verified and documented in this file.

### Prompt 6 Completion Note

What changed:

- added focused integration coverage for the new `ChatSandBox` page structure and inspector/config-preview wiring
- added focused integration coverage for the new backend `inspector_payload` contract and availability request snapshot data
- re-ran existing related integration coverage to guard against regressions in:
  - availability intent gating
  - frontend booking UI assets / wiring
  - `cal.html` scheduling sandbox behavior

Verification completed:

- automated tests run with external temp paths and external `--basetemp`
- command used:
  - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_availability_intent_gating.py .\\tests\\integration\\test_frontend_booking_ui.py .\\tests\\integration\\test_cal_html.py -q --basetemp="F:\\temp\\clinic-ai-assistant\\pytest-slot-widget-final"`
- result:
  - `19 passed`

Manual verification notes:

- the new `ChatSandBox` page is now structurally served and covered for inspector toggle/panel wiring, runtime field presence, and config preview presence
- branch-level manual browser verification is still recommended before merge to `main`
