# modules/telegram_post_generator.py

from datetime import datetime

from matplotlib import lines


def format_video_list(videos):
    lines = []
    for v in videos:
        lines.append(
            f"▪️{v['title']} ({v['url']})"
        )
    return "\n".join(lines)


# modules/telegram_post_generator.py

def generate_caption(country: str, metadata: dict, hashtags: str) -> str:
    # Keep this SHORT (caption-safe)
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


def _short_fa_label(category: str, idx: int) -> str:
    # Minimal no-API labels (you can improve later)
    base = {
        "music": "موسیقی",
        "life": "زندگی و غذا",
        "nature": "طبیعت و مناظر",
        "history": "تاریخ، جامعه و سیاست",
    }.get(category, "ویدئو")
    # Persian digits optional; keep simple for now
    return f"{base} {idx}"


def _format_links(category: str, videos: list) -> str:
    if not videos:
        return "▪️موردی پیدا نشد"
    lines = []
    for i, v in enumerate(videos, start=1):
        label = v.get("fa_label") or _short_fa_label(category, i)
        url = v["url"]
        lines.append(
            f'▪️<a href="{url}">{label}</a>'
            )
    return "\n".join(lines)


def generate_links_post(country: str, videos_by_cat: dict, hashtags: str) -> str:
    parts = [
        "<b>📽 منابع دیجیتال</b>",
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
    tags = (hashtags or "").strip()
    if tags:
        return f"{intro}\n{tags}"
    return intro
