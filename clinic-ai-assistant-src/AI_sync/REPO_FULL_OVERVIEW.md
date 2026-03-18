# REPO_FULL_OVERVIEW

## 1. Repository Identity

- repository name: clinic-ai-assistant
- primary purpose: multi-tenant clinic chat assistant with deterministic routing, tenant-driven configuration, booking/contact collection, and control-layer sync artifacts
- primary stack: FastAPI, OpenAI Responses API, Python, SQLite, static HTML/CSS/JS, JSON tenant profiles, dotenv
- current sync status: deterministic task execution framework active in `clinic-ai-assistant-src/AI_sync/`
- current control-layer identity: AI Execution Protocol Layer complete for task atomicity, identity, session discipline, lifecycle control, context isolation, and backend configuration separation

## 2. Included Scope

- inclusion rules:
  - include `README.md`
  - include files under `clinic-ai-assistant-src/AI_sync/`
  - include files under `clinic-ai-assistant-src/backend/`
  - include files under `clinic-ai-assistant-src/configs/`
  - include files under `clinic-ai-assistant-src/frontend/`
- exclusion rules:
  - exclude `*.db`
  - exclude `.git/`
  - exclude `.venv/`
  - exclude `__pycache__/`
  - exclude binary artifacts outside included frontend assets
  - exclude cache artifacts
  - exclude `clinic-ai-assistant docs/`
  - exclude `personal-team-touch/`
  - exclude `runtime_traces/`
  - exclude `site-packages/`
  - exclude top-level ad hoc artifacts not covered by inclusion rules

## 3. Folder Structure

```text
.
|-- README.md
`-- clinic-ai-assistant-src/
    |-- AI_sync/
    |   |-- ARTIFACT_RULES.md
    |   |-- FAILURE_PROTOCOL.md
    |   |-- OUTPUT_RULES.md
    |   |-- PARALLEL_SCAN_TEMPLATE.md
    |   |-- PROMPT_PROTOCOL.md
    |   |-- REPO_FULL_OVERVIEW.md
    |   `-- REPO_SCOPE.md
    |-- backend/
    |   |-- app/
    |   |   |-- config/
    |   |   |   `-- profiles/
    |   |   |       |-- generic.json
    |   |   |       |-- milena_dental.json
    |   |   |       `-- risto.json
    |   |   |-- main.py
    |   |   |-- routes/
    |   |   |   `-- chat.py
    |   |   `-- services/
    |   |       |-- ai_agent.py
    |   |       |-- config_loader.py
    |   |       |-- lead_store.py
    |   |       `-- session_trace_logger.py
    |   |-- requirements.txt
    |   `-- tests/
    |       |-- test_chat_flow.py
    |       `-- test_config_loader.py
    |-- configs/
    |   `-- settings.env
    `-- frontend/
        |-- favicon-16x16.png
        |-- favicon-32x32.png
        |-- favicon.ico
        `-- index.html
```

## 4. File Index

- path: README.md
  - file type: markdown
  - layer classification: other included infrastructure
  - role/purpose: root project status document and architecture rule reference
- path: clinic-ai-assistant-src/AI_sync/ARTIFACT_RULES.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines mandatory returned artifacts, path formatting rules, and artifact validation requirements
- path: clinic-ai-assistant-src/AI_sync/FAILURE_PROTOCOL.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines deterministic failure types, mandatory failure actions, and next allowed prompt type
- path: clinic-ai-assistant-src/AI_sync/OUTPUT_RULES.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines deterministic output path rules, terminal output limits, and folder creation behavior
- path: clinic-ai-assistant-src/AI_sync/PARALLEL_SCAN_TEMPLATE.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines controlled read-only parallel scan use cases, agent split, and merged output structure
- path: clinic-ai-assistant-src/AI_sync/PROMPT_PROTOCOL.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines the deterministic AI Execution Protocol Layer including prompt size control, task naming, session discipline, task state machine, execution context isolation, and backend configuration separation
- path: clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: deterministic full repository state overview and single sync source of truth
- path: clinic-ai-assistant-src/AI_sync/REPO_SCOPE.md
  - file type: markdown
  - layer classification: sync artifact
  - role/purpose: defines allowed scope, restricted areas, forbidden areas, and controlled repository access rules
- path: clinic-ai-assistant-src/backend/app/config/profiles/generic.json
  - file type: json
  - layer classification: config
  - role/purpose: base tenant profile template with conversation rules, reply texts, output contract schema, and shared conversation behavior structure
- path: clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json
  - file type: json
  - layer classification: config
  - role/purpose: primary Macedonian clinic tenant profile with catalog, rules, profile-driven conversation behavior, refined booking/contact wording, and active clinic flow configuration
- path: clinic-ai-assistant-src/backend/app/config/profiles/risto.json
  - file type: json
  - layer classification: config
  - role/purpose: sample tenant profile using the same configuration schema as the main clinic profile, including behavior/config separation support
