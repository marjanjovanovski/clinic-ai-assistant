# Feature Implementation Guide

This file is the general operating guide for implementing complex features through multiple prompts while keeping a durable record of work status in the repo.

The main objective is:
- to avoid losing context between prompt handoffs
- to avoid copying fragmented instructions from place to place
- to keep a visible record of what has already been executed
- to make long, complex feature work easier to continue across multiple AI sessions

## Core Principle

For every complex feature, create one dedicated master prompt tracking document in this folder.

That document should:
- explain the feature goal
- explain the current reasoning and context
- split the work into several prompts
- track prompt completion status at the top
- track prompt completion status again at each prompt section

This guide is the reusable execution rulebook.
Feature-specific master prompt files should reference this guide instead of duplicating the full workflow rules.

Pending task files should live in `ProjectTasks_Pending`.
Completed task files should be archived into `ProjectTasks_Done`.

## Task File Naming Convention

To keep pending work easy to scan and group visually, use this naming format for feature-specific task files:

`<CATEGORY> - <Task Descriptive Value>.md`

Examples:
- `DATA - Tenant Lead Chat Persistence Refactor.md`
- `API - Scheduling Endpoint Hardening.md`
- `UI - Booking Flow Progress Panel.md`
- `AGENT - Intent Routing Cleanup.md`
- `TEST - Booking Regression Coverage Expansion.md`

Recommended category prefixes:
- `DATA` for schema, database, migrations, persistence, and storage work
- `API` for routes, contracts, backend request/response behavior
- `UI` for frontend interface and interaction work
- `AGENT` for assistant logic, orchestration, prompting, and runtime flow
- `INFRA` for deployment, environments, ops, tooling, and platform work
- `TEST` for test coverage, validation, and verification work
- `DOC` for documentation-only work

Use one clear category prefix only.
Keep the task description short, specific, and outcome-oriented.

## Required Tracking Format

At the top of each feature-specific master prompt document, include a global summary such as:

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending

When prompts are executed, update the summary immediately.

Examples:

If Prompt 1 is done:
- Prompt 1 - Completed
- Prompt 2 - Pending
- Prompt 3 - Pending

If Prompt 1 and Prompt 2 are done:
- Prompt 1 - Completed
- Prompt 2 - Completed
- Prompt 3 - Pending

Each prompt section deeper in the document must also reflect the same state in its header:
- `Prompt 1 - Completed`
- `Prompt 2 - Pending`

Each feature-specific master prompt document should also contain:
- a short feature title
- a short explanation of why the feature exists
- a reference to this guide as the workflow authority
- the global prompt status summary
- prompt sections with their own local status
- a top-level merge status line:
  - `Merge To Main - Pending`
  - or `Merge To Main - Completed`

Strongly recommended standard sections:
- `Execution Tracking Instructions`
- `Last Updated By`
- `Last Updated On`
- `Current Active Prompt`
- `Working Rules For The Implementing AI Agent`
- `Testing And Verification Rules`
- `Do Not Break` for risky flows
- `Current Repo Truth` when repo state matters for handoff
- `Architecture Guidance` when ownership boundaries matter

## Rules For Multi-Prompt Feature Work

- Never assume the next AI agent knows the repo context.
- The first prompt should usually focus on understanding the current implementation and reasoning for the change.
- Later prompts should focus on schema, migration, code integration, and tests in a logical order.
- Prompts should be specific enough to execute, but broad enough that the implementing agent does not need to be micromanaged line by line.
- The tracking document must be treated as the single source of truth for feature progress.
- After finishing any prompt, the agent must update the tracking document before moving on.
- Any prompt not yet executed must remain marked as `Pending`.
- If work cannot continue, mark the prompt as `Blocked` and include the reason directly under that prompt.

## Branch Workflow Rule

Every new feature-specific task file created in `ProjectTasks_Pending` must be executed on its own dedicated git branch.

This branch should represent the whole task, similar to a normal professional feature branch or pull-request branch.

Required behavior:
- when starting work on a new pending task file, create or switch to a dedicated branch for that task before making implementation changes
- keep all prompts for that task on the same branch unless the user explicitly asks for a different branching strategy
- prefer one branch per task and multiple commits inside that branch, rather than creating a new branch for every prompt
- each prompt may still be committed separately, but those commits should normally stay on the same task branch
- if Prompt 1 was already started without a dedicated branch, move the remaining work onto a dedicated branch as early as possible and keep the rest of the task there
- if multiple task files are being implemented in parallel, each task file should get its own branch when practical

Recommended branch naming style:
- use a short task-oriented branch name
- examples:
  - `task-main-chat-booking-completion`
  - `ui-slot-overlap-proposal`
  - `api-scheduling-hardening`

The purpose of this rule is:
- to keep each pending task isolated
- to make review and rollback easier
- to match normal pull-request-oriented git workflow
- to avoid mixing unrelated feature work in the same branch

## Merge Tracking Rule

Every feature-specific task file must track merge readiness explicitly.

