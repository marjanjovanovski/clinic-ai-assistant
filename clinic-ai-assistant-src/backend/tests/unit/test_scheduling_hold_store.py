from datetime import UTC, datetime, timedelta

from app.services import lead_store, scheduling_hold_store


def _init_tmp_db(tmp_path):
    lead_store.DB_PATH = tmp_path / "assistant_velika.db"
    lead_store.init_leads_db()
    scheduling_hold_store.init_hold_store()


def test_create_slot_hold_persists_active_hold(tmp_path):
    _init_tmp_db(tmp_path)

    hold = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-a",
        hold_minutes=5,
    )

    assert hold is not None
    assert hold["service_id"] == "consultation"
    assert hold["slot_id"] == "mock|slot-1"
    assert hold["session_id"] == "session-a"
    assert hold["status"] == scheduling_hold_store.HOLD_STATUS_ACTIVE
    assert hold["hold_id"]


def test_create_slot_hold_returns_existing_active_hold_for_same_slot(tmp_path):
    _init_tmp_db(tmp_path)

    first = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-a",
        hold_minutes=5,
    )
    second = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-b",
        hold_minutes=5,
    )

    assert second["hold_id"] == first["hold_id"]
    assert second["session_id"] == "session-a"
    assert second["status"] == scheduling_hold_store.HOLD_STATUS_ACTIVE


def test_expire_stale_holds_marks_elapsed_active_hold_as_expired(tmp_path):
    _init_tmp_db(tmp_path)

    created_at = datetime(2026, 3, 27, 10, 0, tzinfo=UTC)
    hold = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-a",
        hold_minutes=5,
        now=created_at,
    )

    expired_count = scheduling_hold_store.expire_stale_holds(
        now=created_at + timedelta(minutes=6),
    )
    expired_hold = scheduling_hold_store.get_slot_hold(
        tenant="milena_dental",
        slot_id="mock|slot-1",
        include_inactive=True,
        now=created_at + timedelta(minutes=6),
    )

    assert expired_count == 1
    assert expired_hold["hold_id"] == hold["hold_id"]
    assert expired_hold["status"] == scheduling_hold_store.HOLD_STATUS_EXPIRED
    assert expired_hold["released_reason"] == "expired_by_time"


def test_update_hold_status_supports_released_and_consumed_states(tmp_path):
    _init_tmp_db(tmp_path)

    hold = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-a",
        hold_minutes=5,
    )

    released = scheduling_hold_store.update_hold_status(
        hold_id=hold["hold_id"],
        status=scheduling_hold_store.HOLD_STATUS_RELEASED,
        released_reason="user_abandoned",
    )
    consumed = scheduling_hold_store.update_hold_status(
        hold_id=hold["hold_id"],
        status=scheduling_hold_store.HOLD_STATUS_CONSUMED,
    )

    assert released["status"] == scheduling_hold_store.HOLD_STATUS_RELEASED
    assert released["released_reason"] == "user_abandoned"
    assert released["released_at"] is not None
    assert consumed["status"] == scheduling_hold_store.HOLD_STATUS_CONSUMED
    assert consumed["consumed_at"] is not None


def test_hold_store_emits_trace_events_for_create_reject_expire_and_consume(tmp_path, monkeypatch):
    _init_tmp_db(tmp_path)
    captured = []

    monkeypatch.setattr(
        scheduling_hold_store,
        "trace_event",
        lambda tenant, session_id, event, **fields: captured.append(
            {
                "tenant": tenant,
                "session_id": session_id,
                "event": event,
                "fields": fields,
            }
        ),
    )

    created_at = datetime(2026, 3, 27, 10, 0, tzinfo=UTC)
    first = scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-a",
        hold_minutes=5,
        now=created_at,
    )
    scheduling_hold_store.create_slot_hold(
        tenant="milena_dental",
        service_id="consultation",
        slot_id="mock|slot-1",
        session_id="session-b",
        hold_minutes=5,
        now=created_at,
    )
    scheduling_hold_store.expire_stale_holds(now=created_at + timedelta(minutes=6))
    scheduling_hold_store.update_hold_status(
        hold_id=first["hold_id"],
        status=scheduling_hold_store.HOLD_STATUS_CONSUMED,
    )

    event_names = [item["event"] for item in captured]
    assert "SCHEDULING_HOLD_CREATED" in event_names
    assert "SCHEDULING_HOLD_REJECTED" in event_names
    assert "SCHEDULING_HOLD_EXPIRED" in event_names
    assert "SCHEDULING_HOLD_CONSUMED" in event_names
