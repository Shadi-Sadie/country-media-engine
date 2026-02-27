import requests
import re
from config import YOUTUBE_API_KEY

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"

CATEGORY_CONFIG = {
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
        "street_food": "{country} street food",
        "recipe": "{country} traditional recipe",
        "village": "{country} village life",
        "wedding": "{country} wedding",
        "daily_life": "{country} one day in life"
    },
    "min_minutes": 6
  },
    "nature": {
        "queries": [
            "{country} nature documentary",
            "{country} scenic 4K",
            "{country} travel documentary"
        ],
        "min_minutes": 8
    },
    "history": {
        "queries": [
            "{country} history documentary",
            "{country} politics documentary",
            "{country} BBC documentary",
            "{country} PBS documentary",
            "{country} New York Times documentary",
            "{country} Guardian documentary"
        ],
        "min_minutes": 15
    }
}

BAD_KEYWORDS = [
    "short",
    "shorts",
    "tiktok",
    "reaction",
    "clip",
    "trailer"
]


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


def search_youtube_category(country, category, max_per_category=9):

    if category not in CATEGORY_CONFIG:
        raise ValueError("Unknown category")

    config = CATEGORY_CONFIG[category]
    collected = {}
    
    for query_template in config["queries"]:
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

        video_params = {
            "part": "contentDetails,snippet",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY
        }

        video_response = requests.get(YOUTUBE_VIDEO_URL, params=video_params)
        video_data = video_response.json()

        for item in video_data.get("items", []):
            title = item["snippet"]["title"]
            title_lower = title.lower()

            if any(bad in title_lower for bad in BAD_KEYWORDS):
                continue

            duration_iso = item["contentDetails"]["duration"]
            duration_minutes = parse_duration(duration_iso)

            if duration_minutes < config["min_minutes"]:
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