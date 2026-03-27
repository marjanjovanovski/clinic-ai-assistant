# Task Workflow Guide

This file defines how task files should be structured and executed.

Execution must also follow [Core_Rules.md](./Core_Rules.md).

## Naming

Use:

`<CATEGORY> - <Task Descriptive Value>`

Recommended categories:
- `DATA`
- `API`
- `UI`
- `AGENT`
- `INFRA`
- `TEST`
- `DOC`

Keep the name short, specific, and outcome-oriented.

## Pending Task Folder Convention

Prefer:

`ProjectTasks_Pending/<CATEGORY> - <Task Descriptive Value>/`

Inside the folder:
- `<CATEGORY> - <Task Descriptive Value>.md`
- `manual_testing_coverage.json` when structured manual verification is truly useful
- optional user-added evidence files referenced by filename only

Rules:
- folder name should match the task markdown filename without `.md`
- the markdown file remains the workflow authority
- `manual_testing_coverage.json` is a companion tracker, not a replacement for the markdown file
- reference files in JSON should be plain typed filenames only

## Completed Task Archive Convention

When a folder-based task is completed and merged:
- move the whole folder from `ProjectTasks_Pending` to `ProjectTasks_Done`
- keep the markdown file, JSON files, and same-folder fix follow-ups together

Older flat completed tasks may stay flat.

## Fix Follow-Up Convention

When manual verification reveals follow-up work, keep it in the same parent folder.

Recommended naming:
- `<Original Task Name> FIX 01.md`
- `manual_testing_coverage_FIX01.json`

Increment as needed:
- `FIX 02`
- `manual_testing_coverage_FIX02.json`

## Required Top Section In Every Task File

Include:
- title
- short purpose
- guide reference
- `Merge To Main - Pending` or `Completed`
- prompt status summary
- `Current Active Prompt`
- `Last Updated By`
- `Last Updated On`

Strongly recommended:
- `Working Rules For The Implementing AI Agent`
- `Testing And Verification Rules`
- `Do Not Break`
- `Current Repo Truth`
- `Architecture Guidance`

## Prompt Design

Prefer fewer boundary-based prompts.

Good boundaries:
- repo truth / architecture trace
- implementation slice
- regression coverage
- technical verification
- manual verification / merge readiness

Avoid splitting prompts just to create more headings.

## Prompt Status Tracking

At the top of the task file, keep a compact status summary such as:
- `Prompt 1 - Pending`
- `Prompt 2 - Pending`
- `Prompt 3 - Pending`

Each prompt section deeper in the file must mirror the same status.

Allowed values:
- `Pending`
- `Completed`
- `Blocked`

## Completion Notes

Keep each prompt completion note short:
- `Changed`
- `Verified`
- `Blocked`

Avoid long narrative progress logs.

## Manual Testing In Markdown

If the task does not use `manual_testing_coverage.json`:
- keep manual testing in markdown with a clean category/test/steps structure

If the task does use `manual_testing_coverage.json`:
- keep markdown manual testing compact
- include only:
  - category name
  - test name
  - short purpose
- do not duplicate the full row-level matrix in both markdown and JSON

Preferred split:
- markdown = readable overview
- JSON = operational tracker

## Manual Testing JSON Shape

Use one consistent pattern:
- task metadata
- `manual_verification`
- `categories`
- `tests`
- `rows`
- `summary`

Row fields should stay stable:
- `step`
- `action`
- `what_is_tested`
- `status`
- `comment`
- `reference_files`

Task-level manual verification fields may include:
- `branch_merge_ready`
- `general_comment`

## Final Prompt Rule

Every substantial task should end with a tracked prompt for:
- manual verification
- merge readiness
- or both together

Implementation completion alone is not merge completion.

## Suggested Task Skeleton

```md
# <CATEGORY> - <Task Name>

Short purpose.

Execution of this task must follow [Task_Workflow_Guide.md](...) and [Core_Rules.md](...).

## Execution Tracking Instructions
...

## Merge Status
- `Merge To Main - Pending`

## Prompt Status Summary
- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending

## Current Active Prompt
- `Prompt 1`

## Prompt 1 - Pending
...

## Prompt 2 - Pending
...

## Manual Testing
- Category 1
  - Test 1.1 - Short purpose

```
