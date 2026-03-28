# INFRA - Static Analysis Cleanup 2026-03-28

This task defines the execution-ready cleanup plan for the static analysis bundle generated in `static-code-analysis/CodeAnalysisPython_20260328_1743`.

The purpose of this work is to:
- reduce real security and correctness risk surfaced by Semgrep, Ruff, and CodeQL
- avoid blindly "fixing the scanner" where findings are false positives or acceptable tradeoffs
- keep cleanup token-efficient by grouping work at real engineering boundaries rather than one prompt per file
- preserve current booking, scheduling, chat, and lessons-learned behavior while removing obvious debt
- leave a reusable weekly-analysis workflow that can be resumed without rediscovering the same context

Execution of this task must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Execution Tracking Instructions

Before executing any prompt in this document, the implementing AI agent must first read this file and understand the current status.

Execution of this task must follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).
After each completed prompt, stop, update prompt status in this file, and ask `Commit changes?`
Do not auto-advance to the next prompt.

As soon as a prompt is executed, this file must be updated in two places:
- at the very top of the document in the global status summary
- in the corresponding prompt section header

Status values allowed in this document:
- `Pending`
- `Completed`
- `Blocked`

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-28`

## Task Version

- `Codex V2 - Embedded Findings + Verification Map`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 1`

## Global Status Summary

- Prompt 1 - Pending
- Prompt 2 - Pending
- Prompt 3 - Pending
- Prompt 4 - Pending
- Prompt 5 - Pending
- Prompt 6 - Pending

## Working Rules For The Implementing AI Agent

- Treat the normalized findings in this markdown file as the execution source of truth for this task.
- Use the original analysis bundle only if the user explicitly asks for revalidation against the raw artifacts.
- Do not blindly satisfy every scanner finding if the underlying code is safe and the change would reduce clarity or alter behavior.
- Prefer one prompt per engineering boundary rather than one prompt per file.
- Preserve API contracts, user-facing messages, booking flow state, and scheduling ownership unless a prompt explicitly changes them.
- Keep fixes small and reviewable.
- Reuse existing tests and verification paths before inventing new ones.
- Update this task file immediately after every completed prompt.
- Do not mark a prompt completed unless the requested code and verification work were actually performed.

## Anti-Drift Guardrails

These rules exist to keep future execution accurate without increasing token waste.

### Execution Contract

- Work only from:
  - `Normalized Findings Snapshot`
  - `Fix Strategy Per Finding Cluster`
  - `Verification Map`
  - `Accepted Residual Handling`
- Do not reopen the full report bundle unless:
  - the user explicitly asks
  - the code no longer matches the normalized findings
  - a finding cannot be resolved from the information preserved here

### Scope Control

- Treat each prompt as a bounded patch, not as a general cleanup invitation.
- Do not fix adjacent warnings just because they are nearby unless they are explicitly inside:
  - the current prompt scope
  - the current finding cluster
  - the current verification target
- If a useful extra cleanup is noticed, record it in completion notes instead of silently expanding the patch.

### Decision Order

For each finding touched during execution, decide in this order:
1. Is it explicitly listed in `Fix Now` or `Likely Fix Now`?
2. Does the current code still match the preserved finding description?
3. Is there a small behavior-preserving fix strategy already defined here?
4. If not, should it be left with justification instead of improvised?

### Stop Conditions

Stop and ask `Commit changes?` after a prompt if:
- the prompt goal is completed
- the planned verification for that prompt is completed or honestly blocked
- no additional in-scope findings remain for that prompt boundary

Do not continue because:
- another file looks easy to clean up
- another warning appears nearby
- more context is available than the prompt requires

### Patch Budget

Preferred patch shape per prompt:
- one engineering boundary
- the smallest file set that closes that boundary
- focused verification only for changed behavior

Avoid:
- broad multi-module rewrites
- scanner-driven cleanup across unrelated files
- mixing security fixes, style cleanup, and test rewrites in one patch unless the prompt explicitly groups them

### Drift Check Before Editing

Before changing code in a prompt, confirm all of the following:
- the target file is named in the current prompt or clearly required by the prompt
- the finding is already preserved in this task file
- the intended fix matches the strategy already described here
- the fix can be verified with the mapped verification path

If any answer is no:
- pause
- document the mismatch in the completion note
- do not improvise a broader plan inside the same prompt

## Prompt Input / Output Discipline

