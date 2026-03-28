import os
from pathlib import Path

from app.routes.chat import router as chat_router
from app.routes.manual_verification import router as manual_verification_router
from app.routes.scheduling import router as scheduling_router
from app.services.config_loader import (
    TenantConfigError,
    TenantNotFoundError,
    load_profile_config,
    load_public_profile_config,
)
from app.services.lead_store import init_leads_db
from app.services.scheduling_hold_store import init_hold_store
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is required at startup")

init_leads_db()
init_hold_store()

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip()
    for origin in allowed_origins_env.split(",")
    if origin.strip()
]
if not allowed_origins:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(manual_verification_router)
app.include_router(scheduling_router)

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


@app.get("/health")
def health():
    return {"status": "Clinic AI Assistant running"}


@app.get("/config/{tenant}")
def get_config(tenant: str):
    try:
        load_profile_config(tenant)
        return load_public_profile_config(tenant)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")


@app.get("/agent/{tenant}")
def serve_agent(tenant: str):
    try:
        load_profile_config(tenant)
        return FileResponse(str(INDEX_FILE))
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")
    except TenantConfigError:
        raise HTTPException(status_code=500, detail=f"Tenant '{tenant}' configuration is invalid")
