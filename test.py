import sys
from modules.youtube_fetcher import search_youtube_category

def main():
    if len(sys.argv) < 2:
        print('Usage: python test_youtube.py "CountryName"')
        return

    country = sys.argv[1]

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