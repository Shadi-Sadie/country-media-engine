# modules/telegram_post_generator.py

from datetime import datetime


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
        f"{metadata.get('name_fa', country)} {metadata.get('flag', '')}".strip(),
        f"🏙 پایتخت: {metadata.get('capital', 'نامشخص')}",
        f"📏 مساحت: {metadata.get('area', 'نامشخص')}",
        f"📍 موقعیت: {metadata.get('location', 'نامشخص')}",
        f"🤝 همسایگان: {metadata.get('neighbors', 'نامشخص')}",
        f"👥 جمعیت: {metadata.get('population', 'نامشخص')}",
        f"🗣 زبان رسمی: {metadata.get('languages', 'نامشخص')}",
        "",
        hashtags.strip(),
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
        lines.append(f"▪️{label} ({v['url']})")
    return "\n".join(lines)


def generate_links_post(country: str, videos_by_cat: dict) -> str:
    # This can be LONG — it is a normal message, not a caption.
    parts = [
        "📽 منابع دیجیتال",
        "",
        "🎵 موسیقی:",
        _format_links("music", videos_by_cat.get("music", [])),
        "",
        "🍲 زندگی و غذا:",
        _format_links("life", videos_by_cat.get("life", [])),
        "",
        "🏞 طبیعت و مناظر:",
        _format_links("nature", videos_by_cat.get("nature", [])),
        "",
        "📜 تاریخ، جامعه و سیاست:",
        _format_links("history", videos_by_cat.get("history", [])),
    ]
    return "\n".join(parts).strip()