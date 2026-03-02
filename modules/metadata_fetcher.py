# modules/metadata_fetcher.py

import requests

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

HEADERS = {
    "User-Agent": "country-media-engine/1.0 (contact: seyedi7229@gmail.com)"
}


def _get_qid_from_wikipedia(title: str) -> str | None:
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": 1,
    }
    r = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    for _, page in pages.items():
        qid = page.get("pageprops", {}).get("wikibase_item")
        if qid:
            return qid
    return None


def _fetch_entity(qid: str) -> dict:
    r = requests.get(WIKIDATA_ENTITY.format(qid), headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["entities"][qid]


def _get_label(entity_id: str, lang: str = "fa") -> str | None:
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": entity_id,
        "props": "labels",
        "languages": lang,
    }
    r = requests.get(WIKIDATA_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    ent = r.json().get("entities", {}).get(entity_id, {})
    return ent.get("labels", {}).get(lang, {}).get("value")


def _claim_ids(entity: dict, prop: str) -> list[str]:
    claims = entity.get("claims", {}).get(prop, [])
    ids = []
    for c in claims:
        dv = c.get("mainsnak", {}).get("datavalue", {})
        val = dv.get("value", {})
        if isinstance(val, dict) and "id" in val:
            ids.append(val["id"])
    return ids


def _claim_number(entity: dict, prop: str) -> float | None:
    claims = entity.get("claims", {}).get(prop, [])
    for c in claims:
        dv = c.get("mainsnak", {}).get("datavalue", {})
        val = dv.get("value", {})
        if isinstance(val, dict) and "amount" in val:
            return float(val["amount"].replace("+", ""))
    return None


def _claim_string(entity: dict, prop: str) -> str | None:
    claims = entity.get("claims", {}).get(prop, [])
    for c in claims:
        dv = c.get("mainsnak", {}).get("datavalue", {})
        val = dv.get("value")
        if isinstance(val, str):
            return val.strip() or None
        if isinstance(val, dict):
            text = val.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _iso2_to_flag_emoji(iso2: str | None) -> str:
    if not iso2:
        return ""
    code = iso2.strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(ord(ch) + 127397) for ch in code)


def fetch_country_metadata(country: str) -> dict:
    qid = _get_qid_from_wikipedia(country)
    if not qid:
        return {
            "name_fa": country,
            "flag": "",
            "capital": "نامشخص",
            "area": "نامشخص",
            "location": "نامشخص",
            "neighbors": "نامشخص",
            "population": "نامشخص",
            "languages": "نامشخص",
        }

    ent = _fetch_entity(qid)

    # Claims
    capital_ids = _claim_ids(ent, "P36")     # capital
    lang_ids = _claim_ids(ent, "P37")        # official language
    border_ids = _claim_ids(ent, "P47")      # shares border with (neighbors)
    continent_ids = _claim_ids(ent, "P30")  # continent
    area = _claim_number(ent, "P2046")       # area (km2)
    pop = _claim_number(ent, "P1082")        # population
    iso2 = _claim_string(ent, "P297")        # ISO 3166-1 alpha-2 code

    # Labels in Persian
    name_fa = _get_label(qid, "fa") or country
    capital_fa = _get_label(capital_ids[0], "fa") if capital_ids else None
    langs_fa = [(_get_label(x, "fa") or "") for x in lang_ids[:4]] if lang_ids else []
    borders_fa = [(_get_label(x, "fa") or "") for x in border_ids[:10]] if border_ids else []
    continent_fa = (_get_label(continent_ids[0], "fa")if continent_ids else None)   
    neighbors = "، ".join([b for b in borders_fa if b]) if borders_fa else "مرز زمینی ندارد"
    flag_emoji = _iso2_to_flag_emoji(iso2)

    return {
        "name_fa": name_fa,
        "flag": flag_emoji,
        "capital": capital_fa or "نامشخص",
        "area": f"{area:,.0f} کیلومتر مربع" if area else "نامشخص",
        "location": continent_fa or "نامشخص",  # can be improved later
        "neighbors": neighbors,
        "population": f"{pop:,.0f} نفر" if pop else "نامشخص",
        "languages": "، ".join([l for l in langs_fa if l]) if langs_fa else "نامشخص",
    }
