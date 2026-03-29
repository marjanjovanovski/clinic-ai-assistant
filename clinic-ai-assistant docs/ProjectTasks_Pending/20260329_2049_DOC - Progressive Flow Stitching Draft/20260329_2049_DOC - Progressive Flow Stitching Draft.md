# 20260329_2049_DOC - Progressive Flow Stitching Draft

This note captures a future follow-up idea from the scheduling-flow brainstorming: instead of abrupt flow switches, the system should progressively stitch scheduling, service, catalog, and booking flows together based on how much useful input has already been collected.

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

- define a configurable progressive handoff model between flows
- allow each flow to collect its own useful input set first
- use configurable completion thresholds or readiness rules to determine when one flow can naturally guide into the next
- avoid abrupt or premature switching into booking state

## Product Intent

Example target behavior:

- scheduling collects enough context such as date range, date, time window, or selected slot
- once scheduling reaches a meaningful readiness threshold, it can guide into a narrower next step
- booking starts only when the scheduling side has enough real information to justify it

## Residue To Carry Into The Future Task

The future execution-ready task should define:

- which inputs belong to each flow
- what percentage or readiness rules count as enough progress
- whether the readiness threshold is configurable in JSON
- how flow readiness is represented in backend orchestration without hard-coded phrase dictionaries
