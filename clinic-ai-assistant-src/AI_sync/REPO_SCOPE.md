# REPO_SCOPE

## 1. Allowed Scope

The following directories are allowed for read and write operations:

- backend/
- frontend/
- configs/

## 2. Restricted Scope

The following directories and patterns are restricted:

- runtime_traces/
- AI_sync/

The following directories and patterns are forbidden:

- .git/
- *.db

## 3. runtime_traces Access Rules

- Read access is allowed only when explicitly required by the task
- Trace inspection is allowed only for testing, debugging, or verification tasks
- A valid `session_id` or exact file path must be provided
- If `session_id` and exact file path are both missing:
  - The task must be rejected
- No write operations are allowed
- Access must not be inferred from role or general autonomy

## 4. AI_sync Access Rules

Default behavior:

- Read access is allowed

Write access is allowed ONLY when all conditions are met:

- The task explicitly targets `AI_sync`
- The exact file path is provided
- The operation is limited to a single file

Forbidden:

- Modifying multiple `AI_sync` files in a single task
- Self-modifying `REPO_FULL_OVERVIEW.md` without an explicit task
- Expanding `AI_sync` write scope from a general instruction alone

## 5. Global Enforcement Rule

- Codex must never operate outside defined allowed scope
- Codex must not infer permissions
- Codex must not expand task scope
- Any attempt to access restricted areas without explicit permission:
  - The task must be rejected
- Any attempt to access forbidden areas:
  - The task must be rejected

## 6. Validation Requirements

- Scope rules must be enforced before execution
- Access permissions must match task definition exactly
- Restricted-scope exceptions must satisfy their stated conditions before execution
- Violations must trigger immediate rejection
