import json
import os

from openai import OpenAI, OpenAIError, RateLimitError

from app.services.config_loader import load_profile_config


SESSION_STATE = {}


def generate_reply(tenant: str, message: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    profile = load_profile_config(tenant)

    business = profile.get("business", {})
    conversation = profile.get("conversation", {})
    prompt_template = profile.get("prompt_template", {})
    services = profile.get("services", [])
    actions = profile.get("actions", {})
    output_contract = profile.get("output_contract", {})

    business_name = business.get("name", "Assistant")
    language = business.get("language", "en")
    goal = conversation.get("goal", "")
    rules = conversation.get("rules", [])

    allow_booking = actions.get("allow_booking", False)
    collect_fields = actions.get("collect_contact_fields", [])

    template = prompt_template.get(
        "system",
        "You are an AI assistant for {{business_name}}. Your goal: {{goal}}."
    )

    service_catalog = [
        {
            "id": service.get("id"),
            "name": service.get("name"),
            "description": service.get("description"),
            "keywords": service.get("keywords", []),
            "symptoms": service.get("symptoms", []),
            "bookable": service.get("bookable", False)
        }
        for service in services
    ]

    services_json = json.dumps(service_catalog, ensure_ascii=False, indent=2)
    rules_text = "\n".join(f"- {rule}" for rule in rules)

    system_prompt = (
        template.replace("{{business_name}}", business_name)
        .replace("{{goal}}", goal)
    )

    if rules_text:
        system_prompt += f"\n\nRules:\n{rules_text}"

    system_prompt += f"\n\nAlways respond in this language: {language}"
    system_prompt += f"\n\nAllowed services catalog:\n{services_json}"

    if allow_booking:
        system_prompt += (
            "\n\nBooking capability: enabled."
            "\nIf the user confirms booking (yes/da/ok), start collecting contact details."
            f"\nCollect these fields in order: {collect_fields}"
        )

    if output_contract:
        system_prompt += (
            "\n\nReturn ONLY a JSON object with this structure:\n"
            + json.dumps(output_contract.get("response_format", {}), ensure_ascii=False, indent=2)
        )

    session_key = tenant
    state = SESSION_STATE.get(session_key)

    if state and state.get("stage") == "collecting_contact":
        next_field = state.get("next_field")

        state["data"][next_field] = message

        remaining = [f for f in collect_fields if f not in state["data"]]

        if remaining:
            state["next_field"] = remaining[0]
            return f"Ве молам кажете го вашето {remaining[0]}."

        SESSION_STATE.pop(session_key, None)
        return "Ви благодарам. Вашето барање за термин е примено. Клиниката ќе ве контактира."

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )

        raw_output = response.output_text.strip()

        try:
            parsed = json.loads(raw_output)

            intent = parsed.get("intent")
            service_id = parsed.get("service_id")
            message_text = parsed.get("message")

            if intent == "confirm_booking" and allow_booking:
                SESSION_STATE[session_key] = {
                    "stage": "collecting_contact",
                    "service_id": service_id,
                    "next_field": collect_fields[0],
                    "data": {}
                }
                return f"Ве молам кажете го вашето {collect_fields[0]}."

            if message_text:
                return message_text

            return raw_output

        except json.JSONDecodeError:
            return raw_output

    except RateLimitError:
        return "The AI service is temporarily unavailable because the API quota is not active yet."

    except OpenAIError:
        return "The AI service is temporarily unavailable right now. Please try again shortly."