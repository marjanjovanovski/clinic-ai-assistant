import os

from openai import OpenAI, OpenAIError, RateLimitError

from app.services.config_loader import load_profile_config


def generate_reply(tenant: str, message: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    profile = load_profile_config(tenant)

    business_name = profile.get("business", {}).get("name", "Assistant")
    goal = profile.get("conversation", {}).get("goal", "")

    system_prompt = f"""
You are an AI assistant for {business_name}.

Your job:
{goal}

Be helpful, concise, and professional.
""".strip()

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )

        return response.output_text

    except RateLimitError:
        return "The AI service is temporarily unavailable because the API quota is not active yet."

    except OpenAIError:
        return "The AI service is temporarily unavailable right now. Please try again shortly."