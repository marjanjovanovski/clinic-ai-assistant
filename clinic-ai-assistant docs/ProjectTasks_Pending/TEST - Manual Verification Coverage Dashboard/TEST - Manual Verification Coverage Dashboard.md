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

## Prompt 1 - Pending

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

## Prompt 2 - Pending

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

## Prompt 3 - Pending

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

## Prompt 4 - Pending

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

## Prompt 5 - Pending

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

## Prompt 6 - Pending

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

## Prompt 7 - Pending

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

## Prompt 8 - Pending

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
