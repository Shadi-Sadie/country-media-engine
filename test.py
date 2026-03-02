import sys
import os

from modules.youtube_fetcher import search_youtube_category
from modules.telegram_post_generator import generate_telegram_post
from modules.wikimedia_fetcher import search_country_image
from modules.telegram_publisher import send_photo_with_caption


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

    # Temporary metadata
    metadata = {
        "flag": "",
        "capital": "نامشخص",
        "area": "نامشخص",
        "location": "نامشخص",
        "neighbors": "نامشخص",
        "population": "نامشخص",
        "languages": "نامشخص"
    }

    print("Generating Telegram post...")
    post = generate_telegram_post(country, metadata, videos)

    os.makedirs("outputs", exist_ok=True)

    post_path = f"outputs/{country}_telegram.txt"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post)

    print("Telegram post saved at:", post_path)

    print("Fetching Wikimedia image...")
    image_path = search_country_image(country)

    if not image_path:
        print("No image found. Skipping publishing.")
        return

    print("Image saved at:", image_path)

    print("Publishing to Telegram...")
    success = send_photo_with_caption(image_path, post)

    if success:
        print("Published successfully.")
    else:
        print("Publishing failed.")


if __name__ == "__main__":
    main()