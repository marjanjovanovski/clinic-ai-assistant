# 20260408_1157_AGENT - Premature Booking Flow Regression

Record and later fix the long-running regression where a typed-date scheduling request can sometimes jump into booking/contact collection prematurely instead of staying in availability lookup.

Execution must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Merge To Main

- `Pending`

## Prompt Status Summary

- Prompt 1 - Evidence And Repo Truth - Pending
- Prompt 2 - Root Cause Fix - Pending
- Prompt 3 - Technical Verification - Pending
- Prompt 4 - Manual Verification - Pending
- Prompt 5 - Merge Readiness - Pending

## Current Active Prompt

- `Prompt 1`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-04-08`

## Purpose

- record the premature booking-flow regression separately from the scheduling FIX 01 closeout
- preserve the known evidence and observed behavior so the issue is not lost
- keep the follow-up scoped to the booking-boundary regression only

## Working Rules For The Implementing AI Agent

- treat this as a standalone bug task, not another prompt inside FIX 01
- keep the scope on the premature transition from scheduling into booking/contact collection
- do not reopen broad scheduling redesign or unrelated dashboard tooling

## Testing And Verification Rules

- use external `TMP` / `TEMP` and external pytest `--basetemp`
- prefer the smallest focused scheduling tests that reproduce the premature handoff
- keep any new evidence filenames plain and stable

## Current Repo Truth

- during FIX 01 manual verification, a specific-date request for `09.04.2026` entered name/phone/email collection on the first submission instead of returning normal availability lookup behavior
- repeated attempts then behaved correctly, which suggests an intermittent or stateful regression rather than a fully broken mainline path
- the issue was observed on `2026-04-08` and recorded while closing out scheduling FIX 01

## Known Evidence

- source task: `20260330_1223_AGENT - Scheduling Contract and Flow Extraction FIX 01`
- evidence filename: `trace_2026-04-08_09-31-40_milena_dental_ee8de312-22e3-42e9-bac0-c857a699cf04.txt`

## Do Not Break

- typed-date scheduling must stay in the scheduling/availability path unless the user explicitly confirms booking intent
- clickable slot widgets remain the only valid way to present actionable appointment times
- no broad changes to month calendar, cancellation, or unrelated booking dashboard behavior

## Prompt 1 - Evidence And Repo Truth - Pending

### Goal

Trace the exact conditions that cause typed-date scheduling to jump into booking/contact collection prematurely.

### Required Outcome

The bug is reproducible or its triggering conditions are narrowed clearly enough to implement a focused fix.

## Prompt 2 - Root Cause Fix - Pending

### Goal

Apply the smallest backend fix that keeps specific-date availability requests inside scheduling unless booking intent is truly confirmed.

### Required Outcome

The premature handoff path is removed without regressing slot selection or normal booking confirmation.

## Prompt 3 - Technical Verification - Pending

### Goal

Run the smallest focused test set that proves the bug is fixed and booking boundaries still hold.

## Prompt 4 - Manual Verification - Pending

### Goal

Retest the original reproduction and confirm the regression no longer appears in the chat flow.

## Prompt 5 - Merge Readiness - Pending

### Goal

Confirm the task is ready for merge or document any remaining blocker honestly.