Required behavior:
- each task file must include a top-level line for:
  - `Merge To Main - Pending`
  - or `Merge To Main - Completed`
- when implementation prompts are complete but the branch has not yet been manually verified and merged, the task file must remain in `ProjectTasks_Pending`
- the task file should act as the final source of truth for whether the feature is only implemented on a branch or is actually merged into `main`
- when all prompts are complete but merge is still pending, it is recommended to set:
  - `Current Active Prompt` to `Manual Verification / Merge`
  - `Merge To Main` to `Pending`

This rule exists so that implementation completion and merge completion are not treated as the same event.

## Prompt Completion Stop Rule

After every prompt is executed, execution must stop.

The implementing agent must not automatically continue into the next prompt.

Instead, the agent must wait for further instruction and explicitly ask:

`Commit changes?`

This pause is mandatory even if the next prompt is already clear.

This rule is a hard execution gate.

## Commit Approval Rule

If the user approves `Commit changes?`, the agent must follow this sequence exactly:

1. Commit the changes with a descriptive commit message.
2. Confirm back to the user that the commit was completed.
3. Respond with:
   `Continue with Prompt X`

In that response, `X` must be the next prompt that is still marked as `Pending` in the master prompt tracking document.

If no prompt remains pending, the agent must explicitly say that no pending prompts remain.

If no prompt remains pending, the agent must not automatically move the task file to `ProjectTasks_Done` until merge to `main` is actually completed.

## Lessons Learned Rule

The project does not require a history database update as part of the normal commit workflow.

Git is the source of truth for:
- code history
- commit grouping
- authorship
- rollback and diff inspection

The optional lessons-learned repository may still be used when the user explicitly wants to preserve a reusable engineering lesson, decision, or cross-task insight.

Required behavior:
- do not update the lessons-learned database automatically after normal prompt commits
- do not treat lessons logging as part of the default prompt completion flow
- create or update lessons only when the user explicitly asks for it, or when the task itself is specifically about lessons capture
- keep commit messages and task tracking documents professional enough that routine branch history does not depend on a separate database log

## No Auto-Advance Rule

- The agent must not begin the next prompt immediately after committing.
- The agent must not assume commit approval means permission to execute the next prompt.
- After commit is finished, the agent should only respond with the completion note and the suggested next prompt number.
- The next prompt should begin only after the user gives a new explicit instruction.
- If a prompt is finished but not committed, execution must still remain stopped.
- If the user discusses the result after a prompt is finished, the agent must still wait for explicit instruction before resuming implementation.

## Merge To Main Rule

Merging a task branch into `main` is a separate approval step from committing prompt work on the branch.

Required behavior:
- prompt commits save progress on the task branch only
- merge to `main` must happen only after the user performs manual testing and decides the branch is ready
- the agent must not assume that `Commit changes?` means approval to merge the branch
- merge readiness should be discussed only after implementation prompts are complete or the user explicitly asks about merge readiness

Minimum merge readiness conditions:
- implementation prompts are completed, or any blocked items are explicitly accepted by the user
- the task file statuses are updated
- required automated tests were run, or blockers were documented clearly
- the user has performed manual verification on the branch
- the user has decided the branch is ready for merge

Only after merge is complete:
- set `Merge To Main - Completed`
- merge the branch into `main`
- move the task file from `ProjectTasks_Pending` to `ProjectTasks_Done`
- switch the working branch back to `main` if needed and treat that state as the new clean baseline
- start any new implementation task from a fresh dedicated branch created from the updated `main`

## Commit Gate Example

Example flow after a prompt is completed:

1. Agent finishes the prompt work and updates the master prompt tracking document.
2. Agent stops and asks:
   `Commit changes?`
3. User approves commit.
4. Agent commits with a descriptive message.
5. Agent responds with a short completion note and:
   `Continue with Prompt X`

Example final response after commit:

`Changes committed with a descriptive message. Continue with Prompt 3`

Example final response when no pending prompts remain:

`Changes committed with a descriptive message. No pending prompts remain.`

If no prompts remain but merge is still pending, the task file must stay in `ProjectTasks_Pending` with `Merge To Main - Pending`.

Only after the branch is merged into `main` should the task file be archived into `ProjectTasks_Done`.

## Master Prompt Authoring Rule

To keep the process bulletproof without unnecessary redundancy:
- keep the detailed workflow rules in this guide
- keep only a short workflow reminder inside each feature-specific master prompt file
- duplicate workflow rules into a feature file only when that feature needs a special exception
- if an older pending file started as a proposal-only note but is now intended to drive implementation, rewrite it into a proper execution-ready master prompt document instead of appending more freeform proposal text
- prefer prompt sections that map to real engineering boundaries such as architecture review, contracts, persistence, runtime integration, UI adaptation, logging, tests, and final verification
- split large features into enough prompts that each one has a clear verification target and a natural commit boundary
- do not pack unrelated backend, frontend, and testing work into one oversized prompt when separate prompts would reduce token load and execution risk

