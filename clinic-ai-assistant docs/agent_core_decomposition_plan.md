# Agent Core Decomposition Plan

## Goal

Decompose `clinic-ai-assistant-src/backend/app/services/ai_agent.py` into isolated backend capability modules without changing current runtime behavior during the extraction phases.

This plan is intentionally narrow. It covers only:

- conversation/session state
- booking-credentials capability
- scheduling capability
- orchestration layer

It does not cover broader frontend redesign, speculative future capabilities, or a generic plugin engine.

## Current Repo Truth

- `ai_agent.py` is the current orchestration hotspot for chat flow, booking progression, session state, persistence coordination, and OpenAI fallback.
- booking currently has one dominant backend stage model:
  - `awaiting_booking_confirmation`
  - `collecting_contact`
  - `completed`
- scheduling is already isolated under `backend/app/services/scheduling/` with its own models, factory, service entry points, and providers.
- `/chat` remains the main runtime entrypoint for the production flow.
- `/scheduling/*` remains intentionally separate from the current booking/chat flow.
- current tests already protect:
  - booking confirmation and contact collection behavior
  - edit/recovery behavior
  - persisted-completion rules
  - current frontend booking widget shell
  - isolated scheduling API behavior

## Target Boundaries

### 1. Conversation / Session State

Owns:

- session key generation and normalization
- in-memory session and interaction history access
- state hydration/merge from persistence
- session status projection for `/chat`

Must not own:

- booking-specific field logic
- scheduling-specific rules
- provider calls

### 2. Booking-Credentials Capability

Owns:

- booking confirmation gate handoff
- name / phone / email collection
- clarification and retry rules for these fields
- completed-booking edit flow
- booking progress and summary payload generation, if still tightly coupled

Must not own:

- general greeting / service catalog routing
- scheduling provider interaction
- OpenAI transport setup

### 3. Scheduling Capability

Owns:

- existing isolated scheduling subsystem
- availability lookup
- booking action through scheduling service boundary

Must remain:

- separate from booking-credentials internals
- callable by orchestration instead of directly coupled into booking logic

### 4. Orchestration Layer

Owns:

- deciding which capability handles the next step
- preserving current flow order until an explicit later task changes behavior
- combining capability output into the current `/chat` response shape

Must not own:

- detailed booking field rules
- provider-specific scheduling code
- tenant wording/content beyond reading config-backed outputs

## Safe Extraction Principle

Refactor in this order:

1. move neutral helpers first
2. move booking logic second
3. thin `ai_agent.py` into orchestration third
4. introduce scheduling as a first-class orchestrated capability only after extraction is stable
5. add minimal config-driven coexistence rules last

This order keeps current behavior stable while reducing future split cost.

## Task Board

### Task 01

- Title: Add decomposition plan and fixed target boundaries
- Status: `completed`
- Scope:
  - define the narrow architecture plan
  - define reset-safe extraction phases
- Done when:
  - this document exists
  - no runtime code behavior changes were made

### Task 02

- Title: Extract shared conversation/session state helpers
- Status: `completed`
- Scope:
  - create a dedicated backend module for shared state helpers
  - move session normalization, key generation, state hydration helpers, and related neutral constants
- Guardrails:
  - no behavior changes
  - no booking logic changes
- Manual test after task:
  - greeting/basic chat still works
  - booking still starts and continues normally

### Task 03

- Title: Extract booking-credentials capability
- Status: `completed`
- Scope:
  - create a dedicated backend module for booking confirmation + contact collection behavior
  - move edit/retry/recovery logic for name, phone, and email
- Guardrails:
  - keep current stage names and current `/chat` response shape unless internal-only changes are clearly safe
  - do not integrate scheduling yet
- Manual test after task:
  - service suggestion -> booking confirmation -> name -> phone -> email
  - clarification handling during collection
  - completed-state edit flow

### Task 04

- Title: Thin `ai_agent.py` into orchestration-first flow
- Status: `completed`
- Scope:
  - define a small internal contract between orchestrator and capability modules
  - route booking behavior through the extracted booking-credentials module
- Guardrails:
  - no intentional user-visible flow changes
  - no scheduling-first behavior yet
- Manual test after task:
  - repeat normal chat tests
  - confirm `/chat` response shape is unchanged

### Task 05

- Title: Add scheduling capability bridge for orchestration
- Status: `completed`
- Scope:
  - define how orchestration can invoke scheduling as a capability
  - preserve isolated scheduling runtime and sandbox behavior
- Guardrails:
  - no main chat behavior changes yet
  - do not redo scheduling internals
- Manual test after task:
  - `frontend/cal.html` still works
  - main chat still behaves exactly as before

### Task 06

- Title: Enable controlled scheduling-first chat path
- Status: `not_started`
- Scope:
  - support availability-first user requests in main chat
  - allow scheduling to run before booking-credentials when appropriate
  - continue booking-credentials after slot selection or slot commitment
- Guardrails:
  - preserve current booking-first path
  - backend owns workflow control, not freeform LLM decisions
- Manual test after task:
  - ask for available slots first
  - verify scheduling-first path keeps session continuity
  - verify booking-first path still works

### Task 07

- Title: Add minimal tenant-driven capability coexistence config
- Status: `not_started`
- Scope:
  - introduce only the minimal config needed for current capability ordering/coexistence
  - validate config safely in `config_loader.py`
- Guardrails:
  - avoid building a large rule engine
  - do not move conversational wording into Python
- Manual test after task:
  - current tenant config still works
  - invalid config shapes fail safely
  - scheduling-first and booking-first paths both still behave correctly

## Reset-Safe Restart Prompt

Use this to resume after reset:

```text
Re-anchor from repo truth only and continue the agent-core decomposition plan.

Inspect only:
- latest git state
- `clinic-ai-assistant docs/agent_core_decomposition_plan.md`
- files directly relevant to the current task
- related backend tests for the current task only

Rules:
- do not redo already completed tasks
- keep behavior stable unless the current task explicitly changes runtime behavior
- keep scope limited to conversation/session state, booking-credentials, scheduling capability, and orchestration

Return:
1. what you changed
2. what you verified
3. what remains next
```

## What Remains Next

The next practical step is Task 06: enable a controlled scheduling-first chat path while preserving the current booking-first flow as the default stable path.
