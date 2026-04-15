import argparse
import os
import re
from pathlib import Path

from modules.metadata_fetcher import fetch_country_metadata
from modules.prompt_manager import prepare_country_prompts
from modules.telegram_post_generator_manual import (
    build_hashtags,
    generate_audio_caption,
    generate_caption,
    is_caption_within_limit,
)
from modules.telegram_publisher_manual import publish_package
from modules.un_schedule import resolve_un_schedule
from modules.wiki_fetcher import fetch_wikipedia_full_text
from modules.wikimedia_fetcher import search_country_image, search_fun_fact_image


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _country_paths(country: str) -> dict[str, Path]:
    out_dir = Path("outputs")
    return {
        "out_dir": out_dir,
        "wiki": out_dir / f"{country}_wiki.txt",
        "script": out_dir / f"{country}_script.txt",
        "fun_fact": out_dir / f"{country}_fun_fact.txt",
        "caption": out_dir / f"{country}_telegram.txt",
        "links": out_dir / f"{country}_links.txt",
        "audio": out_dir / f"{country}.mp3",
    }


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _load_fun_facts(path: Path) -> list[str]:
    text = _read_text(path)
    if not text:
        return []

    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(parts) == 1:
        return [line.strip() for line in text.splitlines() if line.strip()]
    return parts


def _load_fun_facts_caption(path: Path) -> str:
    return _read_text(path)


def _find_image_path(country: str, out_dir: Path) -> str | None:
    for ext in (".png", ".jpg", ".jpeg"):
        candidate = out_dir / f"{country}_image{ext}"
        if candidate.exists():
            return str(candidate)
    return None


def _extract_fun_fact_title(fact: str, index: int) -> str:
    match = re.search(r"<b>(.*?)</b>", fact)
    if match:
        title = match.group(1).strip()
        if title:
            return title
    plain = re.sub(r"<[^>]+>", "", fact).strip("▪️ ").strip()
    return plain or f"fact {index}"


def _find_fun_fact_image_by_index(country: str, out_dir: Path, index: int) -> str | None:
    pattern = f"{country}_fun_fact_{index:02d}_*"
    matches = sorted(out_dir.glob(pattern))
    for path in matches:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            return str(path)
    return None


def _ensure_fun_fact_images(country: str, fun_facts: list[str], out_dir: Path) -> list[str]:
    image_paths = []
    for index, fact in enumerate(fun_facts, start=1):
        existing_path = _find_fun_fact_image_by_index(country, out_dir, index)
        if existing_path:
            image_paths.append(existing_path)
            continue

        fact_title = _extract_fun_fact_title(fact, index)
        print(f"Fetching fun-fact image {index}: {fact_title}")
        image_path = search_fun_fact_image(
            country,
            fact_title,
            index=index,
            output_folder=str(out_dir),
        )
        if image_path:
            image_paths.append(image_path)
        else:
            print(f"No Wikimedia image found for fun fact {index}: {fact_title}")

    return image_paths


def _build_audio(country: str, script_text: str, dry_run: bool = False) -> str:
    audio_path = Path("outputs") / f"{country}.mp3"
    overwrite = _env_flag("ELEVENLABS_OVERWRITE", default=False)
    if not overwrite and audio_path.exists() and audio_path.stat().st_size > 0:
        print(
            f"Audio already exists at {audio_path}. "
            "Set ELEVENLABS_OVERWRITE=1 to regenerate."
        )
        return str(audio_path)

    script_text = (script_text or "").strip()
    if not script_text:
        print("Audio generation skipped: no script text available.")
        return ""

    force_chunk = _env_flag("ELEVENLABS_FORCE_CHUNK", default=False)
    max_chars_raw = os.getenv("ELEVENLABS_MAX_CHARS", "").strip()
    max_chars = None
    if max_chars_raw:
        try:
            max_chars = int(max_chars_raw)
        except ValueError:
            print("Invalid ELEVENLABS_MAX_CHARS value; falling back to model default.")

    try:
        from modules.elevenlabs_tts import (
            build_tts_plan,
            elevenlabs_preflight,
            elevenlabs_script_to_mp3,
            resolve_model_id,
            resolve_voice_id,
        )

        model_id = resolve_model_id()
        voice_id = resolve_voice_id()
        plan = build_tts_plan(
            script_fa=script_text,
            model_id=model_id,
            max_chars=max_chars,
            force_chunk=force_chunk,
        )
        print(
            "ElevenLabs plan:",
            f"model={model_id}, chars={plan['char_count']}, chunks={plan['chunk_count']},",
            f"chunk_size={plan['chunk_size']}",
        )

        preflight = elevenlabs_preflight(voice_id=voice_id, model_id=model_id)
        voice_name = preflight.get("voice_name")
        if voice_name:
            print(f"ElevenLabs voice: {voice_name} ({voice_id})")
        if preflight.get("model_available") is False:
            print(f"ElevenLabs preflight warning: model '{model_id}' not returned by /models.")
        for warning in preflight.get("warnings", []):
            print("ElevenLabs preflight warning:", warning)

        if dry_run:
            print("Audio generation skipped: ELEVENLABS_DRY_RUN is enabled.")
            return ""

        output_path = elevenlabs_script_to_mp3(
            script_fa=script_text,
            out_dir="outputs",
            out_mp3_name=f"{country}.mp3",
            voice_id=voice_id,
            model_id=model_id,
            max_chars=max_chars,
            force_chunk=force_chunk,
        )
        return str(output_path)
    except Exception as exc:
        print("ElevenLabs TTS failed:", exc)
        return ""


