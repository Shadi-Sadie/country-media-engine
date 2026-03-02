import requests
import re
from config import YOUTUBE_API_KEY

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_GENERAL_QUERIES_PER_CATEGORY = 2
MAX_HISTORY_QUERIES_TOTAL = 5
QUOTA_EXHAUSTED = False


# --------------------------------------------------
# Configuration
# --------------------------------------------------

INSTITUTIONAL_CHANNEL_KEYWORDS = [
    "bbc",
    "dw",
    "pbs",
    "arte",
    "al jazeera",
    "guardian",
    "new york times",
    "nyt",
    "france 24"
]

BAD_KEYWORDS = [
    "short",
    "shorts",
    "tiktok",
    "reaction",
    "clip",
    "trailer"
]

GENERAL_CATEGORY_CONFIG = {
    "music": {
        "queries": [
            "{country} traditional music",
            "{country} live performance",
            "{country} folk music concert"
        ],
        "min_minutes": 3
    },
    "life": {
        "queries": [
            "{country} street food",
            "{country} traditional recipe",
            "{country} village life",
            "{country} wedding",
            "{country} one day in life"
        ],
        "min_minutes": 6
    },
    "nature": {
        "queries": [
            "{country} nature documentary",
            "{country} scenic 4K",
            "{country} travel documentary"
        ],
        "min_minutes": 8
    }
}

HISTORY_TIERS = {
    "tier1": [
        "{country} BBC documentary",
        "{country} DW documentary",
        "{country} PBS documentary",
        "{country} ARTE documentary",
        "{country} Al Jazeera documentary",
        "{country} Guardian documentary",
        "{country} New York Times documentary"
    ],
    "tier2": [
        "{country} society documentary",
        "{country} political documentary",
        "{country} social issues documentary",
        "{country} minority rights documentary",
        "{country} rural life documentary"
    ],
    "tier3": [
        "{country} history documentary",
        "{country} modern history documentary"
    ]
}


# --------------------------------------------------
# Utilities
# --------------------------------------------------

def _extract_api_error(data):
    error = data.get("error")
    if not isinstance(error, dict):
        return "Unknown YouTube API error"

    message = error.get("message", "Unknown message")
    reasons = []
    for item in error.get("errors", []):
        reason = item.get("reason")
        if reason:
            reasons.append(reason)

    if reasons:
        return f"{message} (reasons: {', '.join(sorted(set(reasons)))})"

    return message


def _extract_error_reasons(data):
    error = data.get("error")
    if not isinstance(error, dict):
        return set()
    reasons = set()
    for item in error.get("errors", []):
        reason = item.get("reason")
        if reason:
            reasons.add(reason)
    return reasons


def _is_quota_error(data):
    reasons = _extract_error_reasons(data)
    return (
        "quotaExceeded" in reasons
        or "dailyLimitExceeded" in reasons
        or "rateLimitExceeded" in reasons
    )


def _redact_sensitive(text):
    if not text:
        return text
    if YOUTUBE_API_KEY:
        return text.replace(YOUTUBE_API_KEY, "<REDACTED>")
    return text


def _safe_get_json(url, params, context):
    global QUOTA_EXHAUSTED
    if QUOTA_EXHAUSTED:
        return {}

    try:
        response = requests.get(url, params=params, timeout=20)
    except requests.RequestException as exc:
        print(f"[YouTube][{context}] request failed: {_redact_sensitive(str(exc))}")
        return {}

    try:
        data = response.json()
    except ValueError:
        print(
            f"[YouTube][{context}] non-JSON response "
            f"(status {response.status_code})."
        )
        return {}

    if response.status_code != 200:
        print(
            f"[YouTube][{context}] API error (status {response.status_code}): "
            f"{_extract_api_error(data)}"
        )
        if _is_quota_error(data):
            QUOTA_EXHAUSTED = True
            print("[YouTube] Quota exhausted. Stopping additional YouTube API calls.")
        return {}

    if isinstance(data, dict) and "error" in data:
        print(f"[YouTube][{context}] API error: {_extract_api_error(data)}")
        if _is_quota_error(data):
            QUOTA_EXHAUSTED = True
            print("[YouTube] Quota exhausted. Stopping additional YouTube API calls.")
        return {}

    return data

