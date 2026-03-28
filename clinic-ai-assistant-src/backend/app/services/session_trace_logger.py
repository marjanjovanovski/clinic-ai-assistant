import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)
_TRACE_LOCK = threading.Lock()
_TRACE_FILES: dict[str, Path] = {}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRACE_DIR = BASE_DIR / "runtime_traces"
SETTINGS_PATH = BASE_DIR.parent / "configs" / "settings.env"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _trace_key(tenant: str, session_id: str) -> str:
    return f"{tenant}:{session_id}"


def _sanitize_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _settings_trace_enabled() -> bool:
    if not SETTINGS_PATH.exists():
        return False

    settings = dotenv_values(SETTINGS_PATH)
    userlogging = settings.get("USERLOGGING", "off")
    debug_session_trace = settings.get("DEBUG_SESSION_TRACE", "false")

    userlogging_enabled = str(userlogging).strip().lower() == "on"
    debug_trace_enabled = str(debug_session_trace).strip().lower() == "true"

    return userlogging_enabled and debug_trace_enabled


def is_session_trace_enabled() -> bool:
    return _settings_trace_enabled()


def _resolve_trace_file(tenant: str, session_id: str) -> Path:
    trace_key = _trace_key(tenant, session_id)
    existing_path = _TRACE_FILES.get(trace_key)
    if existing_path:
        return existing_path

    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        f"trace_{timestamp}_{_sanitize_filename_part(tenant)}_"
        f"{_sanitize_filename_part(session_id)}.txt"
    )
    trace_path = TRACE_DIR / filename
    _TRACE_FILES[trace_key] = trace_path

    header = [
        "=" * 50,
        "TRACE START",
        f"timestamp={_utc_now()}",
        f"tenant={tenant}",
        f"session_id={session_id}",
        f"trace_file={trace_path.name}",
        "=" * 50,
        "",
    ]
    trace_path.write_text("\n".join(header), encoding="utf-8")
    return trace_path


def trace_event(tenant: str, session_id: str, event: str, **fields):
    if not is_session_trace_enabled() or not tenant or not session_id:
        return

    try:
        with _TRACE_LOCK:
            trace_path = _resolve_trace_file(tenant, session_id)
            lines = [f"[{_utc_now()}] {event}"]
            for key, value in fields.items():
                if value is None:
                    continue
                if isinstance(value, (dict, list)):
                    rendered = json.dumps(value, ensure_ascii=False)
                else:
                    rendered = str(value)
                lines.append(f"{key}={rendered}")
            lines.append("")
            with trace_path.open("a", encoding="utf-8") as trace_file:
                trace_file.write("\n".join(lines))
                trace_file.write("\n")
    except Exception as exc:
        logger.warning("Session trace write failed: %s", exc)


def get_trace_directory() -> Path:
    return TRACE_DIR
