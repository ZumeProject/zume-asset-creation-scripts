"""QR code image generation for workbook targets."""

from __future__ import annotations

from pathlib import Path

import qrcode


def make_qr_png(url: str, dest: Path, *, box_size: int = 8, border: int = 1) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(
        url,
        box_size=box_size,
        border=border,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    img.save(dest)
    return dest


def checkin_url(code: str | None = None) -> str:
    if code:
        return f"https://zume.training/checkin?code={code}"
    return "https://zume.training/checkin"


def video_url(video_key: str) -> str:
    return f"https://zume.training/?video={video_key}"


def activity_url(activity_key: str) -> str:
    return f"https://zume.training/?activity={activity_key}"