This section exists to make prompt execution more deterministic.

### Prompt 1 Input

- only the markdown task file

### Prompt 1 Output

- a concise triage confirmation
- any updates needed to `Fix Now`, `Likely Fix Now`, or `Review Carefully Before Fixing`
- a locked execution order for Prompts 2 to 5

### Prompt 2 Input

- `Fix Now`
- `Likely Fix Now` items that are explicitly approved by Prompt 1
- `Fix Strategy Per Finding Cluster`

### Prompt 2 Output

- only the highest-signal security/correctness patch
- compact note:
  - `Changed`
  - `Verified`
  - `Blocked`
  - `Deferred`

### Prompt 3 Input

- route/test findings preserved in this file

### Prompt 3 Output

- only route-level `B904` and dead-test cleanup
- no unrelated service refactors

### Prompt 4 Input

- low-risk service findings preserved in this file

### Prompt 4 Output

- only low-risk service cleanup or explicit justification for skips

### Prompt 5 Input

- changed files from Prompts 2 to 4
- `Verification Map`
- `Accepted Residual Handling`

### Prompt 5 Output

- focused verification result
- residual-finding summary using the residual reporting format

## Completion Note Format

To keep future runs compact and comparable, each completed prompt should end with only:

- `Changed`
- `Verified`
- `Blocked`
- `Deferred`

If `Deferred` is used, add one short line:
- `Deferred Reason`

## Revalidation Trigger Rules

A future implementing agent may reopen raw reports only if one of these triggers is true:

- the code has changed enough that preserved line references are clearly stale
- a preserved finding cannot be located in the current code
- verification results contradict the preserved finding summary
- the user explicitly requests raw-report revalidation

## Testing And Verification Rules

- Follow repo temp-path rules from `Core_Rules.md`.
- Keep verification residue out of the repository.
- Prefer focused verification for the files touched in the current prompt.
- If a finding is intentionally left unchanged, document why the current code is safer or clearer than the proposed scanner-driven fix.
- Final verification must include a residual repo check and a concise summary of remaining findings, if any.

## Do Not Break

- main chat behavior through `/chat`
- scheduling-first booking and slot-selection flows
- sandbox `/scheduling/book` and `/scheduling/select-slot` behavior
- current lessons-learned repository behavior
- tenant profile loading for valid tenant slugs
- current HTTP status codes and response messages unless a prompt explicitly approves a change

## Current Repo Truth

Authoritative analysis bundle:
- `static-code-analysis/CodeAnalysisPython_20260328_1743/analysis-metadata.txt`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/codeql-results.sarif`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/semgrep-report.txt`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/semgrep-results.sarif`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/semgrep-results.json`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/ruff-report.txt`
- `static-code-analysis/CodeAnalysisPython_20260328_1743/ruff-report.json`

Observed high-signal findings from the current bundle:
- Semgrep:
  - 7 findings total
  - 5 `python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query`
  - 2 `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- Ruff:
  - 40 findings total
  - 34 `B904`
  - 4 `F821`
  - 1 `F841`
  - 1 `SIM103`
- CodeQL:
  - 8 `py/log-injection`
  - 4 `py/path-injection`
  - 3 `py/unreachable-statement`
  - 3 `py/unused-local-variable`
  - 1 `py/stack-trace-exposure`
  - 1 `py/empty-except`

Current likely-real issues:
- dead and unreachable assertions in `backend/tests/integration/test_availability_intent_gating.py`
- route-layer exception chaining debt across `main.py`, `chat.py`, `manual_verification.py`, and `scheduling.py`
- a user-visible error-message leakage path from `booking_credentials.py` into the scheduling route
- at least one SQL composition site in `lessons_learned_repo/history_store.py` that needs careful review

Current likely-mixed / needs-triage findings:
- Semgrep SQL flags in `lead_store.py` and `scheduling_hold_store.py` where some interpolated values appear to be internal constants or schema names
- CodeQL log-injection reports where user-controlled values are logged with `%s` placeholders and may be acceptable after normalization review
- CodeQL path-injection reports where the current code may already rely on tenant-slug conventions but does not enforce them explicitly at the boundary

## Normalized Findings Snapshot

This section is intentionally detailed so future execution can proceed even if the original report files are unavailable.

### Fix Now

1. Dead integration-test tail in `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`
- Source:
  - Ruff `F821`
  - CodeQL `py/unreachable-statement`
