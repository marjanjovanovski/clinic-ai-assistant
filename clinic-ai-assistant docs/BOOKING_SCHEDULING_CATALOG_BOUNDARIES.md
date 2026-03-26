# Booking, Scheduling, and Catalogue Boundaries

## Purpose

This document describes the current implemented organization between:

- chat orchestration
- booking/contact collection
- scheduling availability and booking
- catalogue/services logic

It also separates current implemented behavior from future improvements so we do not accidentally describe proposed architecture as if it already exists.

## Quick Conclusion

The current runtime is not concentrated in one file only, but `backend/app/services/ai_agent.py` is the main orchestration anchor.

Today the boundary is:

- `ai_agent.py` decides routing and workflow transitions
- `booking_credentials.py` owns booking confirmation, contact collection, booking progress, and scheduling-first completion bridging
- `scheduling_capability.py` owns the orchestration-facing scheduling contract and handoff payloads
- `services/scheduling/service.py` owns provider-backed availability lookup and slot booking
- `agent_service_helpers.py` owns catalogue/service matching and catalogue-formatted replies

So the logic is centered around `ai_agent.py`, but it already delegates meaningful work to capability-specific modules.

## Implemented Today

### Main Files And Their Responsibilities

| Area | Current owner | What it currently does |
|---|---|---|
| Chat entrypoint | `backend/app/routes/chat.py` | Exposes `/chat`, calls `generate_reply(...)`, then returns `session_status`, `booking_progress`, `reply`, and optional `widget_payload`. |
| Main orchestration | `backend/app/services/ai_agent.py` | Loads profile/config, builds the model prompt, routes intent, manages session transitions, invokes booking capability first, then scheduling capability, and formats final chat responses. |
| Booking workflow | `backend/app/services/booking_credentials.py` | Handles booking confirmation, contact collection, validation, persistence gating, booking summary generation, and final selected-slot booking completion for the main chat path. |
| Scheduling capability bridge | `backend/app/services/scheduling_capability.py` | Provides orchestration-safe scheduling operations, stores scheduling state, builds availability widget payloads, and creates slot-selection handoff payloads. |
| Scheduling backend | `backend/app/services/scheduling/service.py` | Calls the scheduling provider for availability and final booking through `get_availability(...)` and `book_slot(...)`. |
| Scheduling HTTP routes | `backend/app/routes/scheduling.py` | Exposes `/scheduling/availability`, `/scheduling/book`, `/scheduling/select-slot`, and bridges selected chat slots back into chat contact collection. |
| Catalogue/services helpers | `backend/app/services/agent_service_helpers.py` | Matches messages to services, builds service lists, category lists, business overview replies, and price/orientation responses. |
| Main chat UI | `frontend/index.html` | Calls `/chat`, renders booking progress and booking summary widgets, and uses `/scheduling/select-slot` for scheduling-first slot selection. |
| Sandbox scheduling UI | `frontend/cal.html` | Calls `/chat` for chat messages, `/scheduling/availability` for slot lookup, and `/scheduling/book` directly for direct sandbox booking. |

### Current Interconnection

#### 1. Catalogue And Service Discovery

Catalogue logic is currently handled inside the chat runtime, but not as a standalone service.

Current path:

1. User sends a message to `/chat`
2. `ai_agent.py` loads tenant profile and service catalog
3. `agent_service_helpers.py` is used to:
   - match a service from free text
   - build service list replies
   - build business overview replies
   - build price replies
4. `ai_agent.py` returns the final reply to the chat route

Important current rule:

- catalogue lookup is read-oriented guidance logic
- it does not own booking state
- it does not own scheduling provider calls

#### 2. Booking-First Flow

This is the traditional chat-led booking path.

Current path:

1. User asks for a service or confirms booking in `/chat`
2. `ai_agent.py` routes into booking capability
3. `booking_credentials.py` starts and maintains `collecting_contact`
4. Lead/contact progress is persisted through lead-store integration
5. `booking_credentials.py` builds booking progress and booking summary state
6. `chat.py` returns `booking_progress` for the widgets in `index.html`

Important current rule:

- booking state progression is backend-controlled
- the frontend displays progress but does not decide workflow transitions

#### 3. Scheduling-First Main Chat Flow

This is the newer integrated slot-selection flow in the main chat.

Current path:

1. User asks about availability in `/chat`
2. `ai_agent.py` marks or routes the request as scheduling availability
3. `scheduling_capability.py` performs the availability lookup contract
4. scheduling state is stored in the chat session
5. `chat.py` returns a `slot-list` widget payload
6. `frontend/index.html` submits the chosen slot to `/scheduling/select-slot`
7. `routes/scheduling.py` validates the selected slot against the active chat session and builds a handoff payload
8. `ai_agent.py` starts contact collection from that handoff
9. after contact collection completes, `booking_credentials.py` detects `scheduling_handoff.selected_slot`
10. `booking_credentials.py` calls `scheduling_capability.book_selected_slot(...)`
11. `scheduling_capability.py` delegates to `services/scheduling/service.py`
12. provider-backed booking is executed and the result is stored as `booking_result`
13. `booking_progress` and booking summary now reflect the booked slot

Important current rule:

- `index.html` does not book the slot directly
- the main chat still completes through `/chat`
- the backend bridges from booking/contact completion into scheduling-owned booking

#### 4. Sandbox `cal.html` Flow

This flow uses scheduling more directly.

Current path:

