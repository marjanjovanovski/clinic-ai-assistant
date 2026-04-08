# TEST EXECUTION MANIFESTO: Before running tests, follow clinic-ai-assistant-src/backend/pytest.ini and never create repo-local pytest temp folders; use external TMP/TEMP plus --basetemp.
import pytest

from app.services.config_loader import TenantNotFoundError, load_profile_config, load_public_profile_config


def test_all_profiles_load_successfully():
    for tenant in ("generic", "risto", "milena_dental"):
        profile = load_profile_config(tenant)
        assert profile["business"]["name"]


def test_public_profile_config_hides_internal_prompt_fields():
    public_profile = load_public_profile_config("milena_dental")

    assert "prompt_template" not in public_profile
    assert "output_contract" not in public_profile
    assert "business" in public_profile
    assert "services" in public_profile
def test_load_profile_config_rejects_invalid_tenant_slug():
    with pytest.raises(TenantNotFoundError, match=r"Profile '\.\./milena_dental' not found"):
        load_profile_config("../milena_dental")

