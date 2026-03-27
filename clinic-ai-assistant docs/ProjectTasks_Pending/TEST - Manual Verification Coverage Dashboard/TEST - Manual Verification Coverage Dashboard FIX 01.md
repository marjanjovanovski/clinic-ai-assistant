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

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending

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

## Prompt 1 - Pending

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

## Prompt 2 - Pending

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

## Prompt 3 - Pending

### Goal

Tighten task discovery and fix-artifact handling rules.

### Instructions

- limit selector discovery to folder-based JSON-backed items
- stop surfacing legacy flat markdown task leftovers in the selector
- support fix-task artifacts within the same parent task folder at the contract level
- update the guide if implementation details need one small clarification

### Required Outcome

The selector shows only valid JSON-backed folder items and the fix-artifact convention is explicit.

## Prompt 4 - Pending

### Goal

Add focused regression coverage and technical verification for the fix behavior.

### Instructions

- cover folder-only discovery
- cover status-filter behavior
- cover the presence of widened/editable review fields and colored status controls at the page-contract level
- cover any new fix-artifact discovery rule introduced in this fix

### Required Outcome

The fix is technically verified and regression-protected.

## Prompt 5 - Pending

### Goal

Track manual retesting and merge readiness for this fix round.

### Instructions

- keep this fix task pending until manual retesting is completed
- use `manual_testing_coverage_FIX01.json` as the retest artifact
- keep `Merge To Main` as `Pending` until manual retesting confirms the fix

### Required Outcome

The fix is ready for manual retesting without losing separation from the original dashboard task.

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
