import os
import re
import json
import time
import subprocess
from pathlib import Path
import requests

ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")
if not ELEVEN_API_KEY:
    raise RuntimeError("Missing ELEVEN_API_KEY env var (set ELEVEN_API_KEY).")

ELEVEN_BASE = "https://api.elevenlabs.io/v1"


def normalize_fa_for_tts(text: str) -> str:
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 1600) -> list[str]:
    """
    Chunk by paragraph; if a paragraph is too long, split it into slices (no truncation).
    """
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    cur = ""

    def flush():
        nonlocal cur
        if cur.strip():
            chunks.append(cur.strip())
        cur = ""

    for p in paras:
        if len(p) > max_chars:
            # flush current, then split this long paragraph
            flush()
            for i in range(0, len(p), max_chars):
                chunks.append(p[i:i + max_chars].strip())
            continue

        cand = (cur + "\n\n" + p).strip() if cur else p
        if len(cand) <= max_chars:
            cur = cand
        else:
            flush()
            cur = p

    flush()
    return chunks


def elevenlabs_list_voices() -> dict:
    r = requests.get(
        f"{ELEVEN_BASE}/voices",
        headers={"xi-api-key": ELEVEN_API_KEY},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def elevenlabs_tts_chunk(
    text: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.4,
    similarity_boost: float = 0.8,
) -> bytes:
    url = f"{ELEVEN_BASE}/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }

    r = requests.post(
        url,
        headers={
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        data=json.dumps(payload),
        timeout=120,
    )
    r.raise_for_status()
    return r.content


def write_concat_list(mp3_paths: list[Path], list_path: Path) -> None:
    # ffmpeg concat demuxer list file
    # Use absolute paths to avoid working-dir issues
    lines = []
    for p in mp3_paths:
        ap = p.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{ap}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")


def ffmpeg_concat(mp3_paths: list[Path], out_path: Path) -> None:
    list_path = out_path.with_suffix(".concat.txt")
    write_concat_list(mp3_paths, list_path)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out_path)],
        check=True
    )


def elevenlabs_script_to_mp3(
    script_fa: str,
    out_dir: str,
    out_mp3_name: str,
    voice_id: str,
    model_id: str = "eleven_multilingual_v2",
    max_chars: int = 1600
) -> Path:
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    text = normalize_fa_for_tts(script_fa)
    chunks = chunk_text(text, max_chars=max_chars)

    mp3_paths: list[Path] = []
    for i, ch in enumerate(chunks, 1):
        audio = elevenlabs_tts_chunk(ch, voice_id=voice_id, model_id=model_id)
        p = out_dir_p / f"{i:02d}.mp3"
        p.write_bytes(audio)
        mp3_paths.append(p)
        time.sleep(0.25)

    out_path = out_dir_p / out_mp3_name
    ffmpeg_concat(mp3_paths, out_path)
    return out_path