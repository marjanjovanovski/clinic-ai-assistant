"""Scheduling-owned persistence for short-lived slot holds."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from app.services import lead_store
from app.services.session_trace_logger import trace_event

HOLD_STATUS_ACTIVE = "active"
HOLD_STATUS_EXPIRED = "expired"
HOLD_STATUS_RELEASED = "released"
HOLD_STATUS_CONSUMED = "consumed"
DEFAULT_HOLD_MINUTES = 5


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _connect():
    db_path = lead_store.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _active_status_case_sql() -> str:
    return (
        "CASE "
        f"WHEN status = '{HOLD_STATUS_ACTIVE}' AND expires_at <= ? THEN '{HOLD_STATUS_EXPIRED}' "
        "ELSE status "
        "END"
    )


def _active_released_reason_case_sql() -> str:
    return (
        "CASE "
        f"WHEN status = '{HOLD_STATUS_ACTIVE}' AND expires_at <= ? "
        "AND (released_reason IS NULL OR released_reason = '') THEN 'expired_by_time' "
        "ELSE released_reason "
        "END"
    )


def init_hold_store() -> None:
    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS scheduling_slot_holds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hold_id TEXT NOT NULL,
                tenant_id INTEGER NOT NULL,
                service_id TEXT NOT NULL,
                slot_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('{HOLD_STATUS_ACTIVE}', '{HOLD_STATUS_EXPIRED}', '{HOLD_STATUS_RELEASED}', '{HOLD_STATUS_CONSUMED}')
                ),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                released_reason TEXT,
                released_at TEXT,
                consumed_at TEXT,
                UNIQUE(hold_id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_slot_holds_tenant_slot_status
            ON scheduling_slot_holds(tenant_id, slot_id, status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_slot_holds_session_status
            ON scheduling_slot_holds(session_id, status)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_slot_holds_expires_at
            ON scheduling_slot_holds(expires_at)
            """
        )
        connection.commit()


def _expire_stale_holds_with_connection(connection, *, now_iso: str) -> int:
    result = connection.execute(
        f"""
        UPDATE scheduling_slot_holds
        SET status = '{HOLD_STATUS_EXPIRED}',
            released_reason = CASE
                WHEN released_reason IS NULL OR released_reason = '' THEN 'expired_by_time'
                ELSE released_reason
            END,
            released_at = COALESCE(released_at, ?)
        WHERE status = '{HOLD_STATUS_ACTIVE}'
          AND expires_at <= ?
        """,
        (now_iso, now_iso),
    )
    return int(result.rowcount or 0)


def expire_stale_holds(*, now: datetime | None = None) -> int:
    effective_now = (now or _utc_now()).isoformat()
    with _connect() as connection:
        stale_rows = connection.execute(
            f"""
            SELECT holds.hold_id, holds.tenant_id, holds.service_id, holds.slot_id, holds.session_id,
                   holds.status, holds.created_at, holds.expires_at, holds.released_reason,
                   holds.released_at, holds.consumed_at, tenants.name AS tenant_name
            FROM scheduling_slot_holds AS holds
            JOIN tenants ON tenants.id = holds.tenant_id
            WHERE holds.status = '{HOLD_STATUS_ACTIVE}'
              AND holds.expires_at <= ?
            """,
            (effective_now,),
        ).fetchall()
        result_count = _expire_stale_holds_with_connection(connection, now_iso=effective_now)
        connection.commit()
        for row in stale_rows:
            hold = _row_to_public_hold(row)
            if isinstance(hold, dict):
                hold["status"] = HOLD_STATUS_EXPIRED
                hold["released_reason"] = hold.get("released_reason") or "expired_by_time"
            _trace_hold_event(
                row["tenant_name"],
                hold,
                "SCHEDULING_HOLD_EXPIRED",
                reason="expired_by_time",
            )
        return result_count


def _tenant_row(connection, tenant: str):
    tenant_row = lead_store._tenant_row_by_name(connection, tenant)
    if tenant_row:
        return tenant_row
    return lead_store._ensure_tenant_row(connection, tenant)


