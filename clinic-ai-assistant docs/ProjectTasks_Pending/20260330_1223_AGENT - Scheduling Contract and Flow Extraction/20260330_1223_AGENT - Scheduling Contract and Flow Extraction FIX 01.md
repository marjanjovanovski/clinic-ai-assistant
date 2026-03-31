# 20260330_1223_AGENT - Scheduling Contract and Flow Extraction FIX 01

This document defines the execution-ready follow-up fix plan for the manual-testing failures discovered after the original scheduling contract extraction implementation.

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

## Purpose

The purpose of this fix follow-up is to:

- restore the clickable slot-widget contract for scheduling results
- make typed-date, broad-range, weekday, and time-window requests resolve truthfully
- keep no-availability follow-through inside scheduling instead of leaking into booking
- tighten slot-selection follow-through, timezone display, and change-slot escape behavior
- clean up language/script and encoding issues surfaced during manual verification
- provide a lean retesting surface that maps back to every failed manual-testing row from the parent task

## Hard Requirement

- do not display appointment times as plain text availability lists
- if appointment times are offered to the user, they must be rendered as clickable slot widgets

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-31`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Failure Map And Contract Lock - Pending
- Prompt 2 - Scheduling Request Resolution - Pending
- Prompt 3 - Widget-First Availability Presentation - Pending
- Prompt 4 - Scheduling Recovery And Booking Boundaries - Pending
- Prompt 5 - Slot Handoff And Display Integrity - Pending
- Prompt 6 - Regression Coverage - Pending
- Prompt 7 - Technical Verification - Pending
- Prompt 8 - Manual Testing - Pending
- Prompt 9 - Merge To Main - Pending

## Source Of Follow-Up Truth

This fix follow-up is derived from:

- [20260330_1223_AGENT - Scheduling Contract and Flow Extraction.md](./20260330_1223_AGENT%20-%20Scheduling%20Contract%20and%20Flow%20Extraction.md)
- [manual_testing_coverage.json](./manual_testing_coverage.json)
- [20260330_1608_DOC - Runtime Trace Follow-Up Fix Plan.md](./20260330_1608_DOC%20-%20Runtime%20Trace%20Follow-Up%20Fix%20Plan.md)

## Working Rules For The Implementing AI Agent

- keep this follow-up narrow and execution-oriented
- treat the original scheduling extraction contract as the base; only tighten broken behavior
- prefer fixing shared root causes over patching each failed row separately
- prefer the smallest viable code change that restores the contract
- do not redesign UX, orchestration, or data structures unless a failed row requires it
- preserve the current slot-list widget instead of introducing month-calendar scope
- keep scheduling-owned behavior in the scheduling service boundary where practical
- do not regress non-scheduling catalog, service, or business-overview flows
- keep manual-testing traceability explicit back to the original failed rows

## Testing And Verification Rules

- follow repo rules to keep test and runtime residue out of the repository
- use external `TMP` / `TEMP` and external pytest `--basetemp`
- prefer focused unit/integration coverage around the observed failures
- verify both Macedonian and English tenant behavior where the fix touches language-sensitive scheduling logic
- use the companion fix JSON as the operational retest tracker for failed and follow-up-sensitive behavior

## Do Not Break

- direct slot-click handoff into booking when the user selects a concrete slot
- current booking contact collection after a valid slot is selected
- existing slot-conflict recovery behavior already covered by the parent task
- config-owned scheduling language behavior and tenant profile loading
- non-scheduling service list, service description, and business overview flows

## Out Of Scope For FIX 01

- month calendar or day-picker work
- rescheduling or cancellation flows
- broad booking UX redesign outside the failed scheduling handoff path
- general encoding cleanup outside scheduling-related surfaces touched by this fix

## Primary File Targets

Expected primary implementation surface:

- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- the most relevant existing scheduling unit and integration tests
- frontend scheduling surfaces only if the existing backend widget contract cannot satisfy the required clickable-slot behavior

## Unique Failure Map

The original manual-testing JSON contains repeated symptoms across several rows. This fix task groups them into the unique implementation problems below so the execution stays token-efficient.

1. Specific-date requests are not consistently resolved to the requested day.
Mapped failures:
- original rows `1`, `2`, `3`

2. Availability is still shown as inline text lists where the product contract now requires clickable slot widgets.
Mapped failures:
- original rows `2`, `4`, `14`, `32`

3. No-availability replies are too generic and do not provide scheduling-first recovery.
Mapped failures:
- original row `8`

4. Follow-up after no availability can incorrectly fall into booking contact collection.
Mapped failures:
- original row `9`

5. Broad and relative requests such as `next week`, weekdays, and `tomorrow afternoon` are not resolving truthfully enough.
Mapped failures:
- original rows `10`, `11`, `12`, `13`, `14`, `15`, `16`, `17`, `32`

6. Slot-selection follow-through still has user-facing integrity issues.
Mapped failures and remarks:
- original row `24` remark: selected-slot response shows DST-shifted time
- original row `26`: no change-slot / escape path once booking starts

7. Language/script and encoding presentation still leak through in some scheduling surfaces.
Mapped remarks:
- original row `6` remark: Macedonian no-availability text appeared in Latin transliteration
- original row `35` remark: residual widget text displayed broken mojibake characters in the English tenant flow

## Execution Order Rationale

Prompts are ordered by dependency:

1. lock the exact unique failures and contract updates first
2. fix date/range interpretation before shaping presentation
3. restore widget-first availability presentation after request resolution is trustworthy
4. tighten recovery and booking boundaries after availability behavior is stable
5. clean up slot-handoff UX integrity once the core scheduling surface is correct
6. add regression coverage only after the intended behavior is locked
7. run focused technical verification
8. rerun manual testing through the companion fix JSON

## Cost-Reduction Guidance

- collapse duplicate manual-testing failures into shared root-cause fixes
- restore the existing contract instead of expanding product scope
- keep fixes inside the current scheduling service and widget payload boundaries
- prefer config-owned language and wording fixes over new Python-only phrase logic
- reuse the existing slot-list widget as the single actionable availability surface
- add only focused regression tests for unique fixed behaviors
- avoid frontend refactors unless the backend cannot satisfy the required widget contract
- keep each prompt scoped to one real execution boundary

## Prompt 1 - Failure Map And Contract Lock - Pending

### Goal

Translate the original manual-testing failures into the smallest code-facing fix contract needed for implementation.

### Instructions

- confirm the unique failure groups listed in this file against the parent JSON and runtime follow-up note
- lock the absolute rule that appointment times must not be displayed as plain text lists and must be rendered through clickable slot widgets
- lock the expected scheduling-first behavior after no-availability responses
- lock the expected slot-selection follow-through requirements:
  - accurate displayed time
  - preserved selected-slot context
  - explicit change-slot escape path while still staying inside the booking/scheduling handoff
- keep month-calendar, rescheduling, and cancellation out of scope

### Cost Rule

- do not redesign anything in this prompt
- only lock what later prompts must implement

### Required Outcome

The fix contract is explicit enough that later prompts can solve root causes instead of re-litigating expectations.

## Prompt 2 - Scheduling Request Resolution - Pending

### Goal

Fix only request-to-date-window resolution for typed dates, weekdays, relative days, time windows, and broad periods before presentation is assembled.

### Primary Surface

- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- closely related scheduling helpers and config-owned language surfaces

### Must Cover

- exact typed dates such as `09.04.2026`
- weekday-based requests
- `next week`
- same-day requests
- combined relative date and time-window requests such as `tomorrow afternoon`
- Macedonian scheduling concepts that currently collapse to the next day incorrectly

### Cost Rule

- solve shared interpretation bugs once instead of per phrase
- do not redesign widget output or booking flow in this prompt

### Required Outcome

The scheduling request window and any time-window filtering reflect what the user actually asked for before any widget or reply text is produced.

## Prompt 3 - Widget-First Availability Presentation - Pending

### Goal

Restore the absolute clickable slot-widget contract for offered appointment times, and keep reply text short and non-listing.

### Primary Surface

- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- frontend slot-list rendering surface if needed by the payload contract

### Must Cover

- specific-date requests with availability
- relative-date requests with availability
- broad-range behavior that should narrow without flooding the chat
- reply text that references the interpreted request truthfully while the widget holds the actionable slots

### Cost Rule

- reuse the existing slot-list widget and current payload shape where possible
- do not add a second scheduling UI surface

### Required Outcome

Scheduling responses stop dumping slot lists into plain text and instead return a short contextual reply plus a clickable slot-list widget whenever slots are actionable.

## Prompt 4 - Scheduling Recovery And Booking Boundaries - Pending

### Goal

Prevent no-availability follow-up from entering booking before a real slot is selected.

### Primary Surface

- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`

