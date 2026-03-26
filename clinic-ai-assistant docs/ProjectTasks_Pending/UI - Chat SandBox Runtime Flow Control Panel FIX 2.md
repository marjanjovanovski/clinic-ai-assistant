# Chat SandBox Runtime Flow Control Panel FIX 2 Master Prompt

This document tracks the second follow-up fix pass for the Chat SandBox runtime inspector after continued manual review on the feature branch.

The purpose of this work is to:
- split the inspector into left and right outer panels around the chat sandbox
- group categories by flow order so earlier runtime/debugging concerns appear on the left and later concerns appear on the right
- reduce unusable vertical compression caused by stacking every inspector group in one narrow side column

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

## Last Updated By

- `Kai - Codex`

## Last Updated On

- `2026-03-26`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Manual Verification / Merge`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Keep `index.html` production-oriented; do not add the debug panel there.
- Preserve the completed runtime contracts and previous fix-pass improvements unless the new layout requires a narrow structural adjustment.
- Use the latest manual-review screenshots as the source of truth for the panel-placement problem.
- Prefer one focused prompt per layout concern.

## Desired Outcome

After all prompts are complete, the repo should have:
- left and right outer inspector panels flanking the chat sandbox on desktop
- runtime groups ordered by flow importance and execution sequence from left to right
- improved usable space without stacked per-card compression
- focused verification for the new left/right layout

## Prompt 1 - Completed

### Goal

Split the inspector into left and right outer panels around the chat sandbox and place the runtime groups in flow order.

### Instructions

Refactor the desktop Chat SandBox layout so the inspector no longer appears as one stacked panel on a single side.

Requirements:
- place early-flow/runtime groups on the left side
- place later-flow/runtime groups on the right side
- keep the chat sandbox centered between the two outer panels
- keep the inspector toggle behavior intact
- preserve mobile fallback behavior

### Required Outcome

The desktop sandbox layout uses left and right outer inspector panels ordered by runtime flow.

### Prompt 1 Completion Note

What changed:

- split the inspector into left and right outer columns around the centered chat sandbox
- moved the earlier runtime groups to the left side:
  - `Session And Routing`
  - `Booking Flow`
  - `Scheduling Criteria`
- kept the later/runtime-result groups on the right side:
  - `Selected Slot And Booking Result`
  - `Widget And Payload Snapshot`
  - `Config Preview`
- removed the per-card inner-scroll treatment for the desktop split so the new two-sided layout gains usable vertical space instead of stacking multiple tiny scroll regions

Why this prompt stops here:

- this prompt was focused on the new left/right panel placement and category ordering
- focused verification for the split layout remains in Prompt 2

## Prompt 2 - Completed

### Goal

Verify the left/right inspector split and confirm the page remains usable.

### Instructions

Add or update focused verification for the new layout split and panel-group placement.

### Required Outcome

The left/right layout split is verified and documented.

### Prompt 2 Completion Note

What changed:

- updated the focused frontend integration assertions to verify the new left/right inspector split
- verified the presence of the left and right inspector columns and the new desktop three-column layout rules in the served `ChatSandBox.html`

Verification completed:

- automated test run:
  - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_frontend_booking_ui.py -q --basetemp="F:\\temp\\clinic-ai-assistant\\pytest-chat-sandbox-fix-2"`
- result:
  - `10 passed`

Manual verification notes:

- the branch is ready for another manual review pass focused on the new left/right panel arrangement
- merge to `main` should still wait until manual review is accepted
