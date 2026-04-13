import html
import re


TELEGRAM_CAPTION_LIMIT = 1024
RTL_PREFIX_LENGTH = 1


def _hashtag_token(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "", (text or "").replace(" ", "_"))
    return cleaned or "Country"


def build_hashtags(country: str) -> dict[str, str]:
    country_tag = _hashtag_token(country)
    tags = ["#week02", f"#{country_tag}"]
    if country and country[0].isalpha():
        tags.append(f"#{country[0].upper()}")
    tags.append("@countries_AtoZ")
    return {
        "lines": "\n".join(tags),
        "inline": " ".join(tags),
    }


def generate_caption(country: str, metadata: dict, hashtags: str) -> str:
    lines = [
        f"<b>{metadata.get('name_fa', country)} {metadata.get('flag', '')}</b>".strip(),
        f"🏙 <b>پایتخت:</b> {metadata.get('capital', 'نامشخص')}",
        f"📏 <b>مساحت:</b> {metadata.get('area', 'نامشخص')}",
        f"📍 <b>موقعیت:</b> {metadata.get('location', 'نامشخص')}",
        f"🤝 <b>همسایگان:</b> {metadata.get('neighbors', 'نامشخص')}",
        f"👥 <b>جمعیت:</b> {metadata.get('population', 'نامشخص')}",
        f"🗣 <b>زبان رسمی:</b> {metadata.get('languages', 'نامشخص')}",
    ]
    return "\n".join(lines).strip()


def _format_links(category: str, videos: list[dict]) -> str:
    if not videos:
        return "▪️موردی پیدا نشد"

    lines = []
    for index, video in enumerate(videos, start=1):
        label = video.get("fa_label") or f"ویدئو {index}"
        url = video["url"]
        lines.append(f'▪️<a href="{url}">{html.escape(label)}</a>')
    return "\n".join(lines)


def generate_links_post(country: str, videos_by_cat: dict, hashtags: str) -> str:
    parts = [
        f"<b>📽 ویدئوهای منتخب {country}</b>",
        "",
        "<b>🎵 موسیقی:</b>",
        _format_links("music", videos_by_cat.get("music", [])),
        "",
        "<b>🍲 زندگی و غذا:</b>",
        _format_links("life", videos_by_cat.get("life", [])),
        "",
        "<b>🏞 طبیعت و مناظر:</b>",
        _format_links("nature", videos_by_cat.get("nature", [])),
        "",
        "<b>📜 تاریخ، جامعه و سیاست:</b>",
        _format_links("history", videos_by_cat.get("history", [])),
    ]
    if hashtags:
        parts.extend(["", hashtags.strip()])
    return "\n".join(parts).strip()


def generate_audio_caption(country_en: str, country_fa: str, hashtags: str) -> str:
    intro = f"مرور صوتی ویکی‌پدیا {country_fa or country_en}؛ تهیه شده با هوش مصنوعی"
    if hashtags:
        return f"{intro}\n{hashtags.strip()}"
    return intro


def combine_caption_and_links(caption_text: str, links_text: str) -> str:
    parts = [part.strip() for part in [caption_text, links_text] if part and part.strip()]
    return "\n\n".join(parts).strip()


def telegram_caption_text(text: str) -> str:
    if not text:
        return ""
    normalized = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    return html.unescape(normalized).strip()


def telegram_caption_length(text: str) -> int:
    visible_text = telegram_caption_text(text)
    if not visible_text:
        return 0
    # The publisher prepends an RTL mark before sending.
    return RTL_PREFIX_LENGTH + len(visible_text)


def is_caption_within_limit(text: str) -> bool:
    return telegram_caption_length(text) <= TELEGRAM_CAPTION_LIMIT
