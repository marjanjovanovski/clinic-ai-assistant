# PARALLEL_SCAN_TEMPLATE

## 1. Purpose

Define a reusable structure for controlled parallel repository scanning.

## 2. Allowed Use Cases

Parallel scanning may be used only for these read-only analytical tasks:

- repo overview
- validation
- inventory

Parallel scanning must not be used for:

- implementation
- code edits
- refactoring
- broad exploratory scanning without explicit task scope

## 3. Standard Agent Split

The default parallel scan split is:

- Agent A -> backend/
- Agent B -> frontend/
- Agent C -> configs/

Each agent must stay strictly inside its assigned scope.

## 4. Scope Rules

- Parallel scan agents must not cross assigned folder boundaries
- Parallel scan agents must not inspect restricted or forbidden areas unless an explicit task permits it under existing scope rules
- Parallel scan agents must not modify files
- Parallel scan agents must not borrow scope from another agent
- Parallel scan output must be merged only after all agent outputs are complete
- Partial scan coverage must not be presented as final merged output

## 5. Merged Output Requirements

The final merged output MUST be structured and must include:

- agent scope covered
- findings per scope
- consolidated result
- identified gaps or missing coverage, if any

The merged output must preserve scope attribution and must not be a loose summary.

## 6. Enforcement Rules

- Parallel scanning must not be used unless the task explicitly allows it
- Parallel scanning must not expand repository scope
- Parallel scanning must not replace explicit file-level or single-folder targeting when a task is already narrowly scoped
- Parallel scanning must not bypass existing repository guardrails
- Any misuse of parallel scan structure:
  - The task must be rejected

## 7. Validation Requirements

- Agent split must match the defined template or the explicit task definition
- Agent scopes must remain isolated
- Final output must be merged into one structured result
- No file modifications may occur during parallel scan execution
- Validation must occur before task completion is declared
