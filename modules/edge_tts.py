import asyncio
import re
from pathlib import Path
import edge_tts


def normalize_fa_for_tts(text: str) -> str:
    # Persian normalization
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)

    # Improve pacing
    text = text.replace("؛", "،")
    return text.strip()


def chunk_text(text: str, max_chars: int = 3500):
    # edge-tts can handle fairly long text, but chunking is safer
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for p in paragraphs:
        candidate = (current + "\n\n" + p).strip() if current else p
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = p

    if current:
        chunks.append(current)

    return chunks


async def _generate_edge_audio(text: str, output_file: Path,
                               voice: str = "fa-IR-DilaraNeural",
                               rate: str = "-5%",
                               pitch: str = "+0Hz"):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,     # slower pacing for documentary feel
        pitch=pitch
    )
    await communicate.save(str(output_file))


def edge_script_to_mp3(script_fa: str,
                       output_path: str,
                       voice: str = "fa-IR-DilaraNeural") -> Path:

    script_fa = normalize_fa_for_tts(script_fa)
    chunks = chunk_text(script_fa)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_files = []

    # Generate chunk files
    for i, chunk in enumerate(chunks, 1):
        chunk_path = output_path.parent / f"chunk_{i:02d}.mp3"
        asyncio.run(
            _generate_edge_audio(
                text=chunk,
                output_file=chunk_path,
                voice=voice,
                rate="-5%",      # adjust pacing here
                pitch="+0Hz"
            )
        )
        temp_files.append(chunk_path)

    # Concatenate using ffmpeg
    concat_file = output_path.parent / "concat_list.txt"
    concat_file.write_text(
        "\n".join([f"file '{f.resolve()}'" for f in temp_files]),
        encoding="utf-8"
    )

    import subprocess
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path)
    ], check=True)

    # Optional: cleanup chunks
    for f in temp_files:
        f.unlink()
    concat_file.unlink()

    return output_path
