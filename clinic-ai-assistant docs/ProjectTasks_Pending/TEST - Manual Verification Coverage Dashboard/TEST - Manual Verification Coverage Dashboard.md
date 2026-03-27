# Manual Verification Coverage Dashboard Master Prompt

This document defines the execution-ready task plan for adding a local `ManualTesting.html` workflow that loads per-task manual verification coverage from JSON and helps decide merge readiness.

The purpose of this work is to:
- provide one simple HTML page for manual verification tracking
- load manual testing coverage from JSON instead of writing results directly into code
- support switching between multiple pending tasks waiting for final manual verification
- allow manual testers to mark each step as `Not Run`, `Pass`, or `Fail`
- allow failure comments and a separate reference-file field per row
- save progress locally without creating repo junk
- align future task creation so each pending task lives in its own folder with its own `manual_testing_coverage.json`

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

- `Completed`

## Current Active Prompt

- `None - Ready for review`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed
- Prompt 5 - Completed
- Prompt 6 - Completed
- Prompt 7 - Completed
- Prompt 8 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the repo before designing new storage or UI structure.
- Reuse existing JSON read/write helpers or patterns where practical instead of creating redundant utilities.
- Keep this feature local-first and simple; do not introduce unnecessary backend complexity unless the repo structure requires it.
- Treat the dashboard as a manual verification tool, not a replacement for task MD files.
- Keep the UI optimized for wide screens and desk use; mobile responsiveness is not required for this task.
- Use inner scrolling for the main table area so the page remains stable on large verification sets.
- Keep save behavior explicit and reliable.
- Keep reference handling text-only:
  - no upload
  - no preview
  - no attachment management UI
  - only a separate field where the reviewer types filenames that already exist in the same task folder
- Prefer broader execution boundaries over many micro-prompts for this task.
- Keep prompt completion notes short:
  - what changed
  - what was verified
  - blockers or warnings
- Use short descriptive commit messages rather than long narrative commit text.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work has actually been implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to keep test artifacts out of the repository.
- When running pytest, use external `TMP` / `TEMP` and an external `--basetemp`.
- For this Windows environment, if sandbox or `F:\temp` pytest execution hits temp or SQLite permission failures, switch promptly to the proven external-user-temp fallback pattern instead of retrying many temp variants.
- Add or update focused coverage for JSON loading, task discovery, save behavior, and merge-readiness calculation.
- Do not leave repo-local temp artifacts.
- Final verification must include a repo residual check.

## Do Not Break

- existing task MD authoring workflow outside the intended folder-based update
- existing pending task execution tracking semantics
- existing JSON read/write helpers already used elsewhere in the backend or tooling
- existing frontend asset loading and static file serving patterns
- existing manual verification rule that merge still requires human approval

## Current Repo Truth

- Pending tasks currently live directly as `.md` files in `ProjectTasks_Pending`.
- Manual verification guidance currently lives inside task MD appendices.
- There is no dedicated HTML page for tracking manual verification status across tasks.
- There is no standardized `manual_testing_coverage.json` artifact per task yet.
- The guide was just updated to require tracked manual verification prompts before merge.
- This feature now aims to make that manual verification phase more operational and easier to manage.

## Architecture Guidance

### Target User Flow

- Development for a task finishes.
- The task has a pending final manual verification prompt.
- The reviewer opens one local HTML page: `ManualTesting.html`.
- The page discovers pending tasks that are waiting for manual verification.
- The reviewer selects a task from the top switcher.
- The page loads that task's `manual_testing_coverage.json`.
- The reviewer marks each row as `Pass` or `Fail`, adds comments, and lists reference file names if needed.
- The page saves the JSON updates.
- When all required rows are completed acceptably, the task can proceed to final merge steps.

### Folder Convention Target

Future pending tasks should use a folder like:
- `ProjectTasks_Pending/<Task Name>/`

Inside each task folder:
- `<Task Name>.md`
- `manual_testing_coverage.json`
- optional evidence files later added manually by the user such as images or PDFs

### Dashboard Scope

The HTML page should support:
- task switching across pending tasks awaiting manual verification
- table rows driven by JSON
- columns for:
  - category
  - test name
  - step
  - what is tested
  - status
  - comment
  - reference files
- save capability
- merge-readiness summary derived from row statuses

The HTML page should not support in this version:
- file upload
- image preview
- PDF preview
- automatic merge actions
- automatic markdown rewriting
- mobile-focused responsive behavior
- advanced filtering or search

