# 20260408_1238_UI - Index Shell Variant Exploration

Create five visual variants of `frontend/index.html` that explore different shell-only directions for color, borders, edge treatment, and overall visual identity without touching widgets yet, while incorporating `frontend/images/Cheiz_Simbol_01_4_ZaPrint.png` in different ways across the variants.

Execution must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Merge To Main

- `Pending`

## Prompt Status Summary

- Prompt 1 - Shell Scope And Variant Plan - Completed
- Prompt 2 - Implement Five Index Shell Variants - Completed
- Prompt 3 - Lightweight Review And Selection Notes - Pending
- Prompt 4 - Merge To Main - Pending

## Current Active Prompt

- `Prompt 3`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-04-08`

## Purpose

- explore five shell-only visual directions for `index.html`
- compare strong differences in color, border treatment, corner language, and edge sharpness
- incorporate `Cheiz_Simbol_01_4_ZaPrint.png` as part of the shell language in multiple different ways
- keep the task cheap and token-efficient by avoiding widget work and deep frontend refactors

## Working Rules For The Implementing AI Agent

- modify only the shell around `index.html`
- do not touch conversation widgets or widget logic in this task
- variants do not need to be production-polished or fully wired for runtime behavior
- prioritize obvious visual contrast between variants over subtle tweaks
- include at least one variant with hard edges / square corners
- use `frontend/images/Cheiz_Simbol_01_4_ZaPrint.png` in all five variants, but allow the role to vary by concept such as brand stamp, ghosted panel art, title treatment, patterned shell accent, or restrained watermark
- keep implementation lightweight and easy to compare

## Testing And Verification Rules

- prefer minimal technical verification only
- focus on static structure sanity and obvious breakage checks
- do not expand into widget testing for this task

## Do Not Break

- existing widget contracts
- existing scheduling / chat behavior
- backend routes or data structures

## Current Repo Truth

- the current request is limited to `index.html` shell exploration
- widget editing is explicitly out of scope for now
- the output should produce five visual variants rather than one finalized redesign
- `Cheiz_Simbol_01_4_ZaPrint.png` is already present at `frontend/images/Cheiz_Simbol_01_4_ZaPrint.png` and should be incorporated creatively into the shell concepts

## Prompt 1 - Shell Scope And Variant Plan - Completed

### Goal

Inspect the current `index.html` shell and define five intentionally different visual directions before making edits.

### Required Outcome

The variant plan is clear, shell-only, and cheap to execute.

### Shell Read

- the current page shell is a centered single-card layout with inline CSS in `frontend/index.html`
- shell-owned surfaces are `body`, `.chat-app`, `.chat-header`, `.chat-messages`, `.chat-input-area`, `.chat-input`, `.send-button`, and `.status`
- booking widgets mount inside the shell but should remain untouched for this task
- the cheapest execution path is to keep markup changes minimal and express each concept mostly through shell-level classes and CSS variables

### Five Variant Directions

1. `Clinical Light Frame`
   Warm off-white canvas, restrained medical-neutral blue accents, soft card shadow, and the symbol used as a small stamped brand mark near the header title.
2. `Midnight Glass`
   Deep slate shell with translucent panels, luminous edges, cooler cyan highlights, and the symbol used as a large ghosted background watermark behind the header zone.
3. `Terracotta Editorial`
   Paper-and-clay palette, stronger divider rhythm, serif-forward title treatment, and the symbol used inline as a title-side emblem with a more print-like feel.
4. `Signal Grid`
   Hard-edge, no-rounded-corner direction with sharper borders, structured panel segmentation, and the symbol repeated as a subtle technical pattern or corner badge.
5. `Soft Botanical`
   Pale sage and cream direction with lighter borders, gentler depth, and the symbol used as a faint framed panel artwork near the lower shell or status region.

### Prompt 1 Guardrails For Prompt 2

- keep all five variants shell-only and avoid editing widget internals or widget logic
- make the concepts visibly different in palette, border weight, corner treatment, and outer-page atmosphere
- preserve existing element IDs and script behavior so Prompt 2 remains a visual exploration only
- prefer separate compare-ready shell variants over one overly polished final direction

### Completion Note

- `Changed`

## Prompt 2 - Implement Five Index Shell Variants - Completed

### Goal

Create five `index.html` shell variants with clear differences in palette, border language, edge treatment, and overall feel.

### Must Cover

- different color directions across variants
- border-heavy versus lighter treatments
- at least one hard-edge / no-rounded-corner option
- different visual uses of `Cheiz_Simbol_01_4_ZaPrint.png` across the five variants
- shell-only implementation with widgets untouched

### Required Outcome

Five compare-ready shell variants exist in the repo or in clearly separated variant files.

### Implementation Notes

- added five separate compare-ready variant files:
  - `frontend/index.variant-clinical-light-frame.html`
  - `frontend/index.variant-midnight-glass.html`
  - `frontend/index.variant-terracotta-editorial.html`
  - `frontend/index.variant-signal-grid.html`
  - `frontend/index.variant-soft-botanical.html`
- kept widget mounts and IDs aligned with the current page structure so the exploration stays shell-only
- added shared shell styling in `frontend/index-shell-variants.css`
- added shared page behavior in `frontend/index-shell-app.js` so the variants can reuse one lightweight interaction layer without editing widget internals
- used `Cheiz_Simbol_01_4_ZaPrint.png` differently across the concepts as:
  - stamped header brand mark
  - large ghosted shell watermark
  - header-side editorial emblem
  - repeated grid accent plus hard-edge corner badge
  - restrained framed artwork in the lower shell

### Completion Note

- `Changed`

## Prompt 3 - Lightweight Review And Selection Notes - Pending

### Goal

Do a cheap review pass and summarize the distinguishing traits and tradeoffs of each variant.

### Required Outcome

The user can quickly compare the five directions and choose a favorite for deeper refinement later.

## Prompt 4 - Merge To Main - Pending

### Goal

Keep merge tracking explicit and separate from implementation completion.

### Instructions

- mark this prompt completed only after the task work is merged
