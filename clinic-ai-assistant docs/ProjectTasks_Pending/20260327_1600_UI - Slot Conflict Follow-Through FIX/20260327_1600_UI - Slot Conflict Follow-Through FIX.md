# Slot Conflict Follow-Through FIX Master Prompt

This document defines the execution-ready fix plan for the main chat behavior where the system reports a slot conflict but does not follow through by sending a new reply with fresh replacement slots.

The purpose of this fix is to:
- preserve the correct conflict message already being shown
- ensure the user receives a new backend-driven reply with the most recent available replacement slots
- avoid relying on the previously used widget as if it were still current
- disable interaction with the previous widget once the fresh recovery widget is sent
- keep the recovery flow consistent with the overlap-handling contract already implemented
- protect the corrected behavior with focused regression coverage

## Execution Tracking Instructions

Before executing any prompt in this document, the implementing AI agent must first read this file and understand the current status.

Execution of this fix must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).
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

## Working Rules For The Implementing AI Agent

- Treat this as a narrow `FIX` task, not a broad overlap-flow redesign.
- Preserve the existing overlap contract and user-facing conflict wording unless a clearer fix-specific improvement is required.
- The corrected behavior must send a new response with current replacement slots instead of relying on the previous slot widget.
- Once the new recovery reply is shown, the previously shown slot widget must become non-interactive.
- Keep the main chat authoritative to backend state and current replacement-slot payloads.
- Reuse the existing overlap-handling and widget-rendering paths where possible.
- Update this file immediately after each prompt is completed.
- Do not mark a prompt as completed unless the requested work was actually implemented and verified as far as possible.

## Testing And Verification Rules

- Follow the repo rule to keep test artifacts out of the repository.
- When running pytest, use external `TMP` / `TEMP` and an external `--basetemp`.
- For this Windows environment, if sandbox or `F:\temp` pytest execution hits temp or SQLite permission failures, switch promptly to the proven external-user-temp fallback pattern instead of retrying many temp variants.
- Add or update focused coverage for the exact broken recovery path.
- Do not leave repo-local temp artifacts.
- Final verification must include a repo residual check.

## Do Not Break

- normal successful slot selection flow
- normal contact collection after a valid slot selection
- existing overlap conflict messages
- `ChatSandBox.html` parity with the main chat shell if they share the same interaction path
- `cal.html` sandbox behavior, which is a separate surface
- booking summary behavior outside the intentional follow-through correction

## Current Repo Truth

- The overlap-handling work already returns conflict metadata and replacement slots from backend-owned code.
- The main chat already knows how to render slot-list widgets from backend responses.
- The user-reported broken behavior is narrower:
  - the system informs the user that the originally selected slot was taken
  - but it does not follow through by sending a new reply carrying the most recent replacement slots
- the user can still interact with the previously shown widget instead of being guided by a fresh reply
- The intended fix is to send a new response with current replacement slots, not to treat the old widget as the recovery surface.
- The old widget should be disabled once the new recovery reply is present, similar to the current behavior where selecting one slot disables the remaining buttons in that same widget.

## Architecture Guidance

### Expected Correct Behavior

- User selects slot A from a slot-list widget.
- Backend detects that slot A is no longer available.
- Chat returns a new reply message explaining the conflict.
- That same new reply also carries a fresh replacement slot-list widget for the same day when available.
- The old widget should no longer be treated as the active recovery source for the next step.
- The old widget should also become non-clickable once the new recovery widget is shown.
- User selects from the new replacement reply and continues the flow safely.

### Broken Behavior Observed

- User selected `27 Mar 2026 14:00`.
- System replied:
  - `Неуспешен избор на термин. This slot was just taken by another booking. I will show available slots for the same day.`
- But no fresh reply with updated replacement slots followed.
- The user then selected `27 Mar 2026 14:30` from the previous widget instead of from a newly returned recovery reply.
- The flow then continued to contact collection, which suggests the recovery follow-through is incomplete or the wrong widget remains active.
- The fix should prevent further clicks on the previous widget once a new recovery widget has been returned.

### Likely Fix Boundary

- main chat backend-to-frontend recovery path after selection-time or booking-time conflict
- active widget / reply lifecycle in `index.html` and matching `ChatSandBox.html` path if shared
- backend response shape or orchestration only if the current reply does not already carry the correct recovery widget payload at the needed step

## Prompt 1 - Pending

