# REQ-BOOKING-FLOW-001 Coverage Map

This artifact tracks requirement behavior, current implementation anchors, verification evidence, and any explicit scope limits.

Status values:
- `covered`: behavior is implemented and verified by a specific test
- `to add`: behavior is implemented or expected, but verification still needs to be added
- `out of scope`: behavior is intentionally not part of the current requirement contract

## Core Flow

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Suggested bookable service enters `awaiting_booking_confirmation` | `backend/app/services/ai_agent.py` model `suggest_service` branch | `backend/test_req_booking_flow.py::test_main_booking_path_requires_explicit_confirmation_and_persisted_completion` | `covered` |
| Explicit confirmation starts `collecting_contact` | `backend/app/services/ai_agent.py` booking confirmation branch | `backend/test_req_booking_flow.py::test_main_booking_path_requires_explicit_confirmation_and_persisted_completion` | `covered` |
| Contact fields are collected in order `name -> phone -> email` | `backend/app/services/ai_agent.py` active booking lock and next-field progression | `backend/test_req_booking_flow.py::test_main_booking_path_requires_explicit_confirmation_and_persisted_completion` | `covered` |
| Completion depends on persistence verification, not in-memory state alone | `backend/app/services/ai_agent.py` `_persisted_fields_match`, `_recover_from_persistence_failure`; `backend/app/services/lead_store.py` `save_lead_checkpoint` | `backend/test_req_booking_flow.py::test_main_booking_path_requires_explicit_confirmation_and_persisted_completion` | `covered` |
| Persisted lead state is authoritative on reload | `backend/app/services/ai_agent.py` `_load_session_state`; `backend/app/services/lead_store.py` `_hydrate_state_from_row` | `backend/test_req_booking_flow.py::test_main_booking_path_requires_explicit_confirmation_and_persisted_completion` | `covered` |

## Name Capture

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Normal valid names are accepted | `backend/app/services/ai_agent.py` `_is_valid_contact_field_value` during `name` collection | `backend/test_req_booking_flow.py::test_valid_name_progresses_booking_flow` | `covered` |
| Uncertain names can enter candidate confirmation mode | `backend/app/services/ai_agent.py` unknown-name recovery branch | `backend/test_req_booking_flow.py::test_unknown_name_confirmation_accepts_candidate_value` | `covered` |
| Candidate rejection triggers repeat-name fallback | `backend/app/services/ai_agent.py` unknown-name repeat mode | `backend/test_req_booking_flow.py::test_unknown_name_rejection_forces_repeat_until_valid_name` | `covered` |
| Retry path accepts a second attempt such as `Vasilie` | `backend/app/services/ai_agent.py` normalized freeform retry branch | `backend/test_req_booking_flow.py::test_unknown_name_rejection_forces_repeat_until_valid_name` | `covered` |
| Conversational filler is not silently stored as a name | `backend/app/services/ai_agent.py` booking input gating | `backend/test_req_booking_flow.py::test_name_field_rejects_conversational_filler` | `covered` |

## Clarifications And Bundles

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Field-level clarification stays inside booking and resumes the same field | `backend/app/services/ai_agent.py` `_is_field_level_clarification`, `_field_clarification_with_resume` | `backend/test_req_booking_flow.py::test_field_level_clarification_stays_inside_booking_flow` | `covered` |
| Booking-scope clarification stays inside booking and redirects back to active field | `backend/app/services/ai_agent.py` `_contact_collection_redirect_reply` | `backend/test_req_booking_flow.py::test_booking_scope_clarification_resumes_current_field` | `covered` |
| Explicit bundled contact payloads can fill multiple fields safely | `backend/app/services/ai_agent.py` `_should_attempt_contact_bundle_parse`, `_extract_contact_fields_from_message` | `backend/test_req_booking_flow.py::test_explicit_contact_bundle_advances_multiple_fields` | `covered` |
| Casual or ambiguous text is not over-parsed as bundled contact data | `backend/app/services/ai_agent.py` bundle-parse gating | `backend/test_req_booking_flow.py::test_casual_text_is_not_overparsed_as_contact_bundle` | `covered` |

## Persistence Recovery

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Missing required persisted fields block completion and re-prompt | `backend/app/services/lead_store.py` required-field verification; `backend/app/services/ai_agent.py` completion retry | `backend/test_req_booking_flow.py::test_missing_persisted_required_field_blocks_completion` | `covered` |
| Mismatched persisted values block completion and re-prompt | `backend/app/services/lead_store.py` mismatched-field detection | `backend/test_req_booking_flow.py::test_mismatched_persisted_value_blocks_completion` | `covered` |
| Save failures never return a false completed booking | `backend/app/services/lead_store.py` error result; `backend/app/services/ai_agent.py` recovery path | `backend/test_req_booking_flow.py::test_save_failure_blocks_completion_and_keeps_booking_active` | `covered` |

## Edit After Completion

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Completed fields can enter edit-confirm flow | `backend/app/services/ai_agent.py` `__booking_edit__:` handling | `backend/test_req_booking_flow.py::test_completed_name_edit_can_be_confirmed_and_resaved` | `covered` |
| Edit confirmation accepts replacement and persists it | `backend/app/services/ai_agent.py` edit `value` branch | `backend/test_req_booking_flow.py::test_completed_name_edit_can_be_confirmed_and_resaved` | `covered` |
| Edit rejection cancels without changing stored value | `backend/app/services/ai_agent.py` `_edit_record_cancelled_reply` branch | `backend/test_req_booking_flow.py::test_completed_phone_edit_can_be_cancelled` | `covered` |
| Invalid replacement does not overwrite persisted value | `backend/app/services/ai_agent.py` edit invalid-value branch | `backend/test_req_booking_flow.py::test_completed_email_edit_rejects_invalid_replacement_before_resave` | `covered` |

## Frontend Contract

| Behavior | Implementation Anchor | Verification | Status |
| --- | --- | --- | --- |
| Booking progress container exists and is hidden until progress is present | `frontend/index.html` progress markup and `updateBookingProgress` | `backend/test_frontend_booking_ui.py::test_agent_page_includes_booking_progress_shell` | `covered` |
| Active field highlighting and completed editable chips are wired in the client | `frontend/index.html` `updateBookingProgress` | `backend/test_frontend_booking_ui.py::test_booking_progress_script_wires_active_and_editable_states` | `covered` |
| Edit trigger sends internal `__booking_edit__:<field>` message without user echo | `frontend/index.html` `beginBookingFieldEdit` | `backend/test_frontend_booking_ui.py::test_frontend_uses_internal_booking_edit_message` | `covered` |
| Reset starts a new local session only | `frontend/index.html` `resetConversation` | `backend/test_frontend_booking_ui.py::test_reset_behavior_is_local_session_rollover_only` | `covered` |

## Explicit Scope Limits

| Behavior | Reason | Status |
| --- | --- | --- |
| Backend deletion of persisted lead rows on reset | Current frontend contract resets local session only; no backend delete/reset endpoint exists | `out of scope` |