- path: clinic-ai-assistant-src/backend/app/main.py
  - file type: python
  - layer classification: other included infrastructure
  - role/purpose: application bootstrap, environment loading, CORS setup, route registration, frontend serving, and config endpoints
- path: clinic-ai-assistant-src/backend/app/routes/chat.py
  - file type: python
  - layer classification: route
  - role/purpose: chat HTTP endpoint, request validation, and response envelope assembly
- path: clinic-ai-assistant-src/backend/app/services/ai_agent.py
  - file type: python
  - layer classification: service
  - role/purpose: conversation orchestration, deterministic routing, OpenAI fallback, booking state handling, bounded context carry, clarification recovery, and session flow control using JSON-driven behavior configuration
- path: clinic-ai-assistant-src/backend/app/services/config_loader.py
  - file type: python
  - layer classification: service
  - role/purpose: tenant profile loading, validation, and public-config projection
- path: clinic-ai-assistant-src/backend/app/services/lead_store.py
  - file type: python
  - layer classification: service
  - role/purpose: SQLite lead checkpoint initialization, verified persistence, exact-row readback, and checkpoint recovery using tenant/session identity
- path: clinic-ai-assistant-src/backend/app/services/session_trace_logger.py
  - file type: python
  - layer classification: service
  - role/purpose: optional session trace writing controlled by settings flags
- path: clinic-ai-assistant-src/backend/requirements.txt
  - file type: text
  - layer classification: other included infrastructure
  - role/purpose: backend runtime and test dependency list
- path: clinic-ai-assistant-src/backend/tests/test_chat_flow.py
  - file type: python
  - layer classification: test
  - role/purpose: integration-style tests for chat validation, booking transitions, and contact collection flow
- path: clinic-ai-assistant-src/backend/tests/test_config_loader.py
  - file type: python
  - layer classification: test
  - role/purpose: tests for tenant config loading and public config exposure boundaries
- path: clinic-ai-assistant-src/configs/settings.env
  - file type: env
  - layer classification: config
  - role/purpose: runtime trace toggle settings for session trace logging
- path: clinic-ai-assistant-src/frontend/favicon-16x16.png
  - file type: image
  - layer classification: frontend
  - role/purpose: small browser icon asset for the frontend
- path: clinic-ai-assistant-src/frontend/favicon-32x32.png
  - file type: image
  - layer classification: frontend
  - role/purpose: standard browser icon asset for the frontend
- path: clinic-ai-assistant-src/frontend/favicon.ico
  - file type: image
  - layer classification: frontend
  - role/purpose: default favicon asset served with the frontend
- path: clinic-ai-assistant-src/frontend/index.html
  - file type: html
  - layer classification: frontend
  - role/purpose: single-page chat client, tenant config loader, session persistence layer, and structured message renderer

## 5. Architectural Layer Mapping

- route:
  - clinic-ai-assistant-src/backend/app/routes/chat.py
- service:
  - clinic-ai-assistant-src/backend/app/services/ai_agent.py
  - clinic-ai-assistant-src/backend/app/services/config_loader.py
  - clinic-ai-assistant-src/backend/app/services/lead_store.py
  - clinic-ai-assistant-src/backend/app/services/session_trace_logger.py
- config:
  - clinic-ai-assistant-src/backend/app/config/profiles/generic.json
  - clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json
  - clinic-ai-assistant-src/backend/app/config/profiles/risto.json
  - clinic-ai-assistant-src/configs/settings.env
- frontend:
  - clinic-ai-assistant-src/frontend/favicon-16x16.png
  - clinic-ai-assistant-src/frontend/favicon-32x32.png
  - clinic-ai-assistant-src/frontend/favicon.ico
  - clinic-ai-assistant-src/frontend/index.html
- test:
  - clinic-ai-assistant-src/backend/tests/test_chat_flow.py
  - clinic-ai-assistant-src/backend/tests/test_config_loader.py
- sync artifact:
  - clinic-ai-assistant-src/AI_sync/ARTIFACT_RULES.md
  - clinic-ai-assistant-src/AI_sync/FAILURE_PROTOCOL.md
  - clinic-ai-assistant-src/AI_sync/OUTPUT_RULES.md
  - clinic-ai-assistant-src/AI_sync/PARALLEL_SCAN_TEMPLATE.md
  - clinic-ai-assistant-src/AI_sync/PROMPT_PROTOCOL.md
  - clinic-ai-assistant-src/AI_sync/REPO_FULL_OVERVIEW.md
  - clinic-ai-assistant-src/AI_sync/REPO_SCOPE.md
- other included infrastructure:
  - README.md
  - clinic-ai-assistant-src/backend/app/main.py
  - clinic-ai-assistant-src/backend/requirements.txt

## 6. Notes on Deterministic Generation

