# Backend System Message Catalog Master Prompt

This document defines the execution-ready task plan for centralizing backend-generated user-facing system messages into a locale-aware configuration catalog.

The purpose of this work is to:
- remove hard-coded backend workflow messages from Python files
- keep system-controlled messages separate from tenant/business conversational content
- prepare the backend for future translation without rewriting Python logic
- make message ownership easier to audit, test, and maintain
- preserve the current architecture rule that tenant-specific conversational content remains in tenant profile JSON

## Execution Tracking Instructions

Before executing any prompt in this document, the implementing AI agent must first read this file and understand the current status.

Execution of this feature must follow [../Feature_Implementation_Guide.md](../Feature_Implementation_Guide.md).
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

- `Codex`

## Last Updated On

- `2026-03-27`

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
- Prompt 7 - Pending
- Prompt 8 - Pending
- Prompt 9 - Pending
- Prompt 10 - Pending
- Prompt 11 - Pending
- Prompt 12 - Pending

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Keep this task strictly scoped to backend-generated user-facing system messages.
- Do not move tenant/business conversational content out of tenant profile JSON.
- Do not mix catalog/service descriptions, greetings, tone rules, or business overview text into the new system message catalog.
- Prefer per-locale message files over one combined multilingual file.
- Use stable message identifiers and a small loader/helper layer rather than spreading lookup logic across many files.
- Keep runtime lookup simple, deterministic, and testable.
- Prefer a shared default locale plus additional locale files with matching key sets.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to keep test artifacts out of the repository.
- When running pytest, use external `TMP` / `TEMP` and an external `--basetemp`.
- Add or update focused automated coverage for:
  - message loading
  - locale fallback
  - missing-key protection
  - migrated backend message lookups
- If cleanup is required after verification, document it in the prompt completion note.
- If a test cannot run because of environment permissions, document that clearly in the prompt completion note.
- Manual verification is allowed when the environment blocks full automated execution, but it must be described concretely.

## Do Not Break

- existing tenant profile loading
- existing `reply_texts` behavior in tenant profile JSON
- scheduling-first chat flow
- booking-first chat flow
- slot selection flow
- final booking flow
- current service and business overview replies
- any backend behavior that depends on current stage transitions or saved state

## Current Repo Truth

- The repo already uses tenant profile JSON as the approved home for conversational and configuration content.
- Backend Python still contains some user-facing workflow strings in orchestration and scheduling-related paths.
- Many conversational replies already live in tenant profile JSON under `reply_texts`, `conversation`, and related sections.
- The target of this task is narrower: backend-generated system messages only.
- The current repo does not yet have a dedicated locale-aware system message catalog for backend workflow replies.
- The repo should not move system message text into the database for this first version.

## Architecture Guidance

### Scope Boundary

This task covers only system-controlled backend messages such as:
- booking workflow prompts and retries
- scheduling conflict and recovery messages
- persistence-related user-facing status messages
- backend-generated completion, validation, or failure messages

This task does not cover:
- tenant greetings
- service descriptions
- business overview copy
- catalog phrasing
- LLM-authored conversational text
- tenant communication rules and tone settings

### Recommended Design

Use per-locale config files, for example:
- `clinic-ai-assistant-src/backend/app/config/messages/mk.json`
- `clinic-ai-assistant-src/backend/app/config/messages/en.json`

Use shared message IDs across locale files, for example:
- `booking.slot_conflict.selection_lost`
- `booking.slot_conflict.finalize_lost`
- `booking.contact.field.name.prompt`

Use a small backend helper layer to:
- load locale files
- resolve the active locale
- return a message by ID
- format template variables safely
- provide controlled fallback to the default locale

### Why This Design

- keeps message content versioned in git
- avoids unnecessary DB complexity for mostly static content
- keeps translation work isolated by locale
- preserves the current tenant-profile architecture instead of fighting it
- makes it easier to audit and test for hard-coded user-facing literals in backend code

## Desired Outcome

After all prompts are complete, the repo should have:
- a dedicated locale-aware backend system message catalog
- stable message IDs for backend user-facing workflow messages
- loader/helper utilities for lookup and formatting
- migrated backend message lookups in the relevant Python files
- tests that protect against missing locale keys and accidental hard-coded regressions
- a clear separation between tenant conversational content and system workflow messages

## Prompt 1 - Pending

### Goal

Audit the backend and identify every user-facing system message that should move into the new catalog.

### Instructions

Inspect the backend codebase and produce the message inventory before introducing the new catalog.

Requirements:
- identify user-facing hard-coded strings in backend Python
- include message purpose and current file location
- separate in-scope system messages from out-of-scope tenant conversational content
- group messages by area such as:
  - booking workflow
  - scheduling
  - validation and retry
  - persistence/status
- do not migrate messages during this prompt unless a tiny supporting refactor is required for the audit

### Required Outcome

A clear inventory exists of backend system messages to migrate, with scope boundaries confirmed before implementation starts.

