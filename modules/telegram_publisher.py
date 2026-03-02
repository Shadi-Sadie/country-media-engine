# modules/telegram_publisher.py

import requests
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_photo_with_caption(image_path, caption_text):

    url = f"{TELEGRAM_API_URL}/sendPhoto"

    with open(image_path, "rb") as photo:
        response = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption_text
            },
            files={
                "photo": photo
            }
        )

    if response.status_code != 200:
        print("Telegram error:", response.text)
        return False

    return True