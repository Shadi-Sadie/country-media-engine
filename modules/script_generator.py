from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from config import OPENAI_API_KEY

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to .env before running the script."
    )

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_persian_script(country, wiki_text):

    prompt = f"""
You are a cultural documentary writer.

Write a structured, engaging Persian narration script about {country}.
Use the following Wikipedia content as source material.

Structure:
- Introduction
- Geography
- History
- Economy
- Culture & Society

Tone:
Neutral, documentary, informative.

Keep it around 800–1200 words.
Do NOT invent statistics.
Do NOT hallucinate.
Only use information from the text below.

Wikipedia content:
{wiki_text[:8000]}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise documentary script writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
    except APIConnectionError as exc:
        raise Exception(
            "Could not connect to OpenAI API. Check internet, firewall, or proxy settings."
        ) from exc
    except AuthenticationError as exc:
        raise Exception(
            "OpenAI authentication failed. Verify OPENAI_API_KEY in .env."
        ) from exc
    except RateLimitError as exc:
        raise Exception(
            "OpenAI rate limit reached. Wait and retry, or check account quota."
        ) from exc
    except APIStatusError as exc:
        raise Exception(
            f"OpenAI API returned HTTP {exc.status_code}. Try again shortly."
        ) from exc

    content = response.choices[0].message.content
    if not content:
        raise Exception("OpenAI returned an empty script.")
    return content
