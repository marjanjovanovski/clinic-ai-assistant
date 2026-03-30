# 20260330_1223_AGENT - Scheduling Contract and Flow Extraction

This document defines the execution-ready task plan for tightening the scheduling flow, extracting scheduling-owned logic out of `ai_agent.py`, and aligning the current slot-list widget with the agreed scheduling-first product contract.

Execution of this task must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Execution Tracking Instructions

Before executing any prompt in this document, the implementing AI agent must first read this file and understand the current status.

After each completed prompt, stop, update prompt status in this file, and ask `Commit changes?`
Do not auto-advance to the next prompt.

As soon as a prompt is executed, this file must be updated in two places:
- at the top of the document in the global status summary
- in the corresponding prompt section header

Status values allowed in this document:
- `Pending`
- `Completed`
- `Blocked`

## Token Efficiency Guidance

- treat this as a narrow MVP tightening task, not a redesign brief
- do not restudy postponed brainstorming topics unless this file explicitly requires them
- prefer reusing existing scheduling and conflict logic over inventing parallel paths
- prefer code moves and small contract updates over large rewrites
- when a prompt names exact files or behaviors, stay inside that surface
- if a choice is already locked in this file, implement it directly instead of reopening debate
- completion notes must stay compact:
  - `Changed`
  - `Verified`
  - `Blocked`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-30`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Scheduling Contract Lock - Pending
- Prompt 2 - Scheduling Service Boundary - Pending
- Prompt 3 - Scheduling Extraction Core - Pending
- Prompt 4 - Scheduling Extraction Integration - Pending
- Prompt 5 - Config And Language Support - Pending
- Prompt 6 - Slot Widget Alignment - Pending
- Prompt 7 - Regression Coverage - Pending
- Prompt 8 - Technical Verification - Pending
- Prompt 9 - Manual Testing - Pending
- Prompt 10 - Merge To Main - Pending

## Source Brainstorming Coverage

This task is derived from the following previously created DOC notes:

- [../20260329_1704_DOC - Scheduling Flow UX and Logic Brainstorm/20260329_1704_DOC - Scheduling Flow UX and Logic Brainstorm.md](../20260329_1704_DOC%20-%20Scheduling%20Flow%20UX%20and%20Logic%20Brainstorm/20260329_1704_DOC%20-%20Scheduling%20Flow%20UX%20and%20Logic%20Brainstorm.md)
- [../20260329_2037_DOC - Service Flow Independence Draft/20260329_2037_DOC - Service Flow Independence Draft.md](../20260329_2037_DOC%20-%20Service%20Flow%20Independence%20Draft/20260329_2037_DOC%20-%20Service%20Flow%20Independence%20Draft.md)
- [../20260329_2039_DOC - Month Calendar Widget Draft/20260329_2039_DOC - Month Calendar Widget Draft.md](../20260329_2039_DOC%20-%20Month%20Calendar%20Widget%20Draft/20260329_2039_DOC%20-%20Month%20Calendar%20Widget%20Draft.md)
- [../20260329_2049_DOC - Progressive Flow Stitching Draft/20260329_2049_DOC - Progressive Flow Stitching Draft.md](../20260329_2049_DOC%20-%20Progressive%20Flow%20Stitching%20Draft/20260329_2049_DOC%20-%20Progressive%20Flow%20Stitching%20Draft.md)
- [../20260330_1146_DOC - Dynamic Flow Configuration Brainstorm/20260330_1146_DOC - Dynamic Flow Configuration Brainstorm.md](../20260330_1146_DOC%20-%20Dynamic%20Flow%20Configuration%20Brainstorm/20260330_1146_DOC%20-%20Dynamic%20Flow%20Configuration%20Brainstorm.md)

Coverage rule for this execution task:

- the scheduling brainstorming file is the primary source of truth for MVP scheduling behavior
- service-flow independence is in scope as a design constraint for scheduling
- month calendar widget is not in scope for this task and should remain a follow-up
- progressive flow stitching is not a standalone implementation target here, but lightweight context carry and natural handoff should be preserved
- dynamic flow configuration is postponed and must not be pulled into this MVP task

## Purpose

The purpose of this task is to:

- make scheduling-first behavior explicit and stable
- ensure typed date and relative-date availability requests behave correctly
- prevent premature booking transitions before a real slot exists
- define one clean scheduling-to-booking handoff path
- define one clean slot-conflict recovery path
- move scheduling-owned logic out of `ai_agent.py` into a clearer service boundary
- keep wording and language-specific behavior config-driven where appropriate

## Working Rules For The Implementing AI Agent

- treat this as a tightening and extraction task, not a broad redesign
- preserve existing working behavior unless the scheduling contract in this file explicitly changes it
- do not introduce hard-coded business phrase dictionaries in Python
- keep language-aware scheduling intent handling narrow and config-driven
- reuse existing slot-conflict and hold logic where possible instead of duplicating it
- do not pull postponed month-calendar or dynamic-flow-engine scope into this task
- keep top-level orchestration in `ai_agent.py` initially unless a smaller safe extraction is clearly identified
- update this file immediately after each completed prompt
- do not mark a prompt as completed unless the requested work was actually implemented and verified as far as possible

## Testing And Verification Rules

- follow repo rules to keep test artifacts out of the repository
- when running pytest, use external `TMP` / `TEMP` and an external `--basetemp`
- prefer focused scheduling-related verification over broad full-suite retries
- protect both backend behavior and current frontend slot-widget behavior against regression
- if some scheduling logic already exists, verify reuse before adding new behavior
- if environment limits block verification, document the blocker clearly

## Do Not Break

- existing tenant profile loading and JSON config ownership
- existing booking contact collection behavior after a slot is truly selected
- existing slot hold and slot-unavailable recovery paths that are already working
- current slot-list widget rendering contract unless this task explicitly changes it
- existing service list, service description, and business overview flows
- current chat session state and persisted booking progress behavior

## Current Repo Truth

- `ai_agent.py` already contains partial scheduling routing, handoff, and recovery behavior
- the repo already has scheduling support code outside `ai_agent.py`, including scheduling capability and hold logic
- the current frontend already serves a slot-list widget and scheduling-related surfaces through static HTML/CSS/JS
- the month calendar/day-picker is not yet the current implementation target
- dynamic flow configuration has been identified as useful later work, but not MVP scope
- the current task should lock the scheduling contract before broader UX expansion

## Locked Decisions

The following decisions are already locked for this task and must not be reopened during implementation:

- typed specific dates must receive direct availability answers first
- broad-range requests such as `next week` should usually narrow by date instead of dumping many slots
- reservation language without a selected slot stays in scheduling-first behavior
- slot click should directly hand off into booking for MVP
- slot-conflict recovery must stay inside scheduling recovery
- scheduling language support must be config-aware per tenant language
- wording, labels, and behavior knobs belong in JSON/config, not Python wording logic

## Out Of Scope

The following items must not be pulled into this task unless the user explicitly expands scope:

- month calendar / day-picker implementation
- dynamic flow configuration engine
- formal progressive flow stitching as a standalone feature
- broad orchestration redesign outside the narrow scheduling extraction target
- rescheduling and cancellation flows
- provider-specific filtering unless already required by the current scheduling contract

## Primary File Targets

Expected primary implementation surface:

- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- `clinic-ai-assistant-src/backend/app/services/` scheduling-related helpers/modules created or refined by this task
- `clinic-ai-assistant-src/backend/app/config/profiles/*.json` or the appropriate config-owned scheduling-language surface
- `clinic-ai-assistant-src/frontend/widgets/slot-list/slot-list.js`
- `clinic-ai-assistant-src/frontend/widgets/widget-registry.js` only if required by the widget contract
- the most relevant existing scheduling and frontend integration tests

## Architecture Guidance

### MVP Scheduling Contract

This task should implement or preserve these rules:

- availability intent enters scheduling-first behavior
- typed specific dates receive direct availability answers first
- broad-range requests such as `next week` should usually confirm availability in-range and ask the user to narrow by date
- reservation language without a selected slot should stay in scheduling-first behavior
- slot selection should directly hand off into booking for MVP, without an extra confirmation step
- if a selected slot is lost, the user should remain inside scheduling recovery and see replacements or refreshed availability

### Language-Aware Intent Handling

This task must treat language-aware scheduling intent as a first-class requirement.

Required direction:

- time-window and date-like concepts such as `afternoon`, `Tuesday`, `next week` must be supported in a config-aware way per tenant language
- examples for Macedonian and English are expected to differ by config/language context
- this support should be intent-based and config-driven where practical
- do not solve this by building a large Python-only phrase dictionary layer

### Extraction Boundary

The safest first extraction target is:

- scheduling entry assessment
- availability response shaping
- scheduling-to-booking handoff payload preparation
- widget payload assembly for scheduling results and recovery
- slot-conflict recovery reuse/alignment

Leave broader lifecycle orchestration in `ai_agent.py` initially unless a smaller additional extraction is clearly safe.

## Desired Outcome

After all implementation prompts are complete, the repo should have:

- a clearer scheduling contract implemented in code
- scheduling-first handling for broad, relative, and specific-date requests
- explicit config-aware language handling for scheduling intent/time-window/date concepts
- scheduling-owned behavior extracted from `ai_agent.py` into a clearer service boundary
- current slot-list widget behavior aligned to the contract
- focused regression coverage for the tightened scheduling behavior

## Prompt 1 - Scheduling Contract Lock - Pending

### Goal

Lock the exact MVP scheduling contract in code-facing terms before moving logic.

### Instructions

Inspect only the current scheduling-related code paths needed to lock the contract and make the contract explicit in code-facing terms.

Requirements:
- identify the current entry points for:
  - scheduling intent
  - typed date handling
  - broad-range handling such as `next week`
  - slot-selected booking handoff
  - slot-conflict recovery
- produce a compact implementation contract covering only:
  - scheduling-first entry rules
  - typed-date direct answer rules
  - broad-range narrowing rules
  - reservation-without-slot rules
  - slot-selected direct handoff rules
  - slot-conflict recovery rules
- explicitly note which current behaviors are:
  - reused as-is
  - tightened
  - out of scope
- do not redesign month-calendar or dynamic-flow behavior here

### Required Outcome

The scheduling contract is explicit enough that extraction and implementation work can proceed without ambiguity.

## Prompt 2 - Scheduling Service Boundary - Pending

### Goal

Define and create the first safe scheduling-owned service boundary outside `ai_agent.py`.

### Instructions

Introduce or refine the smallest dedicated scheduling service/module boundary needed for the agreed extraction target.

Requirements:
- keep top-level orchestration stable
- define a clean call surface for:
  - scheduling assessment
  - availability response shaping
  - handoff payload preparation
  - recovery/widget payload shaping where needed
- align the boundary with existing scheduling capability modules where practical
- prefer extending an existing scheduling-owned module over creating many new files
- avoid duplicate code paths for slot conflict and hold behavior
- document the chosen ownership split in the task completion note

### Required Outcome

A clear scheduling-owned module boundary exists and is ready to absorb extracted logic safely.

## Prompt 3 - Scheduling Extraction Core - Pending

### Goal

Move the lowest-risk scheduling-owned logic out of `ai_agent.py` without widening scope.

### Instructions

Extract only the core targeted scheduling behavior into the service boundary created in Prompt 2.

Requirements:
- move scheduling entry assessment
- move availability response shaping
- keep behavior stable unless the task contract explicitly changes it
- preserve current working hold/conflict logic by reuse rather than change in this prompt
- do not broaden this prompt into full orchestration redesign
- do not change unrelated booking, catalog, or business-overview behavior

### Required Outcome

`ai_agent.py` delegates core scheduling assessment and response shaping through a clearer service boundary and the scheduling behavior remains correct.

## Prompt 4 - Scheduling Extraction Integration - Pending

### Goal

Complete the remaining scheduling extraction work needed for booking handoff and recovery alignment.

### Instructions

After Prompt 3 is stable, extract only the remaining integration-oriented scheduling behavior.

Requirements:
- move booking handoff payload preparation for slot-selected transitions
- move widget payload assembly for scheduling and recovery responses where appropriate
- align extracted behavior with existing hold/conflict support
- reuse existing slot-conflict and hold logic wherever practical
- do not redesign the broader orchestration lifecycle here

### Required Outcome

The extracted scheduling boundary now covers core assessment plus handoff/recovery integration without duplicating existing recovery logic.

## Prompt 5 - Config And Language Support - Pending

### Goal

Implement the narrow config-driven scheduling language support required for MVP.

### Instructions

Add or update only the config-owned support needed for narrow language-aware scheduling concepts in MVP.

Requirements:
- keep wording and behavior knobs in JSON/config
- support tenant-language-aware scheduling concepts for relative dates and time windows
- handle concepts such as `afternoon`, `Tuesday`, `next week` according to the tenant language context
- avoid expanding hard-coded Python phrase dictionaries
- keep the scope narrow to scheduling-intent/date/time-window behavior required by this task
- prefer one clean config contract over many ad hoc keys
- do not attempt universal multilingual parsing in this prompt

### Required Outcome

Scheduling intent and date/time-window behavior are supported in a config-aware, language-aware MVP shape.

## Prompt 6 - Slot Widget Alignment - Pending

### Goal

Align the current slot-list widget path with the tightened scheduling contract.

### Instructions

Update the current slot-widget behavior only where required to match the agreed MVP scheduling rules.

Requirements:
- preserve the current 3-day widget as the quick-view surface
- ensure typed-date responses do not force widget usage unnecessarily
- ensure broad-range requests narrow sensibly instead of overwhelming users
- ensure slot click transitions directly into booking handoff for MVP
- ensure the selected slot remains clearly represented while booking begins
- keep month calendar/day-picker work out of scope for this task
- avoid visual redesign unless required for contract clarity
- keep changes focused on behavior and interaction contract

### Required Outcome

The existing slot-list widget and chat responses behave consistently with the MVP scheduling contract.

## Prompt 7 - Regression Coverage - Pending

### Goal

Protect the tightened scheduling behavior from silent regression.

### Instructions

Add or update the smallest focused automated coverage set that protects the contract changed in this task.

Requirements:
- cover typed specific date handling
- cover at least one broad-range narrowing path such as `next week`
- cover reservation intent without premature booking
- cover slot-selected direct handoff into booking
- cover slot-conflict recovery reuse or aligned behavior
- cover language-aware scheduling intent/config behavior at least at the narrow MVP boundary
- prefer updating existing scheduling/frontend integration tests before adding many new files
- keep the coverage high-signal and behavior-focused
- target the most relevant existing test surfaces first, such as:
  - backend scheduling integration tests
  - availability intent gating tests
  - frontend slot-widget integration tests
  - current scheduling capability unit tests where extraction changes ownership

### Required Outcome

The new scheduling contract is protected by focused, high-signal automated coverage.

## Prompt 8 - Technical Verification - Pending

### Goal

Run focused verification and confirm the tightened scheduling flow works technically.

### Instructions

Run the smallest relevant focused checks for backend scheduling behavior and current frontend slot widget behavior.

Requirements:
- use repo-clean temp-path rules
- verify the most relevant backend scheduling tests
- verify the relevant frontend scheduling/slot-widget integration coverage
- confirm no repo-local temp residue remains
- document blockers clearly if full verification cannot be completed
- avoid broad suites unless the changed surface truly requires them
- prefer one focused backend run and one focused frontend/integration run over many overlapping reruns

### Required Outcome

The tightened scheduling flow is technically verified and documented honestly.

## Prompt 9 - Manual Testing - Pending

### Goal

Track manual verification for the tightened scheduling contract before merge.

### Instructions

Keep this prompt pending until the user confirms manual verification is complete.

Requirements:
- perform or track the manual checks below
- record what passed and what was blocked
- keep `Merge To Main` pending until merge actually happens

### Required Outcome

Manual verification and branch readiness are tracked explicitly.

## Prompt 10 - Merge To Main - Pending

### Goal

Keep the task visible until the branch is actually merged.

### Instructions

This prompt stays pending after manual verification and only closes when merge is confirmed.

Requirements:
- keep this prompt pending while work is complete but not yet merged
- mark `Merge To Main` completed only after merge is confirmed
- archive the whole task folder only after merge is complete

### Required Outcome

The task cannot silently disappear in a completed-but-unmerged state.

---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is for execution guidance and manual verification only.

### Manual Testing

Use this markdown section as the compact human-readable manual verification checklist. The row-level state tracker lives in `manual_testing_coverage.json`.

### Category 1 - Typed Date Scheduling

- `Test 1.1 - Specific date with availability`
  Purpose: confirm a typed specific date returns direct availability for that date before any widget-first redirection.
  Steps:
  1. Open the chat surface for a tenant with scheduling enabled.
  2. Ask for availability on a concrete date that has available slots.
  3. Confirm the reply references that requested date directly.
  4. Confirm the user sees the available slots for that date in the reply or attached widget payload.
  5. Confirm the system does not prematurely ask for booking details.
- `Test 1.2 - Specific date without availability`
  Purpose: confirm a typed specific date with no availability returns a truthful assessment and alternatives.
  Steps:
  1. Ask for availability on a concrete date known to have no slots.
  2. Confirm the system states that the requested date has no available slots.
  3. Confirm the reply offers nearby dates, next availability, or a valid scheduling exploration path.
  4. Confirm the flow remains scheduling-focused and does not jump into booking.

### Category 2 - Broad And Relative Scheduling

- `Test 2.1 - Broad range such as next week`
  Purpose: confirm broad-range scheduling asks for narrowing rather than dumping too many results.
  Steps:
  1. Ask for availability using a broad-range phrase such as `next week`.
  2. Confirm the system interprets the request as scheduling intent.
  3. Confirm it either states that availability exists in that range or truthfully states none exists.
  4. Confirm it asks the user to narrow by date or gives a focused next-step prompt instead of flooding the chat with many slots.
- `Test 2.2 - Relative date and time window`
  Purpose: confirm relative date and time-window concepts are resolved usefully.
  Steps:
  1. Ask for something like `tomorrow afternoon`.
  2. Confirm the system treats this as scheduling intent.
  3. Confirm the system resolves the request into a concrete day or day-plus-time-window behavior.
  4. Confirm the reply returns filtered availability or asks one targeted clarification only if needed.

### Category 3 - Reservation Intent Without Slot

- `Test 3.1 - Reserve request before slot selection`
  Purpose: confirm reservation language without a selected slot stays in scheduling-first behavior.
  Steps:
  1. Ask to reserve or book an appointment without naming a slot.
  2. Confirm the system does not immediately ask for name, phone, or email.
  3. Confirm the reply stays focused on finding a valid appointment time first.
  4. Confirm the system requests narrowing or returns scheduling options as appropriate.

### Category 4 - Slot Selection And Booking Handoff

- `Test 4.1 - Slot click enters booking directly`
  Purpose: confirm slot selection triggers direct booking handoff for MVP.
  Steps:
  1. Reach a state where a slot-list widget is shown.
  2. Click a slot.
  3. Confirm the selected slot is clearly reflected in the next response.
  4. Confirm booking starts immediately with the first required booking field.
  5. Confirm the user is able to change or back out from the selected slot path if needed.

### Category 5 - Slot Conflict Recovery

- `Test 5.1 - Selected slot becomes unavailable`
  Purpose: confirm lost-slot behavior remains inside scheduling recovery.
  Steps:
  1. Simulate or reproduce a slot-unavailable path after slot selection.
  2. Confirm the system clearly explains that the chosen slot is no longer available.
  3. Confirm the reply offers replacement slots or refreshed availability.
  4. Confirm the user is not forced to restart the whole conversation from scratch.

### Category 6 - Language-Aware Scheduling Intent

- `Test 6.1 - Macedonian scheduling concepts`
  Purpose: confirm scheduling-related concepts work under Macedonian tenant language context.
  Steps:
  1. Use a tenant configured for Macedonian.
  2. Ask for availability using Macedonian scheduling concepts such as a weekday, time window, or relative period.
  3. Confirm the system interprets the message as scheduling intent.
  4. Confirm the returned behavior follows the same scheduling contract as the English flow.
- `Test 6.2 - English scheduling concepts`
  Purpose: confirm scheduling-related concepts work under English tenant language context.
  Steps:
  1. Use a tenant configured for English.
  2. Ask for availability using English scheduling concepts such as `Tuesday`, `afternoon`, or `next week`.
  3. Confirm the system interprets the message as scheduling intent.
  4. Confirm the returned behavior follows the same scheduling contract as the non-English flow.

### Category 7 - No Regression In Non-Scheduling Chat

- `Test 7.1 - Catalog and business overview still behave correctly`
  Purpose: confirm scheduling extraction does not break non-scheduling flows.
  Steps:
  1. Ask for service list or business overview content.
  2. Confirm the reply stays in the correct non-scheduling flow.
  3. Confirm the system does not incorrectly inject scheduling behavior.
