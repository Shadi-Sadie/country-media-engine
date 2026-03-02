# modules/telegram_publisher.py

import os
import requests
from dotenv import load_dotenv


def _get_telegram_config():
    # Resolve env at call time so import order does not break token loading.
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram config missing: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return None, None
    return f"https://api.telegram.org/bot{bot_token}", chat_id


def send_photo(image_path: str, caption: str) -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    RTL = "\u200F"
    caption = RTL + caption   #

    url = f"{base_url}/sendPhoto"
    with open(image_path, "rb") as photo:
        r = requests.post(
            url,
            data={"chat_id": chat_id,
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
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    RTL = "\u200F"
    text = RTL + text  

    url = f"{base_url}/sendMessage"
    r = requests.post(
        url,
        data={"chat_id": chat_id,
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


def send_audio(audio_path: str, caption: str, title: str | None = None) -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    RTL = "\u200F"
    caption = RTL + caption

    if not os.path.exists(audio_path):
        print("Audio file not found:", audio_path)
        return False

    if not title:
        title = os.path.splitext(os.path.basename(audio_path))[0]

    url = f"{base_url}/sendAudio"
    with open(audio_path, "rb") as audio_file:
        r = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML",
                "title": title,
            },
            files={"audio": audio_file},
            timeout=120,
        )

    if r.status_code != 200:
        print("Telegram sendAudio error:", r.text)
        return False
    return True


def publish_photo_then_links(image_path: str, caption: str, links_text: str) -> bool:
    if not send_photo(image_path, caption):
        return False
    if not send_message(links_text):
        return False
    return True