- Exact problem:
  - line `359` returns early
  - lines `360` to `362` then reference undefined names `replacement_payload` and `fallback_slot`
- Exact location:
  - `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py:359-362`
- Required handling:
  - restore the intended test setup if those assertions still matter, or remove the obsolete unreachable block
  - do not weaken the surviving test unnecessarily

2. Route-layer exception chaining debt
- Source:
  - Ruff `B904`
- Primary files:
  - `clinic-ai-assistant-src/backend/app/main.py`
  - `clinic-ai-assistant-src/backend/app/routes/chat.py`
  - `clinic-ai-assistant-src/backend/app/routes/manual_verification.py`
  - `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
- Exact problem:
  - repeated `raise HTTPException(...)` inside `except` blocks without explicit chaining
- Exact location groups already observed:
  - `backend/app/main.py:78-80`
  - `backend/app/main.py:89-91`
  - `backend/app/routes/chat.py:44-48`
  - `backend/app/routes/manual_verification.py:31-35`
  - `backend/app/routes/manual_verification.py:43-47`
  - `backend/app/routes/scheduling.py:91-99`
  - `backend/app/routes/scheduling.py:115-123`
- Required handling:
  - use `raise ... from exc` when the caught exception object is available
  - use `raise ... from None` only if suppressing context is clearly better
  - preserve current messages and status codes exactly

3. Scheduling response may expose internal exception text
- Source:
  - CodeQL `py/stack-trace-exposure`
- Flow summary:
  - `clinic-ai-assistant-src/backend/app/services/booking_credentials.py:244-257`
  - `clinic-ai-assistant-src/backend/app/routes/scheduling.py:228-232`
- Exact problem:
  - `confirmation_message = str(exc)` in the booking payload can surface internal exception wording to users
- Exact location:
  - `clinic-ai-assistant-src/backend/app/services/booking_credentials.py:244-257`
  - downstream route response path around `clinic-ai-assistant-src/backend/app/routes/scheduling.py:228-232`
- Required handling:
  - replace raw exception text with a bounded user-safe message if the current path really returns that payload externally
  - preserve recoverable booking semantics

4. Dynamic `IN (...)` SQL composition in `history_store.py`
- Source:
  - Semgrep `python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query`
- File:
  - `clinic-ai-assistant-src/lessons_learned_repo/history_store.py:103-111`
- Exact problem:
  - query uses `WHERE id IN ({placeholders})`
- Exact location:
  - `clinic-ai-assistant-src/lessons_learned_repo/history_store.py:103-111`
- Required handling:
  - keep returned columns and ordering identical
  - use a safe variable-length placeholder pattern
  - handle empty `execution_ids` safely

### Likely Fix Now

5. Service-layer low-risk cleanup in `ai_agent.py`
- Sources:
  - Ruff `SIM103` at `ai_agent.py:664`
  - Ruff `F841` at `ai_agent.py:2211`
  - CodeQL `py/empty-except` at `ai_agent.py:975`
  - CodeQL `py/unused-local-variable`
- Exact location groups already observed:
  - `clinic-ai-assistant-src/backend/app/services/ai_agent.py:664-665`
  - `clinic-ai-assistant-src/backend/app/services/ai_agent.py:975-976`
  - `clinic-ai-assistant-src/backend/app/services/ai_agent.py:2211`
- Required handling:
  - fix only where behavior is unchanged
  - if the unused-variable call has side effects, keep the call and discard only the value
  - if the empty except should remain, document why

6. Additional low-risk `B904` in provider/service modules
- Sources:
  - Ruff `B904`
- Files likely involved:
  - `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
  - `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`
- Exact location groups already observed:
  - `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py:235`
- Required handling:
  - keep minimal and behavior-preserving

### Review Carefully Before Fixing

7. `lead_store.py` SQL warning at `PRAGMA table_info({table_name})`
- Sources:
  - Semgrep `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
  - Semgrep `python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query`
- File:
  - `clinic-ai-assistant-src/backend/app/services/lead_store.py:34`
- Review note:
  - if `table_name` is already constrained to an internal allowlist, document that and optionally harden the identifier boundary
  - do not force an unnatural rewrite if SQLite cannot parameterize the identifier directly

8. `scheduling_hold_store.py` SQL warnings
- Sources:
  - Semgrep `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
  - Semgrep `python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query`