def _prepare_country_package(country: str, week_number: int) -> dict[str, str]:
    paths = _country_paths(country)
    paths["out_dir"].mkdir(parents=True, exist_ok=True)

    print("Fetching Wikipedia text...")
    wiki_text = fetch_wikipedia_full_text(country)
    _write_text(paths["wiki"], wiki_text)
    print("Wikipedia text saved at:", paths["wiki"])

    print("Rendering country prompts...")
    prompt_paths = prepare_country_prompts(
        country,
        output_dir=str(paths["out_dir"]),
        week_number=week_number,
    )
    for _, prompt_path in prompt_paths.items():
        print("Prompt ready at:", prompt_path)

    print("Fetching metadata...")
    metadata = fetch_country_metadata(country)
    hashtags = build_hashtags(country, week_number=week_number)

    caption_text = generate_caption(country, metadata, hashtags["lines"])
    _write_text(paths["caption"], caption_text)
    print("Caption saved at:", paths["caption"])
    print("Curated links file will be created from the links prompt at:", paths["links"])

    print("Fetching Wikimedia image...")
    image_path = search_country_image(country, output_folder=str(paths["out_dir"]))
    if image_path:
        print("Image saved at:", image_path)
    else:
        print("No image found from Wikimedia.")

    return {
        "country_fa": metadata.get("name_fa", country),
        "image_path": image_path or "",
        "hashtags_inline": hashtags["inline"],
    }