1. `cal.html` can send normal chat messages to `/chat`
2. availability is requested through `/scheduling/availability`
3. the selected slot is booked directly through `/scheduling/book`
4. scheduling service calls the provider-backed booking implementation

Important current rule:

- `cal.html` is a direct scheduling client
- it does not rely on the chat-session handoff bridge used by `index.html`

## Implemented Boundary Rules

These rules describe what the codebase effectively does today.

### Rule 1: `ai_agent.py` Is The Orchestrator, Not The Scheduling Engine

`ai_agent.py` decides:

- which capability should react
- when state changes are allowed
- when a user moves from browsing to booking
- when scheduling handoff is ready

It should not own:

- provider-specific calendar logic
- slot validation rules deep inside the provider
- direct catalogue formatting logic beyond orchestration usage

### Rule 2: Booking Owns Contact Collection And Completion Gating

`booking_credentials.py` currently owns:

- booking confirmation gating
- contact field collection
- field validation and retry behavior
- booking progress payloads
- booking summary payloads
- the scheduling-first completion bridge after all required contact data exists

This means the booking layer is not just "credentials"; it is effectively the booking workflow state machine.

### Rule 3: Scheduling Owns Availability And Final Slot Booking

Scheduling code currently owns:

- availability request contracts
- slot selection validation against session scheduling state
- final provider booking calls
- scheduling provider configuration

This is important because final booking should stay under scheduling-owned backend logic even when the request started in chat.

### Rule 4: Catalogue/Services Own Discovery And Orientation Responses

Catalogue logic currently owns:

- service matching
- service list formatting
- business overview formatting
- price/orientation lookup for services

Catalogue logic should remain read-only and descriptive in the current design.

It should not:

- mutate booking state directly
- call scheduling providers directly
- become a second orchestration layer

## Current Pain Points

### 1. `ai_agent.py` Is Still The Main Coordination Hotspot

This file is the runtime anchor and therefore carries a lot of orchestration responsibility:

- prompt construction
- session loading
- deterministic routing shortcuts
- booking capability invocation
- scheduling capability invocation
- fallback reply handling

That is why it feels like "the logic is in `agent.py`". That feeling is directionally correct, even though the detailed work is partly delegated.

### 2. Catalogue Is A Helper Layer, Not A First-Class Capability

Today catalogue logic lives mostly in `agent_service_helpers.py` and is consumed by `ai_agent.py`.

That means:

- the catalogue boundary exists
- but it is not yet enforced as a formal capability contract like scheduling

### 3. Main Chat And Sandbox Use Different Booking Paths

Both reach scheduling-owned booking behavior, but they arrive differently:

- `index.html` uses chat-state handoff plus backend bridging
- `cal.html` uses direct scheduling API calls

That is workable, but it should be documented clearly so future changes do not accidentally break one path while updating the other.

## Future Improvement

The items below are proposals only. They are not described as implemented behavior.

### Proposed Segmentation Rule

Use this simple rule for future changes:

| Status | Boundary rule |
|---|---|
| Current | `ai_agent.py` orchestrates all user-intent transitions across catalogue, booking, and scheduling. |
| Future improvement | catalogue/services should become a first-class capability boundary with explicit contracts, similar to scheduling, instead of remaining only helper functions called from `ai_agent.py`. |

### Proposed `catalogue-services` Rule

Future rule:

- catalogue-services should be treated as a read-only domain capability
- it should provide explicit contracts for:
  - list services
  - service details
  - category overview
  - price guidance
  - service matching from normalized user intent
- it should not own:
  - booking session transitions
  - scheduling provider calls
  - lead persistence side effects

Recommended outcome:

- `ai_agent.py` remains the orchestrator
- `catalogue-services` becomes a clearly named capability module
- booking remains the workflow state machine
- scheduling remains the provider-facing execution boundary

### Proposed Structural Direction

If we continue cleaning the architecture, the target shape should be:

1. `ai_agent.py`
   Current role: orchestration
   Future role: slimmer orchestration and transition management only
2. `catalogue-services`
   Future role: all catalog/service/business overview/price response contracts
3. `booking-flow`
   Current and future role: confirmation, contact collection, summary state, completion gating
4. `scheduling-capability`
   Current and future role: availability, slot handoff, slot booking, provider-facing scheduling contracts

### Proposed Guardrails For Future Work

- Do not move provider booking logic into `ai_agent.py`.
- Do not let frontend pages invent booking transitions on their own.
- Do not let catalogue logic start mutating booking state directly.
- Do not duplicate service matching rules in multiple places.
- Do not let `index.html` and `cal.html` drift into incompatible booking result contracts.

## Recommended Next Refactor Order

1. Preserve the current orchestration split and document it as the source of truth.
2. Extract catalogue/service behavior behind an explicit capability-style module.
3. Keep booking workflow logic in its dedicated module and consider renaming it later if `booking_credentials.py` no longer fits the true scope.
4. Keep scheduling as the only provider-facing booking authority.
5. Add one shared architecture note or test map whenever a new inter-service handoff is introduced.

## Final Assessment

Yes, the main coordination logic is currently anchored in `ai_agent.py`.

But the codebase already has the beginnings of a cleaner service split:

- orchestration in `ai_agent.py`
- booking workflow in `booking_credentials.py`
- scheduling contracts in `scheduling_capability.py`
- provider execution in `services/scheduling/service.py`
- catalogue logic in `agent_service_helpers.py`

The biggest missing formal boundary is catalogue/services becoming a first-class capability with explicit rules, rather than staying only as helpers attached to the main agent orchestration.