### Storage Shape Direction

The JSON should represent:
- task metadata
- categories
- tests
- rows or steps
- status values
- comment field
- separate reference-files field storing plain typed filenames

Recommended row-level status values:
- `Not Run`
- `Pass`
- `Fail`

Recommended first-version schema:

```json
{
  "task_name": "TEST - Manual Verification Coverage Dashboard",
  "task_file": "TEST - Manual Verification Coverage Dashboard.md",
  "status": "pending_manual_verification",
  "categories": [
    {
      "name": "Category 1 - Example",
      "tests": [
        {
          "name": "Test 1.1 - Example",
          "rows": [
            {
              "step": 1,
              "action": "Do the action",
              "what_is_tested": "The expected behavior",
              "status": "Not Run",
              "comment": "",
              "reference_files": ""
            }
          ]
        }
      ]
    }
  ],
  "summary": {
    "not_run": 1,
    "pass": 0,
    "fail": 0
  }
}
```

Schema decisions for version 1:
- each row represents one manual verification step
- `reference_files` is a plain text field containing typed filenames, optionally comma-separated
- `summary` may be stored for convenience, but runtime should be able to recompute it from row statuses
- merge readiness logic should derive from row status values, not from freeform comments
- categories and tests should remain explicit in JSON so the HTML page does not need to infer structure from flat text

Legacy compatibility direction:
- folder-based tasks are the preferred first-class target
- legacy flat `.md` tasks may still appear in task discovery during transition
- legacy flat tasks should not block implementation of the folder-based contract
- if a flat task has no `manual_testing_coverage.json`, the dashboard may either omit it from editable coverage or surface it as a migration-needed item, depending on the later discovery implementation choice

### Reuse Expectation

Before implementing new JSON utilities, inspect the repo for:
- existing JSON loading helpers
- existing save/update patterns
- existing static file serving conventions
- existing frontend patterns for table rendering or state persistence

## Desired Outcome

After all prompts are complete, the repo should have:
- a `ManualTesting.html` page
- a task-discovery mechanism for pending tasks awaiting manual verification
- a per-task `manual_testing_coverage.json` contract
- save and reload behavior for manual verification progress
- a separate comment field and a separate reference-files field for each verification row
- guide updates enforcing the new folder-based task structure for future pending tasks
- a migration or compatibility plan for current pending task files

## Prompt 1 - Completed

### Goal

Audit the repo for existing JSON read/write helpers, static serving patterns, and task-file assumptions before introducing the dashboard.

### Instructions

Inspect the relevant code and docs first.

Requirements:
- find existing JSON read/write helpers or patterns that can be reused
- find how static HTML files are currently served
- find any assumptions that pending tasks are flat `.md` files rather than task folders
- identify the smallest safe integration boundary for the dashboard

### Required Outcome

The implementation boundary is clear and reuse opportunities are identified before design changes begin.

### Completion Note

Prompt 1 is completed.

Repo audit findings:
- static frontend serving already exists in:
  - `clinic-ai-assistant-src/backend/app/main.py`
  - the backend mounts `"/frontend"` through `StaticFiles(...)`
  - this means `ManualTesting.html` can likely be served through the same frontend static surface instead of inventing a new serving model
- existing JSON read/write patterns already exist and should be reused as style references rather than inventing a new serialization approach:
  - `clinic-ai-assistant-src/backend/app/services/config_loader.py`
    - uses `json.load(...)` for UTF-8 config files
  - `clinic-ai-assistant-src/backend/app/services/lead_store.py`
    - uses `json.loads(...)` / `json.dumps(...)`
    - already persists structured state and demonstrates safe UTF-8 JSON handling patterns
  - `clinic-ai-assistant-src/lessons_learned_repo/history_cli.py`
    - uses `Path(...).read_text(...)` and `json.dumps(...)` for simple file-based prompt/evidence handling
- no strong repo-wide implementation dependency was found that hardcodes `ProjectTasks_Pending` as flat `.md` files in runtime code
- the current pending-task folder is now in a mixed state:
  - legacy flat task files still exist directly in `ProjectTasks_Pending`
  - the new dashboard task already exists as a folder with:
    - `TEST - Manual Verification Coverage Dashboard.md`
    - `manual_testing_coverage.json`
- architecture conclusion for this feature:
  - the safest first version is to keep the dashboard local and static
  - reuse existing JSON handling patterns
  - support folder-based tasks first while documenting how legacy flat files are handled during transition

