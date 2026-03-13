import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "clinic_ai_assistant.db"


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_leads_db():
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant TEXT NOT NULL,
                session_id TEXT NOT NULL,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                collected_data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(tenant, session_id)
            )
            """
        )
        connection.commit()


def save_lead_checkpoint(tenant: str, session_id: str, state: dict):
    now = datetime.now(timezone.utc).isoformat()
    data = state.get("data", {})

    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO leads (
                tenant,
                session_id,
                contact_name,
                contact_phone,
                contact_email,
                collected_data_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant, session_id) DO UPDATE SET
                contact_name = excluded.contact_name,
                contact_phone = excluded.contact_phone,
                contact_email = excluded.contact_email,
                collected_data_json = excluded.collected_data_json,
                updated_at = excluded.updated_at
            """,
            (
                tenant,
                session_id,
                data.get("name"),
                data.get("phone"),
                data.get("email"),
                json.dumps(state, ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.commit()


def load_lead_checkpoint(tenant: str, session_id: str):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT collected_data_json
            FROM leads
            WHERE tenant = ? AND session_id = ?
            """,
            (tenant, session_id),
        ).fetchone()

    if not row:
        return None

    return json.loads(row["collected_data_json"])
