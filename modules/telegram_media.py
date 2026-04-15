from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


TELEGRAM_MAX_PHOTO_BYTES = 10 * 1024 * 1024
TELEGRAM_MAX_DIMENSION = 2400


def _jpeg_resampling():
    try:
        from PIL import Image

        return Image, Image.Resampling.LANCZOS
    except Exception:
        return None, None


def prepare_telegram_photo(image_path: str) -> tuple[str, str | None]:
    if not image_path or not os.path.exists(image_path):
        return image_path, None

    image_lib, resample_filter = _jpeg_resampling()
    if image_lib is None:
        return image_path, None

    try:
        with image_lib.open(image_path) as img:
            needs_conversion = Path(image_path).suffix.lower() not in {".jpg", ".jpeg"}
            needs_resize = max(img.size) > TELEGRAM_MAX_DIMENSION
            needs_repack = os.path.getsize(image_path) > TELEGRAM_MAX_PHOTO_BYTES
            if not (needs_conversion or needs_resize or needs_repack):
                return image_path, None
    except Exception:
        return image_path, None

    temp_dir = tempfile.mkdtemp(prefix="telegram_photo_")
    output_path = Path(temp_dir) / f"{Path(image_path).stem}.jpg"

    try:
        with image_lib.open(image_path) as img:
            img = img.convert("RGB")
            if max(img.size) > TELEGRAM_MAX_DIMENSION:
                img.thumbnail((TELEGRAM_MAX_DIMENSION, TELEGRAM_MAX_DIMENSION), resample_filter)

            quality = 86
            while True:
                img.save(
                    output_path,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                if output_path.stat().st_size <= TELEGRAM_MAX_PHOTO_BYTES or quality <= 50:
                    break
                quality -= 6

        if output_path.stat().st_size > TELEGRAM_MAX_PHOTO_BYTES:
            with image_lib.open(output_path) as img:
                while output_path.stat().st_size > TELEGRAM_MAX_PHOTO_BYTES and max(img.size) > 1200:
                    next_size = (max(1200, img.size[0] * 85 // 100), max(1200, img.size[1] * 85 // 100))
                    img.thumbnail(next_size, resample_filter)
                    img.save(
                        output_path,
                        format="JPEG",
                        quality=76,
                        optimize=True,
                        progressive=True,
                    )
                    if output_path.stat().st_size <= TELEGRAM_MAX_PHOTO_BYTES:
                        break
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return image_path, None

    if output_path.exists() and output_path.stat().st_size <= TELEGRAM_MAX_PHOTO_BYTES:
        print(
            "Prepared Telegram-safe photo copy:",
            f"{Path(image_path).name} -> {output_path.name} ({output_path.stat().st_size} bytes)",
        )
        return str(output_path), temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)
    return image_path, None


def cleanup_prepared_telegram_media(temp_dirs: list[str | None]) -> None:
    for temp_dir in temp_dirs:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
