# 20260329_1704_DOC - Scheduling Flow UX and Logic Brainstorm

This document is a decision-shaping note for refining the chat-driven scheduling experience before we lock an execution-ready implementation task.

Execution conventions for task artifacts in this folder should follow [../Task_Workflow_Guide.md](../Task_Workflow_Guide.md) and [../Core_Rules.md](../Core_Rules.md).

## Last Updated By

- `Codex`

## Last Updated On

- `2026-03-29`

## Merge To Main

- `Pending`

## Current Active Prompt

- `Prompt 2`

## Global Status Summary

- Prompt 1 - Brainstorming Overlay - Completed
- Prompt 2 - Convert To Execution Task - Pending
- Prompt 3 - Merge To Main - Pending

## Purpose

- validate the main logical units around chat, booking, scheduling, and catalog behavior
- define the minimum business coverage that makes scheduling useful in real conversations
- recommend a UX direction for scheduling widgets and date-selection behavior
- capture open product decisions before creating the master implementation task

## Initial Architecture Read

Your current breakdown is close, but one correction and three cross-cutting concerns matter if we want the scheduling flow to behave well.

### Corrected Main Logic View

1. `General chat / orchestration`
   This is the reasoning and routing layer that decides whether the user is browsing, asking, comparing, booking, or scheduling.
2. `Booking flow`
   This is the structured contact collection and booking-confirmation path.
3. `Scheduling flow`
   This is the availability-discovery, slot-evaluation, and slot-selection path.
4. `Catalog flow`
   This is the services listing and service-exploration path.

### Important Correction

There is already meaningful routing and handoff logic in the current architecture. The issue is not that orchestration is absent. The issue is that it still behaves like a centralized mixed layer inside the main agent flow instead of a clearly locked business contract between chat, scheduling, booking, and catalog.

## What Is Missing Or Cross-Cutting

- `Intent routing / flow handoff`
  This already exists in partial form, but it should be treated as an explicit business contract rather than a mixed orchestration behavior hidden inside the main agent file.
- `Slot conflict and recovery behavior`
  This also exists in partial form, but it should be elevated into a clearly defined user-facing flow with protected recovery rules.
- `Service-to-scheduling dependency`
  This dependency is already present in the runtime model, but the product rules still need to be made explicit so scheduling behavior stays consistent.

## Current-State Adjustment

Based on the architecture note and current agent structure, the right framing is:

- `Intent routing / flow handoff` is partially implemented and operational
- `Slot conflict and recovery behavior` is partially implemented and operational
- `Service-to-scheduling dependency` is partially implemented and operational

So the product goal is no longer to invent these from zero. The goal is to tighten them, simplify their business meaning, and make the user experience more deliberate.

## Recommended Product Framing

The safest product model is:

- `catalog` helps the user understand what they can book
- `scheduling` helps the user discover when they can come
- `booking` collects the required details and finalizes the request
- `orchestration` decides when to switch flows and how to recover gracefully

This means the scheduling flow should not feel like a forced booking funnel. It should first solve the user's question:

- "Do you have openings?"
- "What time is free on Tuesday?"
- "Can I come tomorrow afternoon?"
- "Show me the first available slot"

Only after the user sees a meaningful scheduling answer should we nudge toward booking confirmation.

## Product Problem To Solve

The current risk is not lack of capability. The current risk is that the user experience can still feel like this:

- the user asks about availability
- the assistant understands enough to move toward scheduling
- but the conversation still feels too booking-oriented too early

The scheduling flow should instead feel like this:

- the user asks about time availability
- the assistant helps the user discover real options quickly
- the user only enters booking once a slot or direction is clear

This is the main tightening target.

## Minimal Scheduling Coverage

These are the minimum use cases that make scheduling genuinely useful without overbuilding the first version.

### A. Availability Intent Detection

The system should enter scheduling mode when the user expresses intent such as:

- asking for open time slots
- asking for availability
- asking for free times on a date or day
- asking for the next available appointment
- asking whether reservations are possible on a date
- asking for morning / afternoon / evening options
- asking to reserve but without a selected time yet

Representative examples:

- "Do you have anything free tomorrow?"
- "What slots are open on April 2?"
- "I need an appointment next week."
- "Any availability in the afternoon?"
- "Can I reserve something for Friday?"

