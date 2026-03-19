# Project Ops

This folder is the collaboration and execution-ops layer for requirement-linked project history.

It is separate from the live clinic runtime. It does not run through `backend/app/main.py`.

## What It Does

- stores controlled requirement categories
- stores canonical project requirements
- stores execution history records tied to requirements
- provides a CLI trigger entry for logging repo-changing executions

## Trigger Entry

Use:

```bash
python -m project_ops.history_cli commit-with-history ...
```

This is the commit-time trigger for requirement-linked execution logging.

You can also record execution without committing:

```bash
python -m project_ops.history_cli record-execution ...
```

The `commit-with-history` command is the preferred trigger when a successful prompt ends in a repo commit.

## Quick Start

Initialize the database:

```bash
python -m project_ops.history_cli init-db
```

Create a requirement:

```bash
python -m project_ops.history_cli create-requirement --req-code REQ-PROJ-HISTORY-001 --title "Project requirements and execution history tracking" --category-code data --description "Create a lightweight SQLite-based project history layer." --status active
```

Record an execution:

```bash
python -m project_ops.history_cli record-execution --req-code REQ-PROJ-HISTORY-001 --prompt-file path/to/prompt.txt --summary "Implemented the initial project history layer." --impact "Requirement-linked execution history became queryable."
```

Commit and log in one step:

```bash
python -m project_ops.history_cli commit-with-history --req-code REQ-PROJ-HISTORY-001 --category-code data --commit-message "Add project ops history layer" --prompt-file path/to/prompt.txt --summary "Committed the project ops history layer." --impact "Successful repo changes were linked to the requirement history."
```
