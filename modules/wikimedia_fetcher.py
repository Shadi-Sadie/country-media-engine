# modules/wikimedia_fetcher.py

import requests
import os

WIKIMEDIA_API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": "CountryMediaEngine/1.0 (seyedi7229@gmail.com)"
}


def search_country_image(country, output_folder="outputs"):

    # Search ONLY in File namespace (ns=6)
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": f'intitle:"{country}" intitle:"on the globe"',
        "srnamespace": 6,
        "srlimit": 5
    }

    try:
        response = requests.get(
            WIKIMEDIA_API_URL,
            params=params,
            headers=HEADERS,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None

    results = data.get("query", {}).get("search", [])

    if not results:
        return None

    # Prefer SVG map files first, then fallback to other image files.
    ranked_results = sorted(
        results,
        key=lambda item: 0 if item.get("title", "").lower().endswith(".svg") else 1
    )

    for result in ranked_results:
        title = result.get("title", "")
        if not title:
            continue

        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 1200
        }

        try:
            response = requests.get(
                WIKIMEDIA_API_URL,
                params=params,
                headers=HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            continue

        pages = data.get("query", {}).get("pages", {})
        is_svg = title.lower().endswith(".svg")
        extension = ".png" if is_svg else os.path.splitext(title)[1].lower()
        if extension not in (".png", ".jpg", ".jpeg"):
            extension = ".png"

        for page in pages.values():
            imageinfo = page.get("imageinfo")
            if not imageinfo:
                continue

            # For SVG, thumburl is rendered PNG. For non-SVG, keep original URL.
            if is_svg:
                image_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
            else:
                image_url = imageinfo[0].get("url") or imageinfo[0].get("thumburl")

            if not image_url:
                continue

            os.makedirs(output_folder, exist_ok=True)
            image_path = os.path.join(output_folder, f"{country}_image{extension}")

            try:
                img_response = requests.get(image_url, headers=HEADERS, timeout=15)
                img_response.raise_for_status()

                with open(image_path, "wb") as f:
                    f.write(img_response.content)

                return image_path
            except requests.RequestException:
                continue

    return None
