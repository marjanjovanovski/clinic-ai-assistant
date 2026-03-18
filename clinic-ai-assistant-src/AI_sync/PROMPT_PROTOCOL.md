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

## Session Discipline Protocol

### 1.1.14 One Task At A Time

Only one task may be active at a time.

Codex must execute only the current explicitly defined task.

Codex must not combine the current task with follow-up work unless a separate task explicitly authorizes it.

If a new task is introduced before completion of the current task:

- STOP current flow.
- Require explicit confirmation to abandon or pause the current task.

### 1.1.15 No Mid-Task Changes

A task must not change goal, scope, or constraints during execution.

Any change in direction must be treated as a new task.

The current task must be explicitly closed, paused, or rejected before switching.

Codex must not merge mid-task direction changes into the active task.

Codex must not reinterpret the active task to absorb the new request.

### 1.1.16 No Emotional or Non-Operational Prompting

Prompts must remain operational and task-oriented.

Task execution must be guided by explicit task definition, scope, and protocol rules.

Emotional, vague, or conversational instructions must not trigger execution.

Emotional language, urgency framing, praise, frustration, or persuasive wording must not expand, shrink, or redirect the active task.

If a prompt lacks clear task structure:

- Reject execution.
- Request reformulation.

Emotional tone may be acknowledged conversationally, but it must not be used as tasking authority.

### 1.1.17 Direction Change Rule

If user intent shifts:

- Treat it as a new `TASK_ID`.
- Do not merge it with the current task.
- Do not partially reuse execution state.

If the task scope changes:

- Reject continuation under the current task.

### 1.1.18 Enforcement Behavior

If any session-discipline rule is violated:

- STOP execution.
- Report violation clearly.
- Do not proceed.

Session discipline must remain deterministic and must not be overridden by conversational flow alone.

## Task State Machine Protocol

### 1.1.19 State Requirement

Every task must have exactly one explicit state.

Every task must begin in `PENDING`.

The required task states are:

- `PENDING`
- `IMPLEMENT`
- `VERIFY`
- `DONE`

### 1.1.20 Transition Rules

`IMPLEMENT` can only start from `PENDING`.

`VERIFY` can only start after `IMPLEMENT`.

`DONE` can only be reached after successful `VERIFY`.

If `VERIFY` fails:

- The task must return to `IMPLEMENT`.

### 1.1.21 No State Skipping

No state may be skipped.

Direct transition from `PENDING` to `VERIFY` is invalid.

Direct transition from `PENDING` to `DONE` is invalid.

Direct transition from `IMPLEMENT` to `DONE` is invalid.

### 1.1.22 Explicit Transition Rule

Each state transition must be explicit.

Codex must not infer state transitions from context, timing, or conversational flow alone.

### 1.1.23 Verification Gate

No task may reach `DONE` without successful `VERIFY`.

Failed verification must keep the task incomplete.

### 1.1.24 Enforcement Behavior

If state rules are violated:

- STOP execution.
- Report the invalid transition clearly.
- Do not continue under the invalid state flow.

Task execution is a controlled lifecycle, not free-flow execution.

`BLOCKED` may exist only as a future extension and must not be added to the active state machine in this task.

## Execution Context Isolation Protocol

### 1.1.25 Context Boundary

Every task must operate within an explicit context boundary.

Only inputs defined in the task prompt are allowed.

No additional context may be assumed.

### 1.1.26 No Implicit Memory

Codex must not rely on:

- previous tasks
- earlier conversation history
- unstated assumptions

Any required prior information must be explicitly re-provided.

### 1.1.27 Explicit Input Requirement

If a task depends on external or prior data:

- That data must be explicitly included in the task definition.

Missing required input must trigger:

- STOP execution.
- Request for required inputs.

### 1.1.28 No Context Carry-Over

Results, decisions, or state from previous tasks must not influence a new task.

Context reuse is allowed only if explicitly passed as input.

### 1.1.29 Violation Handling

If implicit context usage is detected:

- STOP execution.
- Report context violation.
- Do not continue under hidden assumptions.

### 1.1.30 Input Definition Rule

Valid task inputs are limited to:

- explicitly provided files
- explicitly provided text in the prompt
- explicitly declared references within the task

Any information not included in these inputs must be treated as unavailable.

Task isolation is required for reproducibility and hidden-context prevention.

## Backend Configuration Separation Protocol

### 1.1.31 Core Separation Rule

Configuration content must not be added to Python files.

Python files are reserved for:

- logic
- routing
- state machine behavior
- orchestration

Configuration content must live only in tenant profile JSON under:

- `clinic-ai-assistant-src/backend/app/config/profiles/`

### 1.1.32 Configuration Content Definition

Configuration content includes:

- reply wording
- trigger phrases
- language patterns
- business wording
- booking confirmation words
- fallback texts
- conversation rules
- booking/contact prompts
- behavior instructions
- assistant tone or style wording
- stage or flow instruction text intended for model behavior

### 1.1.33 Python Prohibition Rule

Python files must not define, store, hardcode, or introduce configuration content.

Python may load configuration from approved JSON sources.

Python may format configured values for execution.

Python must not become the source of conversational behavior wording.

### 1.1.34 Approved Configuration Source

Tenant profile JSON is the approved source for backend conversational and configuration content.

Onboarding or behavior variation must be achievable through JSON changes, not Python wording changes.

### 1.1.35 Prompting Enforcement

Every backend development prompt must explicitly respect this rule.

If a backend task attempts to place configuration content into Python:

- STOP execution.
- Report architecture violation.
- Require the content to be moved to tenant profile JSON.

### 1.1.36 Review Rule

Before executing backend changes, prompts must require checking whether the requested change belongs in:

- Python logic
- tenant profile JSON

If the change is configuration or content rather than logic or orchestration:

- It must be implemented in JSON, not Python.

### 1.1.37 Future Prompt Requirement

Future backend prompts must include an architecture constraint equivalent in meaning to:

- configuration content must not be added to Python files
- tenant profile JSON is the only approved source for conversational and configuration content
- Python may only load and orchestrate configuration

### 1.1.38 Enforcement Behavior

If this protocol is violated:

- STOP execution.
- Report the exact violation.
- Do not continue the task under the invalid architecture approach.

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

`TASK_ID: TASK_<TYPE>_<SHORT_NAME>`

`TASK_ID` must follow the required naming convention exactly.

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