### B. Immediate Scheduling Responses

When scheduling intent is detected, the assistant should not stay in vague chat mode. It should respond with one of these useful actions:

1. return available slots directly if enough information is already known
2. ask for the missing minimum detail if the request is incomplete
3. open or attach the scheduling widget if that is the fastest way forward

### C. Broad Availability Requests

If the user asks broadly, for example "anything available soon" or "what is open this week", the system should:

- return a short LLM response that confirms it is checking availability
- present the earliest relevant slots or the scheduling widget
- avoid asking for unnecessary booking details first

### D. Specific Date Requests

If the user asks for a specific date in text, the system should:

- attempt date resolution
- return the available slots for that date if any exist
- return a truthful no-availability assessment if none exist
- offer the next-best alternative such as nearby dates or the calendar control

This should be treated as a first-class path, not a fallback path.

### E. Ambiguous Time Requests

If the user says something like "next Tuesday" or "afternoon", the system should:

- resolve what it safely can
- avoid over-clarifying when a useful answer is possible
- return filtered options when feasible
- ask one targeted follow-up only when needed

### F. No Availability Recovery

When no slots are available for the requested date, the flow should not dead-end. It should:

- say that no slots are available for that date
- offer the nearest alternatives
- offer the widget or calendar control for wider exploration

### G. Scheduling-To-Booking Handoff

When the user has either selected a slot or clearly accepted one of the offered slot options, the system should:

- preserve the selected slot as authoritative scheduling state
- transition into booking only at that moment
- ask only for the booking data needed to finalize the reservation

### H. Slot Conflict Recovery

If the slot becomes unavailable after the user selected it, the system should:

- clearly explain that the slot is no longer available
- keep the user inside a scheduling recovery path
- immediately offer replacement slots or refreshed availability
- avoid making the user restart the entire conversation

## Minimum Business Rules For Scheduling Logic

These are the core business overlays I would treat as mandatory for a useful first version:

### 1. Scheduling Entry Gate

Scheduling should start when any of these are true:

- the user asks for availability or time slots
- the user asks whether the clinic is open for appointments on a date
- the user asks for the next available appointment
- the user selects a date from a calendar control

### 2. Do Not Force Booking Too Early

Do not request name, phone, or email before the user has:

- seen availability
- selected a slot
- or explicitly asked to reserve/book

This is one of the biggest UX protections against the assistant feeling pushy.

### 3. Prefer Utility Over Conversation

For scheduling intents, the first answer should be operational:

- availability result
- missing-detail prompt
- or scheduling widget

Not a generic sales or booking redirection message.

### 4. Service Dependency Must Be Explicit

If slot availability depends on service type, then the system should:

- use the known selected service if already present
- ask for service only if it is truly required to compute valid availability
- otherwise allow generic availability browsing first

Business interpretation:

- if service is mandatory for valid availability, ask for it early and clearly
- if service is not mandatory, do not block scheduling exploration behind service selection

### 5. Specific Date Beats Generic Widget

If the user typed a date explicitly, the assistant should answer that date first rather than immediately redirecting to a widget.

### 6. Recovery Must Stay Inside Scheduling

If the date is unavailable, the recovery should remain scheduling-focused:

- nearby dates
- next available slot
- calendar control

Do not jump straight into booking prompts.

### 7. Selected Slot Becomes The Handoff Contract

The clean handoff into booking should be:

- scheduling resolves actual slot options
- user selects or accepts a slot
- the selected slot becomes the booking handoff payload
- booking collects required personal details

### 8. Slot Conflict Is A Protected Recovery Path

If a previously selected slot is lost:

- do not silently degrade into generic chat
- do not ask the user to repeat the whole intent
- recover with replacement availability if possible
- preserve as much user context as possible

### 9. Catalog And Scheduling Must Not Fight Each Other

If the user is still exploring services:

- catalog should help discover the right service
- scheduling should only request service selection when it is operationally necessary
- once a service is selected, that service context should remain stable into scheduling and booking

## Minimal First-Version Scheduling Contract

The first useful version should lock these behaviors as explicit business logic:

