import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "config" / "profiles"

ALLOWED_TOP_LEVEL_KEYS = {
    "business",
    "agent",
    "prompt_template",
    "conversation",
    "services",
    "actions",
    "output_contract",
    "knowledge",
}
ALLOWED_BUSINESS_KEYS = {"id", "name", "type", "language", "description", "contact"}
ALLOWED_CONTACT_KEYS = {"phone", "email", "address"}
ALLOWED_AGENT_KEYS = {"name", "role", "tone"}
ALLOWED_PROMPT_TEMPLATE_KEYS = {"system"}
ALLOWED_CONVERSATION_KEYS = {"greeting", "goal", "rules", "decision_rules", "fallback_message"}
ALLOWED_ACTION_KEYS = {"allow_booking", "collect_contact_fields", "handoff_enabled", "order_flow_enabled"}
ALLOWED_OUTPUT_CONTRACT_KEYS = {"unknown_service_id", "response_format"}
ALLOWED_KNOWLEDGE_KEYS = {"faq", "source", "notes"}
ALLOWED_SERVICE_KEYS = {
    "id",
    "name",
    "description",
    "keywords",
    "symptoms",
    "price_range",
    "image",
    "bookable",
    "priority",
}


class TenantConfigError(Exception):
    pass


class TenantNotFoundError(FileNotFoundError):
    pass


def _reject_unknown_keys(section_name: str, payload: dict, allowed_keys: set[str]):
    unknown_keys = sorted(set(payload.keys()) - allowed_keys)
    if unknown_keys:
        raise TenantConfigError(
            f"{section_name} contains unsupported keys: {', '.join(unknown_keys)}"
        )


def _require_non_empty_string(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise TenantConfigError(f"{section_name}.{field_name} is required")


def _require_list(section_name: str, payload: dict, field_name: str):
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise TenantConfigError(f"{section_name}.{field_name} must be a list")
    return value


def _validate_service(service: dict, index: int):
    if not isinstance(service, dict):
        raise TenantConfigError(f"services[{index}] must be an object")

    _reject_unknown_keys(f"services[{index}]", service, ALLOWED_SERVICE_KEYS)
    _require_non_empty_string(f"services[{index}]", service, "id")
    _require_non_empty_string(f"services[{index}]", service, "name")
    _require_non_empty_string(f"services[{index}]", service, "description")

    for list_field in ("keywords", "symptoms"):
        value = service.get(list_field, [])
        if not isinstance(value, list):
            raise TenantConfigError(f"services[{index}].{list_field} must be a list")

    if "bookable" in service and not isinstance(service["bookable"], bool):
        raise TenantConfigError(f"services[{index}].bookable must be a boolean")


def _validate_profile(tenant: str, profile: dict):
    if not isinstance(profile, dict):
        raise TenantConfigError(f"Profile '{tenant}' must be a JSON object")

    _reject_unknown_keys(f"Profile '{tenant}'", profile, ALLOWED_TOP_LEVEL_KEYS)

    business = profile.get("business")
    if not isinstance(business, dict):
        raise TenantConfigError(f"Profile '{tenant}' is missing business")
    _reject_unknown_keys(f"Profile '{tenant}'.business", business, ALLOWED_BUSINESS_KEYS)
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "name")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "type")
    _require_non_empty_string(f"Profile '{tenant}'.business", business, "language")
    if "contact" in business:
        if not isinstance(business["contact"], dict):
            raise TenantConfigError(f"Profile '{tenant}'.business.contact must be an object")
        _reject_unknown_keys(
            f"Profile '{tenant}'.business.contact",
            business["contact"],
            ALLOWED_CONTACT_KEYS,
        )

    agent = profile.get("agent", {})
    if agent:
        if not isinstance(agent, dict):
            raise TenantConfigError(f"Profile '{tenant}'.agent must be an object")
        _reject_unknown_keys(f"Profile '{tenant}'.agent", agent, ALLOWED_AGENT_KEYS)

    prompt_template = profile.get("prompt_template")
    if not isinstance(prompt_template, dict):
        raise TenantConfigError(f"Profile '{tenant}' is missing prompt_template")
    _reject_unknown_keys(
        f"Profile '{tenant}'.prompt_template",
        prompt_template,
        ALLOWED_PROMPT_TEMPLATE_KEYS,
    )
    _require_non_empty_string(f"Profile '{tenant}'.prompt_template", prompt_template, "system")

    conversation = profile.get("conversation")
    if not isinstance(conversation, dict):
        raise TenantConfigError(f"Profile '{tenant}' is missing conversation")
    _reject_unknown_keys(f"Profile '{tenant}'.conversation", conversation, ALLOWED_CONVERSATION_KEYS)
    _require_non_empty_string(f"Profile '{tenant}'.conversation", conversation, "goal")
    rules = _require_list(f"Profile '{tenant}'.conversation", conversation, "rules")
    if any(not isinstance(rule, str) or not rule.strip() for rule in rules):
        raise TenantConfigError(f"Profile '{tenant}'.conversation.rules must contain strings")
    decision_rules = _require_list(
        f"Profile '{tenant}'.conversation",
        conversation,
        "decision_rules",
    )
    if any(not isinstance(rule, str) or not rule.strip() for rule in decision_rules):
        raise TenantConfigError(f"Profile '{tenant}'.conversation.decision_rules must contain strings")

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

    actions = profile.get("actions")
    if not isinstance(actions, dict):
        raise TenantConfigError(f"Profile '{tenant}' is missing actions")
    _reject_unknown_keys(f"Profile '{tenant}'.actions", actions, ALLOWED_ACTION_KEYS)
    if "allow_booking" not in actions or not isinstance(actions["allow_booking"], bool):
        raise TenantConfigError(f"Profile '{tenant}'.actions.allow_booking must be a boolean")
    collect_fields = actions.get("collect_contact_fields", [])
    if not isinstance(collect_fields, list):
        raise TenantConfigError(
            f"Profile '{tenant}'.actions.collect_contact_fields must be a list"
        )
    if actions["allow_booking"] and not collect_fields:
        raise TenantConfigError(
            f"Profile '{tenant}' enables booking but does not define collect_contact_fields"
        )

    output_contract = profile.get("output_contract")
    if not isinstance(output_contract, dict):
        raise TenantConfigError(f"Profile '{tenant}' is missing output_contract")
    _reject_unknown_keys(
        f"Profile '{tenant}'.output_contract",
        output_contract,
        ALLOWED_OUTPUT_CONTRACT_KEYS,
    )
    response_format = output_contract.get("response_format")
    if not isinstance(response_format, dict):
        raise TenantConfigError(f"Profile '{tenant}'.output_contract.response_format is required")
    for field_name in ("intent", "service_id", "message"):
        _require_non_empty_string(
            f"Profile '{tenant}'.output_contract.response_format",
            response_format,
            field_name,
        )

    knowledge = profile.get("knowledge", {})
    if knowledge:
        if not isinstance(knowledge, dict):
            raise TenantConfigError(f"Profile '{tenant}'.knowledge must be an object")
        _reject_unknown_keys(f"Profile '{tenant}'.knowledge", knowledge, ALLOWED_KNOWLEDGE_KEYS)


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
    }
