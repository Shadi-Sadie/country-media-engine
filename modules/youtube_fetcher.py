import requests
import re
import math
from config import YOUTUBE_API_KEY

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MIN_VIEWS_BY_CATEGORY = {
    "music": 1_000_000,
    "nature": 200_000,
    "life": 100_000,
    "history": 50_000
}

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

SEARCH_MAX_RESULTS = 15

# Country-specific artist/work queries for music.
# These bypass generic queries and target the actually famous artists.
# Add entries here whenever generic queries produce poor results for a country.
COUNTRY_MUSIC_QUERIES: dict[str, list[str]] = {
    "Armenia": [
        "Aram Khachaturian Sabre Dance",
        "Djivan Gasparyan duduk",
        "Sirusho official",
        "Charles Aznavour She",
        "Komitas Armenian folk music",
    ],
    "Iran": [
        "Shajarian Persian classical music",
        "Googoosh official",
        "Darya Persian music",
    ],
    "Turkey": [
        "Sezen Aksu official",
        "Ibrahim Tatlises official",
        "Tarkan official",
    ],
    "Greece": [
        "Mikis Theodorakis official",
        "Nikos Vertis official",
        "Greek traditional music",
    ],
    "Georgia": [
        "Georgian polyphonic singing",
        "Rustavi Choir official",
    ],
}

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
        "subtopics": {
            "wedding": [
                "{country} traditional wedding",
                "traditional wedding in {country}"
            ],
            "village": [
                "{country} village life",
                "{country} rural life"
            ],
            "daily_life": [
                "{country} one day in life",
                "{country} daily life"
            ],
            "recipe": [
                "{country} traditional recipe",
                "{country} cooking"
            ],
            "street_food": [
                "{country} street food"
            ]
        },
        "min_minutes": 4
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
    params = {
        "part": "contentDetails,snippet,statistics",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(YOUTUBE_VIDEO_URL, params=params)
    return response.json()


def get_view_count(item):
    try:
        return int(item["statistics"].get("viewCount", 0))
    except (KeyError, ValueError):
        return 0


def get_min_views(category):
    return MIN_VIEWS_BY_CATEGORY.get(category, 0)


def normalize_text(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def tokenize_text(text):
    return [token for token in normalize_text(text).split() if token]


def country_tokens(country):
    tokens = [token for token in tokenize_text(country) if len(token) >= 4]
    if not tokens:
        return tokenize_text(country)
    return tokens


def _country_stems(country):
    stems = set()
    for token in country_tokens(country):
        if len(token) >= 6:
            stems.add(token[:-1])
    return stems


def country_match_score(text, country):
    text_normalized = normalize_text(text)
    if not text_normalized:
        return 0

    score = 0
    country_normalized = normalize_text(country)
    if country_normalized and country_normalized in text_normalized:
        score += 5

    text_tokens = tokenize_text(text)
    text_token_set = set(text_tokens)
    for token in country_tokens(country):
        if token in text_token_set:
            score += 2

    for stem in _country_stems(country):
        if any(token.startswith(stem) for token in text_tokens):
            score += 1

    return score


def topic_match_score(text, query, country):
    query_tokens = [
        token
        for token in tokenize_text(query)
        if token not in country_tokens(country) and len(token) >= 4
    ]
    if not query_tokens:
        return 0

    text_tokens = tokenize_text(text)
    score = 0
    for query_token in query_tokens:
        if query_token in text_tokens:
            score += 2
            continue

        if len(query_token) >= 6 and any(token.startswith(query_token[:-1]) for token in text_tokens):
            score += 1

    return score


def score_video_relevance(country, query, title, description, channel):
    score = 0
    score += country_match_score(title, country) * 3
    score += country_match_score(description, country) * 2
    score += country_match_score(channel, country)
    score += topic_match_score(title, query, country) * 2
    score += topic_match_score(description, query, country)
    return score


def is_relevant_video(country, query, title, description, channel, min_score=8):
    relevance = score_video_relevance(country, query, title, description, channel)
    title_country_score = country_match_score(title, country)
    description_country_score = country_match_score(description, country)
    return relevance >= min_score and (title_country_score > 0 or description_country_score > 0)


def score_history_video(title, channel, view_count=0):
    score = 0
    title_lower = title.lower()
    channel_lower = channel.lower()

    if any(key in channel_lower for key in INSTITUTIONAL_CHANNEL_KEYWORDS):
        score += 3

    if "documentary" in title_lower:
        score += 2

    if "investigation" in title_lower or "report" in title_lower:
        score += 1

    # Log-scaled view count bonus (e.g. 1M views → +6, 100K → +5, 10K → +4)
    if view_count > 0:
        score += math.log10(view_count)

    return score


# --------------------------------------------------
# History Retrieval (Credibility First)
# --------------------------------------------------

def search_history(country, max_per_category=9):
    collected = {}
    target = max_per_category * 3  # collect a larger pool, then pick the best
    min_view_count = get_min_views("history")

    for tier in ["tier1", "tier2", "tier3"]:
        for query_template in HISTORY_TIERS[tier]:

            query = query_template.format(country=country)

            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": SEARCH_MAX_RESULTS,
                "key": YOUTUBE_API_KEY
            }

            search_response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            search_data = search_response.json()

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
                description = item["snippet"].get("description", "")
                duration_minutes = parse_duration(item["contentDetails"]["duration"])
                view_count = get_view_count(item)

                if duration_minutes < 8:
                    continue

                if view_count < min_view_count:
                    continue

                if any(bad in title.lower() for bad in BAD_KEYWORDS):
                    continue

                relevance_score = score_video_relevance(country, query, title, description, channel)
                if relevance_score < 8:
                    continue

                video_id = item["id"]

                if video_id not in collected:
                    collected[video_id] = {
                        "title": title,
                        "channel": channel,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "duration_minutes": round(duration_minutes, 1),
                        "view_count": view_count,
                        "score": score_history_video(title, channel, view_count) + relevance_score,
                        "relevance_score": relevance_score,
                    }

        if len(collected) >= target:
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
    min_view_count = get_min_views(category)

    # For music, use country-specific artist queries when available,
    # falling back to generic queries otherwise.
    if category == "music" and country in COUNTRY_MUSIC_QUERIES:
        query_templates = COUNTRY_MUSIC_QUERIES[country]
        use_relaxed_relevance = True  # artist queries don't mention country in title
        # Pick at most 1 result per artist query so one popular artist
        # doesn't fill all slots.
        one_per_query = True
    else:
        query_templates = config["queries"]
        use_relaxed_relevance = False
        one_per_query = False

    for query_template in query_templates:
        if len(collected) >= max_per_category:
            break

        # Country-specific queries are already fully formed; generic ones use {country}
        query = query_template if "{country}" not in query_template else query_template.format(country=country)

        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": SEARCH_MAX_RESULTS,
            "key": YOUTUBE_API_KEY
        }

        search_response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
        search_data = search_response.json()

        video_ids = [
            item["id"]["videoId"]
            for item in search_data.get("items", [])
        ]

        if not video_ids:
            continue

        video_data = fetch_video_details(video_ids)

        # Collect candidates for this query, sorted by view count
        query_candidates = []
        for item in video_data.get("items", []):
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            description = item["snippet"].get("description", "")
            duration_minutes = parse_duration(item["contentDetails"]["duration"])
            view_count = get_view_count(item)

            if duration_minutes < config["min_minutes"]:
                continue

            if view_count < min_view_count:
                continue

            if any(bad in title.lower() for bad in BAD_KEYWORDS):
                continue

            relevance_score = score_video_relevance(country, query, title, description, channel)

            if use_relaxed_relevance:
                topic_score = topic_match_score(title, query, country)
                if topic_score == 0 and relevance_score < 4:
                    continue
            else:
                if not is_relevant_video(country, query, title, description, channel):
                    continue

            query_candidates.append({
                "id": item["id"],
                "title": title,
                "channel": channel,
                "url": f"https://youtube.com/watch?v={item['id']}",
                "duration_minutes": round(duration_minutes, 1),
                "view_count": view_count,
                "relevance_score": relevance_score,
            })

        # Sort this query's candidates by view count descending
        query_candidates.sort(key=lambda x: x["view_count"], reverse=True)

        added = 0
        for entry in query_candidates:
            video_id = entry["id"]
            if video_id in collected:
                continue
            collected[video_id] = {k: v for k, v in entry.items() if k != "id"}
            added += 1
            if one_per_query:
                break  # one best result per artist query for diversity

    # Music: sort by view count — most-viewed = most culturally significant.
    # Other categories: sort by relevance first, then view count.
    if category == "music":
        sorted_videos = sorted(collected.values(), key=lambda x: x["view_count"], reverse=True)
    else:
        sorted_videos = sorted(
            collected.values(),
            key=lambda x: (x["relevance_score"], x["view_count"]),
            reverse=True,
        )
    return sorted_videos[:max_per_category]