def parse_duration(duration):
    hours = minutes = seconds = 0
    h = re.search(r'(\d+)H', duration)
    m = re.search(r'(\d+)M', duration)
    s = re.search(r'(\d+)S', duration)

    if h:
        hours = int(h.group(1))
    if m:
        minutes = int(m.group(1))
    if s:
        seconds = int(s.group(1))

    return hours * 60 + minutes + seconds / 60


def fetch_video_details(video_ids):
    if not video_ids:
        return {}

    params = {
        "part": "contentDetails,snippet",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY
    }

    return _safe_get_json(
        YOUTUBE_VIDEO_URL,
        params,
        context=f"video details ({len(video_ids)} ids)"
    )


def score_history_video(title, channel):
    score = 0
    title_lower = title.lower()
    channel_lower = channel.lower()

    if any(key in channel_lower for key in INSTITUTIONAL_CHANNEL_KEYWORDS):
        score += 3

    if "documentary" in title_lower:
        score += 2

    if "investigation" in title_lower or "report" in title_lower:
        score += 1

    return score


# --------------------------------------------------
# History Retrieval (Credibility First)
# --------------------------------------------------

def search_history(country, max_per_category=9):
    collected = {}
    history_queries_used = 0

    for tier in ["tier1", "tier2", "tier3"]:
        if QUOTA_EXHAUSTED or history_queries_used >= MAX_HISTORY_QUERIES_TOTAL:
            break

        for query_template in HISTORY_TIERS[tier]:
            if QUOTA_EXHAUSTED or history_queries_used >= MAX_HISTORY_QUERIES_TOTAL:
                break

            query = query_template.format(country=country)
            history_queries_used += 1

            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 12,
                "key": YOUTUBE_API_KEY
            }

            search_data = _safe_get_json(
                YOUTUBE_SEARCH_URL,
                search_params,
                context=f"history search: {query}"
            )

            video_ids = [
                item["id"]["videoId"]
                for item in search_data.get("items", [])
            ]

            if not video_ids:
                continue

            video_data = fetch_video_details(video_ids)

            for item in video_data.get("items", []):
                title = item["snippet"]["title"]
                channel = item["snippet"]["channelTitle"]
                duration_minutes = parse_duration(item["contentDetails"]["duration"])

                if duration_minutes < 15:
                    continue

                if any(bad in title.lower() for bad in BAD_KEYWORDS):
                    continue

                video_id = item["id"]

                if video_id not in collected:
                    collected[video_id] = {
                        "title": title,
                        "channel": channel,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "duration_minutes": round(duration_minutes, 1),
                        "score": score_history_video(title, channel)
                    }

        if len(collected) >= max_per_category:
            break

    sorted_videos = sorted(
        collected.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return sorted_videos[:max_per_category]


# --------------------------------------------------
# General Category Retrieval
# --------------------------------------------------

def search_general_category(country, category, max_per_category=9):
    config = GENERAL_CATEGORY_CONFIG[category]
    collected = {}

    for query_template in config["queries"][:MAX_GENERAL_QUERIES_PER_CATEGORY]:
        if QUOTA_EXHAUSTED:
            break

        query = query_template.format(country=country)

        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }

        search_data = _safe_get_json(
            YOUTUBE_SEARCH_URL,
            search_params,
            context=f"{category} search: {query}"
        )

        video_ids = [
            item["id"]["videoId"]
            for item in search_data.get("items", [])
        ]

        if not video_ids:
            continue

        video_data = fetch_video_details(video_ids)

        for item in video_data.get("items", []):
            title = item["snippet"]["title"]
            duration_minutes = parse_duration(item["contentDetails"]["duration"])

            if duration_minutes < config["min_minutes"]:
                continue

            if any(bad in title.lower() for bad in BAD_KEYWORDS):
                continue

            video_id = item["id"]

            if video_id not in collected:
                collected[video_id] = {
                    "title": title,
                    "channel": item["snippet"]["channelTitle"],
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "duration_minutes": round(duration_minutes, 1)
                }

            if len(collected) >= max_per_category:
                break

        if len(collected) >= max_per_category:
            break

    return list(collected.values())


# --------------------------------------------------
# Public Entry Point
# --------------------------------------------------

def search_youtube_category(country, category, max_per_category=9):

    if category == "history":
        return search_history(country, max_per_category)

    if category not in GENERAL_CATEGORY_CONFIG:
        raise ValueError("Unknown category")

    return search_general_category(country, category, max_per_category)