def _row_to_public_hold(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "hold_id": row["hold_id"],
        "tenant_id": row["tenant_id"],
        "service_id": row["service_id"],
        "slot_id": row["slot_id"],
        "session_id": row["session_id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "released_reason": row["released_reason"],
        "released_at": row["released_at"],
        "consumed_at": row["consumed_at"],
    }


def _trace_hold_event(tenant: str, hold: dict | None, event: str, **fields) -> None:
    if not isinstance(hold, dict):
        return
    session_id = hold.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return
    trace_event(
        tenant,
        session_id.strip(),
        event,
        hold_id=hold.get("hold_id"),
        service_id=hold.get("service_id"),
        slot_id=hold.get("slot_id"),
        hold_status=hold.get("status"),
        expires_at=hold.get("expires_at"),
        **fields,
    )


def get_slot_hold(
    *,
    tenant: str,
    slot_id: str,
    session_id: str | None = None,
    include_inactive: bool = False,
    now: datetime | None = None,
) -> dict | None:
    effective_now = (now or _utc_now()).isoformat()
    with _connect() as connection:
        tenant_row = _tenant_row(connection, tenant)
        if not tenant_row:
            return None
        _expire_stale_holds_with_connection(connection, now_iso=effective_now)

        status_sql = _active_status_case_sql()
        reason_sql = _active_released_reason_case_sql()
        query = (
            "SELECT hold_id, tenant_id, service_id, slot_id, session_id, "
            f"{status_sql} AS status, created_at, expires_at, "
            f"{reason_sql} AS released_reason, released_at, consumed_at "
            "FROM scheduling_slot_holds "
            "WHERE tenant_id = ? AND slot_id = ?"
        )
        params: list[object] = [effective_now, effective_now, tenant_row["id"], slot_id]
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if not include_inactive:
            query += " AND status = ?"
            params.append(HOLD_STATUS_ACTIVE)
        query += " ORDER BY id DESC LIMIT 1"
        row = connection.execute(query, tuple(params)).fetchone()
        return _row_to_public_hold(row)


def create_slot_hold(
    *,
    tenant: str,
    service_id: str,
    slot_id: str,
    session_id: str,
    hold_minutes: int = DEFAULT_HOLD_MINUTES,
    now: datetime | None = None,
) -> dict:
    if hold_minutes <= 0:
        raise ValueError("hold_minutes must be positive")

    effective_now = now or _utc_now()
    created_at = effective_now.isoformat()
    expires_at = (effective_now + timedelta(minutes=hold_minutes)).isoformat()
    hold_id = str(uuid.uuid4())

    with _connect() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        tenant_row = _tenant_row(connection, tenant)
        _expire_stale_holds_with_connection(connection, now_iso=effective_now.isoformat())
        existing_hold = connection.execute(
            """
            SELECT hold_id, tenant_id, service_id, slot_id, session_id, status, created_at, expires_at,
                   released_reason, released_at, consumed_at
            FROM scheduling_slot_holds
            WHERE tenant_id = ?
              AND slot_id = ?
              AND status = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (tenant_row["id"], slot_id, HOLD_STATUS_ACTIVE),
        ).fetchone()
        if existing_hold:
            existing_public_hold = _row_to_public_hold(existing_hold)
            _trace_hold_event(
                tenant,
                existing_public_hold,
                "SCHEDULING_HOLD_REJECTED",
                reason="slot_already_held",
                requested_session_id=session_id,
            )
            return existing_public_hold

        connection.execute(
            """
            INSERT INTO scheduling_slot_holds (
                hold_id,
                tenant_id,
                service_id,
                slot_id,
                session_id,
                status,
                created_at,
                expires_at,
                released_reason,
                released_at,
                consumed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                hold_id,
                tenant_row["id"],
                service_id,
                slot_id,
                session_id,
                HOLD_STATUS_ACTIVE,
                created_at,
                expires_at,
            ),
        )
        connection.commit()
        created_hold = connection.execute(
            """
            SELECT hold_id, tenant_id, service_id, slot_id, session_id, status, created_at, expires_at,
                   released_reason, released_at, consumed_at
            FROM scheduling_slot_holds
            WHERE hold_id = ?
            """,
            (hold_id,),
        ).fetchone()
        public_hold = _row_to_public_hold(created_hold)
        _trace_hold_event(
            tenant,
            public_hold,
            "SCHEDULING_HOLD_CREATED",
            hold_minutes=hold_minutes,
        )
        return public_hold


def update_hold_status(
    *,
    hold_id: str,
    status: str,
    released_reason: str | None = None,
    now: datetime | None = None,
) -> dict | None:
    if status not in {HOLD_STATUS_ACTIVE, HOLD_STATUS_EXPIRED, HOLD_STATUS_RELEASED, HOLD_STATUS_CONSUMED}:
        raise ValueError("invalid hold status")

    effective_now = (now or _utc_now()).isoformat()
    released_at = effective_now if status in {HOLD_STATUS_EXPIRED, HOLD_STATUS_RELEASED} else None
    consumed_at = effective_now if status == HOLD_STATUS_CONSUMED else None

    with _connect() as connection:
        connection.execute(
            """
            UPDATE scheduling_slot_holds
            SET status = ?,
                released_reason = ?,
                released_at = COALESCE(?, released_at),
                consumed_at = COALESCE(?, consumed_at)
            WHERE hold_id = ?
            """,
            (
                status,
                released_reason,
                released_at,
                consumed_at,
                hold_id,
            ),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT hold_id, tenant_id, service_id, slot_id, session_id, status, created_at, expires_at,
                   released_reason, released_at, consumed_at
            FROM scheduling_slot_holds
            WHERE hold_id = ?
            """,
            (hold_id,),
        ).fetchone()
        public_hold = _row_to_public_hold(row)
        if isinstance(public_hold, dict):
            if status == HOLD_STATUS_CONSUMED:
                event_name = "SCHEDULING_HOLD_CONSUMED"
            elif status == HOLD_STATUS_RELEASED:
                event_name = "SCHEDULING_HOLD_RELEASED"
            elif status == HOLD_STATUS_EXPIRED:
                event_name = "SCHEDULING_HOLD_EXPIRED"
            else:
                event_name = "SCHEDULING_HOLD_UPDATED"
            tenant_row = connection.execute(
                "SELECT name FROM tenants WHERE id = ?",
                (public_hold["tenant_id"],),
            ).fetchone()
            if tenant_row and tenant_row["name"]:
                _trace_hold_event(
                    tenant_row["name"],
                    public_hold,
                    event_name,
                    reason=released_reason,
                )
        return public_hold
