# modules/telegram_publisher.py

import requests
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_photo(image_path: str, caption: str) -> bool:
    RTL = "\u200F"
    caption = RTL + caption   #

    url = f"{BASE_URL}/sendPhoto"
    with open(image_path, "rb") as photo:
        r = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID,
                   "caption": caption,
                   "parse_mode": "HTML"
                   },
            files={"photo": photo},
            timeout=30,
        )
    if r.status_code != 200:
        print("Telegram sendPhoto error:", r.text)
        return False
    return True


def send_message(text: str) -> bool:
    RTL = "\u200F"
    text = RTL + text  

    url = f"{BASE_URL}/sendMessage"
    r = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID,
               "text": text, 
                "parse_mode": "HTML",
                "disable_web_page_preview": False
        },
        timeout=30,
    )
    if r.status_code != 200:
        print("Telegram sendMessage error:", r.text)
        return False
    return True


def publish_photo_then_links(image_path: str, caption: str, links_text: str) -> bool:
    if not send_photo(image_path, caption):
        return False
    if not send_message(links_text):
        return False
    return True