# FIX Task Template Master Prompt

This document is the reusable template for creating execution-ready `FIX` task files.

The purpose of this template is to:
- keep fix work small, targeted, and fast to execute
- reduce wasted context and token usage
- preserve high verification quality
- separate understanding, implementation, regression protection, and manual verification into clean checkpoints
- make fix tasks easy to resume across sessions

Naming rule for new fix tasks:
- prefix the folder name and the main markdown filename with the creation timestamp in `YYYYMMDD_HHmm_` format
- example: `20260329_1542_UI - Slot Conflict Follow-Through FIX`

## Execution Tracking Instructions

Before executing any prompt in a fix task file, the implementing AI agent must first read the file and understand the current status.

Execution of the fix must follow [Task_Workflow_Guide.md](./Task_Workflow_Guide.md) and [Core_Rules.md](./Core_Rules.md).
After each completed prompt, stop, update prompt status in the file, and ask `Commit changes?`
Do not auto-advance to the next prompt.

As soon as a prompt is executed, the file must be updated in two places:
- at the very top of the document in the global status summary
- in the corresponding prompt section header

Status values allowed in fix task files:
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

- Prompt 1 - Preparation - Pending
- Prompt 2 - Targeted Fix - Pending
- Prompt 3 - Regression Coverage - Pending
- Prompt 4 - Technical Verification - Pending
- Prompt 5 - Manual Testing - Pending
- Prompt 6 - Merge To Main - Pending

## Working Rules For The Implementing AI Agent

- Treat a fix as a narrow correction, not a stealth refactor.
- Preserve existing behavior outside the specific broken path.
- Prefer the smallest reliable implementation that fully closes the bug.
- Split prompts by engineering boundary so each prompt has a clear verification target.
- Reuse existing tests, helpers, and widgets before inventing parallel logic.
- Update the file immediately after each completed prompt.
- Do not mark a prompt completed unless the requested work was actually implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to keep test artifacts out of the repository.
- When running pytest, use external `TMP` / `TEMP` and an external `--basetemp`.
- Add or update focused coverage for the exact broken path and its nearest regression boundary.
- Prefer one focused verification run over many near-identical retries.
- If environment limits block clean automated execution, document the blocker clearly.
- Final verification must include a repo residual check.

## Recommended FIX Structure

Use this prompt order unless the fix is truly trivial:

## Prompt 1 - Preparation - Pending

### Goal

Confirm the exact broken behavior, current boundary, and smallest safe fix surface.

### Instructions

Inspect the current code path before changing anything.

Requirements:
- identify the exact broken user-visible behavior
- identify the current backend and frontend boundary involved
- identify the smallest safe fix surface
- identify the nearest regression risk

### Required Outcome

The bug is precisely located and the implementation boundary is clear before code changes begin.

## Prompt 2 - Targeted Fix - Pending

### Goal

Implement the targeted fix in the minimum required code surface.

### Instructions

Apply the smallest reliable code change that fully closes the bug.

Requirements:
- fix the broken path
- preserve surrounding behavior
- avoid unrelated cleanup unless strictly required
- keep the change aligned with existing architecture

### Required Outcome

The broken behavior is corrected without broadening scope unnecessarily.

## Prompt 3 - Regression Coverage - Pending

### Goal

Add or update focused regression protection for the fix.

### Instructions

Protect the corrected path with the smallest high-signal test coverage needed.

Requirements:
- cover the exact failure mode
- cover the intended corrected result
- include adjacent safety coverage only where it prevents obvious regression

### Required Outcome

The bug is protected against silent regression.

## Prompt 4 - Technical Verification - Pending

### Goal

Perform final technical verification and document the result.

### Instructions

Run the most relevant focused verification for the fix.

Requirements:
- use repo-clean temp-path rules
- document what passed
- document blockers honestly if environment limits interfere
- confirm no repo-local temp residue remains

### Required Outcome

The fix is technically verified and documented clearly.

## Prompt 5 - Manual Testing - Pending

### Goal

Track branch-level manual verification and merge readiness.

### Instructions

Keep this prompt pending until the user confirms manual verification is complete.

Requirements:
- record which manual checks were performed
- record whether the branch is approved for merge
- keep `Merge To Main` pending until merge is actually completed

### Required Outcome

Manual verification and merge readiness are tracked explicitly before merge.

## Prompt 6 - Merge To Main - Pending

### Goal

Keep the task visible and tracked until the branch is actually merged.

### Instructions

This prompt stays pending after manual verification is complete and only closes once the merge has actually happened.

Requirements:
- keep this prompt `Pending` while the branch is approved but not yet merged
- mark `Merge To Main` as `Completed` only after merge is confirmed
- archive or move the task out of `ProjectTasks_Pending` only after merge is completed

### Required Outcome

The task cannot silently disappear into a pending-but-unmerged state.

---

## Archival Appendix - Do Not Extend Into More Prompts

This appendix is for archive and authoring guidance only.

### Use Case

Use this template when:
- a user-visible behavior is broken
- the expected behavior is already known or tightly bounded
- the task should optimize for fast, focused, low-token execution

### Manual Testing

Recommended format:

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reproduce the current broken path | The issue appears consistently enough to validate the fix |
| 2 | Execute the fixed path | The corrected behavior appears |
| 3 | Check one adjacent non-broken path | Existing surrounding behavior still works |
