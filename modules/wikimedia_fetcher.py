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

    # Take first matching file
    title = results[0]["title"]  # e.g. File:Andorra_on_the_globe_(Europe_centered).svg

    # Now fetch imageinfo
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
        return None

    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        imageinfo = page.get("imageinfo")
        if not imageinfo:
            continue

        # Use thumbnail PNG instead of raw SVG
        image_url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
        if not image_url:
            continue

        if not image_url.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        os.makedirs(output_folder, exist_ok=True)
        image_path = os.path.join(output_folder, f"{country}_image.png")

        try:
            img_response = requests.get(image_url, headers=HEADERS, timeout=15)
            img_response.raise_for_status()

            with open(image_path, "wb") as f:
                f.write(img_response.content)

            return image_path
        except requests.RequestException:
            continue

    return None