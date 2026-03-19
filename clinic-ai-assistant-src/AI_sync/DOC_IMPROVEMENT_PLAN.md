# DOC_IMPROVEMENT_PLAN

## PURPOSE

This file is the operational plan for documentation improvements in the repository.
It translates identified documentation gaps into a prioritized backlog of atomic tasks.
Each planned task is limited to one target file and one documentation outcome.
This file is used as the execution reference for future documentation work under AI_sync rules.
It is planning-only and does not implement the documentation changes itself.

## PRIORITY ORDER

### DOC-01
- Title: Create project baseline team-operating note
- Why it matters: The collaboration model is now important enough to deserve one operational baseline. Writing it once reduces repeated prompting, role drift, and ambiguous handoff behavior.
- Dependency: None

### DOC-02
- Title: Create AI_sync entrypoint
- Why it matters: AI_sync is now the active execution contract, but there is no single plain-language entry file for fast orientation. This increases sync overhead for collaborators and future sessions.
- Dependency: None

### DOC-03
- Title: Correct repository scope paths
- Why it matters: `REPO_SCOPE.md` currently uses path wording that is less precise than the actual repo-root structure. Tightening path accuracy reduces scope confusion during execution.
- Dependency: None

### DOC-04
- Title: Create current runtime focus snapshot
- Why it matters: `REPO_FULL_OVERVIEW.md` is broad, but there is no compact operational note for the live backend state and current sensitive implementation focus.
- Dependency: DOC-02

### DOC-05
- Title: Document runtime anchor file roles
- Why it matters: The key ownership split across `ai_agent.py`, `lead_store.py`, and `milena_dental.json` should be readable in one dedicated sync artifact to reduce architecture drift.
- Dependency: DOC-04

### DOC-06
- Title: Document booking and contact state sequence
- Why it matters: The booking/contact flow exists in code and summary form, but not yet as a dedicated explicit state sequence. This is a high-risk area for collaborator misunderstanding.
- Dependency: DOC-04

### DOC-07
- Title: Add sync drift risk guidance
- Why it matters: The repo already has asymmetry between repo-connected and non-repo-connected collaborators. Explicit drift-risk documentation lowers coordination loss.
- Dependency: DOC-02

### DOC-08
- Title: Add encoding and readability standard
- Why it matters: Human-read files lose trust and usefulness when encoding or readability issues appear. A small standard reduces recurring friction in notes, Markdown, and JSON-facing work.
- Dependency: DOC-02

### DOC-09
- Title: Add update-trigger guidance to AI_sync docs
- Why it matters: AI_sync files define the execution contract, but most do not yet state clearly when they should be updated. This can allow silent staleness.
- Dependency: DOC-02

### DOC-10
- Title: Add commit and date anchoring guidance for overview sections
- Why it matters: Sections such as recent development and current stability are stronger when explicitly tied to a stabilization trail rather than implied recency.
- Dependency: DOC-04

### DOC-11
- Title: Separate operational and personal documentation boundaries
- Why it matters: Operational sync artifacts and personal continuity notes serve different purposes. Clear boundary documentation prevents future mixing of governance and personal memory notes.
- Dependency: DOC-02

## TASK BREAKDOWN

### DOC-01
- TASK_ID: TASK_IMPL_TEAM_OPERATING_BASELINE
- Target file: clinic-ai-assistant-src/AI_sync/PROJECT_BASELINE_HOW_TEAM_OPERATES.md
- Action type: CREATE
- Exact outcome: Create a concise baseline document that defines how Marjan, Aris, and Kai work together, how repo truth is established, and how strategy, execution, and verification are separated.
- Scope boundaries: Do not include personal continuity language. Do not redesign AI_sync rules. Keep the note operational and collaborator-facing.

### DOC-02
- TASK_ID: TASK_IMPL_SYNC_START_HERE
- Target file: clinic-ai-assistant-src/AI_sync/START_HERE.md
- Action type: CREATE
- Exact outcome: Create a short AI_sync entrypoint that explains what AI_sync is now, which files form the active contract, and the recommended read order for fast orientation.
- Scope boundaries: Do not modify existing AI_sync files. Do not restate the full repository overview. Do not add execution rules that differ from the existing contract.

### DOC-03
- TASK_ID: TASK_IMPL_SCOPE_PATH_CORRECTION
- Target file: clinic-ai-assistant-src/AI_sync/REPO_SCOPE.md
- Action type: UPDATE
- Exact outcome: Tighten repository-scope path wording so allowed, restricted, and forbidden paths are unambiguous from repo root and consistent with the actual repository structure.
- Scope boundaries: Do not change scope policy intent. Do not modify non-path rules. Do not expand permissions.

### DOC-04
- TASK_ID: TASK_IMPL_CURRENT_RUNTIME_FOCUS
- Target file: clinic-ai-assistant-src/AI_sync/CURRENT_RUNTIME_FOCUS.md
- Action type: CREATE
- Exact outcome: Create a compact runtime snapshot for the current live backend behavior, sensitive areas, recent stabilization context, and current execution focus.
- Scope boundaries: Do not duplicate the full repository overview. Do not introduce speculative roadmap content. Do not redesign architecture.

