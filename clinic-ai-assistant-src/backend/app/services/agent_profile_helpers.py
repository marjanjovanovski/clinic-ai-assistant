"""Profile/config access helpers for chat agent orchestration."""


def _profile_text(profile: dict, *path: str) -> str | None:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _profile_text_map(profile: dict, *path: str) -> dict:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(key)

    return value if isinstance(value, dict) else {}


def _profile_list(profile: dict, *path: str) -> list[str]:
    value = profile
    for key in path:
        if not isinstance(value, dict):
            return []
        value = value.get(key)

    if not isinstance(value, list):
        return []

    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _render_profile_text(profile: dict, path: tuple[str, ...], **values) -> str | None:
    template = _profile_text(profile, *path)
    if not template:
        return None

    return template.format(**values)


def _field_prompt(profile: dict, field_name: str) -> str:
    field_prompts = _profile_text_map(profile, "reply_texts", "field_prompts")
    value = field_prompts.get(field_name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return field_name


def _field_error_prompt(profile: dict, field_name: str, **values) -> str | None:
    error_prompts = _profile_text_map(profile, "reply_texts", "field_error_prompts")
    template = error_prompts.get(field_name)
    if isinstance(template, str) and template.strip():
        return template.strip().format(**values)
    return None


def _conversation_rule_list(profile: dict, rule_name: str) -> list[str]:
    return _profile_list(profile, "conversation_rules", rule_name)


def _conversation_rule_patterns(
    profile: dict,
    rule_name: str = "casual_reply_patterns",
) -> list[tuple[list[str], str]]:
    patterns = profile.get("conversation_rules", {}).get(rule_name, [])
    if not isinstance(patterns, list):
        return []

    normalized_patterns: list[tuple[list[str], str]] = []
    for item in patterns:
        if not isinstance(item, dict):
            continue

        triggers = item.get("triggers")
        reply_key = item.get("reply_key")
        if not isinstance(triggers, list) or not isinstance(reply_key, str) or not reply_key.strip():
            continue

        clean_triggers = [
            trigger.strip()
            for trigger in triggers
            if isinstance(trigger, str) and trigger.strip()
        ]
        if clean_triggers:
            normalized_patterns.append((clean_triggers, reply_key.strip()))

    return normalized_patterns
