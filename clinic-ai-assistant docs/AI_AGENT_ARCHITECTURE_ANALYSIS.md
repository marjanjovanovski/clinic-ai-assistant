# AI Agent Architecture Analysis

## Scope

- Target file: `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- Current measured size: 2187 lines
- Purpose of this note: explain what the file owns at a high level, how its logic is grouped, and which parts are currently doing LLM orchestration versus deterministic backend control

## High-Level Category Map

Percent coverage below is measured against the current 2187-line file size, so it shows how much of the file each category occupies today.

| Category | Approx. logic LOC | % Coverage | Description | What it owns |
|---|---:|---:|---|---|
| LLM prompt / inference orchestration | 898 | 41.1% | The orchestration core that builds prompt context, calls the model, normalizes model output, and routes results into backend-safe branches. | prompt construction, context bounding, model call, structured output handling, final orchestration |
| Booking flow / contact collection / edit flow | 676 | 30.9% | Deterministic booking workflow control for confirmation, contact collection, edit handling, and persistence-aware progression rules. | booking state guidance, validation boundaries, unknown-name handling, persistence-gated collection flow |
| Catalog / service / intent routing | 181 | 8.3% | Rule-based routing and service-aware response shaping that can answer common requests before the LLM is used. | rule-based routing before the model call and service-oriented fallback shaping |
| Repetition / fallback shaping | 97 | 4.4% | Reply-quality control logic that detects repetition, reformulates weak outputs, and keeps final replies usable. | repeated-message handling, fallback reformulation, and final reply shaping |
| Logging / tracing / session bookkeeping | 69 | 3.2% | Operational support logic for trace events, chat-state logging, response tracing, and lightweight session status helpers. | trace events, chat-state logging, response tracing, session status helpers |
| Supporting scaffolding / imports / constants / glue | 266 | 12.2% | Module setup and connective tissue that supports all categories without fitting neatly into one behavior slice. | imports, constants, docstring/header, small wrappers, and uncategorized glue code |

## 1. LLM Prompt / Inference Orchestration

### High-Level Role

This category is the orchestration core of `ai_agent.py`.

It does not mainly contain business wording. Instead, it:

- loads tenant configuration already defined elsewhere
- converts tenant config into a live system prompt
- decides how much session context is allowed into the prompt
- calls the OpenAI Responses API
- normalizes model output into backend-safe intents
- routes the result into deterministic booking and scheduling capability branches
- falls back safely when model output is malformed or incomplete

### LLM-Orchestration Table

| Function / item | Lines | Nature | Inputs | Output | How it is used |
|---|---:|---|---|---|---|
| `_is_availability_intent_output` | 152-155 | intent marker checker | raw intent string | boolean | detects whether the model returned the internal availability intent marker |
| `_bounded_ai_input` | 247-277 | prompt-input builder | `system_prompt`, `session_key`, current `message`, current `stage`, `stage_context_template` | list of chat input items | builds the actual model input with bounded recent interaction history and optional stage context |
| `_normalize_intent` | 1154-1164 | output normalizer | raw model intent | canonical intent string | maps model aliases to allowed backend intents and collapses unknown output to `fallback` |
| `generate_reply` | 1333-2184 | top-level orchestrator | `tenant`, `message`, optional `session_id` | `(reply, session_id)` | owns the full request lifecycle from profile load through routing, model call, and final reply |
| `prompt_template.system` from tenant profile | consumed inside `generate_reply` | config-driven prompt root | business name, goal, tenant config | system prompt base text | provides the initial system prompt shell before runtime augmentation |
| `conversation.rules` | consumed inside `generate_reply` | policy payload | tenant conversation rules | prompt text block | injected into the system prompt as explicit behavioral constraints |
| service catalog JSON | consumed inside `generate_reply` | structured grounding payload | profile services | prompt text block | injected into the system prompt so the model sees only allowed services |
| category catalog JSON | consumed inside `generate_reply` | structured grounding payload | derived categories | prompt text block | gives the model a clinic-category view in addition to the flat service list |
| communication rules text | consumed inside `generate_reply` | supplemental behavioral payload | tenant communication rules | prompt text block | adds human-communication guardrails from config |
| output contract JSON | consumed inside `generate_reply` | structured output constraint | response format schema | prompt text block | tells the model to return only JSON in the expected shape |

### What `generate_reply` Actually Does Inside the LLM Category

`generate_reply` is large because it combines multiple sub-phases:

1. Request bootstrap
   - load tenant profile
   - normalize session id
   - emit trace events

2. Prompt assembly
   - collect business metadata
   - read tenant prompt template
   - serialize service catalog
   - serialize category catalog
   - append communication and booking capability instructions
   - append output contract

3. Pre-LLM deterministic routing
   - completed-session rollover
   - scheduling handoff confirmation path
   - booking capability path
   - scheduling capability path
   - greeting / service-list / price / description / casual deterministic shortcuts

4. LLM call
   - build bounded input via `_bounded_ai_input`
   - call `client.responses.create(model="gpt-4.1-mini", input=...)`
   - trace raw output

5. Post-LLM normalization and enforcement
   - parse JSON
   - normalize intent
   - gate availability intent through scheduling capability
   - shape fallback if output is invalid

### Nature of the LLM Items

| Item type | Meaning in this file | Why it exists |
|---|---|---|
| Prompt root | the tenant-config template for the assistant role | keeps wording/config out of Python |
| Grounding payload | serialized service and category data | narrows the model to clinic-approved options |
| Policy payload | rules and communication rules | adds explicit safety and tone boundaries |
| Capability hint | booking/scheduling instructions | tells the model what intents are valid in this runtime |
| Output contract | required JSON schema | makes model output parseable by deterministic backend code |
| Context limiter | `_bounded_ai_input` | prevents unlimited prompt growth and keeps only recent relevant turns |
| Intent normalizer | `_normalize_intent` | protects the backend from model alias drift |
| Intent marker checker | `_is_availability_intent_output` | lets the backend treat availability as an internal orchestration signal |

### LLM Section Observations

- The LLM section is not “just prompt text”; most of its weight is in orchestration and enforcement.
- The model is not trusted directly. Its output is repeatedly normalized, gated, and overridden by backend checks.
- The file is large partly because `generate_reply` still owns too many transitions that could be decomposed further.
- The prompt assembly is config-driven, but the orchestration around it is still centralized here.

## 2. Booking Flow / Contact Collection / Edit Flow

### High-Level Role

This category owns the deterministic side of booking:

- clarification handling during contact collection
- field-value validation boundaries
- unknown-name recovery
- edit-after-completion support
- persistence-aware completion control

### Booking / Contact Functions

| Function block | Primary role |
|---|---|
| clarification helpers | detect field-level versus scope-level clarification |
| plausibility helpers | lightweight validation for name, phone, and email |
| unknown-name recovery helpers | recover when the entered name is not trustworthy |
| contact-bundle parsing helpers | parse explicit bundled contact input only when safe |
| edit-flow helpers | support editing saved booking fields after completion |
| booking-capability adapters | hand control to `booking_credentials` while keeping orchestration in `ai_agent.py` |

### Notes

- This category is large because it contains many small workflow boundaries.
- Some helpers in this area appear to be leftover wrappers or unused pieces.

## 3. Catalog / Service / Intent Routing

### High-Level Role

This category handles rule-based routing before the model is asked anything expensive.

### Main Responsibilities

| Function group | Purpose |
|---|---|
| service-list detection | recognize general “what do you offer” requests |
| price detection | route specific price questions deterministically |
| greeting / casual handling | answer lightweight social input without a model call |
| service clarification | ask for better precision before suggestion |
| unknown detail fallback | avoid unsafe specificity for treatments not fully grounded |

## 4. Repetition / Fallback Shaping

### High-Level Role

This category is the reply-quality and safety buffer.

### Main Responsibilities

| Function group | Purpose |
|---|---|
| message similarity helpers | detect repeated or near-duplicate requests |
| fallback reply helpers | recover from unclear or malformed situations |
| final reply shaping | normalize the last outgoing payload and attach supporting metadata |

## 5. Logging / Tracing / Session Bookkeeping

### High-Level Role

This is the observability layer inside the file.

### Main Responsibilities

| Function group | Purpose |
|---|---|
| chat-state logging | log stage and intent transitions |
| trace-event emission | record request, response, and stage events |
| interaction recording | maintain bounded recent interaction memory |
| public status helpers | expose session and booking progress state |

## Current Architectural Reading

- `ai_agent.py` is large because it is still the convergence point between:
  - config-driven prompting
  - deterministic booking flow
  - scheduling capability handoff
  - final response shaping
  - trace/session bookkeeping
- The file is not 1800+ lines only because the product is huge.
- It is 1800+ lines because decomposition is only partial and `generate_reply` still owns too much orchestration.

## Immediate Review Direction

The best next review pass for shrinking or clarifying the file is:

1. Identify unreferenced helpers and wrapper duplicates.
2. Separate truly LLM-specific orchestration from general request lifecycle code.
3. Move any booking/scheduling logic that already has a capability module out of `ai_agent.py` when the destination authority is clear.
4. Re-measure category LOC after each extraction so the file stops growing by hidden drift.