- this file is full-regeneration only
- patch-style sync is not allowed

## 7. AI_sync Control-Layer Status

- the AI_sync folder is no longer only a prompting aid
- it now functions as a deterministic task execution framework for repository work
- the active control-layer center is `clinic-ai-assistant-src/AI_sync/PROMPT_PROTOCOL.md`
- the current protocol stack includes:
  - Prompt Size Control Protocol
  - Task Naming Convention Protocol
  - Session Discipline Protocol
  - Task State Machine Protocol
  - Execution Context Isolation Protocol
  - Backend Configuration Separation Protocol
- practical meaning:
  - every task must be atomic
  - every task must have deterministic identity
  - every task must follow explicit session and lifecycle rules
  - no task may rely on hidden context
  - backend configuration content must not be added to Python files

## 8. Architecture Rules Currently In Force

- tenant profile JSON under `clinic-ai-assistant-src/backend/app/config/profiles/` is the approved source for conversational/configuration content
- Python is reserved for:
  - logic
  - routing
  - state machine behavior
  - orchestration
- Python must not become the source of:
  - reply wording
  - trigger phrases
  - behavior instructions
  - booking/contact prompts
  - assistant tone/style wording
  - stage or flow wording intended for model behavior

## 9. Backend State Snapshot

- `ai_agent.py` currently implements:
  - deterministic booking-state handling
  - bounded recent-context carry
  - catalog/service-list routing
  - explicit booking-confirm gating
  - lightweight contact value plausibility checks
  - clarification recovery that distinguishes booking-scope confusion from field-level clarification
  - ownership clarification continuity for name/phone/email during active booking
  - active booking flow lock during `collecting_contact`
  - forward-only contact collection with one active field at a time
  - combined contact parsing only as a secondary path for explicit bundled input
  - persistence-gated booking completion
  - recovery that prefers persisted booking truth over stale in-memory contact state
- `lead_store.py` currently implements:
  - checkpoint save attempts with exact `tenant + session_id` row verification after commit
  - required-field-aware persistence success evaluation
  - structured persistence result reporting back to `ai_agent.py`
  - checkpoint hydration from both saved JSON state and persisted contact columns
- tenant profile JSON currently owns:
  - conversation behavior configuration
  - booking/contact wording
  - clarification reply text
  - service/pricing/catalog phrasing
- `milena_dental.json` currently reflects:
  - stepwise booking contact intro wording
  - natural Macedonian field prompts and clarification replies
  - current live receptionist-style behavior for the main tenant
- `milena_dental.json` is the most actively refined tenant profile and should be treated as the primary live reference for current Macedonian behavior

## 10. Recent Completed Development

- completed the deterministic AI Execution Protocol Layer in `AI_sync`
- formalized backend configuration separation so config content stays in tenant JSON instead of Python
- moved conversation behavior and booking/contact phrasing into tenant profile configuration
- refined `milena_dental.json` contact collection wording for clearer natural Macedonian
- removed clarification reply duplication in contact collection wording
- aligned booking contact intro wording with stepwise collection from the name field first
- tightened booking progression so explicit configured confirmation is required before contact collection starts
- improved booking clarification recovery so confusion about what is being booked no longer collapses into repeated field prompts
- hardened contact input gating so filler and meta replies do not advance booking fields
- hardened phone-field validation and clarification recovery
- stabilized booking checkpoint continuity and forward-only field progression
- kept ownership-style clarification inside the active booking field flow
- added active booking flow lock so `collecting_contact` does not drift into greeting or unrelated informational routing
- enforced verified persistence before booking confirmation
- limited combined contact parsing to explicit bundled input as a secondary convenience path
- hardened persistence authority so only required fields determine save success and persisted DB truth is authoritative during recovery

## 11. Current Stability / Likely Next Testing Focus

- currently stable areas:
  - booking confirmation requires explicit booking confirmation input
  - active booking stays inside booking flow during contact collection
  - contact collection is stepwise by default
  - combined input is convenience-only and no longer the primary path
  - booking completion depends on verified persistence, not only in-memory state
  - recovery prefers persisted checkpoint/database truth for saved contact fields
- likely future testing focus:
  - full end-to-end booking verification against real DB rows during live chat
  - repeated interruption/resume behavior across the same `session_id`
  - tenant-by-tenant behavior parity outside `milena_dental.json`

## 12. Sync Note For Collaborators

- if a collaborator drifted before these updates, they may still think AI_sync is only a prompt-rules folder
- that is no longer accurate
- the correct current framing is:
  - AI_sync = deterministic AI Execution Protocol Layer
  - `PROMPT_PROTOCOL.md` = active execution contract
  - tenant profile JSON = approved home for conversational/configuration content
  - `ai_agent.py` = logic/orchestration, validation, flow control, and persistence-gating layer only
  - `lead_store.py` = verified persistence and checkpoint recovery layer
