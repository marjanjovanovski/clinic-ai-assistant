from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.ai_agent import AIInferenceError, generate_reply
from app.services.config_loader import TenantConfigError, TenantNotFoundError

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/chat")
def chat(payload: ChatRequest, tenant: str = Query(...)):
    try:
        reply, session_id = generate_reply(tenant, payload.message, payload.session_id)
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
        "reply": reply
    }
