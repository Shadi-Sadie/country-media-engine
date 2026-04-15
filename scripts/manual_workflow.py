#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.un_schedule import resolve_un_schedule


def _paths(country: str) -> dict[str, Path]:
    out = ROOT / "outputs"
    return {
        "script_prompt": out / f"{country}_prompt.txt",
        "fun_prompt": out / f"{country}_prompt_fun.txt",
        "links_prompt": out / f"{country}_prompt_links_format.txt",
        "script_output": out / f"{country}_script.txt",
        "fun_output": out / f"{country}_fun_fact.txt",
        "links_output": out / f"{country}_links.txt",
    }


def _run_main_manual(country: str | None, week_number: int | None, mode: str) -> int:
    cmd = [sys.executable, "main_manual.py"]
    if country:
        cmd.append(country)
    if week_number is not None:
        cmd.extend(["--week-number", str(week_number)])
    cmd.append(mode)
    return subprocess.call(cmd, cwd=ROOT)


def _print_prompts(country: str) -> None:
    paths = _paths(country)
    print(f"Read {paths['script_prompt'].relative_to(ROOT)} and execute it")
    print(f"Read {paths['fun_prompt'].relative_to(ROOT)} and execute it")
    print(f"Read {paths['links_prompt'].relative_to(ROOT)} and execute it")


def _print_status(country: str) -> None:
    paths = _paths(country)
    for key, path in paths.items():
        if path.exists():
            print(f"{key}: READY - {path.relative_to(ROOT)}")
        else:
            print(f"{key}: MISSING - {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual workflow helper for the country media engine.")
    parser.add_argument("--country", help="Country name, e.g. Armenia")
    parser.add_argument("--week-number", type=int, help="UN alphabetical position/week number, e.g. 8")
    parser.add_argument(
        "action",
        choices=["prepare", "prompts", "status", "publish"],
        help="Workflow action to run.",
    )
    args = parser.parse_args()

    schedule = resolve_un_schedule(country=args.country, week_number=args.week_number)
    country = schedule.country_name

    print(
        f"Resolved workflow target: {country} "
        f"(week {schedule.week_number:02d}, UN official: {schedule.official_name})"
    )

    if args.action == "prepare":
        return _run_main_manual(country, schedule.week_number, "--prepare-only")
    if args.action == "prompts":
        _print_prompts(country)
        return 0
    if args.action == "status":
        _print_status(country)
        return 0
    if args.action == "publish":
        required = ["script_output", "fun_output", "links_output"]
        paths = _paths(country)
        missing = [name for name in required if not paths[name].exists()]
        if missing:
            print("Cannot publish yet. Missing required generated files:")
            for name in missing:
                print(f"- {paths[name].relative_to(ROOT)}")
            return 1
        return _run_main_manual(country, schedule.week_number, "--publish-only")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