| Situation | Required system behavior |
|---|---|
| User asks for general availability | Start scheduling response, show earliest useful availability, optionally attach scheduling widget |
| User asks for a specific date | Return slots for that date if available, otherwise return truthful no-availability assessment and alternatives |
| User asks for a relative date or time window | Resolve what can be resolved and return filtered availability or one targeted clarification |
| User wants to reserve but no slot is selected yet | Keep the user in scheduling until a real slot is identified |
| User selects a slot | Start booking handoff with preserved selected-slot state |
| Selected slot becomes unavailable | Trigger conflict recovery with replacement slots or refreshed availability |

## Recommended UX Direction

### Primary Recommendation

Use a hybrid model:

1. keep the current scheduling widget as the fast-path surface
2. add a follow-up clickable date-selection control for broader day exploration
3. let text-entered date requests return direct slot answers without forcing clicks first

This gives you:

- fast access for users who want to browse immediately
- direct usefulness for users who already know the date they want
- a controlled fallback when the current 3-day widget is too narrow

## Why The Current 3-Day Widget Alone Is Not Enough

The 3-day span is useful for quick discovery, but weak as the only scheduling surface because:

- it can miss user intent when the requested date is outside the visible window
- it may feel arbitrary if the user wants next week or a specific calendar date
- it can create extra back-and-forth for users who are trying to plan

So I would keep it, but not make it the only navigation model.

## Recommended Interaction Model

### Path 1. User asks broad availability

Example:
- "Do you have any openings?"

Recommended response:
- short intelligent confirmation
- show earliest available slots
- attach current scheduling widget
- offer date selection for another day

### Path 2. User asks for a specific date

Example:
- "Do you have anything on April 4?"

Recommended response:
- return slots for April 4 directly
- if none, say none are available for April 4
- offer nearest available dates
- optionally show date control anchored around that time window

### Path 3. User clicks a date control

Recommended response:
- fetch availability for the selected day
- show available slots for that day
- if none, keep the date visible and explain that the day has no available slots

### Path 4. User selected a slot and proceeds

Recommended response:

- confirm the selected slot in a short clear way
- transition into booking data collection
- do not re-open service exploration or generic scheduling unless needed

### Path 5. Selected slot is lost

Recommended response:

- explain that the slot is no longer available
- offer replacement slots immediately if available
- otherwise offer refreshed day-based availability
- preserve the user's context and keep the conversation calm and forward-moving

## Inactive Day Behavior

The idea of preventing clicks on unavailable days is good, but only if availability is reliable enough to precompute at the calendar level.

Best version:

- inactive days are visibly disabled
- hover or tap explains `No available slots`
- active days remain selectable

Fallback version if precomputed availability is incomplete or expensive:

- allow the click
- return a same-day response of `No available slots for this date`
- immediately offer nearby alternatives

Product guidance:

- prefer disabled days only when the backend can trust that state
- avoid false-disabled dates because that is worse than allowing a click and returning no availability

## Recommended LLM Behavior Contract

The LLM should not own slot truth. It should own conversational framing and intent recognition.

Suggested contract:

- LLM detects scheduling intent
- business logic decides whether to trigger scheduling flow
- scheduling backend returns authoritative availability data
- LLM formats the result into a helpful conversational reply

This avoids hallucinated availability and keeps the chat useful.

High-level architectural guidance:

- keep LLM intent recognition
- keep backend authority for routing, slot truth, handoff payloads, and conflict recovery
- make the scheduling contract easier to read as product logic rather than only as orchestration code

## Suggested Trigger Set For First Version

These are the minimal trigger families I would formalize first:

- `availability_general`
  Example: user asks for free slots or open appointments
- `availability_specific_date`
  Example: user asks for availability on a known date
- `availability_relative_date`
  Example: tomorrow, next Tuesday, this weekend
- `availability_time_window`
  Example: morning, afternoon, after 5 PM
- `reservation_intent`
  Example: book, reserve, schedule me in

Recommended routing meaning:

- `availability_*` should enter scheduling-first behavior
- `reservation_intent` without slot selection should usually still enter scheduling-first behavior
- `reservation_intent` with a selected slot should enter booking handoff behavior

## Suggested First-Version Response Matrix