- File clusters:
  - `clinic-ai-assistant-src/backend/app/services/scheduling_hold_store.py:53-75`
  - `clinic-ai-assistant-src/backend/app/services/scheduling_hold_store.py:97-111`
  - `clinic-ai-assistant-src/backend/app/services/scheduling_hold_store.py:117-126`
- Review note:
  - some interpolated values are internal status constants, not obvious user input
  - fix if a clearer parameter-bound version exists without harming readability
  - otherwise document why the remaining pattern is safe enough

9. `config_loader.py` path-injection findings
- Source:
  - CodeQL `py/path-injection`
- File:
  - `clinic-ai-assistant-src/backend/app/services/config_loader.py:243-245`
- Review note:
  - `profile_path = PROFILES_DIR / f"{tenant}.json"`
  - if tenant slugs are not explicitly validated at this boundary, add small validation
  - if upstream guarantees are already strict, document them

10. Log-injection findings
- Source:
  - CodeQL `py/log-injection`
- Count:
  - `8`
- Representative files:
  - `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
  - `clinic-ai-assistant-src/backend/app/services/lead_store.py:298-303`
- Review note:
  - `%s`-style structured logging is safer than string concatenation
  - only change these if the logged user data needs normalization or redaction, not just because the scanner flagged taint flow

## Execution Order Baseline

Recommended order for this task version:
1. fix the dead test and route-layer `B904` cluster
2. fix the `history_store.py` dynamic `IN (...)` query
3. review and tighten the scheduling exception-text exposure path
4. handle low-risk `ai_agent.py` and provider cleanup
5. evaluate `lead_store.py`, `scheduling_hold_store.py`, `config_loader.py`, and CodeQL log/path findings case by case
6. verify and document what remains intentionally deferred

## Fix Strategy Per Finding Cluster

This section is the execution playbook for the current finding set. Future implementing agents should prefer these strategies unless the code has materially changed.

### Cluster A - Dead test tail and unreachable assertions

- Primary file:
  - `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`
- Strategy:
  - first inspect whether the post-`return` assertions describe an intended second-stage behavior that was accidentally cut off
  - if no missing setup exists, remove the unreachable assertions as obsolete dead code
  - if the assertions still matter, restore the missing setup instead of weakening the test
- Avoid:
  - deleting useful earlier assertions
  - changing production code just to satisfy the test scanner finding

### Cluster B - Route-layer `B904`

- Primary files:
  - `backend/app/main.py`
  - `backend/app/routes/chat.py`
  - `backend/app/routes/manual_verification.py`
  - `backend/app/routes/scheduling.py`
- Strategy:
  - convert each `except` block to explicit exception chaining
  - bind the caught exception only where needed for `raise ... from exc`
  - preserve response payloads, status codes, and control flow exactly
- Avoid:
  - message rewrites
  - broader route refactors

### Cluster C - `history_store.py` variable-length `IN (...)`

- Primary file:
  - `clinic-ai-assistant-src/lessons_learned_repo/history_store.py`
- Strategy:
  - keep sqlite3-compatible placeholder expansion
  - build placeholders from count, not from values
  - short-circuit safely on empty id list if needed
  - preserve selected columns and ordering
- Avoid:
  - introducing ORM abstractions
  - changing return shape

### Cluster D - Scheduling exception-text exposure

- Primary files:
  - `backend/app/services/booking_credentials.py`
  - `backend/app/routes/scheduling.py`
- Strategy:
  - verify whether `confirmation_message` from caught exceptions reaches external clients
  - if yes, replace raw exception text with a stable user-safe message
  - preserve machine-readable status/reason handling
- Avoid:
  - hiding genuinely useful user recovery guidance
  - rewriting unrelated scheduling payload fields

### Cluster E - `ai_agent.py` low-risk cleanup

- Primary file:
  - `backend/app/services/ai_agent.py`
- Strategy:
  - keep side-effectful calls even if their assigned value is unused
  - simplify boolean return only if readability stays equal or better
  - convert empty except to either explicit fallback documentation or a narrow handled branch if safe
- Avoid:
  - changing booking-flow orchestration behavior
  - deleting calls whose result is unused but whose execution matters

### Cluster F - Mixed SQL/path/log findings

- Primary files:
  - `backend/app/services/lead_store.py`
  - `backend/app/services/scheduling_hold_store.py`
  - `backend/app/services/config_loader.py`
  - selected logging sites in `ai_agent.py` and `lead_store.py`
- Strategy:
  - only fix if there is a clear, behavior-preserving safety improvement
  - otherwise document the trust boundary, internal constant, allowlist, or structured-logging property that makes the current code acceptable
- Avoid:
  - cargo-cult rewrites driven only by scanner wording
  - replacing readable sqlite3 code with heavier abstractions unless it truly improves safety

## Verification Map

This section is intended to remove future verification guesswork and reduce weekly usage.

### Prompt 2 Verification Map

If Prompt 2 touches:
- `lessons_learned_repo/history_store.py`
  - preferred verification:
    - focused `test_history_store.py` run from the correct import root
    - recommended command pattern:
      - `$env:PYTHONPATH='F:\\IT Projects\\clinic-ai-assistant\\clinic-ai-assistant-src'; clinic-ai-assistant-src\\backend\\.venv\\Scripts\\python.exe -m pytest clinic-ai-assistant-src\\lessons_learned_repo\\tests\\test_history_store.py -q --basetemp="<external temp path>"`
    - a targeted readback of the affected query path if environment limits block pytest
- `booking_credentials.py` or `routes/scheduling.py`
  - preferred verification:
    - focused scheduling and booking-flow tests
    - confirm user-facing payload message remains stable and recoverable
    - recommended command pattern:
      - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_scheduling_api.py .\\tests\\integration\\test_req_booking_flow.py -q --basetemp="<external temp path>"`
