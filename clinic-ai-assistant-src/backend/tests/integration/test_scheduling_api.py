# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import importlib

from fastapi.testclient import TestClient


def _mock_profile_loader(real_loader):
    def _load_profile(tenant: str):
        profile = real_loader(tenant)
        if tenant == "milena_dental":
            profile = dict(profile)
            scheduling = dict(profile.get("scheduling") or {})
            scheduling["provider"] = "mock"
            profile["scheduling"] = scheduling
        return profile

    return _load_profile


def _build_client(monkeypatch, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.services import lead_store, session_trace_logger

    monkeypatch.setattr(lead_store, "DB_PATH", tmp_path / "scheduling.db")
    monkeypatch.setattr(session_trace_logger, "TRACE_DIR", tmp_path / "runtime_traces")
    monkeypatch.setattr(session_trace_logger, "SETTINGS_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(session_trace_logger, "is_session_trace_enabled", lambda: False)

    import app.services.config_loader as config_loader_module
    import app.services.scheduling.service as scheduling_service_module

    mocked_loader = _mock_profile_loader(config_loader_module.load_profile_config)
    monkeypatch.setattr(config_loader_module, "load_profile_config", mocked_loader)
    monkeypatch.setattr(scheduling_service_module, "load_profile_config", mocked_loader)

    import app.main as main_module

    importlib.reload(main_module)
    return TestClient(main_module.app)


def test_scheduling_config_endpoint_returns_safe_public_config(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.get("/scheduling/config/milena_dental")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["provider"] == "mock"
    assert payload["timezone"] == "Europe/Skopje"
    assert payload["slot_duration_minutes"] == 30
    assert "providers" not in payload


def test_scheduling_availability_endpoint_returns_mock_slots(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post(
        "/scheduling/availability?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-23",
            "date_to": "2026-03-24",
            "timezone": "Europe/Skopje",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert len(payload["slots"]) == 6
    assert payload["slots"][0]["slot_id"].startswith("mock|")
    assert payload["slots"][0]["display_label"].endswith("09:00")


def test_scheduling_booking_endpoint_confirms_selected_mock_slot(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    availability = client.post(
        "/scheduling/availability?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-23",
            "date_to": "2026-03-24",
            "timezone": "Europe/Skopje",
        },
    ).json()

    response = client.post(
        "/scheduling/book?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "slot_id": availability["slots"][0]["slot_id"],
            "patient_name": "Marjan",
            "patient_phone": "070000000",
            "patient_email": "mail@test.mk",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "confirmed"
    assert payload["provider"] == "mock"
    assert payload["booking_id"].startswith("mock-booking-")
    assert "slot_id" in payload["source_payload"]


def test_scheduling_select_slot_endpoint_starts_contact_collection_from_session_state(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    from app.services import ai_agent

    availability = client.post(
        "/scheduling/availability?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-23",
            "date_to": "2026-03-24",
            "timezone": "Europe/Skopje",
        },
    ).json()

    session_id = "slot-selection-session"
    session_key = ai_agent._session_key("milena_dental", session_id)
    ai_agent.SESSION_STATE[session_key] = {
        "stage": "active",
        "scheduling": {
            "operation": "availability_lookup",
            "status": "completed",
            "reason": "availability_lookup_completed",
            "capability_state": {
                "service_id": "consultation",
            },
            "output_payload": {
                "result": availability,
            },
            "booking_handoff_ready": True,
        },
    }

    response = client.post(
        "/scheduling/select-slot?tenant=milena_dental",
        json={
            "session_id": session_id,
            "service_id": "consultation",
            "slot_id": availability["slots"][0]["slot_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_action"] == "collect_contact"
    assert payload["session_status"] == "collecting_contact"
    assert payload["booking_progress"]["next_field"] == "name"
    assert payload["selected_slot"]["slot_id"] == availability["slots"][0]["slot_id"]


def test_scheduling_select_slot_rejects_slot_not_in_active_session_result(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    from app.services import ai_agent

    session_id = "slot-selection-conflict"
    session_key = ai_agent._session_key("milena_dental", session_id)
    ai_agent.SESSION_STATE[session_key] = {
        "stage": "active",
        "scheduling": {
            "operation": "availability_lookup",
            "status": "completed",
            "reason": "availability_lookup_completed",
            "capability_state": {
                "service_id": "consultation",
            },
            "output_payload": {
                "result": {
                    "provider": "mock",
                    "slots": [{"slot_id": "mock|slot-1"}],
                },
            },
            "booking_handoff_ready": True,
        },
    }

    response = client.post(
        "/scheduling/select-slot?tenant=milena_dental",
        json={
            "session_id": session_id,
            "service_id": "consultation",
            "slot_id": "mock|slot-9",
        },
    )

    assert response.status_code == 409
    assert "Selected slot is not part of the active availability result" in response.json()["detail"]


def test_scheduling_availability_rejects_reversed_date_range(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    response = client.post(
        "/scheduling/availability?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-24",
            "date_to": "2026-03-23",
            "timezone": "Europe/Skopje",
        },
    )

    assert response.status_code == 400
    assert "date_from must be on or before date_to" in response.json()["detail"]


def test_scheduling_endpoints_return_conflict_when_scheduling_is_disabled(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    availability = client.post(
        "/scheduling/availability?tenant=generic",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-23",
            "date_to": "2026-03-24",
            "timezone": "Europe/Skopje",
        },
    )
    booking = client.post(
        "/scheduling/book?tenant=generic",
        json={
            "service_id": "consultation",
            "slot_id": "mock|2026-03-23T09:00:00|consultation|generic-mock",
            "patient_name": "Marjan",
        },
    )

    assert availability.status_code == 409
    assert booking.status_code == 409
    assert "Scheduling is disabled" in availability.json()["detail"]
    assert "Scheduling booking is disabled" in booking.json()["detail"]


def test_scheduling_availability_returns_provider_failure_as_service_unavailable(monkeypatch, tmp_path):
    client = _build_client(monkeypatch, tmp_path)

    import app.routes.scheduling as scheduling_route_module

    monkeypatch.setattr(
        scheduling_route_module,
        "get_availability",
        lambda request: (_ for _ in ()).throw(scheduling_route_module.SchedulingProviderError("provider down")),
    )

    response = client.post(
        "/scheduling/availability?tenant=milena_dental",
        json={
            "service_id": "consultation",
            "date_from": "2026-03-23",
            "date_to": "2026-03-24",
            "timezone": "Europe/Skopje",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "provider down"