### DOC-05
- TASK_ID: TASK_IMPL_RUNTIME_ANCHOR_ROLES
- Target file: clinic-ai-assistant-src/AI_sync/RUNTIME_ANCHOR_ROLES.md
- Action type: CREATE
- Exact outcome: Document the role boundaries of the main runtime anchor files, especially `ai_agent.py`, `lead_store.py`, and `milena_dental.json`, in concise operational language.
- Scope boundaries: Do not restate full implementation details. Do not modify source files. Do not duplicate broad overview sections unnecessarily.

### DOC-06
- TASK_ID: TASK_IMPL_BOOKING_STATE_SEQUENCE
- Target file: clinic-ai-assistant-src/AI_sync/BOOKING_STATE_SEQUENCE.md
- Action type: CREATE
- Exact outcome: Document the current booking and contact collection flow as an explicit state sequence, including progression, gating, persistence dependence, and recovery behavior.
- Scope boundaries: Do not invent behavior not grounded in current code. Do not include redesign proposals. Do not modify backend files.

### DOC-07
- TASK_ID: TASK_IMPL_SYNC_DRIFT_GUIDE
- Target file: clinic-ai-assistant-src/AI_sync/SYNC_DRIFT_RISKS.md
- Action type: CREATE
- Exact outcome: Create a focused note describing concrete sync drift risks, especially where unsynced collaborators are most likely to misunderstand current repo truth.
- Scope boundaries: Do not include speculative complaints. Do not broaden into team philosophy. Keep risks evidence-based and operational.

### DOC-08
- TASK_ID: TASK_IMPL_ENCODING_STANDARD
- Target file: clinic-ai-assistant-src/AI_sync/ENCODING_READABILITY_STANDARD.md
- Action type: CREATE
- Exact outcome: Define a small repository documentation standard for encoding and readability expectations in human-read Markdown, JSON-facing content, and sync artifacts.
- Scope boundaries: Do not rewrite existing files in this task. Do not turn this into a global coding standard. Keep it documentation-focused.

### DOC-09
- TASK_ID: TASK_IMPL_UPDATE_TRIGGER_RULES
- Target file: clinic-ai-assistant-src/AI_sync/UPDATE_TRIGGER_RULES.md
- Action type: CREATE
- Exact outcome: Create a single rules file that defines when AI_sync documents should be updated and which classes of changes should trigger refresh.
- Scope boundaries: Do not modify multiple AI_sync docs in the same task. Do not duplicate the full prompt protocol. Keep the guidance deterministic.

### DOC-10
- TASK_ID: TASK_IMPL_OVERVIEW_ANCHOR_GUIDANCE
- Target file: clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md
- Action type: UPDATE
- Exact outcome: Strengthen the overview's recent-development and stability sections with clearer commit/date anchoring guidance while preserving the file's full-regeneration role.
- Scope boundaries: Do not redesign section structure unnecessarily. Do not alter repository inclusion/exclusion rules unless separately requested.

### DOC-11
- TASK_ID: TASK_IMPL_DOC_BOUNDARY_RULE
- Target file: clinic-ai-assistant-src/AI_sync/DOC_BOUNDARY_RULES.md
- Action type: CREATE
- Exact outcome: Define the operational boundary between collaborator-facing sync/governance docs and personal continuity notes so future documentation stays properly classified.
- Scope boundaries: Do not modify personal-team-touch files. Do not move existing notes. Keep the rule operational and repository-scoped.

## EXECUTION SEQUENCE

1. TASK_IMPL_SYNC_START_HERE
2. TASK_IMPL_SYNC_START_HERE
3. TASK_IMPL_SCOPE_PATH_CORRECTION
4. TASK_IMPL_CURRENT_RUNTIME_FOCUS
5. TASK_IMPL_RUNTIME_ANCHOR_ROLES
6. TASK_IMPL_BOOKING_STATE_SEQUENCE
7. TASK_IMPL_SYNC_DRIFT_GUIDE
8. TASK_IMPL_ENCODING_STANDARD
9. TASK_IMPL_UPDATE_TRIGGER_RULES
10. TASK_IMPL_OVERVIEW_ANCHOR_GUIDANCE
11. TASK_IMPL_DOC_BOUNDARY_RULE

## VERIFICATION RULES

- Every task must confirm that the target file exists if it is a create task.
- Every task must confirm that the target file changed only in the requested scope if it is an update task.
- Every task must confirm that the required structure for that document is present.
- Every task must confirm that no unintended file changes occurred outside the named target file.
- Every task must be verified as a separate read-only step before the next implementation task begins.

## DRIFT RISKS

- Multi-file documentation updates may break AI_sync scope rules and create uncontrolled sync changes.
- Broad narrative rewrites may blur the line between planning artifacts and active contract files.
- Repo-connected and non-repo-connected collaborators may diverge if runtime-sensitive docs are not refreshed in sequence.
- Operational sync notes may drift into personal continuity space if boundaries are not made explicit.
- Overview-heavy docs may become stale faster if update triggers remain implicit.

## USAGE RULE

- Use this file as the ordered execution backlog for documentation improvements.
- Do not rewrite the plan unless a verified dependency conflict requires it.
- Execute one planned task at a time, with one target file per task.
- Mark tasks done only after their separate verification step passes.
- Do not use this file for inline discussion or mixed implementation notes.