- `config_loader.py`
  - preferred verification:
    - focused config-loader or route tests that exercise tenant loading
    - recommended command pattern:
      - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_req_booking_flow.py -q --basetemp="<external temp path>"`

### Prompt 3 Verification Map

If Prompt 3 touches:
- `test_availability_intent_gating.py`
  - preferred verification:
    - focused run of `test_availability_intent_gating.py`
    - recommended command pattern:
      - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\integration\\test_availability_intent_gating.py -q --basetemp="<external temp path>"`
- route-layer `B904` files
  - preferred verification:
    - targeted Ruff check on the touched route files
    - optionally relevant route/integration tests if already cheap to run
    - recommended command pattern:
      - `.\\.venv\\Scripts\\ruff.exe check clinic-ai-assistant-src\\backend\\app\\main.py clinic-ai-assistant-src\\backend\\app\\routes\\chat.py clinic-ai-assistant-src\\backend\\app\\routes\\manual_verification.py clinic-ai-assistant-src\\backend\\app\\routes\\scheduling.py`

### Prompt 4 Verification Map

If Prompt 4 touches:
- `ai_agent.py`
  - preferred verification:
    - focused unit/integration tests already covering booking and chat orchestration
    - recommended command pattern:
      - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\unit\\test_ai_agent_helpers.py .\\tests\\integration\\test_req_booking_flow.py -q --basetemp="<external temp path>"`
- `google_calendar.py`
  - preferred verification:
    - focused provider tests
    - recommended command pattern:
      - `.\\.venv\\Scripts\\python.exe -m pytest .\\tests\\unit\\test_google_calendar_provider.py -q --basetemp="<external temp path>"`

### Prompt 5 Verification Commands Baseline

Use the smallest relevant verification set based on changed files. Prefer these command patterns:

- backend focused pytest:
  - `.\\.venv\\Scripts\\python.exe -m pytest <targeted tests> -q --basetemp="<external temp path>"`
- lessons-learned focused pytest:
  - use the backend virtualenv Python
  - ensure `PYTHONPATH` points at `clinic-ai-assistant-src` if needed
- focused Ruff:
  - `.\\.venv\\Scripts\\ruff.exe check <touched paths>`

## Prompt-Specific Do Not Edit Lists

These lists exist to reduce accidental scope expansion.

### Prompt 2 - Do Not Edit

- route-layer `B904` files unless strictly required for the scheduling exception-text path
- unrelated tests
- frontend files
- analysis tooling scripts

### Prompt 3 - Do Not Edit

- SQL query construction files unless a route/test fix absolutely depends on them
- `ai_agent.py` service logic
- lessons-learned repo files

### Prompt 4 - Do Not Edit

- route-layer files already handled in Prompt 3
- test files unless a low-risk service cleanup requires a small focused update
- SQL/security-query files already handled or intentionally deferred in Prompt 2

Verification selection rule:
- do not rerun the entire analysis stack just to verify a narrow code patch
- rerun full static analysis only if the user explicitly wants a refreshed bundle after implementation

## Accepted Residual Handling

This section defines how to treat findings that may remain after implementation.

### Acceptable Residual Categories

1. Structured logging taint-flow findings
- acceptable to leave if:
  - logging uses `%s` placeholders
  - values are not being concatenated into executable contexts
  - there is no clear user-visible or exploit-prone impact

2. SQLite identifier construction findings
- acceptable to leave if:
  - the identifier is constrained to internal names or a small allowlist
  - SQLite does not support cleaner parameterization for that fragment
  - the file documents or enforces the constraint clearly

3. Path findings at trusted tenant boundaries
- acceptable to leave if:
  - the tenant value is explicitly validated
  - or upstream guarantees are clearly documented and enforced close to the boundary

### Not Acceptable To Leave Without Justification

- dead tests or unreachable assertions
- raw exception text exposure to users
- dynamic SQL with user-influenced values and no clear boundary
- remaining `B904` in files touched by the current prompt without an explicit reason

### Residual Reporting Format

When a finding remains, report it in one compact line:
- `Finding`
- `Reason Left`
- `Why Safe / Deferred`
- `Revisit Trigger`

## Task Evolution Record

This section exists so future prompt-comparison discussions can compare Codex-authored versions without reintroducing the earlier GPT draft as the baseline.

### Version Comparison Baseline

| Version | Description | Report dependence during execution | Intended weekly usage profile |
|---|---|---|---|
| `Codex V0` | first Codex master task, boundary-based but still report-dependent | one full reread plus targeted spot-checks | moderate |
| `Codex V1` | current task with embedded normalized findings | no full report reread expected during execution | lower and more predictable |
| `Codex V2` | current task with embedded findings, fix strategy, verification map, and residual policy | execution should not require full report reread or fresh verification planning | lowest and most predictable |

Rule for future comparisons:
- compare future revisions against `Codex V0` and `Codex V1`
- compare future revisions against `Codex V0`, `Codex V1`, and `Codex V2`
- do not use the earlier GPT draft as the official comparison baseline
- if a future version is created, append it here as `Codex V2`, `Codex V3`, and so on

## Why This Task Exists

The initial GPT task draft was directionally useful but not optimal for this repo:
- it over-split work into one prompt per file
- it treated all SQL/security findings as equally actionable
- it underused the actual CodeQL bundle
- it would spend extra tokens re-reading the same context repeatedly

This task replaces that with a higher-signal workflow:
- first separate real issues from scanner noise
- then implement security-sensitive fixes
- then batch the low-risk Ruff and CodeQL cleanup
- then verify the updated finding set

## Architecture Guidance

- Security-sensitive query changes should be reviewed in terms of actual taint reachability, not just scanner wording.
- Route-layer `B904` work is mechanical and should stay narrow.
- Tests should be corrected rather than weakened when a scanner exposed dead code.
- If a path- or log-related finding is left in place, document the specific boundary or normalization that makes it acceptable.
- Prefer preserving readable SQLite code over forcing ORM-style abstractions into modules that currently use `sqlite3` directly.

## Prompt 1 - Pending

### Goal

Confirm the exact actionable subset of the normalized findings before code changes begin.

### Instructions

Review the normalized findings in this markdown file and map them into:
- must-fix now
- likely-fix now
- acceptable-to-defer or likely-false-positive

Requirements:
- review the normalized Semgrep, Ruff, and CodeQL findings together
- identify the smallest safe fix surface for each real issue cluster
- identify any findings that should not be fixed blindly
- record the implementation order for the remaining prompts

### Required Outcome

The task has a repo-specific finding triage and a justified execution order instead of a raw scanner dump.

## Prompt 2 - Pending

### Goal

Fix the highest-signal security and correctness issues from the normalized findings snapshot.

### Instructions

Implement the security-sensitive corrections that are worth fixing immediately.

Scope:
- `clinic-ai-assistant-src/backend/app/services/lead_store.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_hold_store.py`
- `clinic-ai-assistant-src/lessons_learned_repo/history_store.py`
- `clinic-ai-assistant-src/backend/app/services/booking_credentials.py`
- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`
- `clinic-ai-assistant-src/backend/app/services/config_loader.py` only if explicit tenant-path hardening is justified

