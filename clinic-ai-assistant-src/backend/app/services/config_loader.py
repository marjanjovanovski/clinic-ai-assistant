import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"


class TenantConfigError(Exception):
    pass


class TenantNotFoundError(FileNotFoundError):
    pass


DEFAULT_ALLOW_SCHEDULING_FIRST = False
DEFAULT_REQUIRE_CREDENTIALS_BEFORE_CONFIRM = True
TENANT_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _normalize_tenant_slug(tenant: str) -> str:
    if not isinstance(tenant, str):
        raise TenantNotFoundError(f"Profile '{tenant}' not found")

    normalized_tenant = tenant.strip()
    if not normalized_tenant or not TENANT_SLUG_PATTERN.fullmatch(normalized_tenant):
        raise TenantNotFoundError(f"Profile '{tenant}' not found")

    return normalized_tenant


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


def _require_optional_positive_integer(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if value is None:
        return None
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


def _validate_string_term_map(section_name: str, payload, *, allowed_keys: set[str] | None = None):
    if payload is None:
        return
    mapping = _require_object(section_name, payload)
    for key, terms in mapping.items():
        if not isinstance(key, str) or not key.strip():
            raise TenantConfigError(f"{section_name} keys must be non-empty strings")
        normalized_key = key.strip()
        if allowed_keys is not None and normalized_key not in allowed_keys:
            raise TenantConfigError(f"{section_name}.{normalized_key} is not a supported key")
        if not isinstance(terms, list) or not terms:
            raise TenantConfigError(f"{section_name}.{normalized_key} must be a non-empty list")
        for index, term in enumerate(terms):
            if not isinstance(term, str) or not term.strip():
                raise TenantConfigError(f"{section_name}.{normalized_key}[{index}] must be a non-empty string")


def _validate_scheduling_language_support(section_name: str, payload):
    if payload is None:
        return
    language_support = _require_object(section_name, payload)
    _validate_string_term_map(
        f"{section_name}.weekday_terms",
        language_support.get("weekday_terms"),
        allowed_keys={
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        },
    )
    _validate_string_term_map(
        f"{section_name}.relative_date_terms",
        language_support.get("relative_date_terms"),
        allowed_keys={"today", "tomorrow"},
    )
    _validate_string_term_map(
        f"{section_name}.relative_range_terms",
        language_support.get("relative_range_terms"),
        allowed_keys={"next_week"},
    )
    _validate_string_term_map(
        f"{section_name}.time_window_terms",
        language_support.get("time_window_terms"),
        allowed_keys={"morning", "afternoon"},
    )


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
    lookahead_days = _require_positive_integer(f"Profile '{tenant}'.scheduling", scheduling, "lookahead_days")
    default_availability_reach_days = _require_optional_positive_integer(
        f"Profile '{tenant}'.scheduling",
        scheduling,
        "default_availability_reach_days",
    )
    if (
        isinstance(default_availability_reach_days, int)
        and default_availability_reach_days > lookahead_days
    ):
        raise TenantConfigError(
            f"Profile '{tenant}'.scheduling.default_availability_reach_days must not exceed lookahead_days"
        )
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

    _validate_scheduling_language_support(
        f"Profile '{tenant}'.scheduling.language_support",
        scheduling.get("language_support"),
    )


def _normalize_actions(tenant: str, profile: dict) -> dict:
    actions = _require_object(f"Profile '{tenant}'.actions", profile.get("actions"))

    allow_booking = actions.get("allow_booking")
    if not isinstance(allow_booking, bool):
        raise TenantConfigError(f"Profile '{tenant}'.actions.allow_booking must be a boolean")

    allow_scheduling_first = actions.get("allow_scheduling_first", DEFAULT_ALLOW_SCHEDULING_FIRST)
    if not isinstance(allow_scheduling_first, bool):
        raise TenantConfigError(
            f"Profile '{tenant}'.actions.allow_scheduling_first must be a boolean"
        )

    require_credentials_before_confirm = actions.get(
        "require_credentials_before_confirm",
        DEFAULT_REQUIRE_CREDENTIALS_BEFORE_CONFIRM,
    )
    if not isinstance(require_credentials_before_confirm, bool):
        raise TenantConfigError(
            f"Profile '{tenant}'.actions.require_credentials_before_confirm must be a boolean"
        )

    normalized_actions = dict(actions)
    normalized_actions["allow_scheduling_first"] = allow_scheduling_first
    normalized_actions["require_credentials_before_confirm"] = require_credentials_before_confirm
    profile["actions"] = normalized_actions
    return normalized_actions


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

    actions = _normalize_actions(tenant, profile)
    allow_booking = actions.get("allow_booking")

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
    normalized_tenant = _normalize_tenant_slug(tenant)
    profile_path = PROFILES_DIR / f"{normalized_tenant}.json"

    if not profile_path.exists():
        raise TenantNotFoundError(f"Profile '{normalized_tenant}' not found")

    try:
        with open(profile_path, encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as exc:
        raise TenantConfigError(f"Profile '{normalized_tenant}' contains invalid JSON") from exc

    _validate_profile(normalized_tenant, profile)
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
