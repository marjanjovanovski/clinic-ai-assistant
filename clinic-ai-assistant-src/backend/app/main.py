from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from app.routes.chat import router as chat_router
from app.services.config_loader import load_profile_config

load_dotenv()

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
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")


@app.get("/agent/{tenant}")
def serve_agent(tenant: str):
    try:
        load_profile_config(tenant)
        return FileResponse(str(INDEX_FILE))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")