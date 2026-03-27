# Manual Verification Coverage Dashboard FIX 01

This document defines the execution-ready follow-up fix plan for the first round of manual-testing feedback collected through the dashboard itself.

This fix exists to:
- compact the dashboard layout so the page wastes less vertical space
- improve table usability for comments and reference-file entry
- make status values easier to scan visually
- tighten task discovery so only folder-based JSON-backed items are shown
- prepare the dashboard workflow for follow-up fix artifacts generated from manual testing

Execution of this fix must follow [../Feature_Implementation_Guide.md](../Feature_Implementation_Guide.md).

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-27`

## Merge To Main

- `Pending`

## Current Active Prompt

- `None - Ready for review`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed
- Prompt 5 - Completed

## Working Rules For The Implementing AI Agent

- Keep this fix small and directly mapped to the saved manual-testing feedback.
- Prefer UI compaction and clarity over decorative structure.
- Reuse the existing dashboard routes and JSON service instead of redesigning storage.
- Do not re-open the original dashboard feature scope unless needed by the saved feedback.
- Keep completion notes short:
  - what changed
  - what was verified
  - blockers or warnings

## Testing And Verification Rules

- Use external `TMP` / `TEMP` and external `--basetemp` for pytest.
- Do not leave repo-local temp artifacts.
- Final verification must include a repo residual check.

## Current Repo Truth

- `ManualTesting.html` is implemented and working.
- Manual testing feedback has been saved into `manual_testing_coverage.json`.
- The current selector still surfaces legacy flat tasks, which the feedback rejects.
- The current page still spends too much space on header/hero chrome and does not yet include a status filter.
- The current table keeps `Comment` and `Reference Files` narrower than desired for active use.

## Fix Scope

The fix must address these exact feedback items:
- reduce top header overhead:
  - remove `Read-Only Review`
  - simplify the top container
  - reduce overall page height so the main page does not need to scroll
- widen `Comment` and `Reference Files`
- use the full dashboard width more effectively
- color the `Status` control by selected value
- add top-level filtering by status
- tighten selector discovery to folder-based JSON-backed items only
- introduce the repo rule for dashboard-driven fix follow-up files:
  - fix MD in the same task folder
  - companion `manual_testing_coverage_FIX01.json`
- prepare the dashboard to later list original task items and fix follow-up items separately

## Prompt 1 - Completed

### Goal

Trace the saved dashboard feedback into an exact implementation boundary.

### Instructions

- read the saved comments from `manual_testing_coverage.json`
- map each comment to:
  - UI compaction
  - table usability
  - selector discovery
  - fix-artifact workflow
- identify the smallest safe implementation set for this fix

### Required Outcome

The fix boundary is explicit and no extra redesign work is introduced.

### Completion Note

Prompt 1 is completed.

Saved feedback mapped into this exact implementation boundary:
- UI compaction:
  - remove the hero-style overhead and `Read-Only Review`
  - collapse the top shell into a simpler single header/toolbar surface
  - reduce page-height overhead so the table owns the main scrolling
- table usability:
  - widen `Comment` and `Reference Files`
  - use more of the available desktop width
  - color the `Status` control by selected value
  - add a top status filter
- selector discovery:
  - stop listing legacy flat markdown leftovers
  - list only folder-based items that have applicable JSON coverage files
- fix-artifact workflow:
  - the guide now supports same-folder fix follow-ups
  - this fix uses:
    - `TEST - Manual Verification Coverage Dashboard FIX 01.md`
    - `manual_testing_coverage_FIX01.json`

Boundary decision for this fix:
- keep all backend persistence and route behavior as-is unless selector filtering requires a small service adjustment
- keep the fix focused on dashboard usability and valid-task discovery only
- do not redesign merge logic, uploads, previews, or broader task lifecycle behavior in this round

## Prompt 2 - Completed

### Goal

Implement the dashboard UI compaction and table-usability improvements.

### Instructions

- simplify the top layout
- remove unnecessary hero overhead
- reduce main-page scrolling
- widen `Comment` and `Reference Files`
- improve use of horizontal space
- color the `Status` control by selected value
- add a top-level status filter

### Required Outcome

The dashboard is easier to read and use during manual testing on wide screens.

### Completion Note

Prompt 2 is completed.

Implemented dashboard usability updates in:
- `clinic-ai-assistant-src/frontend/ManualTesting.html`

What changed:
- compacted the top shell into one smaller header container
- removed the `Read-Only Review` badge and large hero-style overhead
- expanded the dashboard to use more of the available desktop width
- reduced outer page scrolling so the table is the main scroll surface
- widened `Comment` and `Reference Files`
- added a top `Status Filter`
- colored the `Status` control by selected value:
  - `Pass`
  - `Fail`
  - `Not Run`

Verification completed for Prompt 2:
- lightweight runtime verification through `TestClient`
- confirmed the served page includes:
  - `statusFilter`
  - status-color classes
  - compact width/height layout rules
  - filtered-row empty-state handling

## Prompt 3 - Completed

### Goal

Tighten task discovery and fix-artifact handling rules.

### Instructions

- limit selector discovery to folder-based JSON-backed items
- stop surfacing legacy flat markdown task leftovers in the selector
- support fix-task artifacts within the same parent task folder at the contract level
- update the guide if implementation details need one small clarification

### Required Outcome

The selector shows only valid JSON-backed folder items and the fix-artifact convention is explicit.

### Completion Note

Prompt 3 is completed.

Implemented discovery-contract tightening in:
- `clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py`

What changed:
- dashboard discovery now scans only folder-based task entries
- loose legacy flat markdown files in `ProjectTasks_Pending` are no longer surfaced in the selector
- folder items require applicable JSON coverage to appear
- same-folder fix follow-ups now appear as separate selectable entries when they follow the fix naming contract:
  - `<Task Folder Name> FIX 01.md`
  - `manual_testing_coverage_FIX01.json`

Verification completed for Prompt 3:
- static verification:
  - `python -m py_compile clinic-ai-assistant-src/backend/app/services/manual_verification_dashboard.py clinic-ai-assistant-src/backend/tests/integration/test_manual_verification_dashboard.py`
- focused runtime verification:
  - `/manual-verification/tasks` now returns:
    - the primary dashboard task entry
    - the `FIX 01` follow-up entry
  - legacy flat pending task leftovers are no longer returned

## Prompt 4 - Completed

### Goal

Add focused regression coverage and technical verification for the fix behavior.

### Instructions

- cover folder-only discovery
- cover status-filter behavior
- cover the presence of widened/editable review fields and colored status controls at the page-contract level
- cover any new fix-artifact discovery rule introduced in this fix

### Required Outcome

The fix is technically verified and regression-protected.

### Completion Note

Prompt 4 is completed.

Added focused regression coverage in:
- `clinic-ai-assistant-src/backend/tests/integration/test_manual_verification_dashboard.py`

Covered fix behaviors:
- folder-only discovery
- separate fix-entry discovery inside the same task folder
- status-filter contract at the page level
- compact layout contract
- widened review-field contract
- colored status-control contract

Verification completed for Prompt 4:
- focused pytest suite:
  - `6 passed`
- executed with the proven external user-temp fallback
- repo-local temp residue:
  - none created by this prompt

## Prompt 5 - Completed

### Goal

Track manual retesting and merge readiness for this fix round.

### Instructions

- keep this fix task pending until manual retesting is completed
- use `manual_testing_coverage_FIX01.json` as the retest artifact
- keep `Merge To Main` as `Pending` until manual retesting confirms the fix

### Required Outcome

The fix is ready for manual retesting without losing separation from the original dashboard task.

### Completion Note

Prompt 5 is completed.

Manual retesting outcome recorded in:
- `clinic-ai-assistant docs/ProjectTasks_Pending/TEST - Manual Verification Coverage Dashboard/manual_testing_coverage_FIX01.json`

Recorded result:
- `not_run: 0`
- `pass: 7`
- `fail: 0`
- `branch_merge_ready: true`
- general feedback saved:
  - `There are no remarks left. This can be shipped onto main.`

Workflow state:
- FIX 01 is manually approved
- `Merge To Main` remains `Pending` until the branch is actually merged
- the fix task is now ready for review / merge discussion

---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is archive and manual-retest guidance only.

## Use Case

The original dashboard worked functionally, but the first manual test round showed that it still needs usability hardening before it becomes an efficient daily review tool.

## Manual Testing

Retest focus for FIX 01:
- header is compact and no longer wastes vertical space
- the main page does not need separate outer scrolling in normal use
- `Comment` and `Reference Files` are easier to type into
- the `Status` control shows visible pass/fail color state
- the top filter can reduce the table to a selected status
- the selector shows only valid folder-based JSON-backed items
