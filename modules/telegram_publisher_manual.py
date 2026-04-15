import os
import json

import requests
from dotenv import load_dotenv
from modules.telegram_media import cleanup_prepared_telegram_media, prepare_telegram_photo
from modules.telegram_post_generator_manual import is_caption_within_limit, telegram_caption_length


RTL = "\u200F"


def _get_telegram_config() -> tuple[str | None, str | None]:
    load_dotenv()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("Telegram config missing: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return None, None
    return f"https://api.telegram.org/bot{bot_token}", chat_id


def send_message(text: str, disable_web_page_preview: bool = False) -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    response = requests.post(
        f"{base_url}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": RTL + text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_web_page_preview,
        },
        timeout=30,
    )
    if response.status_code != 200:
        print("Telegram sendMessage error:", response.text)
        return False
    return True


def send_photo(image_path: str, caption: str) -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    prepared_path, temp_dir = prepare_telegram_photo(image_path)
    try:
        with open(prepared_path, "rb") as photo:
            response = requests.post(
                f"{base_url}/sendPhoto",
                data={
                    "chat_id": chat_id,
                    "caption": RTL + caption,
                    "parse_mode": "HTML",
                },
                files={"photo": photo},
                timeout=30,
            )
    finally:
        cleanup_prepared_telegram_media([temp_dir])

    if response.status_code != 200:
        print("Telegram sendPhoto error:", response.text)
        return False
    return True


def send_media_group(image_paths: list[str], caption: str = "") -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    valid_paths = [path for path in image_paths if path and os.path.exists(path)]
    if not valid_paths:
        return False

    if len(valid_paths) == 1:
        return send_photo(valid_paths[0], caption)

    media = []
    files = {}
    handles = []
    temp_dirs: list[str | None] = []

    try:
        for index, image_path in enumerate(valid_paths[:10]):
            attach_name = f"photo{index}"
            prepared_path, temp_dir = prepare_telegram_photo(image_path)
            temp_dirs.append(temp_dir)
            handle = open(prepared_path, "rb")
            handles.append(handle)
            files[attach_name] = (os.path.basename(prepared_path), handle)

            item = {
                "type": "photo",
                "media": f"attach://{attach_name}",
            }
            if index == 0 and caption:
                item["caption"] = RTL + caption
                item["parse_mode"] = "HTML"
            media.append(item)

        response = requests.post(
            f"{base_url}/sendMediaGroup",
            data={
                "chat_id": chat_id,
                "media": json.dumps(media),
            },
            files=files,
            timeout=60,
        )
    finally:
        for handle in handles:
            handle.close()
        cleanup_prepared_telegram_media(temp_dirs)

    if response.status_code != 200:
        print("Telegram sendMediaGroup error:", response.text)
        return False
    return True


def send_audio(audio_path: str, caption: str, title: str | None = None) -> bool:
    base_url, chat_id = _get_telegram_config()
    if not base_url:
        return False

    if not os.path.exists(audio_path):
        print("Audio file not found:", audio_path)
        return False

    audio_title = title or os.path.splitext(os.path.basename(audio_path))[0]
    with open(audio_path, "rb") as audio_file:
        response = requests.post(
            f"{base_url}/sendAudio",
            data={
                "chat_id": chat_id,
                "caption": RTL + caption,
                "parse_mode": "HTML",
                "title": audio_title,
            },
            files={"audio": audio_file},
            timeout=120,
        )

    if response.status_code != 200:
        print("Telegram sendAudio error:", response.text)
        return False
    return True


def publish_package(
    main_post_caption: str,
    links_text: str = "",
    image_path: str | None = None,
    fun_fact_images: list[str] | None = None,
    fun_facts_caption: str = "",
    audio_path: str | None = None,
    audio_caption: str = "",
    audio_title: str | None = None,
) -> bool:
    if not image_path:
        print("Country image is required for the first Telegram post.")
        return False

    caption_text = (main_post_caption or "").strip()
    links_payload = (links_text or "").strip()

    photo_caption = caption_text
    send_links_separately = False
    if links_payload:
        combined_caption = "\n\n".join(part for part in (caption_text, links_payload) if part)
        if is_caption_within_limit(combined_caption):
            photo_caption = combined_caption
        else:
            send_links_separately = True
            print(
                "Combined country caption and links exceed Telegram photo caption limit; "
                f"sending links as a separate message ({telegram_caption_length(combined_caption)} > 1024)."
            )

    if not send_photo(image_path, photo_caption):
        return False

    if send_links_separately and not send_message(links_payload):
        return False

    if fun_fact_images:
        if not send_media_group(fun_fact_images, caption=fun_facts_caption):
            return False

    if audio_path:
        if not send_audio(audio_path, audio_caption, title=audio_title):
            return False

    return True