Branch note:
- work is running on dedicated branch `task-manual-verification-dashboard`

## Prompt 2 - Completed

### Goal

Design the JSON schema and task-folder contract, and update the guide for the new folder-based workflow.

### Instructions

Define the per-task folder and JSON structure before implementation.

Requirements:
- define required task-folder structure
- define the JSON schema for categories, tests, and rows
- define status values and merge-readiness rules
- define how reference filenames are stored as plain text in a dedicated field
- update the guide so future tasks use task folders with `manual_testing_coverage.json`
- keep compatibility guidance clear for existing flat task files
- keep the schema simple enough for direct HTML rendering

### Required Outcome

The task-folder rule and JSON contract are explicit and implementation-ready.

### Completion Note

Prompt 2 is completed.

Design decisions locked for version 1:
- new pending tasks should live in their own folder under `ProjectTasks_Pending`
- the task markdown file remains the workflow authority
- `manual_testing_coverage.json` is the structured companion artifact for manual verification state
- the JSON contract uses:
  - `categories`
  - `tests`
  - `rows`
  - row fields:
    - `step`
    - `action`
    - `what_is_tested`
    - `status`
    - `comment`
    - `reference_files`
- `reference_files` is plain text only, optionally comma-separated, and refers to files manually placed in the same task folder
- row status values for version 1 are:
  - `Not Run`
  - `Pass`
  - `Fail`
- merge readiness should be derived from row statuses, not from prose notes

Guide updates completed in this prompt:
- added a pending-task folder convention for new tasks
- defined the role of `manual_testing_coverage.json`
- documented legacy flat-task compatibility during transition
- documented that state-heavy manual verification data should live in the JSON companion artifact rather than repeated markdown edits

## Prompt 3 - Completed

### Goal

Implement task discovery together with the JSON load/save layer.

### Instructions

Apply the new rule to the guide before building the full feature.

Requirements:
- identify pending tasks with a manual verification prompt still pending
- support the new folder-based convention
- define how to handle legacy flat task files during transition
- load `manual_testing_coverage.json`
- validate minimum required structure
- save status, comments, and reference-file updates
- avoid redundant helper code when existing utilities can be reused
- keep the discovery and persistence logic deterministic and testable

### Required Outcome

The dashboard can discover candidate tasks and persist manual verification data reliably.

### Completion Note

Prompt 3 is completed.

Implemented backend support:
- added task discovery and JSON persistence service in:
  - `clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py`
- added route layer in:
  - `clinic-ai-assistant-src/backend/app/routes/manual_verification.py`
- wired the new route into:
  - `clinic-ai-assistant-src/backend/app/main.py`

Discovery behavior implemented:
- scans `ProjectTasks_Pending`
- supports:
  - folder-based tasks with `<Task Name>.md`
  - legacy flat `.md` tasks during transition
- identifies tasks that currently have a pending manual verification / merge readiness prompt
- returns task metadata including:
  - task id
  - task name
  - task file
  - entry type
  - pending manual prompt number
  - current active prompt
  - merge status
  - whether `manual_testing_coverage.json` is available

Persistence behavior implemented:
- loads `manual_testing_coverage.json` for folder-based tasks
- validates:
  - categories
  - tests
  - rows
  - allowed row status values
- saves:
  - `status`
  - `comment`
  - `reference_files`
- recomputes `summary` from row statuses on save

Compatibility decision in this prompt:
- legacy flat tasks are discoverable during transition
- if they do not yet have `manual_testing_coverage.json`, they are surfaced without editable coverage data rather than being silently ignored

Verification completed for Prompt 3:
- static verification:
  - `python -m py_compile clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py clinic-ai-assistant-src/backend/app/routes/manual_verification.py clinic-ai-assistant-src/backend/app/main.py`

## Prompt 4 - Completed

### Goal

Create `ManualTesting.html` and render the JSON-driven table UI.

### Instructions

Build the discovery path that powers the task selector.

Requirements:
- add a task selector at the top
- add summary area for pass/fail/not-run counts
- add a fixed-header, inner-scroll table area
- render category/test grouping clearly
- render row fields from JSON
- keep the table readable for large task sets
- optimize for desk and wide-screen use rather than mobile responsiveness

### Required Outcome

The page shell and rendered table are usable for real manual verification review.

### Completion Note

Prompt 4 is completed.

Implemented frontend surface:
- added:
  - `clinic-ai-assistant-src/frontend/ManualTesting.html`

