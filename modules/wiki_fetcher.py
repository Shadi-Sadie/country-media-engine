import requests
import re
from urllib.parse import quote

WIKI_SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_QUERY_API = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "country-media-engine/1.0 (contact: seyedi7229@gmail.com)"
}

def _request_or_raise(url, **kwargs):
    try:
        return requests.get(url, **kwargs)
    except requests.exceptions.RequestException as exc:
        raise Exception(
            "Network error while contacting Wikipedia. "
            "Check internet/DNS access and any proxy settings."
        ) from exc

def clean_text(text):
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def fetch_wikipedia_summary(country):
    encoded_country = quote(country)
    url = WIKI_SUMMARY_API + encoded_country

    response = _request_or_raise(url, headers=HEADERS, timeout=20)

    if response.status_code != 200:
        print("Status code:", response.status_code)
        print("Response:", response.text)
        raise Exception(f"Failed to fetch Wikipedia page for {country}")

    data = response.json()
    summary = data.get("extract")

    if not summary:
        raise Exception(f"No summary found for {country}")

    return clean_text(summary)


def fetch_wikipedia_full_text(country):
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "prop": "extracts",
        "explaintext": 1,
        "titles": country,
        "redirects": 1
    }

    response = _request_or_raise(
        WIKI_QUERY_API,
        params=params,
        headers=HEADERS,
        timeout=20
    )

    print("Status code:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise Exception(f"Failed to fetch Wikipedia page for {country}")

    data = response.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise Exception("No pages returned from Wikipedia.")

    page = pages[0]

    extract = page.get("extract")

    if not extract:
        raise Exception(f"No extract found for {country}")

    return clean_text(extract)
