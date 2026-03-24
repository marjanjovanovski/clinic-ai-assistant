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

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
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

## Prompt 1 - Completed

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

---

### Output 1 — Architecture Summary

**Current persistence model**

The app uses a single SQLite database at `clinic-ai-assistant-src/backend/db/assistant_velika.db`. The database is initialized at application startup via `init_leads_db()` in `lead_store.py`, which is called directly from `main.py`.

The `leads` table has this shape:

```
id, tenant TEXT, session_id TEXT, contact_name, contact_phone,
contact_email, collected_data_json TEXT, created_at, updated_at
UNIQUE(tenant, session_id)
```

Tenant identity is stored as a plain text string in the `tenant` column. There is no `tenants` table. The string value `"milena_dental"` is hardcoded at every call site. The unique constraint is on `(tenant, session_id)` which acts as the business key for a session.

**How it works today**

- On each chat turn, `save_lead_checkpoint(tenant, session_id, state)` is called from `ai_agent.py` and `booking_credentials.py` at every stage transition.
- `load_lead_checkpoint(tenant, session_id)` is called by `chat_session_state._load_session_state()` on every request to recover in-memory state from the database.
- The `collected_data_json` column stores the full session state dict (stage, data, next_field, service_id, scheduling_handoff, etc.) as a JSON blob.
- Contact fields (`contact_name`, `contact_phone`, `contact_email`) are also stored as dedicated columns for easy querying and are treated as the authoritative source during hydration — they override stale values in the JSON blob.
- Session recovery (`_load_session_state`) merges the persisted stage and contact data back into in-memory `SESSION_STATE`. Stages `awaiting_booking_confirmation`, `collecting_contact`, and `completed` are the only stages that are restored from persistence.
- There is no chat transcript storage — messages are held only in the in-memory `INTERACTION_HISTORY` dict and are lost when the process restarts.

**Why it works today**

There is currently one tenant (`milena_dental`). The tenant text string is consistent across all call sites. The UNIQUE constraint on `(tenant, session_id)` prevents duplicate rows. Session recovery is reliable as long as the process has already initialized the DB at startup.

**Its limitations**

- No relational integrity — `tenant` is a free-text string. Nothing prevents a typo or a new tenant string that doesn't correspond to any registered business entity.
- No `tenants` table means no place to store tenant metadata (contact info, registration date, etc.).
- Adding a second tenant requires no schema change — it just starts writing new string values, which is fragile.
- No chat transcript — there is no durable record of what was said in any conversation. If the process restarts mid-session, the conversation history is gone.
- `collected_data_json` stores the entire session state, mixing transient workflow state with durable contact data.

**Why the new relational model is needed**

A `tenants` table provides a stable, owned identity for each clinic. `leads.tenant_id` becomes a proper foreign key, enforcing that every lead belongs to a real registered tenant. Chat transcript tables allow every message to be persisted durably, enabling audit, debugging, and future analytics without relying on in-memory state.

---

### Output 2 — Change Map

| File path | Why it matters | Functions / modules likely to change | Phase | Risk |
|---|---|---|---|---|
| `clinic-ai-assistant-src/backend/app/services/lead_store.py` | Owns all DB schema init, lead read/write, and session recovery logic | `init_leads_db`, `save_lead_checkpoint`, `load_lead_checkpoint`, `_fetch_persisted_lead` | schema, migration, runtime | **High** — every lead read/write passes through here; breakage stops the booking flow entirely |
| `clinic-ai-assistant-src/backend/app/main.py` | Calls `init_leads_db()` at startup | `startup block` (line 25), imports | schema, runtime | **Low** — only needs to call any new init functions added alongside `init_leads_db` |
| `clinic-ai-assistant-src/backend/app/services/booking_credentials.py` | Contains all booking stage transitions; calls `save_lead_checkpoint` ~20 times across all stages | `start_collecting_contact`, `mark_booking_confirmation_pending`, `handle_field_input`, `handle_completed_edit`, and all functions accepting `save_lead_checkpoint` as a callable | runtime | **High** — most call sites pass `tenant` as a string; all must remain compatible after the FK refactor |
| `clinic-ai-assistant-src/backend/app/services/ai_agent.py` | Top-level orchestration; imports and passes `save_lead_checkpoint` to booking_credentials at 4 call sites | Lines 1093, 1553, 1946, 1992 — all `save_lead_checkpoint=save_lead_checkpoint` kwarg passes | runtime | **Medium** — the function signature is injected, so changes are localized if the signature stays stable |
| `clinic-ai-assistant-src/backend/app/services/chat_session_state.py` | Calls `load_lead_checkpoint` on every request for session recovery | `_load_session_state` | runtime | **Medium** — recovery logic reads persisted stage and data; must keep working after `tenant` column is removed |
| `clinic-ai-assistant-src/backend/db/assistant_velika.db` | The live SQLite database with real lead rows tied to `"milena_dental"` | N/A — data file, not code | migration | **High** — existing rows must be backfilled to `tenant_id` without data loss; SQLite DDL constraints apply |
| `clinic-ai-assistant-src/backend/tests/integration/test_req_booking_flow.py` | Integration test suite covering the full booking flow end-to-end; directly calls `load_lead_checkpoint("milena_dental", ...)` | `_build_booking_ctx`, all test functions that assert `stored = booking_ctx.lead_store.load_lead_checkpoint(...)` | test | **Medium** — tests use the tenant string directly; will need updates after the FK refactor |
| `clinic-ai-assistant-src/backend/tests/unit/test_lead_store_helpers.py` | Unit tests for `lead_store` internals; directly calls `save_lead_checkpoint` and `load_lead_checkpoint` with `"milena_dental"` | `test_save_lead_checkpoint_*`, `test_load_lead_checkpoint_*`, `isolated_db` fixture | test | **Medium** — fixtures initialize the DB and will need to seed a tenant row after schema change |

**Explicitly excluded: `clinic-ai-assistant-src/backend/app/routes/chat.py`**
This file is a pure pass-through. It receives `tenant` as a string query parameter and passes it unchanged to `ai_agent.py`. It has no direct database interaction. The internal translation from tenant slug to `tenant_id` happens inside `lead_store`, so the route signature and behavior do not change. No modification required.

---

## Prompt 2 - Completed

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

### Completion Note

Prompt 2 was completed in `clinic-ai-assistant-src/backend/app/services/lead_store.py`.

Implemented outcomes:
- `init_leads_db()` now creates the `tenants` table if missing
- a unique index is created on `tenants.unique_identifier`
- `leads.tenant_id` is added idempotently if missing
- an index is created on `leads.tenant_id`
- the default tenant seed row for `milena_dental` is inserted if missing

Explicitly not done in this prompt:
- no backfill of existing `leads.tenant_id` values
- no removal of the legacy `tenant` text column
- no runtime refactor of read/write paths to use `tenant_id`

## Prompt 3 - Completed

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

### Completion Note

Prompt 3 was completed in `clinic-ai-assistant-src/backend/app/services/lead_store.py`.

Implemented outcomes:
- existing `leads` rows are backfilled from tenant name to `tenant_id`
- migration halts if any lead row cannot be matched to a tenant
- the legacy `tenant` column is removed through a SQLite table rebuild
- the rebuilt `leads` table now uses `UNIQUE(tenant_id, session_id)`
- a foreign key integrity check runs after migration
- `lead_store` now resolves tenant names to `tenant_id` internally so the application remains compatible after the legacy column removal

Explicitly not done in this prompt:
- no broader runtime cleanup outside `lead_store.py`
- no test updates yet
- no chat transcript schema work yet

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
