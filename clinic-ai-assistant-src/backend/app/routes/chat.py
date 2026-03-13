from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.services.ai_agent import AIInferenceError, generate_reply, get_session_status
from app.services.config_loader import TenantConfigError, TenantNotFoundError

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


@router.post("/chat")
def chat(payload: ChatRequest, tenant: str = Query(...)):
    try:
        reply, session_id = generate_reply(tenant, payload.message, payload.session_id)
        session_status = get_session_status(tenant, session_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
    except AIInferenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "received_message": payload.message,
        "tenant": tenant,
        "session_id": session_id,
        "session_status": session_status,
        "reply": reply
    }