What the page now does:
- loads pending manual-verification tasks from:
  - `/manual-verification/tasks`
- provides a top task selector
- shows summary cards for:
  - `Not Run`
  - `Pass`
  - `Fail`
  - task state
- renders a wide-screen fixed-header table with inner scrolling
- renders row columns for:
  - category
  - test
  - step
  - action
  - what is tested
  - status
  - comment
  - reference files
- handles both:
  - folder-based tasks with editable coverage available later
  - legacy flat tasks surfaced as migration-needed when coverage JSON is missing

Scope note for this prompt:
- this prompt intentionally built the read/review UI only
- edit and save controls remain for Prompt 5

Verification completed for Prompt 4:
- static verification:
  - `python -m py_compile clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py clinic-ai-assistant-src/backend/app/routes/manual_verification.py clinic-ai-assistant-src/backend/app/main.py`
- focused runtime verification:
  - `GET /frontend/ManualTesting.html` returned `200`
  - `GET /manual-verification/tasks` returned `200`
  - the page rendered the dashboard shell title
  - the task endpoint returned a task list payload

## Prompt 5 - Completed

### Goal

Implement interaction controls, save behavior, and merge-readiness summary.

### Instructions

Build the persistence layer using reused patterns where practical.

Requirements:
- support `Not Run`, `Pass`, `Fail`
- provide a comment field for failures or observations
- provide a separate multiline reference-files field for comma-separated image/PDF names
- add explicit save capability
- reflect unsaved/saved state clearly
- compute pass/fail/not-run counts
- define when a task is ready for merge
- show blocked state clearly when any test is `Fail` or unfinished
- keep merge approval as a human decision even when all rows pass

### Required Outcome

The dashboard is fully usable for tracking manual verification progress and readiness state.

### Completion Note

Prompt 5 is completed.

Implemented interaction behavior in:
- `clinic-ai-assistant-src/frontend/ManualTesting.html`

What changed:
- added explicit `Save` button
- added save-state feedback:
  - `No changes`
  - `Unsaved changes`
  - `Saving...`
  - `Saved`
- replaced read-only status badges with editable status dropdowns
- added editable multiline comment field per row
- added editable multiline `reference_files` field per row
- added client-side dirty tracking
- added client-side summary recomputation from current row values
- added merge-readiness label behavior:
  - `Blocked` when any row is `Fail`
  - `In Review` when rows remain `Not Run`
  - `Ready` when all rows are `Pass`
- wired the page to save through:
  - `PUT /manual-verification/tasks/{task_id}`

Verification completed for Prompt 5:
- static verification:
  - `python -m py_compile clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py clinic-ai-assistant-src/backend/app/routes/manual_verification.py clinic-ai-assistant-src/backend/app/main.py`
- focused runtime verification:
  - exercised `PUT /manual-verification/tasks/{task_id}` with a sample payload
  - confirmed the saved response recomputed summary counts as:
    - `{'not_run': 0, 'pass': 1, 'fail': 0}`
  - confirmed `GET /frontend/ManualTesting.html` returned `200`
  - confirmed the page source now includes:
    - `saveButton`
    - `status-select`

Verification hygiene note:
- the runtime save test restored the original `manual_testing_coverage.json` content immediately after verification

## Prompt 6 - Completed

### Goal

Create sample JSON coverage and one ready-to-use example dataset.

### Instructions

Build the wide-screen HTML shell and scrollable table area.

Requirements:
- create a realistic `manual_testing_coverage.json` example for this feature family
- align the example with the manual testing structure already used in task MD files
- keep the sample high-signal and reusable as a future reference

### Required Outcome

The dashboard can be opened against a realistic example dataset immediately.

### Completion Note

Prompt 6 is completed.

Sample coverage dataset added:
- updated:
  - `clinic-ai-assistant docs/ProjectTasks_Pending/TEST - Manual Verification Coverage Dashboard/manual_testing_coverage.json`

What the dataset now contains:
- 3 realistic manual verification categories
- 3 named tests
- 9 row-level manual verification steps
- row fields aligned with the locked schema:
  - `step`
  - `action`
  - `what_is_tested`
  - `status`
  - `comment`
  - `reference_files`
- a ready-to-use `reference_files` example with plain typed filenames

Why this sample was chosen:
- it lets the dashboard render meaningful grouped rows immediately
- it exercises:
  - task discovery
  - JSON-backed table rendering
  - save/edit flow
  - readiness summary behavior
