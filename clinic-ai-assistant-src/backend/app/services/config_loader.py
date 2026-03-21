import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"


class TenantConfigError(Exception):
    pass


class TenantNotFoundError(FileNotFoundError):
    pass


def _require_non_empty_string(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TenantConfigError(f"{section_name}.{field_name} is required")


def _require_object(section_name: str, payload):
    if not isinstance(payload, dict):
        raise TenantConfigError(f"{section_name} must be an object")
    return payload


def _require_list(section_name: str, payload: dict, field_name: str, *, required: bool):
    value = payload.get(field_name)
    if value is None and not required:
        return None
    if not isinstance(value, list):
        raise TenantConfigError(f"{section_name}.{field_name} must be a list")
    return value


def _validate_service(service: dict, index: int):
    if not isinstance(service, dict):
        raise TenantConfigError(f"services[{index}] must be an object")

    _require_non_empty_string(f"services[{index}]", service, "id")
    _require_non_empty_string(f"services[{index}]", service, "name")

    for list_field in ("keywords", "symptoms"):
        value = service.get(list_field)
        if value is not None and not isinstance(value, list):
            raise TenantConfigError(f"services[{index}].{list_field} must be a list")

    if "bookable" in service and not isinstance(service["bookable"], bool):
        raise TenantConfigError(f"services[{index}].bookable must be a boolean")


def _require_boolean(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise TenantConfigError(f"{section_name}.{field_name} must be a boolean")
    return value


def _require_positive_integer(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise TenantConfigError(f"{section_name}.{field_name} must be a positive integer")
    return value


def _validate_business_hours(section_name: str, business_hours):
    hours = _require_object(section_name, business_hours)
    for day_name, ranges in hours.items():
        if not isinstance(day_name, str) or not day_name.strip():
            raise TenantConfigError(f"{section_name} day names must be non-empty strings")
        if not isinstance(ranges, list):
            raise TenantConfigError(f"{section_name}.{day_name} must be a list")
        for index, time_range in enumerate(ranges):
            if not isinstance(time_range, list) or len(time_range) != 2:
                raise TenantConfigError(f"{section_name}.{day_name}[{index}] must be a two-item list")
            start_at, end_at = time_range
            if not isinstance(start_at, str) or not start_at.strip():
                raise TenantConfigError(f"{section_name}.{day_name}[{index}][0] must be a non-empty string")
            if not isinstance(end_at, str) or not end_at.strip():
                raise TenantConfigError(f"{section_name}.{day_name}[{index}][1] must be a non-empty string")


def _validate_scheduling(profile: dict, tenant: str):
    scheduling = profile.get("scheduling")
    if scheduling is None:
        return

    scheduling = _require_object(f"Profile '{tenant}'.scheduling", scheduling)
    _require_boolean(f"Profile '{tenant}'.scheduling", scheduling, "enabled")
    provider = scheduling.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        raise TenantConfigError(f"Profile '{tenant}'.scheduling.provider is required")
    _require_non_empty_string(f"Profile '{tenant}'.scheduling", scheduling, "timezone")
    _require_positive_integer(f"Profile '{tenant}'.scheduling", scheduling, "slot_duration_minutes")
    _require_positive_integer(f"Profile '{tenant}'.scheduling", scheduling, "slot_interval_minutes")
    _require_positive_integer(f"Profile '{tenant}'.scheduling", scheduling, "minimum_notice_minutes")
    _require_positive_integer(f"Profile '{tenant}'.scheduling", scheduling, "lookahead_days")
    _validate_business_hours(
        f"Profile '{tenant}'.scheduling.business_hours",
        scheduling.get("business_hours"),
    )

    providers = _require_object(
        f"Profile '{tenant}'.scheduling.providers",
        scheduling.get("providers"),
    )
    normalized_provider = provider.strip()
    if normalized_provider not in providers:
        raise TenantConfigError(
            f"Profile '{tenant}'.scheduling.provider must exist in scheduling.providers"
        )

    for provider_name, provider_config in providers.items():
        if not isinstance(provider_name, str) or not provider_name.strip():
            raise TenantConfigError(f"Profile '{tenant}'.scheduling.providers keys must be non-empty strings")
        _require_object(
            f"Profile '{tenant}'.scheduling.providers.{provider_name}",
            provider_config,
        )


def _validate_profile(tenant: str, profile: dict):
    if not isinstance(profile, dict):
        raise TenantConfigError(f"Profile '{tenant}' must be a JSON object")

    business = _require_object(f"Profile '{tenant}'.business", profile.get("business"))
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "name")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "type")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "language")

    prompt_template = _require_object(
        f"Profile '{tenant}'.prompt_template",
        profile.get("prompt_template"),
    )
    _require_non_empty_string(f"Profile '{tenant}'.prompt_template", prompt_template, "system")

    conversation = _require_object(f"Profile '{tenant}'.conversation", profile.get("conversation"))
    _require_non_empty_string(f"Profile '{tenant}'.conversation", conversation, "goal")

    services = profile.get("services")
    if not isinstance(services, list):
        raise TenantConfigError(f"Profile '{tenant}'.services must be a list")

    seen_service_ids = set()
    for index, service in enumerate(services):
        _validate_service(service, index)
        service_id = service["id"].strip()
        if service_id in seen_service_ids:
            raise TenantConfigError(f"Profile '{tenant}' contains duplicate service id '{service_id}'")
        seen_service_ids.add(service_id)

    actions = _require_object(f"Profile '{tenant}'.actions", profile.get("actions"))
    allow_booking = actions.get("allow_booking")
    if not isinstance(allow_booking, bool):
        raise TenantConfigError(f"Profile '{tenant}'.actions.allow_booking must be a boolean")

    collect_fields = _require_list(
        f"Profile '{tenant}'.actions",
        actions,
        "collect_contact_fields",
        required=False,
    )
    if allow_booking:
        if not collect_fields:
            raise TenantConfigError(
                f"Profile '{tenant}' enables booking but does not define collect_contact_fields"
            )
    elif collect_fields is None:
        collect_fields = []

    output_contract = _require_object(
        f"Profile '{tenant}'.output_contract",
        profile.get("output_contract"),
    )
    response_format = _require_object(
        f"Profile '{tenant}'.output_contract.response_format",
        output_contract.get("response_format"),
    )
    for field_name in ("intent", "service_id", "message"):
        _require_non_empty_string(
            f"Profile '{tenant}'.output_contract.response_format",
            response_format,
            field_name,
        )

    _validate_scheduling(profile, tenant)


