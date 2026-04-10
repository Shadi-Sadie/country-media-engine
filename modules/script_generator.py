"""
Countries A–Z Production Pipeline

Architecture:
1) Extract detailed structured notes from provided source
2) Generate high-quality grounded Persian script (2-pass if needed)
3) Generate independent cultural fun facts
4) Verify script against extracted notes

Optimized for:
- 900–1100 Persian words (~5000 characters)
- GPT-4o literary quality
- Stable output token handling
"""

from __future__ import annotations
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from openai import OpenAI, APIConnectionError, APIStatusError, AuthenticationError, RateLimitError


# =============================
# Configuration
# =============================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY missing.")

client = OpenAI(api_key=OPENAI_API_KEY)


@dataclass
class PipelineOptions:
    model_extract: str = "gpt-4o-mini"
    model_generate: str = "gpt-4o"
    model_fun_fact: str = "gpt-5.4"
    model_verify: str = "gpt-4o-mini"

    temperature_extract: float = 0.0
    temperature_generate: float = 0.6
    temperature_fun_fact: float = 0.7
    temperature_verify: float = 0.0

    total_words_min: int = 900
    total_words_max: int = 1100

    max_retries: int = 5
    base_backoff_s: float = 0.8


# =============================
# Utilities
# =============================

def count_words(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def _normalize_fun_fact_line(line: str) -> str:
    text = (line or "").strip()
    text = re.sub(r"^\d+[\)\.\-:\s]+", "", text).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    if not text:
        return ""
    if not text.startswith("▪️"):
        text = f"▪️ {text}"
    return text


def _parse_fun_facts(raw: str) -> List[str]:
    lines = [ln.strip() for ln in (raw or "").splitlines() if ln.strip()]
    facts: List[str] = []
    for ln in lines:
        normalized = _normalize_fun_fact_line(ln)
        if normalized:
            facts.append(normalized)
    return facts


def _extract_fun_fact_lines(raw: str) -> List[str]:
    lines = [ln.strip() for ln in (raw or "").splitlines() if ln.strip()]
    if not lines:
        return []

    meta_patterns = (
        "در اینجا",
        "حتماً",
        "اگر بخواهی",
        "می‌توانم",
        "میتونم",
        "نسخه",
        "فهرست",
    )

    parsed: List[tuple[str, bool]] = []
    for ln in lines:
        t = re.sub(r"^[▪•\-\*\s]+", "", ln).strip()
        if not t:
            continue
        if any(p in t for p in meta_patterns):
            continue

        was_numbered = bool(re.match(r"^[0-9۰-۹]+[\)\.\-:\s]+", t))
        t = re.sub(r"^[0-9۰-۹]+[\)\.\-:\s]+", "", t).strip()
        if len(t) < 20:
            continue
        parsed.append((t, was_numbered))

    if not parsed:
        return []

    detailed_non_numbered = [
        t for t, was_numbered in parsed if (not was_numbered and len(t) >= 45)
    ]
    selected = detailed_non_numbered if len(detailed_non_numbered) >= 3 else [t for t, _ in parsed]

    deduped: List[str] = []
    seen: set[str] = set()
    for item in selected:
        key = re.sub(r"\s+", " ", item).strip()
        if key in seen:
            continue
        seen.add(key)
        normalized = _normalize_fun_fact_line(item)
        if normalized:
            deduped.append(normalized)
    return deduped


def call_openai(model, messages, temperature, max_tokens, opt: PipelineOptions):
    attempt = 0
    while True:
        try:
            resp = client.responses.create(
                model=model,
                input=messages,
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            output = resp.output_text.strip()
            if not output:
                raise RuntimeError("Empty response from OpenAI.")
            return output

        except AuthenticationError:
            raise RuntimeError("Authentication failed.")
        except (APIConnectionError, RateLimitError):
            attempt += 1
            if attempt > opt.max_retries:
                raise
            time.sleep(opt.base_backoff_s * (2 ** (attempt - 1)))
        except APIStatusError as e:
            if e.status_code in (429, 500, 502, 503, 504):
                attempt += 1
                if attempt > opt.max_retries:
                    raise
                time.sleep(opt.base_backoff_s * (2 ** (attempt - 1)))
            else:
                raise


# =============================
# Step 1 — Detailed Extraction
# =============================

def extract_structured_notes(country: str, source_text: str, opt: PipelineOptions) -> str:

    developer = "You extract detailed structured factual information."

    user = f"""
Extract detailed structured factual notes about {country}.

CRITICAL:
- Capture as much detail as possible.
- Do NOT summarize aggressively.
- Preserve names, dates, numbers, geographic features, institutions, and events.
- Include descriptive detail when present in the source.
- Do not invent anything.

Organize under headings:
1. Geography
2. History
3. Political System
4. Society & Demographics
5. Economy
6. Culture
7. Current Issues

Source:
<<<
{source_text}
>>>
"""

    return call_openai(
        opt.model_extract,
        [{"role": "developer", "content": developer},
         {"role": "user", "content": user}],
        opt.temperature_extract,
        max_tokens=2000,
        opt=opt
    )


# =============================
# Step 2 — Script Generation
# =============================

def generate_persian_script(country: str, notes: str, opt: PipelineOptions) -> str:

    developer = (
        "You are a professional Persian documentary narrator. "
        "You write elegant, flowing, analytical scripts."
    )

    user = f"""
Write a Persian documentary script about {country}.

Accuracy:
- Base narration strictly on structured notes.
- You may explain relationships and implications.
- Do NOT introduce new factual claims.
- Do NOT add new numbers or dates.

Style:
- Calm, analytical, mature tone.
- Vary sentence length.
- Use smooth transitions (اما، در عین حال، با این حال).
- No headings or bullet points.
- Suitable for voice narration.
- End with a reflective but restrained final sentence.

Length:
{opt.total_words_min}–{opt.total_words_max} Persian words.

If the script feels short, expand analytical depth in:
- Historical transitions
- Social structure
- Geographic implications

Notes:
<<<
{notes}
>>>
"""

    script = call_openai(
        opt.model_generate,
        [{"role": "developer", "content": developer},
         {"role": "user", "content": user}],
        opt.temperature_generate,
        max_tokens=3000,
        opt=opt
    )

    # Second-pass expansion if too short
    wc = count_words(script)
    if wc < opt.total_words_min:
        expand_prompt = f"""
Expand the script below to {opt.total_words_min}–{opt.total_words_max} Persian words.

Rules:
- Do NOT introduce new facts.
- Deepen analysis and transitions.
- Improve descriptive richness.

SCRIPT:
<<<
{script}
>>>
"""
        script = call_openai(
            opt.model_generate,
            [{"role": "developer", "content": developer},
             {"role": "user", "content": expand_prompt}],
            opt.temperature_generate,
            max_tokens=3000,
            opt=opt
        )

    return script


# =============================
# Step 3 — Cultural Fun Facts
# =============================

def generate_fun_facts(country: str, opt: PipelineOptions) -> List[str]:

    prompt = f"""
Tell me several interesting fun facts about {country} in Persian.

Rules:
- Give multiple facts (prefer 5).
- Use natural, fluent Persian like a native writer.
- Avoid generic statements.
- Output only fact lines.
- Do NOT add intro or outro text.
- Use this exact format for each line:
  ▪️ <b>عنوان کوتاه</b>: توضیح
"""

    raw = call_openai(
        opt.model_fun_fact,
        [{"role": "user", "content": prompt}],
        opt.temperature_fun_fact,
        max_tokens=800,
        opt=opt
    )

    facts = _extract_fun_fact_lines(raw)
    if not facts:
        # Fallback if model ignores format completely.
        facts = [f.strip() for f in (raw or "").split("\n") if f.strip()]
        facts = _parse_fun_facts("\n".join(facts))
    return facts


# =============================
# Step 4 — Script Verification
# =============================

def verify_script(country: str, notes: str, script: str, opt: PipelineOptions) -> str:

    developer = "You are a strict factual verifier."

    user = f"""
Compare the script to the structured notes.

Flag sentences that:
- Add new facts
- Add new numbers or dates
- Make unsupported causal claims

If clean, output:
CLEAN

Notes:
<<<
{notes}
>>>

Script:
<<<
{script}
>>>
"""

    return call_openai(
        opt.model_verify,
        [{"role": "developer", "content": developer},
         {"role": "user", "content": user}],
        opt.temperature_verify,
        max_tokens=800,
        opt=opt
    )


# =============================
# Full Pipeline
# =============================

def run_country_pipeline(country: str,
                         source_text: str,
                         week_num: int = 2,
                         country_en: Optional[str] = None,
                         opt: Optional[PipelineOptions] = None) -> Dict[str, object]:

    opt = opt or PipelineOptions()
    country_en = country_en or country

    notes = extract_structured_notes(country, source_text, opt)
    script = generate_persian_script(country, notes, opt)
    fun_facts = generate_fun_facts(country, opt)
    verification = verify_script(country, notes, script, opt)
    primary_fun_fact = fun_facts[0] if fun_facts else ""

    return {
        "country": country,
        "structured_notes": notes,
        "script_fa": script,
        "script_word_count": str(count_words(script)),
        "fun_facts": fun_facts,
        "verification": verification,
        # Backward-compatible keys expected by main.py integration.
        "telegram_fun_fact_fa": primary_fun_fact,
        "verify_script_report": verification,
        "verify_fun_fact_status": "",
    }


# =============================
# Example
# =============================

if __name__ == "__main__":

    country = "Albania"
    country_en = "Albania"
    week_num = 1

    source_text = "PASTE YOUR SOURCE TEXT HERE"

    result = run_country_pipeline(country, source_text, week_num, country_en)

    print("\n=== SCRIPT ===\n")
    print(result["script_fa"])

    print("\n=== WORD COUNT ===\n")
    print(result["script_word_count"])

    print("\n=== FUN FACTS ===\n")
    for f in result["fun_facts"]:
        print(f)

    print("\n=== VERIFICATION ===\n")
    print(result["verification"])