Requirements:
- use the `Normalized Findings Snapshot` in this file as the execution reference instead of rereading the raw reports
- review each SQL finding and fix only the ones where the safer pattern is clear and behavior-preserving
- for `history_store.py`, use a safe variable-length `IN` strategy
- prevent leaking raw internal exception text to external users if the current scheduling path exposes it
- if `config_loader.py` path hardening is needed, keep it compatible with valid existing tenant names
- document any scanner finding intentionally left unchanged and why

### Required Outcome

The most credible security and externally visible correctness issues are fixed without cargo-cult rewrites.

## Prompt 3 - Pending

### Goal

Clean up the dead-code and route-level correctness findings with minimal behavior change.

### Instructions

Apply the high-confidence non-security cleanup surfaced by Ruff and CodeQL.

Scope:
- `clinic-ai-assistant-src/backend/tests/integration/test_availability_intent_gating.py`
- `clinic-ai-assistant-src/backend/app/main.py`
- `clinic-ai-assistant-src/backend/app/routes/chat.py`
- `clinic-ai-assistant-src/backend/app/routes/manual_verification.py`
- `clinic-ai-assistant-src/backend/app/routes/scheduling.py`

Requirements:
- remove or restore the dead/unreachable assertions in `test_availability_intent_gating.py` so the test remains meaningful
- fix `B904` findings in the route-layer files using explicit exception chaining
- preserve current HTTP status codes and messages exactly
- do not broaden the patch into unrelated refactoring

