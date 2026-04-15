# Country Media Engine

A semi-autonomous AI media engine that generates structured country profiles (A–Z), validates content quality, and produces publish-ready narration scripts and formatted posts.

---

## Vision

This project builds a modular content system that:

1. Ingests country data from structured sources
2. Generates narration scripts using LLMs
3. Validates structure and content quality
4. Formats platform-ready posts (Telegram and beyond)
5. Optionally produces audio narration
6. Can evolve into a fully autonomous publishing agent

The system is intentionally designed as a **semi-agent**:
It performs validation, retries, and structured decision logic — while remaining controllable and debuggable.

---

## Core Principles

- Deterministic data ingestion
- Structured prompting
- Modular tool design
- Output validation before publishing
- Expandable architecture

---

## Planned Architecture

country-media-engine/
│
├── main.py
├── config.py
├── modules/
│   ├── wiki_fetcher.py
│   ├── script_generator.py
│   ├── telegram_post_generator.py
│   ├── tts_generator.py
│   ├── telegram_publisher.py
│   └── validator.py
│
└── outputs/

---

## Semi-Agent Behavior (Phase 1–2)

- Checks script length
- Ensures required sections exist
- Prevents missing data fields
- Retries generation when validation fails
- Separates tool execution from decision logic

---

## Development Roadmap

Phase 1 — Wikipedia ingestion (MVP)  
Phase 2 — Script generation  
Phase 3 — Output validation (semi-agent layer)  
Phase 4 — Post formatting  
Phase 5 — Audio integration  
Phase 6 — Optional scheduling / full autonomy  

---

## Status

Project initialized.

---

## Manual Weekly Workflow

Use the new manual entrypoint when you want to keep script writing and fun-fact generation outside the app:

```bash
python main_manual.py Armenia --prepare-only
```

or let the app resolve the country from the UN alphabetical list and the week number:

```bash
python main_manual.py --week-number 8 --prepare-only
```

This prepares the weekly raw materials:
- `outputs/Armenia_wiki.txt`
- `outputs/Armenia_telegram.txt`
- `outputs/Armenia_image.*` if Wikimedia finds one
- `prompt.txt`
- `prompt_fun.txt`
- `prompt_links.txt`
- `prompt_links_format.txt` (legacy alias)
- `outputs/Armenia_prompt.txt`
- `outputs/Armenia_prompt_fun.txt`
- `outputs/Armenia_prompt_links.txt`
- `outputs/Armenia_prompt_links_format.txt` (legacy alias)

Then use the generated prompt files manually:
- Run `prompt.txt` to create `outputs/Armenia_script.txt`
- Run `prompt_fun.txt` to create `outputs/Armenia_fun_fact.txt`
- Run `prompt_links.txt`, `prompt_links_format.txt`, `outputs/Armenia_prompt_links.txt`, or `outputs/Armenia_prompt_links_format.txt` to create `outputs/Armenia_links.txt`

After those files exist, run:

```bash
python main_manual.py Armenia
```

or:

```bash
python main_manual.py --week-number 8
```

That will:
- generate the ElevenLabs audio from `outputs/Armenia_script.txt`
- publish the caption, YouTube links, fun facts, image, and audio to Telegram

If everything is already prepared and you only want to publish again:

```bash
python main_manual.py Armenia --publish-only
```
