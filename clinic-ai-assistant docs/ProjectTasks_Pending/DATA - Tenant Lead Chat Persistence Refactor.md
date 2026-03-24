# Tenant, Lead, and Chat Persistence Refactor Master Prompt

This document serves to guide, track, and coordinate the implementation of the Tenant, Lead, and Chat Persistence Refactor.

The purpose of this work is to evolve the current tenant-name-based lead persistence model into a proper relational design with:
- a first-class `tenants` table
- `leads` owned by `tenant_id`
- a safe migration path for existing `assistant_velika.db` records
- durable chat transcript logging for every session

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

Update rules:
- If only Prompt 1 is finished, the top summary must say: `Prompt 1 - Completed`
- If Prompt 1 and Prompt 2 are finished, the top summary must say: `Prompt 1, 2 - Completed`
- All prompts not yet executed must remain marked as `Pending`
- If a prompt cannot be completed, mark it as `Blocked` and add a short reason under that prompt

## Global Status Summary

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending
- Prompt 6 - Pending

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Respect the current booking and lead persistence flow.
- Preserve existing behavior unless a deliberate migration adjustment is required.
- Prefer production-grade schema design and migration safety over quick patching.
- Use the current `assistant_velika.db` and repo code to understand how persistence works today.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work for that prompt has actually been implemented and verified as far as possible.

## Prompt 1 - Pending

### Goal

Understand the current implementation and produce a structured Change Map that all later prompts will reference instead of re-exploring the repo.

### Instructions

Inspect the repo and become fully up to speed with the current logic before implementing anything.

You must understand:
- where the current leads database is initialized
- how `assistant_velika.db` is structured
- where lead rows are created and updated
- how `tenant` is currently stored in `leads`
- how session recovery works
- how stages like `awaiting_booking_confirmation`, `collecting_contact`, and `completed` are persisted
- how the current booking flow relies on lead persistence
- what tests currently validate this behavior

You must then write two outputs:

**Output 1 — Architecture Summary**

A concise prose summary covering:
- the current persistence model
- why it works today
- its limitations
- why the new relational model is needed

**Output 2 — Change Map**

A structured table listing every file that will need to change. For each file include:

| Field | Description |
|---|---|
| File path | Exact relative path from repo root |
| Why it matters | One sentence on its role in the current model |
| Functions / modules likely to change | Specific named functions or classes, not vague descriptions |
| Phase | One or more of: `schema`, `migration`, `runtime`, `test` |
| Risk | `Low`, `Medium`, or `High` with a one-line reason |

The Change Map must be complete enough that agents executing Prompts 2–6 can go directly to the relevant files and functions without re-exploring the repo.

### Required Outcome

An architecture summary and a complete Change Map. No code changes in this prompt.

## Prompt 2 - Pending

### Goal

Design and implement the complete schema for the new relational model — tenants table and leads FK refactor — in a single pass.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions identified there as `phase: schema`.

**Step 1 — Create the `tenants` table**

The table must include:
- `id` — autoincrement integer primary key
- `unique_identifier` — stable unique business identifier, non-nullable, unique-indexed
- `name`
- `comment`
- `phone`
- `email`
- `primary_contact_name`
- `secondary_contact_name`
- `date_registered`

Add a unique index on `unique_identifier`. Insert an initial tenant record with `name = "milena_dental"`.

**Step 2 — Refactor the `leads` table**

Add `tenant_id` as a foreign key referencing `tenants.id`. Do not remove the existing `tenant` text column yet — that is handled in Prompt 3 during safe migration. The column must coexist in this step.

Add an index on `tenant_id`.

### Required Outcome

Both schema changes are implemented in the database initialization layer. The `tenant` text column still exists at the end of this prompt — it will be removed in Prompt 3.

## Prompt 3 - Pending

### Goal

Execute the safe SQLite data migration — backfill `tenant_id`, verify data integrity, then remove the legacy `tenant` column.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions identified there as `phase: migration`.

