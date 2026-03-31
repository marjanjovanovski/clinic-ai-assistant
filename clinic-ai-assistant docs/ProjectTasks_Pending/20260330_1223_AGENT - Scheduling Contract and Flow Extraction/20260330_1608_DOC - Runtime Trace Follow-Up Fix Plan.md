# 20260330_1608_DOC - Runtime Trace Follow-Up Fix Plan

This note converts the issues observed in these two traces into a concrete implementation sequence:

- `clinic-ai-assistant-src/backend/runtime_traces/trace_2026-03-30_14-39-51_milena_dental_db97e97a-4aef-4cdf-9082-11eb925f75bb.txt`
- `clinic-ai-assistant-src/backend/runtime_traces/trace_2026-03-30_14-30-31_milena_dental_5914159d-c8cd-46b2-8f60-28e75ce770b8.txt`

The latest trace also contains the user-authored guidance that should drive the next follow-up prompts.

## What The Two Traces Show

### Trace A - `14-39-51`

- `slednata nedela` did not produce a useful narrowing flow and fell back poorly.
- `a za dve nedeli od sega?` returned a reply claiming a two-week check, but the actual slots shown were for `31 Mar 2026`, not two weeks out.
- `a za denes shto imate?` and `za denes` both ended in the generic no-availability reply instead of a useful same-day answer path.
- The assistant replied in Latin transliteration instead of tenant-native Macedonian Cyrillic.
- A later widget click failed with `No active availability result is ready for slot selection in this chat session`.

### Trace B - `14-30-31`

- `utre?` and `petok?` correctly returned typed specific-day text lists.
- After that, booking-intent messages such as `moze`, `vo 12:00`, `moze na 3 April vo 12:00`, and `moze da zakazeme` were classified as `confirm_booking`.
- Even though intent classification moved toward booking, the returned user-facing reply stayed stuck on the same availability list instead of selecting the slot and moving into booking handoff.
- This created the perceived loop reported in the later trace.

## Root Causes To Fix

1. Relative-date resolution is not being carried through cleanly from the interpreted user request into the actual scheduling request window.
2. Text-only specific-day replies do not preserve enough actionable availability context for the next booking-style turn.
3. Booking-intent follow-through is incomplete when the current surface is a suppressed-widget typed-date reply.
4. Tenant language/script output is leaking into user-script mimicry.
5. Widget slot selection depends on active availability state that can disappear before the user clicks.

## Step-By-Step Fix Plan

## Prompt 1 - Enforce Tenant-Native Script In Final Replies

### Goal

Ensure final user-visible scheduling replies always use the tenant-configured native language/script, even when the user types in Latin transliteration.

### Likely Surface

- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- tenant config reply/language shaping surface already introduced in Prompt 5

### Steps

1. Trace where AI-produced `message` text is passed through unchanged into the final scheduling reply.
2. Confirm what tenant config field defines the canonical language/script behavior.
3. Ensure final scheduling replies are normalized to tenant-native output rather than mirroring user input script.
4. Keep this narrow to scheduling-facing responses so non-scheduling flows are not disturbed.

### Verify

- Reproduce a Latin-input Macedonian scheduling request.
- Confirm returned text is in Macedonian Cyrillic.

## Prompt 2 - Fix Relative-Date Window Resolution

### Goal

Make broad and relative requests resolve to the correct date window before availability is fetched or presented.

### Failures To Cover

- `slednata nedela`
- `dve nedeli od sega`
- `za denes`

### Likely Surface

- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- any existing date-resolution helper already used by scheduling extraction prompts

### Steps

1. Trace how relative-date intent becomes `date_from` and `date_to`.
2. Add or tighten assertions so resolved dates match the interpreted user request before reply shaping.
3. Ensure broad ranges narrow intentionally instead of silently collapsing to today/tomorrow.
4. Ensure same-day requests stay on a same-day path and do not fall back to an irrelevant generic message.

### Verify

- `slednata nedela` should either produce in-range narrowing or an in-range summary.
- `dve nedeli od sega` must not return `31 Mar 2026` slots when the date window should be mid-April 2026.
- `za denes` should either show today’s slots or a same-day no-availability response that is clearly about today.

## Prompt 3 - Let Text-Only Availability Replies Progress Into Booking

### Goal

When typed specific-day replies suppress the widget, the next booking-style user turn must still be able to select a valid slot and continue.

### Failure To Cover

Trace `14-30-31` shows `confirm_booking` intent being recognized, but the response remains stuck repeating the same availability list.

### Likely Surface

- `clinic-ai-assistant-src/backend/app/services/ai_agent.py`
- `clinic-ai-assistant-src/backend/app/services/scheduling_capability.py`
- existing scheduling handoff / hold selection helpers

### Steps

1. Preserve a compact active availability context after text-only specific-day replies.
2. On follow-up booking intent, resolve references like `moze`, `vo 12:00`, and `na 3 April vo 12:00` against that preserved availability context.
3. If exactly one slot matches, transition directly into normal booking handoff.
4. If multiple matches remain, ask a narrowing question instead of replaying the whole list.
5. Reuse existing hold and conflict logic rather than inventing a second booking path.

### Verify

- `petok?` -> list -> `vo 12:00` should move into contact collection or booking hold flow.
- `moze na 3 April vo 12:00` should not replay the availability list.

## Prompt 4 - Keep Widget Clicks Valid After Reply Delay

### Goal

Prevent late slot clicks from failing just because the active availability result was not retained long enough in session state.

### Failure To Cover

- `Неуспешен избор на термин. No active availability result is ready for slot selection in this chat session`

### Likely Surface

- frontend slot click payload handling
- backend slot selection / session recovery path
- existing persisted scheduling session state

### Steps

1. Confirm when active availability context is discarded.
2. Keep enough availability metadata in session state for a later widget click to map back to the selected slot.
3. If the original availability truly expired, return a scheduling recovery response instead of a raw technical failure.
4. Preserve the Prompt 6 contract: slot click should hand off directly into booking for MVP.

### Verify

- Load slots, wait, click a still-rendered slot, confirm it either proceeds or gracefully refreshes availability.

## Prompt 5 - Add Focused Regression Coverage

### Goal

Lock the observed trace failures into small backend/integration tests.

### Tests To Add

1. Tenant-native script reply on scheduling responses.
2. Relative-date window correctness for `next week` and `two weeks from now`.
3. Text-only specific-day list followed by booking-intent message progresses instead of looping.
4. Late widget click uses preserved availability context or clean recovery.
5. Same-day request returns same-day-aware handling.

## Execution Notes

- Keep this as a narrow follow-up to the scheduling contract work already completed.
- Do not reopen month calendar/day-picker scope.
- Do not introduce dynamic flow configuration.
- Prefer preserving the existing slot-list widget and current hold/conflict logic.
- If the fix sequence is split into multiple implementation prompts, Prompt 2 and Prompt 3 should come before Prompt 4 because they address the highest-value trace regressions.