def load_profile_config(tenant: str):
    profile_path = PROFILES_DIR / f"{tenant}.json"

    if not profile_path.exists():
        raise TenantNotFoundError(f"Profile '{tenant}' not found")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as exc:
        raise TenantConfigError(f"Profile '{tenant}' contains invalid JSON") from exc

    _validate_profile(tenant, profile)
    return profile


def load_public_profile_config(tenant: str) -> dict:
    profile = load_profile_config(tenant)
    business = profile.get("business", {})
    agent = profile.get("agent", {})
    services = profile.get("services", [])
    scheduling = profile.get("scheduling", {})
    actions = profile.get("actions", {})

    public_services = [
        {
            "id": service.get("id"),
            "name": service.get("name"),
            "description": service.get("description"),
            "price_range": service.get("price_range"),
            "image": service.get("image"),
            "bookable": service.get("bookable", False),
        }
        for service in services
    ]

    return {
        "business": {
            "id": business.get("id", tenant),
            "name": business.get("name", "Assistant"),
            "type": business.get("type"),
            "language": business.get("language", "en"),
            "contact": business.get("contact", {}),
        },
        "assistant": {
            "name": agent.get("name") or business.get("name", "Assistant"),
        },
        "conversation": {
            "greeting": profile.get("conversation", {}).get("greeting"),
        },
        "services": public_services,
        "scheduling": {
            "enabled": scheduling.get("enabled", False),
            "provider": scheduling.get("provider"),
            "timezone": scheduling.get("timezone"),
            "slot_duration_minutes": scheduling.get("slot_duration_minutes"),
            "booking_enabled": bool(
                scheduling.get("enabled", False) and actions.get("allow_booking", False)
            ),
        },
    }