### Must Cover

- no-availability replies that should suggest next exploration paths
- follow-up questions such as `koga ima sloboden termin` staying inside scheduling
- protection against jumping into booking contact collection without a selected slot
- language/script shaping for scheduling-facing fallback and no-availability responses

### Cost Rule

- fix the booking-boundary leak without reopening the full booking flow
- keep recovery messaging compact and scheduling-first

### Required Outcome

No-availability flows remain truthful, helpful, and scheduling-first instead of leaking into booking.

## Prompt 5 - Slot Handoff And Display Integrity - Pending

### Goal

Correct selected-slot display integrity and add the smallest supported change-slot escape path.

### Primary Surface

- scheduling handoff helpers
- selected-slot response shaping
- booking-start response payload
- frontend display contract if required

### Must Cover

- selected-slot display time matches the clicked slot without DST drift
- selected-slot confirmation and carry-through remain encoding-safe
- user gets a lean change-slot / back-out path after slot selection without restarting the conversation
- preserve direct booking handoff once a valid slot is selected

### Cost Rule

- preserve the current direct-handoff architecture
- implement the smallest reversible path that satisfies the failed manual test

### Required Outcome

Slot click still starts booking directly, but the user-facing transition is accurate and does not trap the user.

## Prompt 6 - Regression Coverage - Pending

