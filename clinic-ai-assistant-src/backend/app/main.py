import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.routes.chat import router as chat_router
from app.services.config_loader import TenantConfigError, TenantNotFoundError, load_profile_config
from app.services.lead_store import init_leads_db

load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is required at startup")

init_leads_db()

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

@app.get("/health")
def health():
    return {"status": "Clinic AI Assistant running"}

@app.get("/config/{tenant}")
def get_config(tenant: str):
    try:
        return load_profile_config(tenant)
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
