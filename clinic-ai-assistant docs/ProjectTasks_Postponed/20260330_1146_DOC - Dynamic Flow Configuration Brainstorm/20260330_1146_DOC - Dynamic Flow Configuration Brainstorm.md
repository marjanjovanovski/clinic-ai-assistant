# 20260330_1146_DOC - Dynamic Flow Configuration Brainstorm

This document is a decision-shaping note for how dynamic flow behavior should be configured across booking, scheduling, and related chat workflows, with special focus on JSON-driven field configuration, tenant overrides, and future-safe flow extensibility.

Execution conventions for task artifacts in this folder should follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-30`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 2`

## Global Status Summary

- Prompt 1 - Brainstorming Overlay - Completed
- Prompt 2 - Convert To Execution Task - Pending
- Prompt 3 - Merge To Main - Pending

## Purpose

- explore whether flow steps and required parameters should become JSON-driven
- define the value of a master flow configuration plus tenant-level override layer
- assess whether this belongs in MVP or should be phased in
- make future parameter additions easier without turning Python orchestration into a hard-coded maze

## Initial Architecture Idea

The core idea is strong:

- one master JSON flow definition describes the allowed fields and their order
- each field can be enabled or disabled
- backend logic reads the active set and derives:
  - required steps
  - completion progress
  - next field to collect
  - what the LLM should ask for next
- tenant configuration can narrow that flow further, but should not expand beyond the master schema without deliberate support

Example shape at a high level:

- master flow config defines:
  - `name`
  - `email`
  - `phone`
  - `date_of_birth`
  - `social_security_number`
- tenant config enables only:
  - `name`
  - `email`

In that case:

- the booking flow should know it is a 2-field flow
- completion should become 50 percent after `name`
- the next expected field should become `email`

## Why This Is Attractive

- adding or removing a field becomes a config task rather than a Python rewrite
- progress tracking becomes dynamic and consistent
- tenant differences can be handled with less branching
- future flow stitching becomes easier because the backend can reason over structured flow state rather than special-case code paths

## Important Boundary

This should not mean that JSON owns everything.

Recommended ownership split:

- JSON owns:
  - field definitions
  - enable/disable state
  - order
  - labels and prompts
  - validation metadata where practical
  - flow-level behavior knobs
- Python owns:
  - orchestration
  - deterministic validation
  - state transitions
  - persistence contracts
  - protected side effects

## MVP Question

This is valuable, but it may not all belong in MVP.

My high-level view:

- a small first version is very beneficial for MVP
- a fully generalized dynamic flow engine is probably too large for MVP

So the likely best path is:

- introduce a controlled JSON-driven field registry first
- keep orchestration still explicit in Python
- avoid trying to generalize every possible flow behavior immediately

## Recommended MVP Scope

For MVP, the most useful dynamic configuration would be:

- enabled/disabled booking fields
- field order
- field labels and field prompts
- dynamic completion percentage
- active required-field list per tenant

What can wait:

- fully generic branching flow engine
- per-field custom orchestration logic in config
- complex conditional dependencies between many fields
- tenant-defined new schema behavior without backend support

## Adding New Parameters

Your example is exactly where this can help.

If later you want to add:

- `date_of_birth`
- `social_security_number`

the desired experience would be:

- add the field in the master schema
- define prompt text / intent guidance in JSON
- enable it for the relevant tenant
- backend automatically recalculates total required fields and progress
- the LLM is guided to request that field in the correct place

This is useful, but it needs guardrails.

## Guardrails To Keep It Safe

- new fields should come from an approved master schema, not arbitrary tenant freeform additions
- field prompts and intent guidance can live in JSON, but Python should still know the field identity and validation rules
- highly sensitive fields should require explicit product and legal review before they are allowed into booking
- progress should be derived from active required fields, not hard-coded counts

## High-Level Product Risk

If this is over-generalized too early, the system can become:

- harder to reason about
- harder to test
- easier to misconfigure
- too dependent on prompt behavior instead of business contracts

So the value is real, but the shape should be narrow and disciplined.

## Recommended Direction Summary

- yes, JSON-driven dynamic field configuration is beneficial
- no, a fully generic flow engine is not required for MVP
- the first useful version should focus on booking fields and completion logic
- tenant config should probably be able to reduce or disable fields, but not freely invent unsupported flow behavior
- prompts and labels can be config-driven, but validation and transitions should stay in Python

## Next Task Candidate

The next execution-ready task should likely translate this note into:

- master booking-field schema design
- tenant override rules
- progress-calculation rules
- config contract for prompts and labels
- backend boundary for validation and transitions

## Brainstorming Conclusions

- this idea has real long-term value because it reduces Python hard-coding pressure
- it is especially useful for progress tracking and tenant-specific required-field differences
- it can also help future progressive flow stitching because flows can reason over structured completeness
- the MVP should likely stop short of a universal configurable flow engine
- the first implementation should be narrow, booking-focused, and schema-driven

## Brainstorming Decision Table

| Question | Recommended answer | Why | Your final decision |
|---|---|---|---|
| 1. Should required booking fields become JSON-configurable? | Yes, in a controlled schema-driven way. | This gives flexibility without forcing Python rewrites for every field change. | `Pending` |
| 2. Should there be a master flow configuration plus tenant wrapper/override? | Yes. Use one master schema and allow tenant configs to enable fewer fields or narrower behavior. | This keeps the system consistent while still supporting tenant-specific differences. | `Pending` |
| 3. Should tenant config be allowed to introduce completely new unsupported fields? | No, not by default. New fields should first be added to the master schema. | This avoids misconfiguration and keeps validation/test coverage manageable. | `Pending` |
| 4. Is this vital for MVP? | Partially. A narrow field-config version is valuable for MVP, but a full dynamic flow engine is not required. | The smaller version gives immediate benefit without overexpanding scope. | `Pending` |
| 5. What should the first MVP configuration cover? | Enabled fields, field order, labels/prompts, and progress calculation. | These are the highest-value dynamic pieces with the lowest architectural risk. | `Pending` |
| 6. Should progress percentage be derived dynamically from enabled fields? | Yes. | This is one of the clearest wins of a config-driven approach and removes hard-coded assumptions. | `Pending` |
| 7. Where should field prompts and wording live? | In JSON config. | This follows your config-first rule and keeps wording out of Python. | `Pending` |
| 8. Where should validation and state transitions live? | In Python services. | These are deterministic workflow rules and should not be delegated to config alone. | `Pending` |
| 9. If we add a field like `date_of_birth`, what should happen? | Add it to the master schema, define prompt/label metadata, then enable it per tenant if needed. | This keeps growth explicit, testable, and consistent. | `Pending` |
| 10. If we add a field like `social_security_number`, should it be treated the same as normal fields? | No. Sensitive fields should require explicit product and legal review before being allowed. | Some fields carry much higher trust, privacy, and compliance impact. | `Pending` |
| 11. Should this same model later support scheduling and service flows too? | Yes, but only after the booking-focused version proves stable. | Booking is the cleanest place to validate the pattern before expanding it. | `Pending` |
| 12. What should be explicitly avoided? | Avoid a universal no-rules flow engine, tenant-defined arbitrary fields, config-owned side effects, and prompt-only workflow behavior. | These would make the architecture fragile and harder to verify. | `Pending` |

## Update Instructions

Use the `Your final decision` column with values like:

- `OK`
- `OK with note: ...`
- `Change to: ...`
- `Later`