- it stays aligned with the manual testing structure already used in task markdown files

Verification completed for Prompt 6:
- focused runtime verification:
  - loaded `GET /manual-verification/tasks/test-manual-verification-coverage-dashboard`
  - confirmed:
    - task name loaded correctly
    - `3` categories were returned
    - summary returned as:
      - `{'not_run': 9, 'pass': 0, 'fail': 0}`

## Prompt 7 - Completed

### Goal

Add focused regression coverage and final technical verification for the dashboard feature.

### Instructions

Render the loaded task data into the table UI.

Requirements:
- cover task discovery
- cover JSON load/save behavior
- cover merge-readiness summary logic
- cover at least one rendered task-switching scenario
- follow repo-clean temp-path rules

### Required Outcome

The dashboard feature is regression-protected and technically verified.

### Completion Note

Prompt 7 is completed.

Added focused regression coverage in:
- `clinic-ai-assistant-src/backend/tests/integration/test_manual_verification_dashboard.py`

Covered behaviors:
- task discovery for:
  - folder-based tasks with editable JSON
  - legacy flat tasks surfaced as migration-needed
- coverage loading for a folder-based task
- save behavior with persisted comment and `reference_files`
- summary recomputation from row statuses on save
- invalid status rejection
- dashboard HTML entry-point wiring for:
  - task selector
  - save button
  - task-state summary
  - task-loading script path

Verification completed for Prompt 7:
- static verification:
  - `python -m py_compile clinic-ai-assistant-src/backend/tests/integration/test_manual_verification_dashboard.py clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py clinic-ai-assistant-src/backend/app/routes/manual_verification.py clinic-ai-assistant-src/backend/app/main.py`
- focused pytest verification:
  - `5 passed`
  - executed with the proven external user-temp fallback after the standard `F:\temp` basetemp path hit a Windows permission blocker

## Prompt 8 - Completed

### Goal

Track branch-level manual verification and merge readiness for this dashboard feature.

### Instructions

Add the manual testing interaction workflow.

Requirements:
- record which manual checks were performed
- record whether the branch is approved as merge-ready
- keep `Merge To Main` as `Pending` until merge is actually completed

### Required Outcome

Manual verification and merge readiness are tracked explicitly before merge.

### Completion Note

Prompt 8 is completed.

Manual verification for the dashboard branch is now confirmed complete.

Recorded branch state:
- main dashboard feature implemented
- follow-up `FIX 01` completed and manually approved
- dashboard workflow is now in active use for manual retest tracking

Merge state remains:
- `Merge To Main = Pending`

The task is now ready for merge discussion and branch review.


---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is for archive, handoff, and manual-verification guidance only.

Execution rule for future implementing agents:
- do not treat this appendix as additional implementation scope
- do not create extra prompts from this appendix unless the user explicitly asks for that
- use it only to understand expected runtime behavior and manual verification outcomes

## Use Case

The reviewer opens one HTML page and switches between pending tasks that are waiting for final manual verification.

| Step | Event | Expected Result |
|---|---|---|
| 1 | Reviewer opens `ManualTesting.html` | Task selector loads pending tasks awaiting manual verification |
| 2 | Reviewer chooses a task | JSON-driven test rows appear |
| 3 | Reviewer marks rows `Pass` / `Fail` | Progress is tracked per row |
| 4 | Reviewer writes comments and reference filenames | Notes are captured inline and filenames point to files in the same task folder |
| 5 | Reviewer saves | JSON is updated |
| 6 | All tests are completed acceptably | Merge readiness can be discussed |

## Simple Flow Chart

```text
Open ManualTesting.html
   |
   v
Discover pending tasks
   |
   v
Select task
   |
   v
Load manual_testing_coverage.json
   |
   v
Render rows
   |
   v
Mark Pass / Fail + comments + references
   |
   v
Save JSON
   |
   v
Review merge readiness summary
```

## Manual Testing

### Category 1 - Task Discovery

#### Test 1.1 - Pending task appears in selector

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the HTML page | The page loads successfully |
| 2 | Inspect the task selector | Pending tasks waiting for manual verification are listed |

### Category 2 - JSON Load And Save

#### Test 2.1 - Edit and save a row

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open a task from the selector | Task rows load from JSON |
| 2 | Change one row status and add a comment | The row becomes dirty/modified |
| 3 | Add one or more reference filenames in the separate reference field | Filenames are stored as plain text for that row |
| 4 | Save | The updated values persist after reload |
