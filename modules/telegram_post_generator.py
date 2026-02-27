from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_telegram_post(country, script_text):

    prompt = f"""
You are a cultural content editor.

Create a structured Telegram post in Persian about {country},
based strictly on the narration script below.

The post must:

- Be concise (400–700 words max)
- Be structured with clear sections
- Include basic facts (capital, population, location)
- Use minimal emojis
- Be visually clean for Telegram
- NOT invent new information
- ONLY use content from the script

Script:
{script_text[:7000]}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise cultural editor."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content