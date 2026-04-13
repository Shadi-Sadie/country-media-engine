import os
import re

import requests

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": "CountryMediaEngine/1.0 (seyedi7229@gmail.com)"
}


def _search_file_results(search_query, limit=5):
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": search_query,
        "srnamespace": 6,
        "srlimit": limit,
    }

    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []

    return data.get("query", {}).get("search", [])


def _resolve_commons_image(title):
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 1200,
    }

    try:
        response = requests.get(WIKIMEDIA_API_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None, None

    pages = data.get("query", {}).get("pages", {})
    is_svg = title.lower().endswith(".svg")
    extension = ".png" if is_svg else os.path.splitext(title)[1].lower()
    if extension not in (".png", ".jpg", ".jpeg"):
        extension = ".png"

    for page in pages.values():
        imageinfo = page.get("imageinfo")
        if not imageinfo:
            continue

        if is_svg:
            image_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
        else:
            image_url = imageinfo[0].get("url") or imageinfo[0].get("thumburl")

        if image_url:
            return image_url, extension

    return None, None


def _download_image(image_url, output_path):
    try:
        img_response = requests.get(image_url, headers=HEADERS, timeout=15)
        img_response.raise_for_status()
    except requests.RequestException:
        return None

    with open(output_path, "wb") as f:
        f.write(img_response.content)
    return output_path


def _download_best_search_result(search_queries, output_prefix, prefer_svg=False):
    for search_query in search_queries:
        results = _search_file_results(search_query)
        if not results:
            continue

        ranked_results = sorted(
            results,
            key=lambda item: 0 if item.get("title", "").lower().endswith(".svg") == prefer_svg else 1,
        )

        for result in ranked_results:
            title = result.get("title", "")
            if not title:
                continue

            image_url, extension = _resolve_commons_image(title)
            if not image_url:
                continue

            output_path = f"{output_prefix}{extension}"
            downloaded = _download_image(image_url, output_path)
            if downloaded:
                return downloaded

    return None


def _slugify(text):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return slug[:40] or "fact"


def search_country_image(country, output_folder="outputs"):
    os.makedirs(output_folder, exist_ok=True)
    return _download_best_search_result(
        [
            f'intitle:"{country}" intitle:"on the globe"',
            f'intitle:"{country}" map',
            f'{country} location map',
        ],
        os.path.join(output_folder, f"{country}_image"),
        prefer_svg=True,
    )


def search_fun_fact_image(country, fact_title, index, output_folder="outputs"):
    os.makedirs(output_folder, exist_ok=True)
    safe_title = _slugify(fact_title)
    output_prefix = os.path.join(output_folder, f"{country}_fun_fact_{index:02d}_{safe_title}")

    search_queries = [
        f'intitle:"{country}" intitle:"{fact_title}"',
        f'"{country}" "{fact_title}"',
        f"{country} {fact_title}",
        fact_title,
    ]
    return _download_best_search_result(
        search_queries,
        output_prefix,
        prefer_svg=False,
    )
