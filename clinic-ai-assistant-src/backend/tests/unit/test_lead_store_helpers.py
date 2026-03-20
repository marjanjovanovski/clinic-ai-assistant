import json
import sqlite3

import pytest

from app.services import lead_store


def test_normalize_saved_value_trims_strings_and_drops_blank_values():
    assert lead_store._normalize_saved_value("  Marjan  ") == "Marjan"
    assert lead_store._normalize_saved_value("   ") is None
    assert lead_store._normalize_saved_value(None) is None


def test_hydrate_state_from_row_recovers_dict_and_overlays_persisted_contact_fields():
    row = {
        "contact_name": "  Marjan  ",
        "contact_phone": "070000000",
        "contact_email": "mail@test.mk",
        "collected_data_json": json.dumps({"stage": "collecting_contact", "data": {"name": "Old Name"}}),
    }

    state = lead_store._hydrate_state_from_row(row)

    assert state["stage"] == "collecting_contact"
    assert state["data"] == {
        "name": "Marjan",
        "phone": "070000000",
        "email": "mail@test.mk",
    }


def test_hydrate_state_from_row_tolerates_invalid_json_and_missing_data_dict():
    row = {
        "contact_name": "Marjan",
        "contact_phone": None,
        "contact_email": None,
        "collected_data_json": "{not-json",
    }

    state = lead_store._hydrate_state_from_row(row)

    assert state == {"data": {"name": "Marjan"}}


@pytest.fixture
def isolated_db(monkeypatch, tmp_path):
    db_path = tmp_path / "lead_store_unit.db"
    monkeypatch.setattr(lead_store, "DB_PATH", db_path)
    lead_store.init_leads_db()
    return db_path


def test_save_lead_checkpoint_ignores_unknown_required_fields_and_succeeds(isolated_db):
    result = lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-1",
        {"stage": "collecting_contact", "data": {"name": "Marjan"}},
        required_fields=["name", "unknown_field"],
    )

    assert result["success"] is True
    assert result["required_fields"] == ["name"]
    assert result["persisted_data"]["name"] == "Marjan"


def test_save_lead_checkpoint_reports_state_saved_false_for_non_object_json(monkeypatch, isolated_db):
    original_fetch = lead_store._fetch_persisted_lead

    def fake_fetch(connection, tenant, session_id):
        row = original_fetch(connection, tenant, session_id)
        return {
            "contact_name": row["contact_name"],
            "contact_phone": row["contact_phone"],
            "contact_email": row["contact_email"],
            "collected_data_json": '["not", "an", "object"]',
        }

    monkeypatch.setattr(lead_store, "_fetch_persisted_lead", fake_fetch)

    result = lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-non-object-state",
        {"stage": "collecting_contact", "data": {"name": "Marjan"}},
        required_fields=["name"],
    )

    assert result["success"] is False
    assert result["state_saved"] is False
    assert result["persisted_state"] == ["not", "an", "object"]


def test_load_lead_checkpoint_returns_hydrated_persisted_truth(isolated_db):
    lead_store.save_lead_checkpoint(
        "milena_dental",
        "session-load",
        {"stage": "completed", "data": {"name": "Ignored", "phone": "070000000"}},
    )

    with sqlite3.connect(lead_store.DB_PATH) as connection:
        connection.execute(
            """
            UPDATE leads
            SET contact_name = ?, contact_email = ?, collected_data_json = ?
            WHERE tenant = ? AND session_id = ?
            """,
            (
                "Marjan",
                "mail@test.mk",
                json.dumps({"stage": "completed", "data": {"name": "Stale Name"}}),
                "milena_dental",
                "session-load",
            ),
        )
        connection.commit()

    loaded = lead_store.load_lead_checkpoint("milena_dental", "session-load")

    assert loaded["data"] == {
        "name": "Marjan",
        "phone": "070000000",
        "email": "mail@test.mk",
    }