def _fetch_subtopic_candidates(country, query_list, min_minutes, max_results, min_view_count):
    """Return all valid candidates from a subtopic's queries, sorted by view count."""
    candidates = {}

    for query_template in query_list:
        query = query_template.format(country=country)

        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": YOUTUBE_API_KEY
        }

        search_response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
        search_data = search_response.json()

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
            description = item["snippet"].get("description", "")
            duration_minutes = parse_duration(item["contentDetails"]["duration"])
            view_count = get_view_count(item)

            if duration_minutes < min_minutes:
                continue

            if view_count < min_view_count:
                continue

            if any(bad in title.lower() for bad in BAD_KEYWORDS):
                continue

            relevance_score = score_video_relevance(country, query, title, description, channel)
            if not is_relevant_video(country, query, title, description, channel):
                continue

            video_id = item["id"]

            if video_id not in candidates:
                candidates[video_id] = {
                    "title": title,
                    "channel": channel,
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "duration_minutes": round(duration_minutes, 1),
                    "view_count": view_count,
                    "relevance_score": relevance_score,
                }

    return sorted(
        candidates.values(),
        key=lambda x: (x["relevance_score"], x["view_count"]),
        reverse=True,
    )


def search_life_with_subtopics(country, max_per_category=9):
    config = GENERAL_CATEGORY_CONFIG["life"]
    collected = {}  # video_id → entry
    min_view_count = get_min_views("life")

    # First pass: pick the most-viewed valid video from each subtopic
    for query_list in config["subtopics"].values():
        candidates = _fetch_subtopic_candidates(
            country,
            query_list,
            config["min_minutes"],
            max_results=SEARCH_MAX_RESULTS,
            min_view_count=min_view_count,
        )

        for entry in candidates:
            video_id = entry["url"].split("v=")[-1]
            if video_id not in collected:
                collected[video_id] = entry
                break  # one best pick per subtopic

        if len(collected) >= max_per_category:
            return list(collected.values())

    # Second pass: fill remaining slots from all subtopics, sorted by view count
    overflow = {}
    for query_list in config["subtopics"].values():
        candidates = _fetch_subtopic_candidates(
            country,
            query_list,
            config["min_minutes"],
            max_results=SEARCH_MAX_RESULTS,
            min_view_count=min_view_count,
        )
        for entry in candidates:
            video_id = entry["url"].split("v=")[-1]
            if video_id not in collected and video_id not in overflow:
                overflow[video_id] = entry

    sorted_overflow = sorted(overflow.values(), key=lambda x: x["view_count"], reverse=True)
    for entry in sorted_overflow:
        if len(collected) >= max_per_category:
            break
        video_id = entry["url"].split("v=")[-1]
        collected[video_id] = entry

    return list(collected.values())[:max_per_category]


# --------------------------------------------------
# Public Entry Point
# --------------------------------------------------

def search_youtube_category(country, category, max_per_category=9):

    if category == "history":
        return search_history(country, max_per_category)
    
    if category == "life":
        return search_life_with_subtopics(country, max_per_category)

    if category not in GENERAL_CATEGORY_CONFIG:
        raise ValueError("Unknown category")

    return search_general_category(country, category, max_per_category)
