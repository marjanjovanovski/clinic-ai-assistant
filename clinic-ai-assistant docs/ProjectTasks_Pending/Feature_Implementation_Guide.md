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

## Rules For Multi-Prompt Feature Work

- Never assume the next AI agent knows the repo context.
- The first prompt should usually focus on understanding the current implementation and reasoning for the change.
- Later prompts should focus on schema, migration, code integration, and tests in a logical order.
- Prompts should be specific enough to execute, but broad enough that the implementing agent does not need to be micromanaged line by line.
- The tracking document must be treated as the single source of truth for feature progress.
- After finishing any prompt, the agent must update the tracking document before moving on.
- Any prompt not yet executed must remain marked as `Pending`.
- If work cannot continue, mark the prompt as `Blocked` and include the reason directly under that prompt.

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
2. Follow the project rules for updating the history database.
3. Confirm back to the user that the commit and history update were completed.
4. Respond with:
   `Continue with Prompt X`

In that response, `X` must be the next prompt that is still marked as `Pending` in the master prompt tracking document.

If no prompt remains pending, the agent must explicitly say that no pending prompts remain.

If no prompt remains pending and the final commit is complete, the agent must archive the feature-specific master prompt file by moving it from `ProjectTasks_Pending` to `ProjectTasks_Done`.

## History DB Author Rule

Every history database entry created after a commit must explicitly set the `author_name` field to the agent that performed the work and recorded the entry.

This author value must represent the acting AI agent, not the git commit identity and not the human repository owner by default.

Required behavior:
- always set `author_name` deliberately when creating a `requirement_execution` entry
- always set `author_name` deliberately when creating a `lessons_learned` entry
- never leave author attribution to implicit fallback behavior if the active agent identity is known
- never use `Marjan Jovanovski` as the history DB author for agent-executed work unless the user explicitly instructs that exact attribution

Examples:
- if Codex performs the work, set `author_name` to `Kai - Codex`
- if Claude performs the work, set `author_name` to `Claude`

This rule applies even if the git commit author remains a different value.

## History DB Location And Update Path

The project history database referenced by the commit workflow lives here:

- `clinic-ai-assistant-src/lessons_learned_repo/project_history.db`

The implementation layer for reading and writing that database lives here:

- `clinic-ai-assistant-src/lessons_learned_repo/history_store.py`
- `clinic-ai-assistant-src/lessons_learned_repo/history_cli.py`

Preferred update path:
- use the helpers in `history_store.py` when working directly in code
- use `history_cli.py` when a CLI-based workflow is more appropriate

Tables relevant to the commit workflow:
- `project_requirements`
- `requirement_execution`
- `lessons_learned`

For post-commit logging, the most important table is:
- `requirement_execution`

Minimum required fields for a `requirement_execution` entry:
- `req_code`
- `prompt_text`
- `execution_summary`
- `execution_impact`
- `git_commit_hash`
- `author_name`

Required author rule for those entries:
- `author_name` must be the acting AI agent
- do not default it to `Marjan Jovanovski`
- examples:
  - `Kai - Codex`
  - `Claude`

If a lesson is also created or updated as part of the work, `lessons_learned.author_name` must follow the same rule.

When a new agent joins and asks where the commit-history database lives or how it should be updated, this section is the source of truth.

## No Auto-Advance Rule

- The agent must not begin the next prompt immediately after committing.
- The agent must not assume commit approval means permission to execute the next prompt.
- After commit and history update are finished, the agent should only respond with the completion note and the suggested next prompt number.
- The next prompt should begin only after the user gives a new explicit instruction.
- If a prompt is finished but not committed, execution must still remain stopped.
- If the user discusses the result after a prompt is finished, the agent must still wait for explicit instruction before resuming implementation.

## Commit Gate Example

Example flow after a prompt is completed:

1. Agent finishes the prompt work and updates the master prompt tracking document.
2. Agent stops and asks:
   `Commit changes?`
3. User approves commit.
4. Agent commits with a descriptive message.
5. Agent updates the history database according to project rules, including explicit `author_name` attribution to the acting agent.
6. Agent responds with a short completion note and:
   `Continue with Prompt X`

Example final response after commit:

`Changes committed with a descriptive message and history database updated. Continue with Prompt 3`

Example final response when no pending prompts remain:

`Changes committed with a descriptive message and history database updated. No pending prompts remain.`

After that final completion state, the agent must archive the feature-specific master prompt file into `ProjectTasks_Done`.

## Master Prompt Authoring Rule

To keep the process bulletproof without unnecessary redundancy:
- keep the detailed workflow rules in this guide
- keep only a short workflow reminder inside each feature-specific master prompt file
- duplicate workflow rules into a feature file only when that feature needs a special exception

Recommended reminder text for feature-specific master prompt files:

`Execution of this feature must follow Feature_Implementation_Guide.md. After each completed prompt, stop, update prompt status, and ask "Commit changes?" Do not auto-advance.`

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
