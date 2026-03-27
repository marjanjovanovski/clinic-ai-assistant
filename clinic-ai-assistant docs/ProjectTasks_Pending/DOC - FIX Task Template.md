# FIX Task Template Master Prompt

This document is the reusable template for creating execution-ready `FIX` task files.

The purpose of this template is to:
- keep fix work small, targeted, and fast to execute
- reduce wasted context and token usage
- preserve high verification quality
- separate understanding, implementation, regression protection, and manual verification into clean checkpoints
- make fix tasks easy to resume across sessions

## Execution Tracking Instructions

Before executing any prompt in a fix task file, the implementing AI agent must first read the file and understand the current status.

Execution of the fix must follow [Feature_Implementation_Guide.md](./Feature_Implementation_Guide.md).
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

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending

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

## Prompt 1 - Pending

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

## Prompt 2 - Pending

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

## Prompt 3 - Pending

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

## Prompt 4 - Pending

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

## Prompt 5 - Pending

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
