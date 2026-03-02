import sys
import os
from modules.wiki_fetcher import fetch_wikipedia_full_text
from modules.script_generator import generate_persian_script

def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "CountryName"')
        return

    country = sys.argv[1]

    print(f"Fetching Wikipedia full text for {country}...")
    summary = fetch_wikipedia_full_text(country)
    os.makedirs("outputs", exist_ok=True)

    file_path = f"outputs/{country}_wiki.txt"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Saved to {file_path}")

if __name__ == "__main__":
    main()

    print("Generating Persian script...")
script = generate_persian_script(country, summary)

script_path = f"outputs/{country}_script.txt"
with open(script_path, "w", encoding="utf-8") as f:
    f.write(script)

print(f"Script saved to {script_path}")


# fetch YouTube videos related to the country

from modules.youtube_fetcher import search_youtube_category

print(f"\nSearching categorized YouTube videos for {country}...")

    for category in ["music", "life", "nature", "history"]:
        print(f"\n=== {category.upper()} ===")

        videos = search_youtube_category(
            country=country,
            category=category,
            max_per_category=9
        )

        if not videos:
            print("No videos found.")
            continue

        for v in videos:
            print(f"{v['title']} ({v['duration_minutes']} min)")
            print(v["url"])
            print("---")

if __name__ == "__main__":
    main()
