import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"


class TenantConfigError(Exception):
    pass


class TenantNotFoundError(FileNotFoundError):
    pass


def load_profile_config(tenant: str):
    profile_path = PROFILES_DIR / f"{tenant}.json"

    if not profile_path.exists():
        raise TenantNotFoundError(f"Profile '{tenant}' not found")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as exc:
        raise TenantConfigError(f"Profile '{tenant}' contains invalid JSON") from exc

    actions = profile.get("actions", {})
    allow_booking = actions.get("allow_booking", False)
    collect_fields = actions.get("collect_contact_fields", [])

    if allow_booking and not collect_fields:
        raise TenantConfigError(
            f"Profile '{tenant}' enables booking but does not define collect_contact_fields"
        )

    return profile
