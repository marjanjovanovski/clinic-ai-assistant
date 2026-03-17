# OUTPUT_RULES

## 1. Purpose

Define deterministic output rules for tasks that create or write files.

## 2. Mandatory Output Path Rule

- Every task that creates or writes a file MUST define an exact output path
- If no exact output path is provided:
  - The task is invalid
  - The task must be rejected
- Codex must not infer output destinations
- Codex must not choose a path on its own
- Codex must not invent filenames
- Codex must not redirect output to a nearby or alternative path

## 3. Terminal Output Rule

- Large generated outputs must not be used as the primary delivery channel through terminal output
- Generated file outputs must be written to the predefined file path
- Terminal output must remain minimal and verification-oriented
- Terminal output must not replace required file output
- If the task explicitly requires return artifacts, only the requested verification artifacts may be returned

## 4. Folder Creation Rule

- If the required output folder does not exist:
  - Codex may create it only when the exact output path is explicitly provided
- Folder creation must be limited to the exact required output path only
- Folder creation must not expand scope beyond the requested destination
- If the output path is missing or ambiguous:
  - The task must be rejected

## 5. Enforcement Rules

- Codex must not proceed with generation if path requirements are missing
- Codex must not replace file output with terminal summaries
- Codex must not redirect output to an alternative path
- Any violation of deterministic output rules:
  - The task must be rejected

## 6. Validation Requirements

- Output path must be explicitly defined before execution
- Output file must match the requested path exactly
- Terminal output must remain limited to requested verification artifacts
- Folder creation, if needed, must match the requested path only
- Validation must occur before task completion is declared