SQLite does not support `DROP COLUMN` before version 3.35 and has significant DDL constraints. Handle this with care.

Required steps in order:
1. Backfill `tenant_id` on all existing `leads` rows where `tenant = "milena_dental"` by looking up the inserted tenant record.
2. Verify that no lead row has a null `tenant_id` after backfill. If any row cannot be matched, log it and halt — do not silently discard data.
3. Remove the legacy `tenant` column using a safe SQLite table-rebuild migration (create new table, copy data, drop old, rename).
4. Confirm foreign key integrity after migration completes.

Important:
- preserve compatibility with the current lead checkpoint and recovery behavior
- ensure existing session-linked lead rows continue to work after the column removal
- the migration must be repeatable and safe to run against the current `assistant_velika.db`

### Required Outcome

All existing lead data is intact, linked to the correct tenant via `tenant_id`, and the legacy `tenant` text column no longer exists.

## Prompt 4 - Pending

### Goal

Add durable chat transcript persistence via a two-table schema and wire it into the runtime flow.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions identified there as `phase: schema` or `phase: runtime` related to chat logging.

**Schema — two tables required:**

`chat_sessions`
- `id` — autoincrement integer primary key
- `session_id` — stable unique session identifier, unique-indexed
- `tenant_id` — foreign key to `tenants.id`
- `started_at` — timestamp

`chat_messages`
- `id` — autoincrement integer primary key
- `chat_session_id` — foreign key to `chat_sessions.id`
- `role` — `user` or `assistant`
- `content` — message text
- `created_at` — timestamp, used for ordering

Add an index on `chat_messages.chat_session_id` and `created_at`.

**Runtime integration:**

Wire both tables into the actual message handling flow so that:
- a `chat_session` row is created or retrieved at the start of each session
- every user message and every assistant reply is written to `chat_messages` immediately after it occurs
- messages are never written in bulk at session end — each turn is persisted as it happens

Do not mix session-level metadata into the messages table.

### Required Outcome

Both tables exist, are correctly indexed, and every real chat turn is persisted automatically during runtime. No test work in this prompt.

## Prompt 5 - Pending

### Goal

Complete runtime integration — update all application code that reads or writes leads and sessions to use the new relational model.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions identified there as `phase: runtime`.

Update the application code so:
- new leads are written with `tenant_id` instead of the legacy `tenant` text value
- lead loading and session recovery continue to function using `tenant_id`
- existing booking semantics — stages like `awaiting_booking_confirmation`, `collecting_contact`, `completed` — are fully preserved
- no runtime path still references the removed `tenant` column

Do not write tests in this prompt. Do not modify schema or migration files unless a runtime bug requires a targeted fix.

### Required Outcome

All runtime paths use the new relational model. The application functions correctly end-to-end with the refactored schema.

## Prompt 6 - Pending

### Goal

Add test coverage for the refactored model and produce the final delivery summary.

### Instructions

Reference the Change Map produced in Prompt 1. Work only on the files and functions identified there as `phase: test`.

Add or update tests for:
- tenant creation
- seed record for `milena_dental`
- lead backfill to `tenant_id`
- lead recovery after migration
- chat session creation
- chat message ordering by `created_at`
- correct tenant and session ownership on both leads and chat messages
- prevention of cross-session message mixing

After tests pass, write a final summary covering:
- what changed across all six prompts
- why the new design is better than the original
- what assumptions were made during implementation
- any risks or recommended follow-up work

### Required Outcome

Test suite passes. Final summary is written. All prompts are marked `Completed` and this document is ready to be archived to `ProjectTasks_Done`.

## Final Completion Rule

This document should only show all prompts as `Completed` once:
- schema changes are implemented
- data migration is handled
- runtime code is updated
- tests are updated or added
- the implementing AI agent has written a concise final summary of the delivered work
