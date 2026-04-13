import html
import re

# --------------------------------------------------
# Persian keyword map — no API needed.
# Scan the English title for these keywords (longest match first)
# and build a short Persian label from whatever is found.
# --------------------------------------------------

TOPIC_KEYWORDS_FA: list[tuple[str, str]] = [
    # Music — ordered longest-match first
    ("sabre dance",         "رقص شمشیرها"),
    ("folk music",          "موسیقی فولکلور"),
    ("traditional music",   "موسیقی سنتی"),
    ("live concert",        "کنسرت زنده"),
    ("live performance",    "اجرای زنده"),
    ("concert",             "کنسرت"),
    ("duduk",               "دودوک"),
    ("ashugh",              "آشوغ"),
    # Life & food
    ("street food",         "غذای خیابانی"),
    ("traditional wedding", "عروسی سنتی"),
    ("wedding",             "عروسی"),
    ("village life",        "زندگی روستایی"),
    ("rural life",          "زندگی روستایی"),
    ("remote village",      "روستای دورافتاده"),
    ("village",             "روستا"),
    ("rural",               "روستایی"),
    ("daily life",          "زندگی روزمره"),
    ("one day in",          "یک روز در"),
    ("how people live",     "زندگی مردم"),
    ("lavash",              "لواش"),
    ("bread baking",        "نان‌پزی"),
    ("baking",              "نانوایی"),
    ("bakery",              "نانوایی"),
    ("cooking",             "آشپزی"),
    ("recipe",              "دستور پخت"),
    ("market",              "بازار"),
    ("bazaar",              "بازار"),
    ("food",                "غذا"),
    # Nature — specific before generic
    ("waterfall",           "آبشار"),
    ("mountain",            "کوه"),
    ("lake",                "دریاچه"),
    ("river",               "رود"),
    ("forest",              "جنگل"),
    ("desert",              "بیابان"),
    ("valley",              "دره"),
    ("landscape",           "منظره"),
    ("scenic",              "چشم‌انداز"),
    ("journey",             "سفر"),
    ("travel",              "سفر"),
    ("land of noah",        "سرزمین نوح"),
    ("land of",             "سرزمین"),
    ("on the road",         "سفر جاده‌ای"),
    ("nature",              "طبیعت"),
    # NOTE: "4k", "hd", "uhd" intentionally excluded — they are noise, not topics
    # History / society — specific before generic
    ("genocide",            "نسل‌کشی"),
    ("civil war",           "جنگ داخلی"),
    ("world war",           "جنگ جهانی"),
    ("war",                 "جنگ"),
    ("revolution",          "انقلاب"),
    ("conflict",            "درگیری"),
    ("coup",                "کودتا"),
    ("occupation",          "اشغال"),
    ("ancient history",     "تاریخ باستان"),
    ("hidden wonders",      "شگفتی‌های پنهان"),
    ("forgotten",           "فراموش‌شده"),
    ("alone among enemies", "تنها در میان دشمنان"),
    ("enemies",             "دشمنان"),
    ("space",               "فضا"),
    ("ancient",             "باستانی"),
    ("history",             "تاریخ"),
    ("empire",              "امپراتوری"),
    ("politics",            "سیاست"),
    ("society",             "جامعه"),
    ("minority",            "اقلیت"),
    ("refugee",             "پناهنده"),
    ("crisis",              "بحران"),
    ("explained",           "توضیح داده شده"),
    ("report",              "گزارش"),
    ("documentary",         "مستند"),
]

OUTLET_LABELS: dict[str, str] = {
    "bbc":        "بی‌بی‌سی",
    "dw":         "دویچه‌وله",
    "pbs":        "PBS",
    "arte":       "ARTE",
    "al jazeera": "الجزیره",
    "aljazeera":  "الجزیره",
    "vox":        "Vox",
    "vice":       "Vice",
    "guardian":   "گاردین",
    "france 24":  "فرانس ۲۴",
    "cnn":        "CNN",
    "nyt":        "نیویورک تایمز",
}

CATEGORY_LABELS_FA: dict[str, str] = {
    "music":   "موسیقی",
    "life":    "زندگی و غذا",
    "nature":  "طبیعت",
    "history": "مستند",
}

NOISE_PATTERNS = [
    r"\bofficial\s+(video|music video|audio|lyric video|visualizer)\b",
    r"\bfull\s+(documentary|movie|video|album)\b",
    r"\b(lyrics?|hd|hq|uhd|4k|4\s*k|1080p|60fps)\b",
    r"\btravel\s+guide\b",
    r"\bwith subtitles\b",
    r"\benglish subtitles\b",
    r"\btravel\s+documentary\b",
]


