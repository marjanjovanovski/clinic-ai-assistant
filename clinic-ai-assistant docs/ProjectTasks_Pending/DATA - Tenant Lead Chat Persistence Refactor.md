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

Understand the current implementation and document the reasoning for the refactor before making structural changes.

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

You must then write a concise implementation understanding summary covering:
- the current persistence model
- why it works today
- its limitations
- why the new relational model is needed
- the likely code touchpoints that will need to change

### Required Outcome

Produce a concise but clear architecture/migration understanding before schema work begins.

## Prompt 2 - Pending

### Goal

Design and implement the new tenant model.

### Instructions

Create a new `tenants` table.

The table must include:
- `id`
- `unique_identifier`
- `name`
- `comment`
- `phone`
- `email`
- `primary_contact_name`
- `secondary_contact_name`
- `date_registered`

Design requirements:
- If `id` is an autoincrement integer primary key, also keep `unique_identifier` as a stable unique business identifier.
- If a different key strategy is better, explain it briefly, but still provide a stable unique identifier suitable for business use.
- Add appropriate uniqueness and indexing where justified.
- Insert an initial tenant record with `name = "milena_dental"`.

### Required Outcome

A production-minded tenant parent table exists and includes the migrated seed tenant.

## Prompt 3 - Pending

### Goal

Refactor the leads model to use relational tenant ownership.

### Instructions

Modify the existing `leads` table so it no longer relies on the current `tenant` text column.

Required changes:
- introduce `tenant_id`
- connect `tenant_id` to `tenants.id`
- preserve all existing lead data
- migrate all records currently tied to `milena_dental` so they now reference the inserted tenant row
- remove the old `tenant` column after migration is safely handled

Important:
- preserve compatibility with the current lead checkpoint and recovery behavior
- be careful with SQLite migration constraints
- ensure existing session-linked lead rows continue to work

### Required Outcome

`leads` is tenant-owned through a foreign key and all current lead data remains intact and linked to the correct tenant parent.

## Prompt 4 - Pending

### Goal

Add durable, professional-grade chat transcript persistence.

### Instructions

Create a new schema structure for logging all chat encounters.

Business intent:
- every user message must be stored
- every assistant reply must be stored
- each conversation must be clearly tied to the correct tenant
- each conversation must be clearly tied to the correct session
- natural ordering of the conversation must be easy to reconstruct
- chats must never mix with one another
- the design must be suitable for future simultaneous activity and higher write volume

Design freedom:
- if appropriate, create `chat_sessions` and `chat_messages`
- if a different normalized structure is better, use it and explain why
- avoid redundant repetition of session-level data where a better structure exists

Implementation requirement:
- integrate this into the actual runtime flow so new chat turns are persisted automatically
- make the ownership and ordering model easy to inspect later

### Required Outcome

A durable transcript/audit structure exists and captures the real flow of every conversation in a session-safe and tenant-safe way.

## Prompt 5 - Pending

### Goal

Finish application integration, validation, and test coverage.

### Instructions

Update the application code so:
- new leads are written with `tenant_id`
- lead loading and recovery continue to function
- new chat sessions and messages are persisted
- existing booking semantics are preserved

Add or update tests for:
- tenant creation
- seed/migration of `milena_dental`
- lead backfill to `tenant_id`
- lead recovery after migration
- chat session creation
- chat message ordering
- correct tenant/session ownership
- prevention of cross-session mixing

Then summarize:
- what changed
- why the new design is better
- what assumptions were made
- any risks or recommended follow-up work

### Required Outcome

The refactor is fully integrated, validated, and documented.

## Final Completion Rule

This document should only show all prompts as `Completed` once:
- schema changes are implemented
- data migration is handled
- runtime code is updated
- tests are updated or added
- the implementing AI agent has written a concise final summary of the delivered work
