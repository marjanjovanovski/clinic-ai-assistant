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

## Prompt Size Control Protocol

### 1.1.1 Task Unit Definition

A task must produce exactly one outcome.

A task must modify exactly one logical area such as one file, one function, or one concern.

A task must be executable without requiring another task to complete its own goal.

A task is atomic only if it leads to one bounded implementation outcome.

A task may contain multiple words or sub-actions only if they serve the same single outcome and the same logical concern.

Natural language coordination alone must not be treated as proof of a multi-goal task.

If a task does not satisfy all three conditions:

- The task is not atomic.
- The task must be rejected.

### 1.1.2 Refined Multi-Goal Detection

A prompt must be treated as multi-goal only when it requests more than one independent outcome.

A prompt must be treated as multi-goal only when it requests changes to more than one independent concern.

A prompt must be treated as multi-goal only when it includes more than one execution path that could be completed separately.

Detection must be based on task intent and separability, not keyword presence alone.

Words such as `and`, `also`, and `then` are signals for review, not automatic failure conditions.

The protocol must not reject a task only because those words appear in natural language.

### 1.1.3 Split Rule

If a task is identified as multi-goal:

- STOP execution.
- Do not execute the task as written.
- Return a structured split recommendation before any implementation proceeds.

The required split format is:

```text
TASK SPLIT REQUIRED

Original Task:
<original prompt>

Suggested Tasks:
1. <task 1>
2. <task 2>
3. <task 3>
```

No task execution may proceed until the user confirms the split.

### 1.1.4 Max Scope Rule

The task must be rejected if it requires reading more than 3 files.

The task must be rejected if it affects multiple system layers.

The task must be rejected if it requires both `IMPLEMENT` and `VERIFY` in the same task.

### 1.1.5 Enforcement Rule

`IF TASK IS NOT ATOMIC -> DO NOT EXECUTE`

Non-atomic prompts are invalid for execution under this protocol.

## Task Naming Convention Protocol

### 1.1.6 Required Format

All tasks must follow the exact format:

`TASK_<TYPE>_<SHORT_NAME>`

### 1.1.7 TYPE Definition

`<TYPE>` is deterministic and not free text.

The only allowed values are:

- `IMPL`
- `VERIFY`

No other `<TYPE>` values are allowed.

### 1.1.8 SHORT_NAME Rules

`<SHORT_NAME>` represents the concise description of the task outcome.

`<SHORT_NAME>` must be uppercase.

`<SHORT_NAME>` must use underscores only.

`<SHORT_NAME>` must be concise and descriptive of the outcome.

`<SHORT_NAME>` must not exceed 5 words.

`<SHORT_NAME>` must describe the task result, not the action.

Example:

- `SYNC_FILE`
- not `DO_SYNC`

### 1.1.9 Naming Enforcement

`TASK_ID` must be present in every task.

`TASK_ID` must match the naming convention exactly.

If `TASK_ID` is missing:

- The task must be rejected.

If `TASK_ID` format is invalid:

- The task must be rejected.

### 1.1.10 Duplicate Prevention

`TASK_ID` must be unique per task.

If duplicate `TASK_ID` is detected:

- The task must be rejected.

### 1.1.11 Consistency With Mode

`TASK_<TYPE>` must match `MODE`.

If the task uses `MODE: IMPLEMENT`:

- `TYPE` must be `IMPL`

If the task uses `MODE: VERIFY`:

- `TYPE` must be `VERIFY`

If `MODE` and `TYPE` do not match:

- The task must be rejected.

### 1.1.12 Naming Quality Rule

Task names must be short, descriptive, uppercase, and underscore-separated.

Naming must remain consistent between related implementation and verification tasks when they refer to the same work item.

### 1.1.13 Required Examples

The section must include at minimum:

- `TASK_IMPL_SYNC_FILE`
- `TASK_VERIFY_BOOKING_FLOW`

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

### 1.9 Execution Feedback Loop (Mandatory)

After every `MODE: IMPLEMENT` task, a verification step MUST be executed before any new implementation task begins.

The verification must explicitly confirm:

- Did the target file change as expected
- Does the file content exactly match the requested output
- Does the result satisfy the stated goal
- Did the task remain inside the defined scope

Rules:

- No new implementation task may begin before verification passes
- Verification must be performed as a separate `MODE: VERIFY` task
- Verification must follow the defined verification template
- Verification must not modify any files
- If the verification step is skipped:
  - The implementation task must be rejected
- If verification fails:
  - The implementation task is considered incomplete
  - The task must not be closed
  - A corrective implementation task must be issued

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