# --------------------------------------------------
# Internal helpers
# --------------------------------------------------

def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip(" -|/:")


def _strip_noise(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = cleaned.replace("—", "-").replace("–", "-")
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"[\[(](?:official|lyrics?|hd|hq|uhd|4k|1080p|full documentary|full movie).*?[\])]",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_spaces(cleaned)


def _detect_outlet(title: str, channel: str) -> str:
    combined = f"{title} {channel}".lower()
    for key, label in OUTLET_LABELS.items():
        if key in combined:
            return label
    return ""


def _extract_artist_track(title: str) -> tuple[str, str]:
    """Return (artist, track) when title matches 'Artist - Track ...' pattern."""
    cleaned = _strip_noise(title)
    # Match "Something - Something else" where the separator is a dash
    m = re.match(r"^(.+?)\s*[-–]\s*(.+)$", cleaned)
    if m:
        return _normalize_spaces(m.group(1)), _normalize_spaces(m.group(2))
    return "", ""


def _find_fa_keywords(title: str) -> list[str]:
    """Return Persian equivalents of topic keywords found in the title."""
    lower = title.lower()
    found: list[str] = []
    seen: set[str] = set()
    # Iterate longest keys first (already ordered in list)
    for en_key, fa_val in TOPIC_KEYWORDS_FA:
        if en_key in lower and fa_val not in seen:
            found.append(fa_val)
            seen.add(fa_val)
            if len(found) >= 2:
                break
    return found


def _trim(text: str, limit: int = 58) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" -|/:") + "…"


# --------------------------------------------------
# Public entry point
# --------------------------------------------------

def short_fa_title(category: str, title: str, channel: str) -> str:
    fallback = CATEGORY_LABELS_FA.get(category, "ویدئو")
    cleaned = _strip_noise(title)

    # --- History: outlet label + topic keyword or stripped title fragment ---
    if category == "history":
        outlet = _detect_outlet(cleaned, channel)
        keywords = _find_fa_keywords(cleaned)
        if outlet and keywords:
            return _trim(f"{outlet}: {keywords[0]}")
        if outlet:
            # Strip outlet/noise words and use whatever meaningful fragment remains
            stripped = re.sub(
                r"(?i)\b(bbc|dw|pbs|arte|al jazeera|aljazeera|cnn|vox|vice|guardian"
                r"|france 24|france24|documentary|report|investigation|witness)\b",
                "",
                cleaned,
            )
            stripped = re.sub(r"^[\s:,\|\-]+|[\s:,\|\-]+$", "", stripped)
            stripped = _normalize_spaces(stripped)
            if stripped:
                return _trim(f"{outlet}: {stripped}")
            return _trim(f"{outlet}: مستند")
        if keywords:
            return _trim(f"مستند: {keywords[0]}")
        if cleaned:
            return _trim(f"مستند: {cleaned}")
        return fallback

    # --- Music: artist + track if detectable, else keywords, else cleaned title ---
    if category == "music":
        artist, track = _extract_artist_track(cleaned)
        keywords = _find_fa_keywords(cleaned)
        if artist and keywords:
            return _trim(f"{artist}: {keywords[0]}")
        if artist and track:
            # Keep artist name; try to translate the track keyword
            track_kw = _find_fa_keywords(track)
            track_label = track_kw[0] if track_kw else _trim(track, 30)
            return _trim(f"{artist}: {track_label}")
        if artist:
            return _trim(f"موسیقی: {artist}")
        if keywords:
            return _trim(f"موسیقی: {keywords[0]}")
        # Last resort: use the cleaned title as-is (artist names, etc.)
        if cleaned:
            return _trim(f"موسیقی: {cleaned}")
        return fallback

    # --- Nature: first matching keyword, else cleaned title ---
    if category == "nature":
        keywords = _find_fa_keywords(cleaned)
        if keywords:
            return _trim(f"طبیعت: {keywords[0]}")
        if cleaned:
            return _trim(f"طبیعت: {cleaned}")
        return fallback

    # --- Life: first matching keyword, else cleaned title ---
    if category == "life":
        keywords = _find_fa_keywords(cleaned)
        if keywords:
            return _trim(f"زندگی: {keywords[0]}")
        if cleaned:
            return _trim(f"زندگی: {cleaned}")
        return fallback

    return fallback
