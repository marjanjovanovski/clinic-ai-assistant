# FAILURE_PROTOCOL

## 1. Purpose

Define deterministic failure handling behavior for execution failures.

## 2. Global Failure Rule

- Execution failures must not be corrected inside the same prompt
- A failed task must be treated as incomplete until a valid follow-up task is executed
- Recovery must follow the defined next allowed prompt type

## 3. Failure Type: timeout

- Detection signal:
  - Execution does not complete within the allowed task run
- Mandatory action:
  - Stop execution
  - Mark the task as incomplete
  - Report timeout failure
- Next allowed prompt type:
  - `MODE: IMPLEMENT`

## 4. Failure Type: partial artifact

- Detection signal:
  - One or more required artifacts are missing or incomplete
- Mandatory action:
  - Mark the task as failed
  - Report artifact failure
  - Do not close the task
- Next allowed prompt type:
  - `MODE: IMPLEMENT`

## 5. Failure Type: invalid format

- Detection signal:
  - Returned output does not match the required structure or artifact format
- Mandatory action:
  - Mark the task as failed
  - Report format failure
  - Require corrective re-execution
- Next allowed prompt type:
  - `MODE: IMPLEMENT`

## 6. Failure Type: scope violation

- Detection signal:
  - Read or write activity exceeds the task's allowed scope
- Mandatory action:
  - Stop execution immediately
  - Mark the task as failed
  - Report scope violation
- Next allowed prompt type:
  - `MODE: VERIFY`

## 7. Validation Requirements

- All 4 required failure types must be present
- Each failure type must define detection signal, mandatory action, and next allowed prompt type
- The global failure rule must prohibit same-prompt correction
- File structure must match the requested section order exactly
