import requests
import re
from config import YOUTUBE_API_KEY

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


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
        "part": "contentDetails,snippet",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(YOUTUBE_VIDEO_URL, params=params)
    return response.json()


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

    for tier in ["tier1", "tier2", "tier3"]:
        for query_template in HISTORY_TIERS[tier]:

            query = query_template.format(country=country)

            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 12,
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

    for query_template in config["queries"]:
        query = query_template.format(country=country)

        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
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


def search_life_with_subtopics(country, max_per_category=9):
    config = GENERAL_CATEGORY_CONFIG["life"]
    collected = {}

    # First pass: guarantee at least 1 per subtopic
    for subtopic, query_list in config["subtopics"].items():
        for query_template in query_list:

            query = query_template.format(country=country)

            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 8,
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
                    break  # move to next subtopic

            if len(collected) >= max_per_category:
                return list(collected.values())

    # Second pass: fill remaining slots
    for subtopic, query_list in config["subtopics"].items():
        for query_template in query_list:

            if len(collected) >= max_per_category:
                return list(collected.values())

            query = query_template.format(country=country)

            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 10,
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