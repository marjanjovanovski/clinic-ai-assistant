import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.services.session_trace_logger import trace_event


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "assistant_velika.db"
DEFAULT_TENANT_NAME = "milena_dental"
DEFAULT_TENANT_UNIQUE_IDENTIFIER = "milena_dental"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _normalize_saved_value(value):
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    return normalized or None


def _table_columns(connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _tenant_row_by_name(connection, tenant: str):
    return connection.execute(
        """
        SELECT id, unique_identifier, name
        FROM tenants
        WHERE name = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (tenant,),
    ).fetchone()


def _ensure_tenant_row(connection, tenant: str):
    tenant_row = _tenant_row_by_name(connection, tenant)
    if tenant_row:
        return tenant_row

    connection.execute(
        """
        INSERT INTO tenants (
            unique_identifier,
            name,
            comment,
            phone,
            email,
            primary_contact_name,
            secondary_contact_name,
            date_registered
        )
        VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, ?)
        """,
        (
            tenant,
            tenant,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return _tenant_row_by_name(connection, tenant)


def _fetch_persisted_lead(connection, tenant: str, session_id: str):
    tenant_row = _tenant_row_by_name(connection, tenant)
    if not tenant_row:
        return None

    return connection.execute(
        """
        SELECT contact_name, contact_phone, contact_email, collected_data_json
        FROM leads
        WHERE tenant_id = ? AND session_id = ?
        """,
        (tenant_row["id"], session_id),
    ).fetchone()


def _hydrate_state_from_row(row):
    raw_state = row["collected_data_json"]

    try:
        state = json.loads(raw_state) if raw_state else {}
    except (TypeError, json.JSONDecodeError):
        state = {}

    if not isinstance(state, dict):
        state = {}

    data = state.get("data")
    if not isinstance(data, dict):
        data = {}
        state["data"] = data

    persisted_data = {
        "name": _normalize_saved_value(row["contact_name"]),
        "phone": _normalize_saved_value(row["contact_phone"]),
        "email": _normalize_saved_value(row["contact_email"]),
    }

    for field_name, value in persisted_data.items():
        if value is not None:
            data[field_name] = value

    return state


def _seed_default_tenant(connection) -> None:
    connection.execute(
        """
        INSERT INTO tenants (
            unique_identifier,
            name,
            comment,
            phone,
            email,
            primary_contact_name,
            secondary_contact_name,
            date_registered
        )
        SELECT ?, ?, NULL, NULL, NULL, NULL, NULL, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM tenants
            WHERE name = ?
        )
        """,
        (
            DEFAULT_TENANT_UNIQUE_IDENTIFIER,
            DEFAULT_TENANT_NAME,
            datetime.now(timezone.utc).isoformat(),
            DEFAULT_TENANT_NAME,
        ),
    )


def _backfill_lead_tenant_ids(connection) -> None:
    lead_columns = _table_columns(connection, "leads")
    if "tenant_id" not in lead_columns or "tenant" not in lead_columns:
        return

    connection.execute(
        """
        UPDATE leads
        SET tenant_id = (
            SELECT tenants.id
            FROM tenants
            WHERE tenants.name = leads.tenant
            ORDER BY tenants.id ASC
            LIMIT 1
        )
        WHERE tenant_id IS NULL
        """
    )

    missing_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM leads
        WHERE tenant_id IS NULL
        """
    ).fetchone()[0]
    if missing_count:
        raise RuntimeError(
            f"Lead migration halted: {missing_count} lead rows could not be matched to a tenant_id."
        )


def _rebuild_leads_table_without_legacy_tenant(connection) -> None:
    lead_columns = _table_columns(connection, "leads")
    if "tenant" not in lead_columns:
        return

    connection.execute("DROP TABLE IF EXISTS leads__new")
    connection.execute(
        """
        CREATE TABLE leads__new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            collected_data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(tenant_id, session_id),
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO leads__new (
            id,
            tenant_id,
            session_id,
            contact_name,
            contact_phone,
            contact_email,
            collected_data_json,
            created_at,
            updated_at
        )
        SELECT
            id,
            tenant_id,
            session_id,
            contact_name,
            contact_phone,
            contact_email,
            collected_data_json,
            created_at,
            updated_at
        FROM leads
        """
    )
    connection.execute("DROP TABLE leads")
    connection.execute("ALTER TABLE leads__new RENAME TO leads")


def init_leads_db():
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unique_identifier TEXT NOT NULL,
                name TEXT NOT NULL,
                comment TEXT,
                phone TEXT,
                email TEXT,
                primary_contact_name TEXT,
                secondary_contact_name TEXT,
                date_registered TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_unique_identifier
            ON tenants(unique_identifier)
            """
        )
        _seed_default_tenant(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,
                collected_data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, session_id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
            """
        )
        lead_columns = _table_columns(connection, "leads")
        if "tenant_id" not in lead_columns:
            connection.execute(
                """
                ALTER TABLE leads
                ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)
                """
            )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_leads_tenant_id
            ON leads(tenant_id)
            """
        )
        _backfill_lead_tenant_ids(connection)
        _rebuild_leads_table_without_legacy_tenant(connection)
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_leads_tenant_id
            ON leads(tenant_id)
            """
        )
        foreign_key_violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        if foreign_key_violations:
            raise RuntimeError(
                f"Lead migration halted: foreign key integrity check failed with {len(foreign_key_violations)} violation(s)."
            )
        connection.commit()


