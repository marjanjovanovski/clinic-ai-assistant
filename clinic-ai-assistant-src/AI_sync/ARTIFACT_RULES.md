# ARTIFACT_RULES

## 1. Purpose

Define mandatory artifact outputs required for task execution.

## 2. Mandatory Artifact Contract

Every applicable task MUST return all of the following:

- Exact file path
- Line count
- Full file content OR diff of changes
- First 20 lines preview

For newly created files:
- Full file content MUST be returned

For modified existing files:
- Full file content OR diff of changes MUST be returned, according to the task request

## 3. Enforcement Rules

- If any required artifact is missing:
  - The task is considered FAILED
- Partial outputs are not allowed
- Codex must not omit any required artifact
- Codex must not replace required artifacts with summaries
- Codex must not alter the requested artifact format
- If returned artifacts do not match actual file state:
  - The task is considered FAILED

## 4. Applicability

- Applies to all IMPLEMENT tasks that create or modify files
- Applies to VERIFY tasks only when the prompt explicitly requires artifact return items
- Does not apply to pure VERIFY tasks without explicit artifact-return requirements

## 5. Validation Requirements

- All mandatory artifacts required by the task must be present
- Artifact values must correspond to actual file state
- Output must match the requested return structure exactly
- Validation must occur before task completion is declared
