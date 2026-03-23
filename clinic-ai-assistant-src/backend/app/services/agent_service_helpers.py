"""Service/catalog helper functions for chat agent orchestration."""

import re

from app.services.agent_profile_helpers import (
    _conversation_rule_list,
    _profile_text,
    _render_profile_text,
)


def _normalize_lookup_text(value: str) -> str:
    lowered = value.casefold()
    normalized = re.sub(r"\s+", " ", lowered)
    return normalized.strip()


def _service_variants(service: dict) -> set[str]:
    variants = set()
    for field_name in ("name", "\u0438\u043c\u0435", "description", "\u043e\u043f\u0438\u0441"):
        value = service.get(field_name)
        if isinstance(value, str) and value.strip():
            variants.add(_normalize_lookup_text(value))

    for field_name in ("aliases", "keywords", "symptoms", "\u043f\u0440\u0435\u043f\u043e\u0440\u0430\u0447\u0430\u043d\u043e_\u0437\u0430"):
        values = service.get(field_name) or []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, str) and item.strip():
                    variants.add(_normalize_lookup_text(item))

    return variants


def _service_by_id(services: list[dict], service_id: str | None) -> dict | None:
    if not isinstance(service_id, str) or not service_id.strip():
        return None

    normalized_service_id = service_id.strip()
    return next(
        (service for service in services if service.get("id") == normalized_service_id),
        None,
    )


def _match_service_for_message(message: str, services: list[dict]) -> dict | None:
    normalized_message = _normalize_lookup_text(message)
    best_match = None
    best_score = 0

    for service in services:
        for variant in _service_variants(service):
            if not variant:
                continue
            if variant in normalized_message:
                score = len(variant)
                if score > best_score:
                    best_score = score
                    best_match = service

    return best_match


def _catalog_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = profile.get("\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438")
    if isinstance(categories, list) and categories:
        return categories

    grouped: dict[str, list[dict]] = {}
    for service in services:
        category_name = service.get("category") or "\u0423\u0441\u043b\u0443\u0433\u0438"
        grouped.setdefault(category_name, []).append(service)

    return [
        {
            "\u0438\u043c\u0435": category_name,
            "\u0443\u0441\u043b\u0443\u0433\u0438": category_services,
        }
        for category_name, category_services in grouped.items()
    ]


def _ordered_categories(profile: dict, services: list[dict]) -> list[dict]:
    categories = list(_catalog_categories(profile, services))
    consultation_name = _normalize_lookup_text("\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430")

    consultation_categories = []
    other_categories = []
    for category in categories:
        category_name = category.get("\u0438\u043c\u0435") or category.get("name") or ""
        if _normalize_lookup_text(category_name) == consultation_name:
            consultation_categories.append(category)
        else:
            other_categories.append(category)

    return consultation_categories + other_categories


def _service_display_name(service: dict) -> str:
    return service.get("\u0438\u043c\u0435") or service.get("name") or service.get("id", "")


def _service_display_description(service: dict) -> str | None:
    description = service.get("\u043e\u043f\u0438\u0441") or service.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _join_natural_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} \u0438 {items[1]}"
    return f"{', '.join(items[:-1])} \u0438 {items[-1]}"


def _business_overview_reply(profile: dict, services: list[dict]) -> str:
    business = profile.get("business", {})
    business_name = business.get("name", "\u041e\u0440\u0434\u0438\u043d\u0430\u0446\u0438\u0458\u0430\u0442\u0430")
    category_names: list[str] = []
    for category in _ordered_categories(profile, services):
        category_name = category.get("\u0438\u043c\u0435") or category.get("name")
        if isinstance(category_name, str) and category_name.strip():
            category_names.append(category_name.strip().lower())

    category_summary = _join_natural_list(category_names)
    summary = _render_profile_text(
        profile,
        ("reply_texts", "business_overview_summary"),
        business_name=business_name,
        category_summary=category_summary,
    )
    if not summary:
        summary = (
            f"{business_name} \u0435 \u0441\u0442\u043e\u043c\u0430\u0442\u043e\u043b\u043e\u0448\u043a\u0430 "
            f"\u043e\u0440\u0434\u0438\u043d\u0430\u0446\u0438\u0458\u0430 \u0441\u043e \u0443\u0441\u043b\u0443\u0433\u0438 "
            f"\u043e\u0434 \u043e\u0431\u043b\u0430\u0441\u0442\u0430 \u043d\u0430 {category_summary}."
        )

    catalog = _service_list_reply(profile, services)
    return f"{summary}\n\n{catalog}" if catalog else summary


