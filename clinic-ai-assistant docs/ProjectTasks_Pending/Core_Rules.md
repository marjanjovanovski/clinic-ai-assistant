# Core Rules

This file contains the short, always-on operating rules for work in `ProjectTasks_Pending`.

## Source Of Truth

- the task markdown file is the workflow authority for the feature or fix
- git is the source of truth for code and commit history
- do not auto-update the lessons/history database unless the task explicitly requires it

## Execution Gates

- work only on the dedicated branch for that task unless the user explicitly changes the branching plan
- after completing a tracked prompt, stop and ask `Commit changes?`
- directly below `Commit changes?`, always provide one proposed descriptive commit message matching the commit you would create if the user approves
- do not auto-advance past a prompt boundary
- treat manual verification / merge readiness as a tracked final prompt, not an informal afterthought

## Token Efficiency

- prefer one master task file per workstream
- create prompts only at real execution boundaries
- keep completion notes compact:
  - `Changed`
  - `Verified`
  - `Blocked`
- do not turn task files into long-running diaries
- when a task has `manual_testing_coverage.json`, keep markdown manual-testing sections compact and use JSON as the primary state tracker

## Testing Hygiene

- keep test and runtime residue out of the repo
- use external `TMP` / `TEMP` and external pytest `--basetemp`
- do not create repo-local scratch or fallback temp folders without explicit user approval
- if cleanup is blocked, report the exact leftover paths and do not present the repo as clean
- a prompt is not complete until temporary verification artifacts are removed or the blocker is documented

## This Environment

For this machine, if sandboxed or `F:\\temp`-based test execution hits temp or SQLite permission failures:
- use the proven fallback pattern outside sandbox
- use `C:\\Users\\Marjan Velika\\AppData\\Local\\Temp\\...` for `TMP`, `TEMP`, and `--basetemp`
- do not spend repeated retries on failing temp-path variants first

## Manual Verification

- use `manual_testing_coverage.json` only when it materially simplifies repeated manual testing, retesting, or fix follow-up work
- the markdown file should keep the readable overview
- JSON should hold row-level status, comments, reference filenames, general comment, and branch merge readiness
- every manual-testing row in JSON should carry a stable positive integer `row_id` unique within that JSON file
- `row_id` exists to support precise reviewer references across save cycles, retests, and fix follow-ups, so do not key row identity off `step` alone
- new optional JSON fields must default safely so older task JSON does not break

## Fix Follow-Ups

- if manual verification produces concrete follow-up work, keep the fix in the same parent task folder
- use a separate fix task file and a separate fix JSON
- keep the fix scope lean; do not reopen and expand the original task unnecessarily

## Archive Rule

- folder-based completed tasks must be archived as whole folders into `ProjectTasks_Done`
- do not flatten them and separate the markdown from companion JSON artifacts

## Required Honesty

- if a rule was available and not followed, say so plainly
- if verification was partial, say so plainly
- if a task is blocked, mark it as blocked instead of forcing progress
