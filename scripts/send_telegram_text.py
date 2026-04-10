#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.telegram_publisher import send_message


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a Telegram HTML message without running the full pipeline."
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to a UTF-8 text/HTML file to send. If omitted, stdin is used.",
    )
    args = parser.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8").strip()
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("No message text provided.")
        return 1

    ok = send_message(text)
    if not ok:
        return 1

    print("Message sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
