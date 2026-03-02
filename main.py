import os
import sys

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


def _build_script_and_fun_fact(country: str) -> tuple[str, str]:
    try:
        wiki_text = fetch_wikipedia_full_text(country)
        with open(f"outputs/{country}_wiki.txt", "w", encoding="utf-8") as f:
            f.write(wiki_text)

        from modules.script_generator import run_country_pipeline

        result = run_country_pipeline(country, wiki_text)
        script_fa = (result.get("script_fa") or "").strip()
        fun_fact = (result.get("telegram_fun_fact_fa") or "").strip()
        script_status = (result.get("verify_script_report") or "").strip()
        fun_fact_status = (result.get("verify_fun_fact_status") or "").strip()

        if script_status and script_status != "CLEAN":
            print("Script verification warning:", script_status)
        if fun_fact_status and not fun_fact_status.startswith("SUPPORTED"):
            print("Fun fact verification warning:", fun_fact_status)

        return script_fa, fun_fact
    except Exception as exc:
        print("Script/fun-fact generation skipped:", exc)
        return "", ""


def _build_audio(country: str, script_fa: str) -> str:
    audio_path = f"outputs/{country}.mp3"
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
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

    try:
        from modules.edge_tts import edge_script_to_mp3

        voice = os.getenv("EDGE_TTS_VOICE", "fa-IR-DilaraNeural")
        out_path = edge_script_to_mp3(
            script_fa=script_text,
            output_path=audio_path,
            voice=voice,
        )
        return str(out_path)
    except Exception as edge_exc:
        print("Edge TTS failed, trying ElevenLabs:", edge_exc)

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not voice_id:
        print("Audio generation skipped: ELEVENLABS_VOICE_ID is not set.")
        return ""

    try:
        from modules.elevenlabs_tts import elevenlabs_script_to_mp3

        out_path = elevenlabs_script_to_mp3(
            script_fa=script_text,
            out_dir="outputs",
            out_mp3_name=f"{country}.mp3",
            voice_id=voice_id,
        )
        return str(out_path)
    except Exception as eleven_exc:
        print("ElevenLabs TTS failed:", eleven_exc)
        return ""


def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "CountryName"')
        return

    country = sys.argv[1]
    print(f"\n=== Generating media package for {country} ===\n")

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
    script_text, fun_fact_text = _build_script_and_fun_fact(country)
    if script_text:
        with open(f"outputs/{country}_script.txt", "w", encoding="utf-8") as f:
            f.write(script_text)
        print("Script saved at:", f"outputs/{country}_script.txt")
    if fun_fact_text:
        with open(f"outputs/{country}_fun_fact.txt", "w", encoding="utf-8") as f:
            f.write(fun_fact_text)
        print("Fun fact saved at:", f"outputs/{country}_fun_fact.txt")

    print("Generating audio...")
    audio_path = _build_audio(country, script_text)
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

    if publish_ok and fun_fact_text:
        print("Publishing fun fact message...")
        ok_fun = send_message(fun_fact_text)
        print("Fun fact sent successfully." if ok_fun else "Fun fact sending failed.")

    if publish_ok and audio_path:
        print("Publishing audio message...")
        country_fa = metadata.get("name_fa", country)
        audio_caption = generate_audio_caption(country, country_fa, hashtags_inline)
        ok_audio = send_audio(audio_path, audio_caption, title=country)
        print("Audio sent." if ok_audio else "Audio send failed.")


if __name__ == "__main__":
    main()