| User situation | System action | UX outcome |
|---|---|---|
| Broad availability request | show earliest slots + widget | fast discovery |
| Specific date request with matches | return slots for date | direct usefulness |
| Specific date request with no matches | explain none + offer nearest alternatives | graceful recovery |
| Relative date request | resolve date and return slots if possible | natural chat behavior |
| User selects slot | hand off to booking flow | clean transition |
| User asks to reserve before seeing slots | start scheduling or confirm slot first | prevents premature booking |
| User loses selected slot | offer replacement slots or refreshed availability | resilient recovery |

## What I Would Treat As Out Of Scope For The Minimal Version

- advanced calendar month navigation rules
- provider-specific filtering unless already required by the business
- rescheduling and cancellation flows
- waitlist logic
- complex recurring-availability explanations

These can come later once the first scheduling experience is stable.

## Proposed Decisions To Lock Next

Before writing the master implementation task, I would lock these decisions:

1. whether service selection is required before valid scheduling lookup
2. whether the 3-day widget stays as the first widget or becomes a secondary quick-view
3. whether a day-picker / calendar control is added in the first implementation
4. how relative dates like `tomorrow` and `next Tuesday` are resolved
5. what the no-availability recovery response must always include

## Tightening Priorities

If the next implementation task is meant to tighten scheduling rather than broadly expand it, the top priorities should be:

1. make scheduling-entry triggers explicit and stable
2. ensure specific-date text requests return direct availability answers
3. prevent premature booking prompts before a slot exists
4. define one clean scheduling-to-booking handoff contract
5. define one clean slot-conflict recovery contract
6. keep widget strategy hybrid rather than widget-only

## Recommended Direction Summary

- your current four-part framing is useful, but orchestration/handoff should be treated as an explicit contract layer across them
- the minimum useful scheduling coverage is intent detection plus useful availability answers, not just booking nudges
- specific typed dates should receive direct availability answers
- the current 3-day widget should remain, but as part of a hybrid scheduling UX rather than the only interface
- a date-selection control is the most natural complement to the current widget
- disabled unavailable dates are good only when the backend can trust calendar-level availability state
- scheduling should transition to booking only after slot resolution, not merely because reservation language appeared
- slot conflict recovery should be treated as a protected product flow, not just a backend edge case

## Next Task Candidate

The next execution-ready task should likely translate this note into:

- scheduling intent taxonomy
- trigger-to-action business rules
- response contract between LLM orchestration and scheduling backend
- widget behavior rules for broad requests, specific dates, and no-availability recovery
- scheduling-to-booking handoff contract
- slot-conflict recovery contract

## Brainstorming Conclusions

- the current architecture already contains partial scheduling routing, handoff, and recovery behavior
- the main need is to tighten and formalize scheduling as a clearer product contract
- scheduling should solve availability discovery first and only then hand off into booking
- the best first-version UX is hybrid:
  - direct answers for typed dates
  - current 3-day widget as quick-view
  - date-picker / calendar control for broader exploration
- slot-conflict recovery should be treated as a first-class protected flow
- service dependency should be explicit and should only block scheduling when operationally necessary
- backend should remain the authority for routing, slot truth, handoff, and recovery
- JSON config should remain the home for copy, labels, and behavior knobs, not Python wording logic

## Brainstorming Decision Table