def save_lead_checkpoint(tenant: str, session_id: str, state: dict, required_fields: list[str] | None = None):
    now = datetime.now(timezone.utc).isoformat()
    data = state.get("data", {})
    stage = state.get("stage")
    required_fields = [field_name for field_name in (required_fields or []) if field_name in {"name", "phone", "email"}]
    expected_data = {
        "name": _normalize_saved_value(data.get("name")),
        "phone": _normalize_saved_value(data.get("phone")),
        "email": _normalize_saved_value(data.get("email")),
    }

    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_SAVE",
        action="attempt",
        stage=stage,
        data=data,
        required_fields=required_fields,
    )

    try:
        with _connect() as connection:
            tenant_row = _ensure_tenant_row(connection, tenant)
            connection.execute(
                """
                INSERT INTO leads (
                    tenant_id,
                    session_id,
                    contact_name,
                    contact_phone,
                    contact_email,
                    collected_data_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, session_id) DO UPDATE SET
                    contact_name = excluded.contact_name,
                    contact_phone = excluded.contact_phone,
                    contact_email = excluded.contact_email,
                    collected_data_json = excluded.collected_data_json,
                    updated_at = excluded.updated_at
                """,
                (
                    tenant_row["id"],
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
            persisted_row = _fetch_persisted_lead(connection, tenant, session_id)
    except sqlite3.Error as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="lead_store.save_lead_checkpoint",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        logger.exception("Failed to save lead checkpoint")
        return {
            "success": False,
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "persisted_data": {},
            "state_saved": False,
        }

    if not persisted_row:
        trace_event(
            tenant,
            session_id,
            "CHECKPOINT_SAVE",
            action="failure",
            stage=stage,
            reason="missing_row_after_save",
        )
        return {
            "success": False,
            "stage": stage,
            "error_type": "MissingPersistedRow",
            "error": "Lead row missing after checkpoint save.",
            "persisted_data": {},
            "state_saved": False,
        }

    persisted_data = {
        "name": _normalize_saved_value(persisted_row["contact_name"]),
        "phone": _normalize_saved_value(persisted_row["contact_phone"]),
        "email": _normalize_saved_value(persisted_row["contact_email"]),
    }

    try:
        persisted_state = json.loads(persisted_row["collected_data_json"])
        state_saved = isinstance(persisted_state, dict)
    except (TypeError, json.JSONDecodeError):
        persisted_state = None
        state_saved = False

    mismatched_fields = [
        field_name
        for field_name, expected_value in expected_data.items()
        if field_name in required_fields and expected_value is not None and persisted_data.get(field_name) != expected_value
    ]

    missing_required_fields = [
        field_name for field_name in required_fields
        if not persisted_data.get(field_name)
    ]

    success = state_saved and not mismatched_fields and not missing_required_fields

    trace_event(
        tenant,
        session_id,
        "DB_UPDATE",
        stage=stage,
        contact_name=persisted_data.get("name"),
        contact_phone=persisted_data.get("phone"),
        contact_email=persisted_data.get("email"),
    )

    trace_event(
        tenant,
        session_id,
        "LEAD_FINAL_SAVE" if stage == "completed" else "CHECKPOINT_SAVE",
        action="success" if success else "failure",
        stage=stage,
        required_fields=required_fields,
        persisted_data=persisted_data,
        missing_required_fields=missing_required_fields,
        mismatched_fields=mismatched_fields,
        state_saved=state_saved,
    )

    return {
        "success": success,
        "stage": stage,
        "required_fields": required_fields,
        "persisted_data": persisted_data,
        "persisted_state": persisted_state,
        "state_saved": state_saved,
        "missing_required_fields": missing_required_fields,
        "mismatched_fields": mismatched_fields,
    }


def load_lead_checkpoint(tenant: str, session_id: str):
    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_LOAD",
        action="attempt",
    )

    try:
        with _connect() as connection:
            row = _fetch_persisted_lead(connection, tenant, session_id)
    except sqlite3.Error as exc:
        trace_event(
            tenant,
            session_id,
            "ERROR",
            source="lead_store.load_lead_checkpoint",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        logger.exception("Failed to load lead checkpoint")
        raise

    if not row:
        trace_event(
            tenant,
            session_id,
            "CHECKPOINT_LOAD",
            action="miss",
        )
        return None

    state = _hydrate_state_from_row(row)
    trace_event(
        tenant,
        session_id,
        "CHECKPOINT_LOAD",
        action="hit",
        stage=state.get("stage"),
        state=state,
    )
    return state