### Goal

Add only focused automated coverage for the unique fixed behaviors in this follow-up.

### Minimum Coverage

- typed-date request resolves to the requested day and returns widget-backed availability
- broad/relative requests resolve truthfully and narrow correctly
- no-availability follow-up stays in scheduling and does not start booking
- selected-slot message reflects the chosen slot time correctly
- change-slot escape path and encoding-safe scheduling display where applicable

### Cost Rule

- avoid one-test-per-row duplication
- prefer one focused test per unique behavior or root cause

### Required Outcome

The new behavior is locked by focused tests instead of depending only on manual retesting.

## Prompt 7 - Technical Verification - Pending

### Goal

Run the smallest focused technical verification set that proves the fix prompts above.

### Verify

- the relevant scheduling unit tests
- the relevant scheduling integration tests
- any focused frontend booking/scheduling test needed by the widget contract

### Completion Notes

- `Changed`
- `Verified`
- `Blocked`

## Prompt 8 - Manual Testing - Pending

### Goal

Retest every failed row from the parent task through the companion fix JSON and confirm whether the branch is now merge-ready.

### Verify

- use [manual_testing_coverage_FIX01.json](./manual_testing_coverage_FIX01.json)
- keep row-level retest results there instead of duplicating them in markdown
- if new bugs are discovered, record them plainly and decide whether they belong in this fix or in `FIX 02`

## Prompt 9 - Merge To Main - Pending

### Goal

Keep merge tracking explicit and separate from implementation completion.

### Instructions

- mark this prompt completed only after the fix work is merged
- keep the parent task and this fix follow-up aligned on final merge state