## Prompt 2 - Pending

### Goal

Design the system message catalog schema, naming rules, and locale layout.

### Instructions

Define the file structure and identifier conventions for the new catalog.

Requirements:
- use per-locale files rather than one combined multilingual file
- define stable message ID naming rules
- define which messages are plain strings versus format templates
- define default locale and fallback behavior
- define how message metadata is handled without bloating the runtime files

### Required Outcome

The catalog structure is explicit and ready to support implementation without ad hoc naming or file-layout decisions later.

## Prompt 3 - Pending

### Goal

Implement the config files for the first system message catalog.

### Instructions

Create the locale files and populate them with the audited message set for the first supported languages.

Requirements:
- create at least the default locale file
- create at least one secondary locale file if the task scope includes translation-ready scaffolding
- use matching keys across locale files
- keep only runtime-relevant message content in the locale files
- do not mix tenant profile content into these files

### Required Outcome

The repo contains the first version of the system message catalog in a clean locale-aware config structure.

## Prompt 4 - Pending

### Goal

Add a backend helper layer for system message lookup and formatting.

### Instructions

Implement the loading and retrieval path for the message catalog.

Requirements:
- load locale files from config
- support default locale fallback
- support template formatting for message variables
- fail safely and observably when a message key is missing
- keep the API simple enough to use widely from backend code

### Required Outcome

Backend code has a small, reusable, deterministic message lookup interface for system replies.

## Prompt 5 - Pending

### Goal

Wire locale resolution into the backend without disturbing tenant profile behavior.

### Instructions

Define how the backend decides which locale file to use for system messages.

Requirements:
- align with existing tenant/business language settings where practical
- keep fallback behavior explicit
- do not redesign tenant profile ownership unnecessarily
- document how locale selection works for future languages

### Required Outcome

The backend can resolve system messages by locale in a way that fits the current config architecture.

## Prompt 6 - Pending

### Goal

Migrate booking workflow system messages out of Python and into the new catalog.

### Instructions

Update booking-related backend paths to retrieve system messages from the catalog.

Requirements:
- migrate booking field prompts that are truly system-controlled within this task boundary
- migrate validation and retry messages that are backend workflow-driven
- preserve existing booking state and transition behavior
- avoid changing tenant/business conversational content during this prompt

### Required Outcome

Booking-related system messages no longer rely on hard-coded backend literals in the targeted files.

## Prompt 7 - Pending

### Goal

Migrate scheduling and slot-conflict system messages out of Python and into the new catalog.

### Instructions

Update scheduling-related backend paths to retrieve system messages from the catalog.

Requirements:
- migrate selection conflict messages
- migrate final-booking conflict and recovery messages
- preserve scheduling-owned backend authority
- keep conflict contracts and status values stable unless the task explicitly improves them

### Required Outcome

Scheduling-related user-facing system messages are resolved through the catalog rather than embedded in Python.

## Prompt 8 - Pending

### Goal

Add protection against future hard-coded backend system messages.

### Instructions

Add lightweight guardrails so the architecture remains clean after migration.

Requirements:
- add focused tests or checks for catalog loading and missing keys
- add a targeted regression test or audit rule that discourages new hard-coded user-facing backend workflow strings
- keep the protection practical rather than brittle

### Required Outcome

The repo has enforceable protection against drifting back to scattered hard-coded backend system messages.

## Prompt 9 - Pending

### Goal

Document message ownership boundaries and developer usage rules.

### Instructions

Update or add supporting documentation so future changes follow the intended split.

Requirements:
- document that tenant profile JSON remains the home for tenant conversational content
- document that the new catalog owns backend system workflow messages
- document how to add a new message ID and locale entry
- document how to decide whether a message belongs in tenant config or system catalog

### Required Outcome

The ownership model is documented clearly enough that future contributors will extend the right layer.

## Prompt 10 - Pending

### Goal

Run focused verification and confirm the migrated flows still behave correctly.

### Instructions

Verify the migrated backend paths through tests and targeted manual checks.

Requirements:
- test message lookup and fallback behavior
- test at least one booking flow that uses migrated system prompts
- test at least one scheduling conflict path that uses migrated system prompts
- follow repo-clean temp-path rules
- document what was verified automatically and manually

### Required Outcome

The migrated message catalog works in the targeted backend flows and the verification is documented clearly.

## Prompt 11 - Pending

### Goal

Perform final cleanup, tighten naming or structure if needed, and document completion in this file.

### Instructions

After implementation prompts are complete, do the final pass.

Requirements:
- confirm no repo-local junk was left by testing
- confirm no tenant conversational content was accidentally moved into the system catalog
- document accepted follow-up work only if truly out of scope
- leave this task file ready for manual review and merge discussion

### Required Outcome

The backend system message catalog feature is complete, verified, and documented without scope creep.

## Prompt 12 - Pending

### Goal

Track branch-level manual verification and merge readiness before this task can move out of `ProjectTasks_Pending`.

