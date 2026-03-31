from app.services.config_loader import TenantConfigError, load_profile_config


def test_load_profile_config_accepts_scheduling_language_support_for_existing_tenants():
    milena = load_profile_config("milena_dental")
    risto = load_profile_config("risto")

    assert milena["scheduling"]["language_support"]["relative_date_terms"]["tomorrow"]
    assert milena["scheduling"]["language_support"]["relative_date_terms"]["in_two_weeks"]
    assert milena["scheduling"]["contract_texts"]["broad_range_narrowing"]
    assert risto["scheduling"]["language_support"]["time_window_terms"]["afternoon"] == ["afternoon"]
    assert risto["scheduling"]["language_support"]["relative_date_terms"]["in_two_weeks"]


def test_load_profile_config_rejects_invalid_scheduling_language_support_key(monkeypatch, tmp_path):
    invalid_profile = """
    {
      "business": {"name": "Test", "type": "service", "language": "en"},
      "prompt_template": {"system": "test"},
      "conversation": {"goal": "test"},
      "services": [],
      "actions": {"allow_booking": false, "collect_contact_fields": []},
      "scheduling": {
        "enabled": false,
        "provider": "mock",
        "timezone": "Europe/Skopje",
        "slot_duration_minutes": 30,
        "slot_interval_minutes": 30,
        "minimum_notice_minutes": 120,
        "lookahead_days": 14,
        "business_hours": {"monday": [["09:00", "17:00"]]},
        "language_support": {
          "time_window_terms": {
            "evening": ["evening"]
          }
        },
        "providers": {
          "mock": {"seed": "test"}
        }
      },
      "output_contract": {
        "response_format": {"intent": "string", "service_id": "string", "message": "string"}
      }
    }
    """
    profile_path = tmp_path / "invalid_language_support.json"
    profile_path.write_text(invalid_profile, encoding="utf-8")

    import app.services.config_loader as config_loader

    monkeypatch.setattr(config_loader, "PROFILES_DIR", tmp_path)

    try:
        load_profile_config("invalid_language_support")
    except TenantConfigError as exc:
        assert "time_window_terms.evening is not a supported key" in str(exc)
    else:
        raise AssertionError("Expected invalid scheduling.language_support config to be rejected")


def test_load_profile_config_rejects_invalid_scheduling_contract_text_key(monkeypatch, tmp_path):
    invalid_profile = """
    {
      "business": {"name": "Test", "type": "service", "language": "en"},
      "prompt_template": {"system": "test"},
      "conversation": {"goal": "test"},
      "services": [],
      "actions": {"allow_booking": false, "collect_contact_fields": []},
      "scheduling": {
        "enabled": false,
        "provider": "mock",
        "timezone": "Europe/Skopje",
        "slot_duration_minutes": 30,
        "slot_interval_minutes": 30,
        "minimum_notice_minutes": 120,
        "lookahead_days": 14,
        "business_hours": {"monday": [["09:00", "17:00"]]},
        "contract_texts": {
          "unexpected_text": "Not allowed"
        },
        "providers": {
          "mock": {"seed": "test"}
        }
      },
      "output_contract": {
        "response_format": {"intent": "string", "service_id": "string", "message": "string"}
      }
    }
    """
    profile_path = tmp_path / "invalid_contract_text.json"
    profile_path.write_text(invalid_profile, encoding="utf-8")

    import app.services.config_loader as config_loader

    monkeypatch.setattr(config_loader, "PROFILES_DIR", tmp_path)

    try:
        load_profile_config("invalid_contract_text")
    except TenantConfigError as exc:
        assert "contract_texts.unexpected_text is not a supported key" in str(exc)
    else:
        raise AssertionError("Expected invalid scheduling.contract_texts config to be rejected")
