from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata


UN_MEMBER_STATES_PATH = Path(__file__).resolve().parents[1] / "data" / "un_member_states.txt"

UN_NAME_TO_PIPELINE_NAME = {
    "Bahamas (The)": "Bahamas",
    "Bolivia (Plurinational State of)": "Bolivia",
    "Brunei Darussalam": "Brunei",
    "China (the People's Republic of)": "China",
    "Congo": "Republic of the Congo",
    "Côte D'Ivoire": "Ivory Coast",
    "Democratic People's Republic of Korea": "North Korea",
    "Gambia (Republic of The)": "Gambia",
    "Iran (Islamic Republic of)": "Iran",
    "Lao People’s Democratic Republic": "Laos",
    "Micronesia (Federated States of)": "Micronesia",
    "Netherlands (Kingdom of the)": "Netherlands",
    "Republic of Korea": "South Korea",
    "Republic of Moldova": "Moldova",
    "Russian Federation": "Russia",
    "Syrian Arab Republic": "Syria",
    "Türkiye": "Turkey",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United Republic of Tanzania": "Tanzania",
    "United States of America": "United States",
    "Venezuela, Bolivarian Republic of": "Venezuela",
    "Viet Nam": "Vietnam",
}


@dataclass(frozen=True)
class UnScheduleEntry:
    week_number: int
    official_name: str
    country_name: str


def _normalize_key(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").strip())
    normalized = normalized.replace("’", "'").replace("‘", "'").replace("`", "'")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def load_un_member_states() -> list[str]:
    if not UN_MEMBER_STATES_PATH.exists():
        raise FileNotFoundError(f"UN member states file not found: {UN_MEMBER_STATES_PATH}")
    return [
        line.strip()
        for line in UN_MEMBER_STATES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def pipeline_country_name(official_name: str) -> str:
    return UN_NAME_TO_PIPELINE_NAME.get(official_name, official_name)


def get_un_schedule() -> list[UnScheduleEntry]:
    return [
        UnScheduleEntry(
            week_number=index,
            official_name=official_name,
            country_name=pipeline_country_name(official_name),
        )
        for index, official_name in enumerate(load_un_member_states(), start=1)
    ]


def resolve_un_schedule(country: str | None = None, week_number: int | None = None) -> UnScheduleEntry:
    schedule = get_un_schedule()

    if week_number is not None:
        if week_number < 1 or week_number > len(schedule):
            raise ValueError(
                f"Week number must be between 1 and {len(schedule)} for the UN member-state list."
            )
        entry = schedule[week_number - 1]
        if country:
            country_key = _normalize_key(country)
            valid_keys = {
                _normalize_key(entry.country_name),
                _normalize_key(entry.official_name),
            }
            if country_key not in valid_keys:
                raise ValueError(
                    f"Week {week_number:02d} maps to '{entry.country_name}' "
                    f"(official UN name: '{entry.official_name}'), not '{country}'."
                )
        return entry

    if not country:
        raise ValueError("Provide either a country name or --week-number.")

    country_key = _normalize_key(country)
    for entry in schedule:
        if country_key in {
            _normalize_key(entry.country_name),
            _normalize_key(entry.official_name),
        }:
            return entry

    raise ValueError(f"Country '{country}' was not found in the cached UN member-state list.")


def format_week_tag(week_number: int) -> str:
    return f"#week{week_number:02d}"