### Instructions

After implementation and automated verification prompts are complete, wait for user-driven manual verification on the branch.

Requirements:
- keep this prompt `Pending` until the user confirms manual verification is complete
- record which manual verification scenarios were performed
- record the user decision on merge readiness
- only after this prompt is completed should merge into `main` be considered
- if manual verification finds issues, keep `Merge To Main` as `Pending` and continue the task with follow-up prompts or notes as needed

### Required Outcome

Manual verification and merge readiness are tracked explicitly as a prompt status rather than only as freeform discussion.

---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is for archive, handoff, and manual-verification guidance only.

Execution rule for future implementing agents:
- do not treat this appendix as additional implementation scope
- do not create extra prompts from this appendix unless the user explicitly asks for that
- use it only to understand expected runtime behavior and manual verification outcomes
- once the implementation reaches the matching prompt stages above, this appendix should not consume further context planning time

## Use Case

The backend currently returns some workflow messages directly from Python code.

The target business logic is:
- backend workflow state decides which system message is needed
- Python asks the system message catalog for the message by ID
- the catalog returns the correct locale version
- the backend formats variables if needed and returns the final user-facing message

Example flow:

| Step | Backend state | Message source | Result |
|---|---|---|---|
| 1 | User enters booking flow | System message catalog | Prompt for name/phone/email comes from locale file |
| 2 | User enters invalid email | System message catalog | Retry message comes from locale file |
| 3 | User loses selected slot | System message catalog | Conflict message comes from locale file |
| 4 | A new language is added | Locale files only | Python logic stays unchanged |

## Scenarios

### Scenario A - Booking field prompt

- The backend reaches the state where it needs the next contact field.
- Instead of returning a hard-coded string from Python, it looks up the message ID for that field prompt.
- The returned message depends on the active locale.

### Scenario B - Scheduling conflict

- The backend detects that a selected slot is no longer available.
- It uses the conflict message ID for that state.
- The user receives the correct locale-specific conflict reply without changing Python logic per language.

### Scenario C - Translation expansion

- A second locale file is updated with the same message IDs.
- The backend now serves translated system messages without touching the booking or scheduling code paths.

## Simple Flow Chart

```text
Backend reaches workflow state
   |
   v
Choose message ID
   |
   v
Resolve locale
   |
   v
Load message from catalog
   |
   +-- Missing in locale --> Fallback to default locale
   |
   +-- Missing entirely --> Controlled failure / test protection
   |
   v
Format variables if needed
   |
   v
Return final user-facing message
```

## Manual Testing Steps

Manual verification status values to use in the companion JSON:
- `Not Run`
- `Pass`
- `Fail`

Recommended usage:
- mark `Status` after each test is performed
- use `Comment / Failure Note` for observations, blockers, or unexpected behavior
- if a test fails, keep the failing detail in the same row

### Category 1 - Booking Workflow Messages

#### Test 1.1 - Contact field prompt comes from the system catalog

| Step | Action | What Is Tested | Status | Comment / Failure Note |
|---|---|---|---|---|
| 1 | Start a booking flow that asks for contact details | The backend resolves the field prompt from the system message catalog | Not Run | |
| 2 | Review the returned user-facing prompt | The reply appears correct and is not coming from a hard-coded backend literal path | Not Run | |

#### Test 1.2 - Validation retry uses the catalog

| Step | Action | What Is Tested | Status | Comment / Failure Note |
|---|---|---|---|---|
| 1 | Enter an invalid phone or email value | The backend reaches the retry-validation path | Not Run | |
| 2 | Review the retry message | The retry message comes from the system message catalog and matches the active locale | Not Run | |

### Category 2 - Scheduling Conflict Messages

#### Test 2.1 - Lost-slot conflict uses the catalog

| Step | Action | What Is Tested | Status | Comment / Failure Note |
|---|---|---|---|---|
| 1 | Trigger a scheduling conflict such as a lost selected slot | The backend reaches a conflict-message path | Not Run | |
| 2 | Review the returned conflict message | The conflict message comes from the system message catalog rather than hard-coded backend text | Not Run | |

### Category 3 - Locale And Ownership Boundary

#### Test 3.1 - Locale switch changes system messages without code changes

| Step | Action | What Is Tested | Status | Comment / Failure Note |
|---|---|---|---|---|
| 1 | Switch to another configured locale if supported in scope | Locale resolution changes the message source file | Not Run | |
| 2 | Re-run a booking or conflict state already covered above | The same backend state returns the translated system message | Not Run | |

#### Test 3.2 - Tenant conversational content remains outside the system catalog

| Step | Action | What Is Tested | Status | Comment / Failure Note |
|---|---|---|---|---|
| 1 | Review tenant-driven replies such as greetings, services, or business overview | Tenant profile content ownership remains unchanged | Not Run | |
| 2 | Compare those replies with system workflow messages | System messages come from the new catalog while tenant conversational content still comes from tenant profile behavior | Not Run | |
