# Tomorrow Sync Prompts

This note collects the current prompt set for tomorrow's sync with Aris and for fast project bootstrap.

## AI_sync Snapshot Refresh

```text
MODE: IMPLEMENT
TASK_ID: TASK_IMPL_SYNC_REPO_OVERVIEW
STATE: PENDING

Target folder:
clinic-ai-assistant-src/AI_sync/

Target file:
clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md

Goal:
Regenerate REPO_FULL_OVERVIEW.md so it reflects the current repository snapshot after the latest backend stabilization trail, while preserving the existing file’s role as the deterministic full repository state overview.

Constraints:
- Modify only clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md
- Do not modify any other AI_sync file
- Treat this as full-regeneration only, not patch-style sync
- Preserve the existing repository inclusion/exclusion boundaries unless the provided context explicitly changes them
- Do not include personal-team-touch/ in the official repository scope
- Do not redesign architecture
- Respect backend configuration separation: conversational/config content belongs in tenant JSON, Python remains logic/orchestration
- Use the following current state as the authoritative update context:
  - AI_sync is now an active deterministic execution framework, not only a prompt aid
  - PROMPT_PROTOCOL.md is the active execution contract
  - ai_agent.py currently owns deterministic conversation orchestration, booking-state handling, active booking lock during collecting_contact, bounded context carry, clarification recovery, field-level contact validation, explicit booking confirmation gating, persistence-gated completion, and recovery that prefers persisted truth over stale in-memory contact state
  - lead_store.py currently owns SQLite checkpoint save/load, exact-row verification after commit, required-field-aware persistence success evaluation, persisted-state hydration, and authoritative persisted contact recovery
  - milena_dental.json currently owns receptionist-style Macedonian behavior, booking/contact wording, clarification replies, and stepwise booking contact collection wording starting from the name field
  - Recent stabilization trail to reflect:
    - 6b32392 refactor(profile): align booking intro with stepwise collection
    - 29b5245 fix(backend): harden persistence authority rules
    - 71e2345 refactor(profile): refine booking contact intro wording
    - 5751fb0 fix(backend): limit combined contact parsing to explicit bundles
    - caaac77 fix(backend): verify booking persistence before confirmation
    - 55f7262 fix(backend): lock active booking flow
    - 4f704de fix(backend): keep ownership clarifications inside booking flow
    - 908da86 fix(backend): stabilize booking checkpoint continuity
    - 976a0a1 fix(backend): harden phone field handling
    - 88f2b7d fix(backend): harden contact input gating
    - 71d743d docs(sync): update repo overview and progress tracker
    - 6fc20be fix(backend): recover booking clarification replies

Return:
1. Exact file path
2. Line count
3. Full file content
4. First 20 lines preview
```

```text
MODE: VERIFY
TASK_ID: TASK_VERIFY_REPO_OVERVIEW_SYNC
STATE: PENDING

Context:
Verification for the regenerated clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md snapshot.

Verify:
- The file reflects the current backend architecture and recent stabilization trail
- The file stayed within its existing repository scope and exclusion rules
- No unintended AI_sync files were modified
- The regenerated overview keeps AI_sync framed as the active deterministic execution layer

Constraints:
- read-only operation
- no file modifications
- no new files
- inspect only clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md and git diff metadata needed to confirm scope
- do not perform architecture redesign

Return:
1. Compliance result
2. Missing or stale snapshot items, if any
3. Scope or accuracy risk, if any
4. Explicit confirmation whether the file is ready for collaborator sync
```

## Bootstrap Sequence

```text
MODE: VERIFY
TASK_ID: TASK_VERIFY_SYNC_GOVERNANCE
STATE: PENDING

Context:
Bootstrap step 1 for current AI_sync governance.

Verify:
- What execution rules are active
- What output/artifact rules are active
- What backend architecture separation rules are active

Constraints:
- read-only operation
- no file modifications
- no new files
- read only:
  - clinic-ai-assistant-src/AI_sync/ARTIFACT_RULES.md
  - clinic-ai-assistant-src/AI_sync/OUTPUT_RULES.md
  - clinic-ai-assistant-src/AI_sync/PROMPT_PROTOCOL.md
- return only high-signal synthesis

Return:
1. AI_sync Governance Snapshot
2. Active architectural constraints
3. Any protocol caveat that affects future work
4. Explicit confirmation of compliance understanding
```

```text
MODE: VERIFY
TASK_ID: TASK_VERIFY_REPO_CONTROL_CONTEXT
STATE: PENDING

Context:
Bootstrap step 2 for current repository control-layer and scope state.

Verify:
- Current repository identity and included scope
- Current control-layer status
- Current restricted and forbidden scope rules

Constraints:
- read-only operation
- no file modifications
- no new files
- read only:
  - clinic-ai-assistant-src/AI_sync/FAILURE_PROTOCOL.md
  - clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md
  - clinic-ai-assistant-src/AI_sync/REPO_SCOPE.md
- return only high-signal synthesis

Return:
1. Repository and control-layer snapshot
2. Restricted-scope rules that matter in practice
3. Any sync drift or caution signs, if present
4. Explicit confirmation of compliance understanding
```

```text
MODE: VERIFY
TASK_ID: TASK_VERIFY_BACKEND_RUNTIME_SNAPSHOT
STATE: PENDING

Context:
Bootstrap step 3 for the current live backend behavior and booking/contact flow state.

Verify:
- What ai_agent.py is responsible for
- What lead_store.py is responsible for
- What milena_dental.json is responsible for
- How booking confirmation, contact collection, persistence verification, and recovery currently work
- Summarize the stabilization trail represented by these commits:
  - 6b32392 refactor(profile): align booking intro with stepwise collection
  - 29b5245 fix(backend): harden persistence authority rules
  - 71e2345 refactor(profile): refine booking contact intro wording
  - 5751fb0 fix(backend): limit combined contact parsing to explicit bundles
  - caaac77 fix(backend): verify booking persistence before confirmation
  - 55f7262 fix(backend): lock active booking flow
  - 4f704de fix(backend): keep ownership clarifications inside booking flow
  - 908da86 fix(backend): stabilize booking checkpoint continuity
  - 976a0a1 fix(backend): harden phone field handling
  - 88f2b7d fix(backend): harden contact input gating
  - 71d743d docs(sync): update repo overview and progress tracker
  - 6fc20be fix(backend): recover booking clarification replies

Constraints:
- read-only operation
- no file modifications
- no new files
- read only:
  - clinic-ai-assistant-src/backend/app/services/ai_agent.py
  - clinic-ai-assistant-src/backend/app/services/lead_store.py
  - clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json
- keep the output concise and evidence-based
- do not invent risks without code evidence

Return:
1. Current Backend Architecture
2. Current Booking/Contact Flow State
3. Recent Stabilization Summary
4. Open Caution Areas
```

## Snapshot Note

- Today's repository change that I made was outside official AI_sync scope:
  - personal-team-touch/OPEN_HAND_WITH_MARJAN.md updated, UTF-8 normalized, and committed as `491f5cb`
- That note is intentionally excluded from REPO_FULL_OVERVIEW.md repository scope and should not be treated as operational backend state