def _publish_from_outputs(country: str, week_number: int, skip_audio: bool = False) -> bool:
    paths = _country_paths(country)
    caption_text = _read_text(paths["caption"])
    links_text = _read_text(paths["links"])
    if not caption_text or not links_text:
        print("Publish-only mode failed: caption or curated links file is missing.")
        return False

    fun_facts = _load_fun_facts(paths["fun_fact"])
    if not fun_facts:
        print("Publish-only mode failed: fun-facts file is missing or empty.")
        return False
    fun_facts_caption = _load_fun_facts_caption(paths["fun_fact"])
    fun_fact_images = _ensure_fun_fact_images(country, fun_facts, paths["out_dir"])
    image_path = _find_image_path(country, paths["out_dir"])
    audio_path = str(paths["audio"]) if paths["audio"].exists() and not skip_audio else ""
    hashtags = build_hashtags(country, week_number=week_number)
    audio_caption = generate_audio_caption(country, country, hashtags["inline"]) if audio_path else ""

    if not image_path:
        print("Publish-only mode failed: country image is missing.")
        return False

    if fun_fact_images and not is_caption_within_limit(fun_facts_caption):
        print(
            "Publish-only mode failed: fun-facts caption exceeds Telegram caption limit "
            f"({len(fun_facts_caption)} > 1024)."
        )
        return False

    if len(fun_fact_images) != len(fun_facts):
        print(
            "Publish-only mode failed: not every fun fact has a matching image "
            f"({len(fun_fact_images)} images for {len(fun_facts)} facts)."
        )
        return False

    if not skip_audio and not audio_path:
        print("Publish-only mode failed: audio file is missing.")
        return False

    return publish_package(
        main_post_caption=caption_text,
        links_text=links_text,
        image_path=image_path,
        fun_fact_images=fun_fact_images,
        fun_facts_caption=fun_facts_caption,
        audio_path=audio_path or None,
        audio_caption=audio_caption,
        audio_title=country,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual country media pipeline")
    parser.add_argument("country", nargs="?", help="Country name, e.g. Armenia")
    parser.add_argument(
        "--week-number",
        type=int,
        help="UN list position/week number, e.g. 8 resolves to Armenia in the current cached list.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Fetch raw materials and render prompt files, but do not publish.",
    )
    parser.add_argument(
        "--publish-only",
        action="store_true",
        help="Publish from files that already exist in outputs/.",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip ElevenLabs audio generation and audio publishing.",
    )
    args = parser.parse_args()

    if args.prepare_only and args.publish_only:
        raise SystemExit("Choose only one mode: --prepare-only or --publish-only")

    try:
        schedule = resolve_un_schedule(country=args.country, week_number=args.week_number)
    except ValueError as exc:
        raise SystemExit(str(exc))

    country = schedule.country_name
    week_number = schedule.week_number
    print(
        f"\n=== Manual media pipeline for {country} "
        f"(week {week_number:02d}, UN official: {schedule.official_name}) ===\n"
    )

    if args.publish_only:
        publish_ok = _publish_from_outputs(country, week_number=week_number, skip_audio=args.no_audio)
        print("Published successfully." if publish_ok else "Publishing failed.")
        return

    prepared = _prepare_country_package(country, week_number=week_number)
    if args.prepare_only:
        print("Preparation complete. Create the script, fun facts, and links from the rendered prompts, then rerun.")
        return

    paths = _country_paths(country)
    script_text = _read_text(paths["script"])
    if not script_text:
        print(f"Script file not found or empty: {paths['script']}")
        print("Prompt files are ready. Generate the script first, then rerun this command.")
        return

    links_text = _read_text(paths["links"])
    if not links_text:
        print(f"Links file not found or empty: {paths['links']}")
        print("Run the links prompt first, then rerun this command.")
        return

    audio_path = ""
    if args.no_audio:
        print("Audio generation skipped: --no-audio is enabled.")
    else:
        print("Generating audio...")
        audio_path = _build_audio(
            country,
            script_text,
            dry_run=_env_flag("ELEVENLABS_DRY_RUN", default=False),
        )
        if audio_path:
            print("Audio saved at:", audio_path)

    fun_facts = _load_fun_facts(paths["fun_fact"])
    if not fun_facts:
        print(f"Fun fact file not found or empty: {paths['fun_fact']}")
        print("Run the fun-facts prompt first, then rerun this command.")
        return
    fun_facts_caption = _load_fun_facts_caption(paths["fun_fact"])
    fun_fact_images = _ensure_fun_fact_images(country, fun_facts, paths["out_dir"])

    caption_text = _read_text(paths["caption"])
    image_path = prepared["image_path"] or _find_image_path(country, paths["out_dir"])
    audio_caption = ""
    if audio_path:
        audio_caption = generate_audio_caption(country, prepared["country_fa"], prepared["hashtags_inline"])

    if not image_path:
        print("Publishing failed: country image is missing.")
        return

    if fun_fact_images and not is_caption_within_limit(fun_facts_caption):
        print(
            "Publishing failed: fun-facts caption exceeds Telegram caption limit "
            f"({len(fun_facts_caption)} > 1024)."
        )
        return

    if len(fun_fact_images) != len(fun_facts):
        print(
            "Publishing failed: not every fun fact has a matching image "
            f"({len(fun_fact_images)} images for {len(fun_facts)} facts)."
        )
        return

    if not args.no_audio and not audio_path:
        print("Publishing failed: audio generation did not produce the required MP3.")
        return

    publish_ok = publish_package(
        main_post_caption=caption_text,
        links_text=links_text,
        image_path=image_path or None,
        fun_fact_images=fun_fact_images,
        fun_facts_caption=fun_facts_caption,
        audio_path=audio_path or None,
        audio_caption=audio_caption,
        audio_title=country,
    )
    print("Published successfully." if publish_ok else "Publishing failed.")


if __name__ == "__main__":
    main()
