import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"


def load_profile_config(tenant: str):
    profile_path = PROFILES_DIR / f"{tenant}.json"

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile '{tenant}' not found")

    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)