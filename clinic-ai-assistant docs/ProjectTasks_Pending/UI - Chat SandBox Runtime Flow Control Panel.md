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

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending
- Prompt 6 - Pending

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

## Prompt 1 - Pending

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

## Prompt 2 - Pending

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

## Prompt 3 - Pending

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

## Prompt 4 - Pending

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

## Prompt 5 - Pending

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

## Prompt 6 - Pending

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
