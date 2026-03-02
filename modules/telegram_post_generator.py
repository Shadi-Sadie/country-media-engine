# modules/telegram_post_generator.py

from datetime import datetime


def format_video_list(videos):
    lines = []
    for v in videos:
        lines.append(
            f"▪️{v['title']} ({v['url']})"
        )
    return "\n".join(lines)


def generate_telegram_post(country, metadata, videos):

    post_lines = []

    # Header
    post_lines.append(f"{country} {metadata.get('flag', '')}")
    post_lines.append("")

    # Basic Info
    post_lines.append(f"🔹پایتخت: {metadata.get('capital', 'نامشخص')}")
    post_lines.append(f"🔹مساحت: {metadata.get('area', 'نامشخص')}")
    post_lines.append(f"🔹موقعیت جغرافیایی: {metadata.get('location', 'نامشخص')}")
    post_lines.append(f"🔹همسایگان: {metadata.get('neighbors', 'نامشخص')}")
    post_lines.append(f"🔹جمعیت: {metadata.get('population', 'نامشخص')}")
    post_lines.append(f"🔹زبان‌های رسمی: {metadata.get('languages', 'نامشخص')}")
    post_lines.append("")

    post_lines.append("📌 منابع دیجیتال")
    post_lines.append("")

    # Music
    if videos.get("music"):
        post_lines.append("🎵 موسیقی:")
        post_lines.append(format_video_list(videos["music"]))
        post_lines.append("")

    # Life
    if videos.get("life"):
        post_lines.append("🍲 زندگی و غذا:")
        post_lines.append(format_video_list(videos["life"]))
        post_lines.append("")

    # Nature
    if videos.get("nature"):
        post_lines.append("🏞 طبیعت و دیدنی‌ها:")
        post_lines.append(format_video_list(videos["nature"]))
        post_lines.append("")

    # History
    if videos.get("history"):
        post_lines.append("📜 تاریخ، سیاست و جامعه:")
        post_lines.append(format_video_list(videos["history"]))
        post_lines.append("")

    # Hashtags
    week_number = datetime.now().isocalendar()[1]
    post_lines.append(f"#week{week_number}")
    post_lines.append(f"#{country.replace(' ', '')}")
    post_lines.append(f"@countries_AtoZ")

    return "\n".join(post_lines)