def _service_list_reply(profile: dict, services: list[dict]) -> str:
    lines: list[str] = []

    for category in _ordered_categories(profile, services):
        category_name = category.get("\u0438\u043c\u0435") or category.get("name")
        if not isinstance(category_name, str) or not category_name.strip():
            continue

        lines.append(f"\u2022 {category_name.strip()}")
        category_services = category.get("\u0443\u0441\u043b\u0443\u0433\u0438") or category.get("services") or []

        for service in category_services:
            if not isinstance(service, dict):
                continue

            service_name = _service_display_name(service)
            if not service_name:
                continue

            description = _service_display_description(service)
            if description and category_name == "\u041a\u043e\u043d\u0441\u0443\u043b\u0442\u0430\u0446\u0438\u0458\u0430":
                lines.append(f"  \u2013 {service_name} \u2014 {description}")
            else:
                lines.append(f"  \u2013 {service_name}")

        lines.append("")

    return "\n".join(lines).strip()


def _orientation_price_text(service: dict, profile: dict) -> str | None:
    service_name = _service_display_name(service)
    price = service.get("price", service.get("\u0446\u0435\u043d\u0430"))
    currency = service.get("\u0432\u0430\u043b\u0443\u0442\u0430")
    price_range = service.get("price_range", service.get("\u0446\u0435\u043d\u043e\u0432\u0435\u043d_\u043e\u043f\u0441\u0435\u0433"))
    description = _service_display_description(service)

    if isinstance(price, (int, float)):
        currency_text = f" {currency}" if isinstance(currency, str) and currency.strip() else ""
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "numeric"),
            service_name=service_name,
            price=f"{price:g}",
            currency=currency_text,
        )
    elif isinstance(price, str) and price.strip():
        if price.strip().casefold() == "\u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e":
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "free"),
                service_name=service_name,
            )
        else:
            first_line = _render_profile_text(
                profile,
                ("reply_texts", "price_templates", "text"),
                service_name=service_name,
                price=price.strip(),
            )
    elif isinstance(price_range, str) and price_range.strip():
        first_line = _render_profile_text(
            profile,
            ("reply_texts", "price_templates", "range"),
            service_name=service_name,
            service_name_lower=service_name.lower(),
            price_range=price_range.strip(),
        )
    else:
        return None

    if not first_line:
        return None

    lines = [first_line]
    if description:
        lines.append(description)
    lines.append("")
    followup = _profile_text(profile, "reply_texts", "price_followup")
    if followup:
        lines.append(followup)
    return "\n".join(lines)


def _service_description_reply(message: str, services: list[dict], profile: dict) -> str | None:
    normalized_message = _normalize_lookup_text(message)
    if not any(
        trigger in normalized_message
        for trigger in _conversation_rule_list(profile, "service_description_triggers")
    ):
        return None

    service = _match_service_for_message(message, services)
    if not service:
        return None

    service_name = _service_display_name(service)
    description = _service_display_description(service)
    if not description:
        return None

    article_name = service.get("article_name") or service_name
    sentence_description = description[0].lower() + description[1:] if description else description
    followup = _profile_text(profile, "reply_texts", "service_description_followup")
    return _render_profile_text(
        profile,
        ("reply_texts", "service_description_template"),
        article_name=article_name,
        service_name=service_name,
        description=sentence_description,
        followup=followup or "",
    )
