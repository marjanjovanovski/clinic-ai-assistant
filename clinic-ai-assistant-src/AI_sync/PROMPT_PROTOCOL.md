# PROMPT_PROTOCOL

## 1. Codex Tasking Protocol

This document is the single standard for writing Codex tasks in this repository. All future tasks must follow this protocol exactly.

### 1.1 Reduce Task Scope

Every task must explicitly define:

- `Target folder`
- `Target file`
- `Goal`
- `Constraints`
- `Return`

Tasks must be narrowed to the smallest safe scope. If a task can be limited to one folder, one file, or one artifact, it must be.

### 1.2 Separate Verification vs Implementation

Every task must declare exactly one mode:

- `MODE: IMPLEMENT`
- `MODE: VERIFY`

`IMPLEMENT` is for making changes.

`VERIFY` is for read-only analysis, validation, readiness checks, and compliance review.

Modes must never be mixed in a single task.

### 1.2.1 Mode Enforcement (Mandatory)

Every task MUST begin with exactly one explicit mode declaration.

The only valid mode declarations are:

- `MODE: IMPLEMENT`
- `MODE: VERIFY`

If `MODE` is missing:

- The task must be rejected.

If more than one mode declaration is present:

- The task must be rejected.

If both valid modes are present anywhere in the same task:

- The task must be rejected.

If the task contains both read-only intent and write intent:

- The task must be rejected.

Codex must not infer mode from context.

Codex must not infer mode from wording.

Codex must not infer mode from implied intent.

Codex must not proceed on ambiguous prompts.

Codex must require explicit mode before execution begins.

### 1.3 Artifact-Based Outputs Required

Every task must define the required output artifact or response artifact in advance.

If a file must be created or updated, the task must name the exact file path.

If no file change is allowed, the task must define the required return structure explicitly.

Outputs must be tied to named artifacts, not open-ended summaries.

Examples:

- "Return exact file path"
- "Return full file content"
- "Return line count"
- "Return first 20 lines preview"
- "Return diff of changes"

If a required artifact is not returned, the task is invalid.

### 1.4 Repository Scope Constraints

Every task must explicitly limit repository scope.

The prompt must state:

- what may be read
- what may be modified
- what may not be touched

If a task is intended for a single file or folder, Codex must stay inside that boundary.

`runtime_traces` is read-only only when an explicit task requires it.

`AI_sync` is writable only when explicitly targeted by the task.

No architecture redesign is allowed unless the task explicitly requests it.

### 1.5 Deterministic Output Enforcement

Prompts must require deterministic, structured output.

Tasks must:

- request exact sections
- request exact artifact paths where applicable
- request exact return items
- avoid optional template branches
- avoid multiple prompt variants
- avoid ambiguous language such as "maybe", "if needed", or "any format"

Only the defined template structures in this document may be used.

### 1.6 Final Verification Requirement

Every implementation task must end with a verification pass against the stated constraints.

At minimum, final verification must confirm:

- target path correctness
- scope compliance
- artifact completeness
- no unintended file changes
- requested return items present

Verification tasks must end with a readiness, compliance, or findings summary tied to the requested return format.

### 1.7 Failure Handling (Mandatory)

If any protocol rule is violated:

- STOP execution immediately
- Report violation
- Do not continue task

No partial completion allowed.

### 1.8 Task Traceability

Every task must include:

`TASK_ID: <unique_name>`

`TASK_ID` must be unique per task.

It is used for tracking and debugging execution.

## 2. Implementation Prompt Template

Use this template for all write tasks. No variations are allowed.

```text
MODE: IMPLEMENT

Target folder:
[exact folder path]

Target file:
[exact file path]

Goal:
[single task goal]

Constraints:
- [scope limit]
- [write limit]
- [read limit]
- [artifact limit]
- [any additional hard rule]

Return:
1. [artifact or result item]
2. [artifact or result item]
3. [verification item]
```

## 3. Verification Prompt Template

Use this template for all read-only tasks. No variations are allowed.

```text
MODE: VERIFY

Context:
[what this verification is for]

Verify:
- [item to verify]
- [item to verify]
- [item to verify]

Constraints:
- read-only operation
- no file modifications
- no new files
- [scope limit]
- [any additional hard rule]

Return:
1. [finding, readiness value, or compliance result]
2. [missing information, if any]
3. [dependency conflict or risk, if any]
4. [explicit confirmation of understanding or compliance]
```
