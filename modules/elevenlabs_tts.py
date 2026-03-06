import os
import re
import json
import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Any, Optional
import requests
from dotenv import load_dotenv

ELEVEN_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_v3"
DEFAULT_ELEVENLABS_VOICE_ID = "cgSgspJ2msm6clMCkdW9"


def _api_key_or_raise() -> str:
    load_dotenv()
    api_key = os.environ.get("ELEVEN_LAB_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing ELEVEN_LAB_API_KEY env var (set ELEVEN_LAB_API_KEY).")
    return api_key


def resolve_model_id(model_id: Optional[str] = None) -> str:
    load_dotenv()
    if model_id and model_id.strip():
        return model_id.strip()
    return os.getenv("ELEVENLABS_MODEL_ID", "").strip() or DEFAULT_ELEVENLABS_MODEL_ID


def resolve_voice_id(voice_id: Optional[str] = None) -> str:
    load_dotenv()
    if voice_id and voice_id.strip():
        return voice_id.strip()
    return os.getenv("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_ELEVENLABS_VOICE_ID


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


def build_tts_plan(
    script_fa: str,
    model_id: Optional[str] = None,
    max_chars: Optional[int] = None,
    force_chunk: bool = False,
) -> dict[str, Any]:
    """
    Build a request plan without spending credits.
    Default chunk size is 5000 chars to avoid unnecessary chunking on short scripts.
    """
    text = normalize_fa_for_tts(script_fa)
    if not text:
        raise ValueError("Script text is empty.")

    chunk_size = max_chars or 5000
    if chunk_size < 100:
        raise ValueError("max_chars must be >= 100.")

    if not force_chunk and len(text) <= chunk_size:
        chunks = [text]
    else:
        chunks = chunk_text(text, max_chars=chunk_size)
        if not chunks:
            chunks = [text]

    resolved_model_id = resolve_model_id(model_id)
    return {
        "model_id": resolved_model_id,
        "char_count": len(text),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "chunk_lengths": [len(c) for c in chunks],
    }


def _get_json(path: str, timeout: int = 60) -> Any:
    r = requests.get(
        f"{ELEVEN_BASE}{path}",
        headers={"xi-api-key": _api_key_or_raise()},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def elevenlabs_preflight(voice_id: str, model_id: str) -> dict[str, Any]:
    """
    Zero-synthesis preflight: validate API key, voice id, and model visibility.
    """
    result: dict[str, Any] = {
        "voice_id": voice_id,
        "model_id": model_id,
        "voice_name": "",
        "voice_labels": {},
        "model_available": None,
        "warnings": [],
    }

    try:
        voice_data = _get_json(f"/voices/{voice_id}", timeout=30)
        result["voice_name"] = voice_data.get("name", "")
        result["voice_labels"] = voice_data.get("labels", {}) or {}
    except Exception as exc:
        result["warnings"].append(f"Voice lookup failed: {exc}")

    try:
        models = _get_json("/models", timeout=30)
        model_ids = {
            item.get("model_id")
            for item in (models or [])
            if isinstance(item, dict) and item.get("model_id")
        }
        result["model_available"] = model_id in model_ids
    except Exception as exc:
        result["warnings"].append(f"Model lookup failed: {exc}")

    return result


def elevenlabs_list_voices() -> dict:
    return _get_json("/voices", timeout=60)


def elevenlabs_tts_chunk(
    text: str,
    voice_id: str,
    model_id: Optional[str] = None,
    stability: float = 0.4,
    similarity_boost: float = 0.8,
) -> bytes:
    model_id = resolve_model_id(model_id)
    voice_id = resolve_voice_id(voice_id)
    url = f"{ELEVEN_BASE}/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }

    timeout_raw = os.getenv("ELEVENLABS_TTS_TIMEOUT_SECONDS", "").strip()
    try:
        timeout_seconds = int(timeout_raw) if timeout_raw else 300
    except ValueError:
        timeout_seconds = 300
    if timeout_seconds < 60:
        timeout_seconds = 60

    r = requests.post(
        url,
        headers={
            "xi-api-key": _api_key_or_raise(),
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        data=json.dumps(payload),
        timeout=timeout_seconds,
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
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(out_path),
            ],
            check=True,
        )
    finally:
        if list_path.exists():
            list_path.unlink()


def elevenlabs_script_to_mp3(
    script_fa: str,
    out_dir: str,
    out_mp3_name: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    max_chars: Optional[int] = None,
    force_chunk: bool = False,
) -> Path:
    voice_id = resolve_voice_id(voice_id)
    model_id = resolve_model_id(model_id)
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    plan = build_tts_plan(
        script_fa=script_fa,
        model_id=model_id,
        max_chars=max_chars,
        force_chunk=force_chunk,
    )
    text = normalize_fa_for_tts(script_fa)
    chunks = [text] if plan["chunk_count"] == 1 else chunk_text(text, max_chars=plan["chunk_size"])

    out_path = out_dir_p / out_mp3_name
    if len(chunks) == 1:
        audio = elevenlabs_tts_chunk(chunks[0], voice_id=voice_id, model_id=model_id)
        out_path.write_bytes(audio)
        return out_path

    temp_dir = Path(tempfile.mkdtemp(prefix="elevenlabs_", dir=str(out_dir_p)))
    mp3_paths: list[Path] = []
    try:
        for i, ch in enumerate(chunks, 1):
            audio = elevenlabs_tts_chunk(ch, voice_id=voice_id, model_id=model_id)
            p = temp_dir / f"{i:02d}.mp3"
            p.write_bytes(audio)
            mp3_paths.append(p)
            time.sleep(0.25)
        ffmpeg_concat(mp3_paths, out_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return out_path
