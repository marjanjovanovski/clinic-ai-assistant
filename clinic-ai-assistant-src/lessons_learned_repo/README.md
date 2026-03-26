# Lessons Learned Repo

This folder is an optional engineering-memory layer for curated lessons learned and requirement-linked notes.

It is separate from the live clinic runtime and is not part of the default commit workflow.

## Current Role

Git is the source of truth for normal code history, commit grouping, and rollback.

This repository exists for the cases where the team wants to preserve higher-value knowledge that Git does not express cleanly, such as:
- reusable engineering lessons
- cross-task implementation patterns
- requirement-linked rationale
- validated guidance worth carrying into future work

## What It Supports

- controlled requirement categories
- canonical project requirements
- optional execution records tied to requirements
- curated lessons learned linked back to execution evidence

## What It Does Not Do

- it does not replace Git history
- it is not required after every commit
- it should not be used to mirror routine branch activity
- it no longer provides a combined commit-and-log command

## Recommended Use

Initialize the database:

```bash
python -m lessons_learned_repo.history_cli init-db
```

Create a requirement:

```bash
python -m lessons_learned_repo.history_cli create-requirement --req-code REQ-PROJ-HISTORY-001 --title "Project requirements and execution history tracking" --category-code lessons_learned_repo --description "Create a lightweight SQLite-based project history layer." --status active
```

Optionally record an execution when the team explicitly wants requirement-linked evidence:

```bash
python -m lessons_learned_repo.history_cli record-execution --req-code REQ-PROJ-HISTORY-001 --prompt-file path/to/prompt.txt --summary "Implemented the initial history layer." --impact "Requirement-linked execution history became queryable."
```

Create a lesson from one or more execution ids:

```bash
python -m lessons_learned_repo.history_cli create-lesson --lesson-code LESSON-REQ-001 --title "Separate project memory from product runtime" --statement "Project memory and collaboration logging should live outside the patient-facing runtime." --why-it-matters "This keeps operational learning infrastructure from bleeding into live clinic behavior." --execution-ids 1 2 --status validated
```

List lessons with requirement, category, and source execution ids:

```bash
python -m lessons_learned_repo.history_cli list-lessons
```
