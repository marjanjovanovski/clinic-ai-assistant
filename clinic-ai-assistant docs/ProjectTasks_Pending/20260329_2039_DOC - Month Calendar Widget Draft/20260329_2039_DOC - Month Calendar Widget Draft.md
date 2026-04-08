# 20260329_2039_DOC - Month Calendar Widget Draft

This note captures a follow-up UI/product task discovered during scheduling-flow brainstorming: add a month calendar widget as a broader date-exploration surface after the current scheduling slot widget is stabilized.

Execution conventions for task artifacts in this folder should follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-29`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Draft Requirement Capture - Completed
- Prompt 2 - Convert To Execution Task - Pending
- Prompt 3 - Merge To Main - Pending

## Draft Requirement

- create a dedicated month calendar widget as a future scheduling surface
- keep this out of the immediate implementation scope while the current scheduling time-slot widget is being stabilized
- use the month calendar as a broader date-exploration companion, not as a replacement for the quick slot-list widget

## Product Intent

The widget should eventually support:

- month-level day browsing
- day selection that requests availability for the chosen day
- optional disabled/inactive day states only when backend availability confidence is reliable
- graceful no-availability handling for selected days

## Scope Boundary

Current priority:

- stabilize the scheduling time-slot widget
- stabilize scheduling-first chat behavior
- stabilize scheduling-to-booking handoff and slot-conflict recovery

Follow-up priority:

- design and implement the month calendar widget after the above path is stable

## Residue To Carry Into The Future Task

The future execution-ready task should define:

- widget UX rules for active, inactive, and unknown-availability dates
- backend contract for day-level availability lookup
- interaction rules between the month calendar widget and the existing slot-list widget
- JSON-config-owned labels and copy for the calendar experience
