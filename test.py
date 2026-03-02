import sys
import os

from openai import videos

from modules.metadata_fetcher import fetch_country_metadata
from modules.youtube_fetcher import search_youtube_category
from modules.wikimedia_fetcher import search_country_image
from modules.telegram_publisher import publish_photo_then_links
from modules.title_shortener import short_fa_title
from modules.telegram_post_generator import generate_caption, generate_links_post
from modules.metadata_fetcher import fetch_country_metadata


def main():
    if len(sys.argv) < 2:
        print('Usage: python test.py "CountryName"')
        return

    country = sys.argv[1]

    print(f"\n=== Generating media package for {country} ===\n")

    # Fetch videos
    print("Fetching YouTube videos...")
    videos = {
        "music": search_youtube_category(country, "music"),
        "life": search_youtube_category(country, "life"),
        "nature": search_youtube_category(country, "nature"),
        "history": search_youtube_category(country, "history")
    }

  # Add short Persian labels
    for cat, items in videos.items():
        for v in items:
            v["fa_label"] = short_fa_title(cat, v.get("title",""), v.get("channel",""))

    # Temporary metadata

    metadata = fetch_country_metadata(country)
    
    # Hashtags (you can compute week/letter later)
    hashtags = f"#weekXX\n#{country}\n@countries_AtoZ"

    caption_text = generate_caption(country, metadata, hashtags)
    links_text = generate_links_post(country, videos, hashtags)

    
    os.makedirs("outputs", exist_ok=True)

    post_path = f"outputs/{country}_telegram.txt"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(caption_text 
                )
    with open(f"outputs/{country}_links.txt", "w", encoding="utf-8") as f:
        f.write(links_text)

    print("Caption saved at:", f"outputs/{country}_caption.txt")
    print("Links saved at:", f"outputs/{country}_links.txt")


    print("Fetching Wikimedia image...")
    image_path = search_country_image(country)

    if not image_path:
        print("No image found. Skipping publishing.")
        return

    print("Image saved at:", image_path)

    
    print("Publishing to Telegram (photo caption + separate links message)...")
    ok = publish_photo_then_links(image_path, caption_text, links_text)

    print("Published successfully." if ok else "Publishing failed.")



if __name__ == "__main__":
    main()