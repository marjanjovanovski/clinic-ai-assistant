# 20260329_2037_DOC - Service Flow Independence Draft

This note captures a follow-up architecture/product requirement discovered during the scheduling-flow brainstorming: service flow, scheduling flow, booking flow, and catalog flow should remain as independent as possible, with explicit dependency rules instead of accidental coupling.

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

- formulate stronger independence between service flow, scheduling flow, booking flow, and catalog flow
- avoid making service selection a blanket prerequisite for scheduling
- allow scheduling exploration without forced service selection whenever valid availability can still be shown
- require explicit service/category selection only when slot rendering truly depends on service-specific rules such as duration, provider, or category-dependent availability

## Product Intent

The system should behave as follows:

- if availability can be explored without a chosen service, keep service flow independent
- if availability differs materially by service or category, require the user to specify what they are booking before rendering slots
- once a service-dependent scheduling path is entered, preserve that dependency explicitly instead of mixing it back into generic chat

## Residue To Carry Into The Future Task

The future execution-ready task should define:

- independence rules between catalog, service, scheduling, and booking flows
- the exact conditions that force service/category selection before scheduling
- the handoff contract when generic scheduling becomes service-bound scheduling
- how this logic is represented in config and backend services without hard-coded phrase dictionaries