### Goal

Trace the exact broken recovery path and confirm whether the missing follow-through is backend, frontend, or active-widget lifecycle behavior.

### Instructions

Inspect the current conflict path end to end before changing code.

Requirements:
- identify where the conflict message is produced
- identify whether a fresh replacement widget payload is already present but not rendered, or missing entirely
- identify why the previously shown widget remains usable as the active selection source
- identify where the previous widget should be disabled once the new recovery reply is rendered
- confirm whether the same fix must apply to `ChatSandBox.html`

### Required Outcome

The exact fix boundary is known before implementation starts.

## Prompt 2 - Pending

### Goal

Implement the smallest reliable fix so the user receives a new reply with current replacement slots after the conflict.

### Instructions

Apply the narrowest change that closes the follow-through gap.

Requirements:
- ensure conflict handling produces a new recovery reply with current replacement slots
- ensure the recovery path does not depend on the previously shown widget as if it were current
- ensure the previous widget becomes disabled once the new recovery reply is rendered
- preserve valid non-conflict selection flow
- keep the change aligned with existing overlap architecture

### Required Outcome

The chat recovery path follows through correctly with a fresh reply and replacement slots.

## Prompt 3 - Pending

### Goal

Add or update focused regression coverage for the corrected follow-through behavior.

### Instructions

Protect the fixed path with high-signal regression coverage.

Requirements:
- cover the exact broken scenario
- assert that a fresh recovery reply is returned
- assert that replacement slots come from the new reply path
- assert that the previous widget becomes non-interactive after the new recovery reply appears
- include `ChatSandBox.html` parity coverage if the same interaction path applies

### Required Outcome

The follow-through bug is protected against silent regression.

## Prompt 4 - Pending

### Goal

Perform final technical verification and document the fix outcome.

### Instructions

Run the most relevant verification for the fix.

Requirements:
- use repo-clean temp-path rules
- document what was verified automatically and manually
- confirm no repo-local test residue remains
- document blockers honestly if environment limits interfere

### Required Outcome

The fix is technically verified and documented clearly.

## Prompt 5 - Pending

### Goal

Track branch-level manual verification and merge readiness before this fix can move out of `ProjectTasks_Pending`.

### Instructions

After implementation and automated verification are complete, wait for user-driven manual verification on the branch.

Requirements:
- keep this prompt `Pending` until the user confirms manual verification is complete
- record which manual verification scenarios were performed
- record whether the branch is approved as merge-ready
- keep `Merge To Main` as `Pending` until this prompt is completed and the branch is actually merged

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

The user should never be left on an outdated slot widget after a conflict is already known.

Correct business logic:

| Step | Event | Expected Result |
|---|---|---|
| 1 | User selects a slot from the current list | Backend validates that selection |
| 2 | Slot is already taken | Backend returns conflict message plus fresh same-day replacements |
| 3 | Chat renders a new recovery reply | User sees updated current choices and the previous widget is disabled |
| 4 | User selects from the new reply | Flow continues normally |

## Scenarios

### Scenario A - Immediate conflict on selection

- User clicks a slot that was just taken.
- System sends a new conflict reply.
- That new reply includes current replacement slots.
- The previous widget becomes disabled and cannot be clicked again.
- The user continues from the new reply, not the old widget.

### Scenario B - Normal non-conflict selection

- User clicks a valid slot.
- Contact collection starts normally.
- No extra recovery reply is added.

## Simple Flow Chart

```text
User selects slot
   |
   v
Backend validates slot
   |
   +-- Available --> Continue normal flow
   |
   +-- Taken --> Return new conflict reply
                    |
                    v
          Include fresh replacement slots
                    |
                    v
        User selects from new recovery reply
```

## Manual Testing

Execution-state tracking for this fix should live in `manual_testing_coverage.json`.

Keep markdown as the compact overview only:

- Category 1 - Main Chat Recovery Follow-Through
  - Test 1.1 - Fresh recovery reply appears after conflict
    - Purpose: confirm the chat sends a new reply with current replacement slots instead of leaving the user on the old widget
  - Test 1.2 - Previous widget becomes non-interactive
    - Purpose: confirm the outdated widget can no longer be used after the fresh recovery reply appears
- Category 2 - Surface Parity
  - Test 2.1 - `ChatSandBox.html` parity
    - Purpose: confirm the same follow-through fix is present if the sandbox shares the same interaction path