Recommended reminder text for feature-specific master prompt files:

`Execution of this feature must follow Feature_Implementation_Guide.md. After each completed prompt, stop, update prompt status, and ask "Commit changes?" Do not auto-advance.`

## Testing Hygiene Rule

Task files that involve test execution should state repo-clean verification rules explicitly.

Required behavior:
- do not allow automated testing to create junk files or temp folders inside the repo
- when using pytest, prefer external `TMP` / `TEMP` and an external `--basetemp`
- if a tool or framework tends to generate artifacts, direct them to an approved temp location outside the repository when practical
- if cleanup is required after verification, document it in the prompt completion note
- if environment limits prevent clean automated execution, document the blocker instead of falling back to repo-local temp output

Recommended wording for task files:

`Follow the repo rule to keep test artifacts out of the repository. Use external TMP/TEMP and external basetemp locations for pytest or similar tooling.`

## Standard Master Prompt Skeleton

For new task files, prefer this top-level order:

1. Title and short purpose
2. `Execution Tracking Instructions`
3. `Last Updated By`
4. `Last Updated On`
5. `Merge To Main`
6. `Current Active Prompt`
7. `Global Status Summary`
8. `Working Rules For The Implementing AI Agent`
9. `Testing And Verification Rules`
10. `Do Not Break` when applicable
11. `Current Repo Truth`
12. `Architecture Guidance`
13. Prompt sections in execution order

This keeps task files easier to continue across sessions and makes it easier for an implementing agent to identify status, constraints, architecture boundaries, and the next safe execution step quickly.

## End Of Document Appendix Rule

When creating a new task markdown file, add a compact appendix at the very end of the document.

Purpose:
- preserve a simple business-level explanation of the feature
- make handoff and manual verification easier
- improve readability for future sessions without inflating the execution prompts

Required appendix sections:
- `Use Case`
- `Manual Testing`

Recommended optional sections when helpful:
- `Scenarios`
- `Simple Flow Chart`

Required behavior:
- clearly mark the appendix as archive and manual-verification guidance only
- clearly state that the appendix must not be treated as additional implementation scope unless the user explicitly asks
- keep the appendix concise and high-signal
- prefer simple tables for actor/outcome comparisons when they improve clarity
- include a small chart only when it makes the runtime flow easier to understand
- avoid large narrative examples that consume tokens without improving execution clarity

## Use Case Appendix Rule

The `Use Case` section should explain the business logic in practical terms.

Required behavior:
- describe the real user flow in short, concrete steps
- explain what the system is trying to protect or enable
- show who does what and what the backend decides
- use a compact table when multiple actors, paths, or outcomes are involved
- optimize for fast understanding with minimal token usage

## Manual Testing Appendix Rule

The `Manual Testing` section should provide a step-by-step reproduction guide for verifying the feature.

Required behavior:
- list the exact actions to take in execution order
- include expected results beside each step or immediately under it
- make it possible for a reviewer to validate the feature without reverse-engineering the code
- include separate scenario coverage when success path and conflict path differ meaningfully
- keep steps practical, observable, and concise

Recommended format:
- Step
- Action
- Expected Result

Example compact table:

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the page or trigger the flow | Initial state loads correctly |
| 2 | Perform the user action under test | Target state change appears |
| 3 | Repeat the conflicting or recovery action | Conflict or recovery behavior matches the task definition |

## Minimal Token Guidance For Appendices

To preserve high quality output with low token usage:
- keep appendix language direct and operational
- prefer one compact table over several repetitive bullet lists
- prefer one small flow chart over a long prose explanation when sequence matters
- do not restate the full prompt document in the appendix
- include only the scenarios needed for business understanding and manual verification

## Recommended Prompt Order

For most backend or persistence-heavy features, prefer this order:

1. Understanding and architecture review
2. Schema design
3. Data migration
4. Runtime integration
5. Testing and verification
6. Final summary and follow-up recommendations

## Writing Style Guidance For Prompt Documents

- Explain not only what to build, but why the feature is needed.
- Include business intent where possible.
- Include the current architectural limitation being solved.
- State any non-negotiable requirements clearly.
- Give professional freedom where implementation details should be chosen by engineering judgment.
- Avoid vague prompts like "improve this" without explaining target outcomes.

## Suggested Improvement

For larger features, add one more small section near the top of each master prompt document:

`Last Updated By`
`Last Updated On`
`Current Active Prompt`

This makes handoff even easier when multiple implementation sessions happen over time.

## Suggested Improvement

For features that include schema changes, add a short checklist section:

- schema designed
- migration created
- existing data preserved
- runtime code updated
- tests added or updated
- docs updated

This helps future agents quickly see whether the feature is only partially complete.

## Suggested Improvement

If the feature is especially risky, include a short section called `Do Not Break` with the flows that must remain intact.

Example:
- booking recovery from persisted lead state
- tenant-scoped session ownership
- message ordering within a conversation

This is helpful when a future agent joins mid-stream and might otherwise optimize the wrong thing.
