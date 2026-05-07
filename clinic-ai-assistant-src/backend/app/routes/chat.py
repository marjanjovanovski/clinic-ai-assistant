from app.services.ai_agent import (
    AIInferenceError,
    build_runtime_inspector_payload,
    execute_flow_entry_action,
    generate_reply,
    get_booking_progress,
    get_session_status,
)
from app.services.config_loader import TenantConfigError, TenantNotFoundError
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("message must not be empty")
        return trimmed

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        trimmed = value.strip()
        return trimmed or None


class ChatActionRequest(BaseModel):
    action: str = Field(..., max_length=64)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        trimmed = value.strip().casefold()
        if trimmed not in {"catalog", "availability", "booking"}:
            raise ValueError("action must be one of: catalog, availability, booking")
        return trimmed

    @field_validator("session_id")
    @classmethod
    def validate_action_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        trimmed = value.strip()
        return trimmed or None


@router.post("/chat")
def chat(payload: ChatRequest, tenant: str = Query(...)):
    try:
        response_payload, session_id = generate_reply(tenant, payload.message, payload.session_id)
        session_status = get_session_status(tenant, session_id)
        booking_progress = get_booking_progress(tenant, session_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except AIInferenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "received_message": payload.message,
        "tenant": tenant,
        "session_id": session_id,
        "session_status": session_status,
        "booking_progress": booking_progress,
        "reply": response_payload.get("reply"),
        "widget_payload": response_payload.get("widget_payload"),
        "inspector_payload": build_runtime_inspector_payload(
            tenant,
            session_id,
            response_payload=response_payload,
            session_status=session_status,
            booking_progress=booking_progress,
            last_user_message=payload.message,
        ),
    }


@router.post("/chat/action")
def chat_action(payload: ChatActionRequest, tenant: str = Query(...)):
    try:
        result = execute_flow_entry_action(tenant, payload.action, payload.session_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found") from exc
    except TenantConfigError as exc:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid") from exc
    except AIInferenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "received_action": payload.action,
        "tenant": tenant,
        **result,
    }
