"""Shared chat/session-state helpers for the chat runtime."""

from __future__ import annotations

import uuid

from app.services.lead_store import load_lead_checkpoint

SESSION_STATE = {}
INTERACTION_HISTORY = {}
MAX_INTERACTION_HISTORY = 6
MAX_CONTEXT_INTERACTIONS = 1


def _session_key(tenant: str, session_id: str) -> str:
    return f"{tenant}:{session_id}"


def _normalize_session_id(session_id: str | None) -> str:
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()

    return str(uuid.uuid4())


def _load_session_state(tenant: str, session_id: str) -> dict | None:
    session_key = _session_key(tenant, session_id)
    state = SESSION_STATE.get(session_key)
    persisted_state = load_lead_checkpoint(tenant, session_id)

    if state is None:
        state = persisted_state
    elif isinstance(state, dict) and isinstance(persisted_state, dict):
        persisted_data = persisted_state.get("data")
        if isinstance(persisted_data, dict):
            authoritative_data = {}
            for field_name, value in persisted_data.items():
                if isinstance(value, str) and value.strip():
                    authoritative_data[field_name] = value
            state["data"] = authoritative_data

        persisted_stage = persisted_state.get("stage")
        if persisted_stage in {"awaiting_booking_confirmation", "collecting_contact", "completed"}:
            state["stage"] = persisted_stage

        if persisted_state.get("service_id"):
            state["service_id"] = persisted_state.get("service_id")

        if persisted_state.get("next_field") is not None:
            state["next_field"] = persisted_state.get("next_field")

    if state:
        SESSION_STATE[session_key] = state

    return state


def _stage_name(state: dict | None) -> str | None:
    if not isinstance(state, dict):
        return None

    return state.get("stage")


def _status_for_stage(stage: str | None) -> str:
    if stage == "collecting_contact":
        return "collecting_contact"
    if stage == "completed":
        return "completed"
    return "active"


def _recent_interactions(session_key: str) -> list[dict]:
    return INTERACTION_HISTORY.get(session_key, [])


def _last_interaction(session_key: str) -> dict | None:
    history = _recent_interactions(session_key)
    if not history:
        return None

    return history[-1]
