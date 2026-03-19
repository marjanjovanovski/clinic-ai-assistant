# Lessons Learned Repo

This folder is the collaboration and execution-memory layer for requirement-linked project history.

It is separate from the live clinic runtime. It does not run through `backend/app/main.py`.

## What It Does

- stores controlled requirement categories
- stores canonical project requirements
- stores execution history records tied to requirements
- stores curated lessons learned linked back to execution evidence
- provides a CLI trigger entry for logging repo-changing executions

## Trigger Entry

Use:

```bash
python -m lessons_learned_repo.history_cli commit-with-history ...
```

This is the commit-time trigger for requirement-linked execution logging.

You can also record execution without committing:

```bash
python -m lessons_learned_repo.history_cli record-execution ...
```

The `commit-with-history` command is the preferred trigger when a successful prompt ends in a repo commit.

## Quick Start

Initialize the database:

```bash
python -m lessons_learned_repo.history_cli init-db
```

Create a requirement:

```bash
python -m lessons_learned_repo.history_cli create-requirement --req-code REQ-PROJ-HISTORY-001 --title "Project requirements and execution history tracking" --category-code lessons_learned_repo --description "Create a lightweight SQLite-based project history layer." --status active
```

Record an execution:

```bash
python -m lessons_learned_repo.history_cli record-execution --req-code REQ-PROJ-HISTORY-001 --prompt-file path/to/prompt.txt --summary "Implemented the initial history layer." --impact "Requirement-linked execution history became queryable."
```

Commit and log in one step:

```bash
python -m lessons_learned_repo.history_cli commit-with-history --req-code REQ-PROJ-HISTORY-001 --category-code lessons_learned_repo --commit-message "Add lessons learned repo history layer" --prompt-file path/to/prompt.txt --summary "Committed the lessons learned repo history layer." --impact "Successful repo changes were linked to the requirement history."
```

Create a lesson from one or more execution ids:

```bash
python -m lessons_learned_repo.history_cli create-lesson --lesson-code LESSON-REQ-001 --title "Separate project memory from product runtime" --statement "Project memory and collaboration logging should live outside the patient-facing runtime." --why-it-matters "This keeps operational learning infrastructure from bleeding into live clinic behavior." --execution-ids 1 2 --status validated
```

List lessons with requirement, category, and source execution ids:

```bash
python -m lessons_learned_repo.history_cli list-lessons
```
