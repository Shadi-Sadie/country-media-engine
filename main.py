import argparse
import os

from modules.metadata_fetcher import fetch_country_metadata
from modules.telegram_post_generator import (
    generate_audio_caption,
    generate_caption,
    generate_links_post,
)
from modules.telegram_publisher import publish_photo_then_links, send_audio, send_message
from modules.title_shortener import short_fa_title
from modules.wiki_fetcher import fetch_wikipedia_full_text
from modules.wikimedia_fetcher import search_country_image
from modules.youtube_fetcher import search_youtube_category


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _build_script_and_fun_fact(country: str) -> tuple[str, list[str]]:
    try:
        wiki_text = fetch_wikipedia_full_text(country)
        with open(f"outputs/{country}_wiki.txt", "w", encoding="utf-8") as f:
            f.write(wiki_text)

        from modules.script_generator import run_country_pipeline

        result = run_country_pipeline(country, wiki_text)
        script_fa = (result.get("script_fa") or "").strip()
        fun_facts = result.get("fun_facts") or []
        if not isinstance(fun_facts, list):
            fun_facts = []
        fun_facts = [str(x).strip() for x in fun_facts if str(x).strip()]
        if not fun_facts:
            fallback = (result.get("telegram_fun_fact_fa") or "").strip()
            if fallback:
                fun_facts = [fallback]
        script_status = (result.get("verify_script_report") or "").strip()
        fun_fact_status = (result.get("verify_fun_fact_status") or "").strip()

        if script_status and script_status != "CLEAN":
            print("Script verification warning:", script_status)
        if fun_fact_status and not fun_fact_status.startswith("SUPPORTED"):
            print("Fun fact verification warning:", fun_fact_status)

        return script_fa, fun_facts
    except Exception as exc:
        print("Script/fun-fact generation skipped:", exc)
        return "", []


def _build_audio(country: str, script_fa: str, dry_run: bool = False) -> str:
    audio_path = f"outputs/{country}.mp3"
    overwrite = _env_flag("ELEVENLABS_OVERWRITE", default=False)
    if not overwrite and os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        print(
            f"Audio already exists at {audio_path}. "
            "Set ELEVENLABS_OVERWRITE=1 to regenerate."
        )
        return audio_path

    script_text = (script_fa or "").strip()
    if not script_text:
        script_file = f"outputs/{country}_script.txt"
        if os.path.exists(script_file):
            with open(script_file, "r", encoding="utf-8") as f:
                script_text = f.read().strip()

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
            resolve_model_id,
            resolve_voice_id,
            elevenlabs_preflight,
            elevenlabs_script_to_mp3,
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

        out_path = elevenlabs_script_to_mp3(
            script_fa=script_text,
            out_dir="outputs",
            out_mp3_name=f"{country}.mp3",
            voice_id=voice_id,
            model_id=model_id,
            max_chars=max_chars,
            force_chunk=force_chunk,
        )
        return str(out_path)
    except Exception as eleven_exc:
        print("ElevenLabs TTS failed:", eleven_exc)
        return ""


def main():
    parser = argparse.ArgumentParser(description="Country media pipeline")
    parser.add_argument("country", help="Country name, e.g. Algeria")
    parser.add_argument(
        "--voice-only",
        action="store_true",
        help="Generate only ElevenLabs audio from outputs/<Country>_script.txt",
    )
    args = parser.parse_args()

    country = args.country
    print(f"\n=== Generating media package for {country} ===\n")

    if args.voice_only:
        script_file = f"outputs/{country}_script.txt"
        script_text = ""
        if os.path.exists(script_file):
            with open(script_file, "r", encoding="utf-8") as f:
                script_text = f.read().strip()
        if not script_text:
            print(f"Voice-only mode failed: script file missing or empty at {script_file}")
            return

        print("Generating audio in voice-only mode...")
        audio_path = _build_audio(
            country,
            script_text,
            dry_run=_env_flag("ELEVENLABS_DRY_RUN", default=False),
        )
        if audio_path:
            print("Audio saved at:", audio_path)
        return

    print("Fetching YouTube videos...")
    videos = {
        "music": search_youtube_category(country, "music"),
        "life": search_youtube_category(country, "life"),
        "nature": search_youtube_category(country, "nature"),
        "history": search_youtube_category(country, "history"),
    }

    for cat, items in videos.items():
        for v in items:
            v["fa_label"] = short_fa_title(cat, v.get("title", ""), v.get("channel", ""))

    metadata = fetch_country_metadata(country)
    tags = ["#week02", f"#{country}"]
    if country and country[0].isalpha():
        tags.append(f"#{country[0].upper()}")
    tags.append("@countries_AtoZ")
    hashtags_lines = "\n".join(tags)
    hashtags_inline = " ".join(tags)

    caption_text = generate_caption(country, metadata, hashtags_lines)
    links_text = generate_links_post(country, videos, hashtags_lines)

    os.makedirs("outputs", exist_ok=True)
    with open(f"outputs/{country}_telegram.txt", "w", encoding="utf-8") as f:
        f.write(caption_text)
    with open(f"outputs/{country}_links.txt", "w", encoding="utf-8") as f:
        f.write(links_text)
    print("Caption saved at:", f"outputs/{country}_telegram.txt")
    print("Links saved at:", f"outputs/{country}_links.txt")

    print("Generating script and fun fact...")
    script_text, fun_facts = _build_script_and_fun_fact(country)
    if script_text:
        with open(f"outputs/{country}_script.txt", "w", encoding="utf-8") as f:
            f.write(script_text)
        print("Script saved at:", f"outputs/{country}_script.txt")
    if fun_facts:
        with open(f"outputs/{country}_fun_fact.txt", "w", encoding="utf-8") as f:
            f.write("\n\n".join(fun_facts))
        print("Fun fact saved at:", f"outputs/{country}_fun_fact.txt")

    print("Generating audio...")
    audio_path = _build_audio(
        country,
        script_text,
        dry_run=_env_flag("ELEVENLABS_DRY_RUN", default=False),
    )
    if audio_path:
        print("Audio saved at:", audio_path)

    print("Fetching Wikimedia image...")
    image_path = search_country_image(country)
    publish_ok = False
    if image_path:
        print("Image saved at:", image_path)
        print("Publishing to Telegram (photo caption + separate links message)...")
        publish_ok = publish_photo_then_links(image_path, caption_text, links_text)
        print("Published successfully." if publish_ok else "Publishing failed.")
    else:
        print("No image found. Falling back to text-only publishing.")
        ok_caption = send_message(caption_text)
        ok_links = send_message(links_text)
        publish_ok = ok_caption and ok_links
        print("Published successfully." if publish_ok else "Publishing failed.")

    if publish_ok and fun_facts:
        print(f"Publishing {len(fun_facts)} fun fact message(s)...")
        all_sent = True
        for idx, fact in enumerate(fun_facts, start=1):
            ok_fun = send_message(fact)
            print(
                f"Fun fact {idx} sent successfully."
                if ok_fun else f"Fun fact {idx} sending failed."
            )
            all_sent = all_sent and ok_fun
        if len(fun_facts) < 5:
            print(f"Warning: only {len(fun_facts)} fun facts were available.")

    if publish_ok and audio_path:
        print("Publishing audio message...")
        country_fa = metadata.get("name_fa", country)
        audio_caption = generate_audio_caption(country, country_fa, hashtags_inline)
        ok_audio = send_audio(audio_path, audio_caption, title=country)
        print("Audio sent." if ok_audio else "Audio send failed.")


if __name__ == "__main__":
    main()
