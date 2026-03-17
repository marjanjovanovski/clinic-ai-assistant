# REPO_FULL_OVERVIEW

## 1. Repository Identity

- repository name: clinic-ai-assistant
- primary purpose: multi-tenant clinic chat assistant with deterministic routing, tenant-driven configuration, booking/contact collection, and control-layer sync artifacts
- primary stack: FastAPI, OpenAI Responses API, Python, SQLite, static HTML/CSS/JS, JSON tenant profiles, dotenv

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
  - exclude `clinic-ai-assistant docs/`
  - exclude `personal-team-touch/`
  - exclude `runtime_traces/`
  - exclude `site-packages/`
  - exclude `__pycache__/`
  - exclude binary artifacts outside included frontend assets
  - exclude cache artifacts
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
  - role/purpose: defines the tasking protocol, execution modes, verification rules, and control-layer workflow
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
  - role/purpose: base tenant profile template with conversation rules, reply texts, and output contract schema
- path: clinic-ai-assistant-src/backend/app/config/profiles/milena_dental.json
  - file type: json
  - layer classification: config
  - role/purpose: primary Macedonian clinic tenant profile with catalog, rules, prompts, and booking configuration
- path: clinic-ai-assistant-src/backend/app/config/profiles/risto.json
  - file type: json
  - layer classification: config
  - role/purpose: sample tenant profile using the same configuration schema as the main clinic profile
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
  - role/purpose: conversation orchestration, deterministic routing, OpenAI fallback, booking state handling, and session flow control
- path: clinic-ai-assistant-src/backend/app/services/config_loader.py
  - file type: python
  - layer classification: service
  - role/purpose: tenant profile loading, validation, and public-config projection
- path: clinic-ai-assistant-src/backend/app/services/lead_store.py
  - file type: python
  - layer classification: service
  - role/purpose: SQLite lead checkpoint initialization, persistence, and checkpoint recovery
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