| Question | Recommended answer | Why | Your final decision |
|---|---|---|---|
| 1. Should service selection be required before scheduling lookup? | Require it only when availability truly depends on service duration, provider, or business rules. | This preserves flexibility and avoids blocking broad scheduling exploration unnecessarily. | `No, service selection must be handled differently. As a conclusion from this task we need to leave a footprint in the task list, you need to engage into puting a very short draft that we will have to formulate an independence between the flows as much as possible. There would be logic, in case there are different reservation slots per service/categoy then, yes, it would be mandatory to state what you are after so the system knows what to render back. So this is the resedue for the upcoming task you need to create so we don't forget it. Do it now, then come back on point 2. ` |
| 2. For broad availability requests, what should happen first? | Return a short useful text response and attach the current 3-day widget. | This keeps the chat feeling helpful while still giving fast visual exploration. | `Agreed` |
| 3. Should the day-picker / calendar control be added in the first implementation? | Yes, if scope allows; otherwise make it the immediate next follow-up after the 3-day widget flow is stable. | The 3-day widget alone is too narrow for date-driven planning. | `Generate a new task for a month calendar widget, at this stage we have to stabilize the scheduling time slot widget ` |
| 4. If the user types a specific date, should that date be answered directly first? | Yes. Always answer the typed date first before redirecting to a widget. | This is the most natural and useful user experience. | `Agreed` |
| 5. How should relative dates and time windows be resolved? | Resolve them in backend business logic into concrete dates or filters, with one targeted clarification only when ambiguity blocks a useful answer. | This preserves natural conversation while keeping availability authoritative. | `Agreed` |
| 6. If the user says they want to reserve but no slot is selected yet, what should happen? | Keep the user in scheduling-first behavior until a real slot exists. | This prevents premature booking prompts and reduces friction. | `It should be treated as a scheduiiling intent first. Also it should not force into booking state. You might want to create a specific task for, don't know how to define it really, but in reality it would be something like, if i have severla parameters per flow, lets say collction of inputs in sceduling is X, now when the system knows that we have successfully acquired a certain Y%, can be configurable, then the system will use that to gude and stich the flows together, this will be a lot more natural. I don't know if you agree, but this is for a future task, not for this one. For this one we stick with your proposal....If possible for your solution at this moment, how would i image it should operate, if user sayas next week, the system checks but does not gives, there are X ammount of free slots, or here are the slots, it simply confirm that there are and asks for a more specific narrow, like for which date, maybe this would be a good moment after we create a monthly calendar widget to show it here.... ` |
| 7. What should trigger the handoff from scheduling to booking? | Either an explicit slot click or a clear user acceptance of a proposed slot in text. | Both are valid user confirmations and should lead to the same backend handoff contract. | `Until we have progressive stitching, the handoff from scheduling to booking should happen directly after the user selects a slot, without adding an extra confirmation step. The system should treat the slot click as sufficient intent, move into booking, and immediately start the first booking field while keeping the temporary hold active. The reply should clearly show the selected slot and make it easy for the user to change the slot or back out if needed. This is not my ideal final model, but it is a better low-friction transitional approach than adding one more confirmation question.`|
| 8. What must a no-availability response always include? | A truthful no-availability assessment plus nearest alternatives or a clear calendar/date-selection path. | This keeps the flow useful and prevents dead ends. | `Agreed` |
| 9. Should unavailable calendar days be disabled? | Yes, but only when backend confidence is reliable; otherwise leave them clickable and return `No available slots` with alternatives. | False-disabled dates are worse than graceful no-availability responses. | `Pending` |
| 10. How should slot conflict recovery behave? | Immediately explain the conflict and offer replacement slots or refreshed availability in the same response. | Recovery should feel fast and continuous, not like a restart. | `Pending` |
| 11. What is the long-term role of the 3-day widget? | Keep it as the default quick-view widget, but not as the only scheduling surface once the date-picker exists. | It is useful for speed, but too narrow as a complete scheduling interface. | `Pending` |
| 12. What should the LLM own versus backend logic? | LLM owns intent recognition and reply framing; backend owns slot truth, routing, handoff, and conflict recovery. | This avoids hallucinated availability and keeps behavior deterministic. | `Pending` |
| 13. What should move out of `ai_agent.py` first? | Extract scheduling entry logic, availability response shaping, handoff preparation, widget payload assembly, and conflict recovery into a scheduling service layer. | These are the clearest scheduling-owned behaviors and reduce orchestration sprawl. | `Pending` |
| 14. Where should copy, labels, and behavior knobs live? | In JSON config from the start, not in Python logic. | This keeps the architecture aligned with your config-first rule. | `Pending` |
| 15. What should be explicitly avoided? | Avoid hard-coded phrase dictionaries, premature booking prompts, widget-only scheduling, and duplicated scheduling logic across files. | These are the main paths that would weaken both architecture and UX. | `Pending` |
| 16. What should be the first implementation priority? | Lock intent routing, direct typed-date answers, scheduling-to-booking handoff, and slot-conflict recovery before adding wider UX polish. | These produce the biggest functional and product improvement first. | `Pending` |

## Update Instructions

Use the `Your final decision` column with values like:

- `OK`
- `OK with note: ...`
- `Change to: ...`
- `Later`
