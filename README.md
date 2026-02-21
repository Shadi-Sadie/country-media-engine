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
