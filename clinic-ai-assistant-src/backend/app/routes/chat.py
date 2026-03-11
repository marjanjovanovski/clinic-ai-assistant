from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.ai_agent import generate_reply

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(payload: ChatRequest, tenant: str = Query(...)):
    reply = generate_reply(tenant, payload.message)

    return {
        "received_message": payload.message,
        "tenant": tenant,
        "reply": reply
    }