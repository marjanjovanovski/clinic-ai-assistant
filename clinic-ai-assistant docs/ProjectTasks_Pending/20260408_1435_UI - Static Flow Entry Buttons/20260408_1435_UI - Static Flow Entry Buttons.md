# 20260408_1435_UI - Static Flow Entry Buttons

Add static flow-entry buttons to the main chat shell so the user can immediately enter key flows such as `Каталог`, `Слободни термин`, and `Закажи`, while starting with a proposal-first prompt before implementation.

Execution must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Merge To Main

- `Pending`

## Prompt Status Summary

- Prompt 1 - Proposal And Scope Lock - Completed
- Prompt 2 - Implement Static Flow Entry Buttons - Completed
- Prompt 3 - Lightweight Technical Verification - Completed
- Prompt 4 - Manual Verification And Notes - Pending
- Prompt 5 - Merge To Main - Pending

## Current Active Prompt

- `Prompt 4`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-04-16`

## Purpose

- add static high-visibility flow-entry buttons for `Каталог`, `Слободни термин`, and `Закажи`
- let a user click once and immediately engage the intended flow instead of typing a first message
- start with a proposal so placement, treatment, and click behavior are reviewed before code implementation
- keep the work token-efficient by using a small number of high-value execution prompts

## Working Rules For The Implementing AI Agent

- treat this markdown file as the workflow authority
- work prompt-by-prompt only
- after completing a tracked prompt, update task status in both required places, then stop and ask `Commit changes?`
- preserve current widget contracts unless a shell-level integration change is explicitly needed
- prefer the cheapest reliable integration path that still makes each button immediately engage the intended flow
- keep static entry controls distinct from the conversational transcript so they feel like shell navigation, not bot messages
- make button labels patient-friendly and keep Macedonian-first labels unless the current page or tenant config requires another language
- if a click behavior could be implemented either by synthetic user-message submission or by a more explicit frontend action contract, compare both and choose the safer lower-regression path

## Testing And Verification Rules

- use minimal technical verification first
- focus on flow-entry behavior, shell placement, and obvious regression risk
- do not expand this task into broad widget redesign
- if Python or pytest verification is used, use external `TMP` / `TEMP` and an external `--basetemp`
- keep repo-local scratch files out of the repo

## Do Not Break

- existing `/chat` request flow
- existing scheduling slot-selection behavior
- existing booking progress and booking summary rendering
- current tenant config loading and session behavior
- existing manual text-based ways of entering catalog, scheduling, or booking

## Current Repo Truth

- the main chat shell currently lives in `clinic-ai-assistant-src/frontend/index.html`
- the chat surface already calls `/chat`, `/config/{tenant}`, and `/scheduling/select-slot`
- the main chat currently relies on typed input and widget interactions; it does not yet expose static shell buttons for direct flow entry
- catalog and booking behavior already exist in backend orchestration and profile/config data
- scheduling entry behavior already exists through text requests and slot widgets, so this task should integrate with existing flow logic rather than create duplicate business paths

## Architecture Guidance

- inspect the current `frontend/index.html` shell and any shared frontend helpers before deciding placement or implementation style
- inspect current backend flow-entry logic for catalog, scheduling, and booking so button clicks reuse the same contracts where possible
- if the frontend needs a tiny helper for static flow-entry actions, keep it narrow and local to the chat shell
- prefer explicit low-risk trigger messages or a small action map over spreading special cases across unrelated files
- keep future extensibility in mind so more static entry buttons can be added later without rewriting the interaction model

## Prompt 1 - Proposal And Scope Lock - Completed

### Goal

Inspect the current chat shell and propose how the static flow-entry buttons should look and behave before making code changes.

### Required Outcome

A concrete proposal exists for:

- visual placement such as above the transcript, below the header, or another shell-level position
- button treatment and grouping
- click behavior for `Каталог`, `Слободни термин`, and `Закажи`
- how the click should immediately engage the intended flow
- the safest implementation path with the lowest regression risk

### Prompt 1 Instructions

- inspect the current shell structure and identify the exact insertion zone for these buttons
- compare at least two placement options briefly, then recommend one
- define whether button clicks should:
  - submit authoritative hidden messages into the existing chat flow
  - call a narrow frontend action helper that still reuses existing backend flow entry
  - or use another clearly justified low-risk path
- explain how each button should map to user intent:
  - `Каталог`
  - `Слободни термин`
  - `Закажи`
- keep the proposal compact and implementation-oriented
- do not edit code in this prompt

### Prompt 1 Outcome

- recommended placement: shell-level strip directly below the header so the controls stay distinct from the transcript
- rejected placement: inside the transcript, because it would mix navigation chrome with conversation history and widget rendering
- click behavior: reuse the existing `performSend(...)` path with centralized explicit trigger messages instead of introducing a separate backend contract
- mapping:
  - catalog button -> service-list trigger
  - availability button -> availability trigger
  - booking button -> booking-start trigger using the safest existing booking entry phrasing
- safest implementation path: lightweight shell markup plus a small frontend trigger map with no duplicate backend flow logic

## Prompt 2 - Implement Static Flow Entry Buttons - Completed

### Goal

Implement the approved shell-level static buttons and wire them so each click immediately engages the intended flow.

### Required Outcome

The main chat shell exposes clear static flow-entry buttons and clicking each one starts the expected flow without requiring typed input first.

### Must Cover

- shell-level placement only
- immediate engagement into the intended flow
- preserved existing typed-input behavior
- preserved widget behavior
- visually clear active click affordance
- desktop and mobile sanity

### Prompt 2 Instructions

- implement the buttons in the recommended shell location from Prompt 1
- keep the implementation lightweight and easy to extend
- make sure each click is distinguishable in behavior:
  - `Каталог` should immediately engage the catalog/service-list path
  - `Слободни термин` should immediately engage scheduling / availability discovery
  - `Закажи` should immediately engage the booking-oriented path or the safest existing booking-entry equivalent
- avoid introducing duplicate backend flow logic when the current orchestration already supports the intent
- if text triggers are used under the hood, keep them explicit and centralized so the mapping is easy to audit later
- preserve accessibility basics such as button semantics and visible focus

### Prompt 2 Outcome

- added a responsive shell-level button strip to the main chat shell and shared shell variants
- centralized localized labels and trigger text in the frontend so tenant language can swap the button copy
- routed button clicks through the existing `performSend(...)` helper with active-state affordance and no new backend path
- preserved typed input, slot widgets, booking progress, summary rendering, and reset behavior

## Prompt 3 - Lightweight Technical Verification - Completed

### Goal

Do a cheap technical verification pass for the new static flow-entry integration.

### Required Outcome

Obvious structural issues are checked and any technical risks are summarized plainly.

### Prompt 3 Instructions

- run only the lightest useful verification for the touched files
- prefer static review or focused checks before heavier verification
- confirm that the integration preserves existing core shell behavior and does not obviously break IDs, event wiring, or fetch entry points
- if a browser/manual-only point remains, note it clearly and leave it for Prompt 4

### Prompt 3 Outcome

- updated focused frontend integration coverage for shell-level entry buttons, trigger mapping, and event wiring
- verification stayed lightweight and targeted to touched shell behavior and fetch entry points
- remaining manual-only checks: real-browser placement on narrow viewports and live confirmation that each button enters the intended flow

## Prompt 4 - Manual Verification And Notes - Pending

### Goal

Use the companion `manual_testing_coverage.json` to verify the flow-entry buttons manually and capture the outcome.

### Required Outcome

Manual verification is recorded in the JSON and the markdown notes stay compact.

### Prompt 4 Instructions

- use `manual_testing_coverage.json` in this folder as the row-level tracker
- update row statuses, comments, summary counts, and merge-readiness honestly
- keep markdown notes compact and point to the JSON as the operational tracker

## Prompt 5 - Merge To Main - Pending

### Goal

Keep merge tracking explicit and separate from implementation completion.

### Instructions

- mark this prompt completed only after the task work is merged

## Manual Testing

- Category 1 - Shell placement and visibility
  - Test 1.1 - Buttons appear in a clear shell-level location
- Category 2 - Direct flow entry behavior
  - Test 2.1 - `Каталог` enters catalog flow
  - Test 2.2 - `Слободни термин` enters scheduling flow
  - Test 2.3 - `Закажи` enters booking-oriented flow
- Category 3 - Regression and responsiveness
  - Test 3.1 - Typed chat still works after button usage
  - Test 3.2 - Layout remains usable on narrow width
