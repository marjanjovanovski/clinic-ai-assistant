# Chat SandBox Runtime Flow Control Panel FIX Master Prompt

This document tracks the follow-up fix pass for the Chat SandBox runtime inspector after manual review on the feature branch.

The purpose of this work is to:
- switch the sandbox to `milena_dental` defaults for manual testing
- make the inspector visible by default
- bring the chat presentation closer to the production `index.html` surface
- correct inspector field rendering and readability issues
- add inner scrolling inside inspector groups that contain larger content

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

- `Completed`

## Current Active Prompt

- `Merged To Main`

## Global Status Summary

- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Completed
- Prompt 4 - Completed
- Prompt 5 - Completed

## Working Rules For The Implementing AI Agent

- Inspect the existing repo logic before changing code.
- Keep `index.html` production-oriented; do not add the debug panel there.
- Apply the smallest prompt needed for the next manual-review checkpoint.
- Preserve the completed runtime-inspector contracts unless a fix requires a narrow correction.
- Use the manual-review screenshots and notes as the source of truth for the fix priorities.
- Avoid temporary repo artifacts and keep verification focused.

## Desired Outcome

After all prompts are complete, the repo should have:
- `ChatSandBox.html` defaulting to `milena_dental` for immediate manual review
- the inspector visible by default
- a main chat area that more closely mimics `index.html`
- readable inspector groups and form-field layout
- inner scrolling for large inspector-group content where needed
- focused verification for the fix pass

## Prompt 1 - Completed

### Goal

Switch the Chat SandBox default tenant/config fallback from `generic` to `milena_dental` so manual review can continue against the intended clinic profile immediately.

### Instructions

Update the sandbox page so the fallback tenant and any matching initial labels/defaults use `milena_dental` instead of `generic`.

Requirements:
- keep tenant resolution by path intact when a tenant is explicitly present in the route
- change only the fallback/default behavior for this prompt
- do not mix in the layout/readability fixes yet

### Required Outcome

The Chat SandBox page defaults to `milena_dental` when the route does not provide a tenant.

### Prompt 1 Completion Note

What changed:

- changed the fallback tenant resolution in `ChatSandBox.html` from `generic` to `milena_dental`
- updated the initial tenant chip text to match the new default so the page reflects the intended clinic profile immediately during manual review

Why this prompt stops here:

- this prompt was intentionally limited to the immediate testing unblock requested during manual review
- inspector-visibility and layout corrections remain for later prompts in this fix track

## Prompt 2 - Completed

### Goal

Make the inspector visible by default for manual review on desktop and mobile.

### Instructions

Adjust the page bootstrap so the inspector starts open by default while keeping the toggle available.

### Required Outcome

The inspector is visible on initial load without user interaction.

### Prompt 2 Completion Note

What changed:

- changed the Chat SandBox bootstrap so the inspector opens by default on load
- kept the existing inspector toggle behavior intact so the panel can still be hidden during testing if needed

Why this prompt stops here:

- this prompt was limited to the default-visibility fix only
- the production-mimic and inspector-layout corrections remain for the next prompts

## Prompt 3 - Completed

### Goal

Bring the main chat presentation closer to the production `index.html` layout and behavior.

### Instructions

Compare `ChatSandBox.html` against `index.html` and align the main chat shell styling, spacing, and presentation more closely while preserving the sandbox inspector.

### Required Outcome

The sandbox chat column more closely mimics the production chat experience.

### Prompt 3 Completion Note

What changed:

- adjusted the sandbox shell and chat column so the main chat sits as a centered production-style card, closer to `index.html`
- changed the page background, card sizing, border radius, border treatment, and shadow so the main chat reads more like the production surface instead of a separate dashboard layout
- aligned the toolbar styling with the simpler production card treatment while keeping the sandbox controls available above the chat

Why this prompt stops here:

- this prompt was limited to making the main chat presentation more production-like
- inspector field readability and inner scrolling remain scoped to Prompt 4

## Prompt 4 - Completed

### Goal

Fix inspector field rendering/readability problems and add inner scrolling inside inspector groups where needed.

### Instructions

Correct the layout issues shown during manual review, especially label/input crowding, cramped group presentation, and large-content overflow.

Requirements:
- keep each group readable
- add inner scrolling for larger content areas instead of letting long content break layout
- preserve the grouped runtime/debugging structure

### Required Outcome

Inspector groups render clearly and handle larger content with inner scrolls.

### Prompt 4 Completion Note

What changed:

- simplified the inspector field layout to a single-column readable stack so labels and values no longer compete for narrow horizontal space
- widened the inspector panel and improved field-label wrapping so long runtime keys render cleanly instead of clipping
- increased textarea readability for larger payload/config content
- added inner scroll regions to the larger inspector groups so content-heavy sections can scroll internally without breaking the overall page layout

Why this prompt stops here:

- this prompt was focused on the inspector readability and overflow problems from manual review
- final verification for the fix track remains in Prompt 5

## Prompt 5 - Completed

### Goal

Verify the follow-up fixes and confirm the sandbox is ready for renewed manual testing.

### Instructions

Run focused verification for the new fallback tenant behavior and any UI/layout corrections made in this fix pass.

### Required Outcome

The follow-up fix pass is verified and documented.

### Prompt 5 Completion Note

What changed:

- added focused frontend integration assertions for the fix-pass behavior in `test_frontend_booking_ui.py`
- verified the new sandbox default tenant, default-open inspector, and inspector readability/scrolling hooks through the served `ChatSandBox.html` asset

Verification completed:

- automated test run:
  - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_frontend_booking_ui.py -q --basetemp="F:\\temp\\clinic-ai-assistant\\pytest-chat-sandbox-fix-2"`
- result:
  - `10 passed`

Manual verification notes:

- the branch is ready for another manual review pass focused on the visual/layout corrections
- merge to `main` should still wait until manual review is accepted