### Required Outcome

The dead test code and the route-layer exception-chaining debt are cleaned up with a narrow, safe diff.

## Prompt 4 - Pending

### Goal

Handle the remaining service-layer low-risk cleanup identified by Ruff and CodeQL.

### Instructions

Address the remaining clearly safe issues in service modules.

Scope:
- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling/providers/google_calendar.py`
- `clinic-ai-assistant-src/backend/app/services/config_loader.py`
- any other file only if it is directly required by a currently-open finding from the same bundle

Requirements:
- fix `SIM103`, `F841`, `B904`, unused-local, and empty-except style findings only where behavior remains identical
- do not remove side-effectful calls just to silence a warning
- review CodeQL log-injection findings and either mitigate them or document why `%s`-style structured logging is acceptable at that site
- keep changes small and easy to verify

### Required Outcome

The remaining low-risk service-layer findings are either fixed or explicitly justified.

## Prompt 5 - Pending

### Goal

Perform a focused post-fix verification pass against the touched analysis surfaces.

### Instructions

Run the smallest verification set that proves the fixes are correct and identifies what remains.

Requirements:
- use the `Verification Map` in this file first instead of rediscovering commands from scratch
- run focused tests for touched backend and lessons-learned modules as appropriate
- rerun the most relevant lint or analysis commands where practical
- report which original findings are gone
- report which findings remain and whether they are accepted, deferred, or need another prompt
- classify remaining findings using `Accepted Residual Handling`
- perform a repo residual check and document any leftover temp paths if cleanup is blocked

### Required Outcome

The cleanup is technically verified and the new residual finding set is clear.

## Prompt 6 - Pending

### Goal

Track manual verification and merge readiness for this cleanup workstream.

### Instructions

Keep this prompt pending until the user confirms the branch is reviewed and ready.

Requirements:
- record any manual review the user performs on the branch
- record whether the user approves merge readiness
- keep `Merge To Main` pending until the branch is actually merged
- if verification reveals new cleanup work, continue in this same task rather than creating a fragmented prompt chain unless the user asks otherwise

### Required Outcome

Manual verification and merge readiness are tracked explicitly before the task leaves `ProjectTasks_Pending`.

---

## Archival Appendix - Do Not Extend Into More Prompts

### Why This Prompt Set Is Better Than The Initial GPT Draft

- It uses one official master task file per workstream, matching repo rules.
- It groups work by engineering boundary rather than by single file, which reduces token reuse and context reload.
- It incorporates the actual CodeQL findings instead of only Semgrep and Ruff.
- It distinguishes must-fix findings from likely false positives.
- It preserves room for "leave unchanged, with justification" when the scanner is overly aggressive.
- It now embeds the likely fix strategy and the verification map, which further reduces execution-time planning cost.

### Expected Weekly Use

For future weekly scans:
1. generate a new `CodeAnalysisPython_<timestamp>` bundle
2. update `Current Repo Truth`, `Normalized Findings Snapshot`, and `Task Evolution Record`
3. execute from `Prompt 1`
4. keep manual verification and merge readiness as the final tracked prompt
