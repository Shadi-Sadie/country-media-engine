import sys
import os
from modules.wiki_fetcher import fetch_wikipedia_full_text

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