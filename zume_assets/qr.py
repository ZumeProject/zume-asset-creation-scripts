"""QR code image generation for workbook targets.

Payloads match zume6 workbook/admin (see zume6-qr-url-scheme.md):

    https://zume.training/app/qr/?l={locale}&{c|v|a}={id}

These are redirect entrypoints — not final destination pages.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

import qrcode

SITE = "https://zume.training"


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


def _app_qr_url(locale: str, **params: str) -> str:
    """Build trailing-slash /app/qr/?l=…&… form used by workbook generators."""
    query = urlencode({"l": locale, **params})
    return f"{SITE}/app/qr/?{query}"


def checkin_url(code: str | None = None, *, locale: str = "en") -> str:
    if code:
        return _app_qr_url(locale, c=str(code))
    # Open check-in still goes through the QR redirect with an empty code omitted;
    # workbook always supplies a session code — fall back to bare check-in page.
    return f"{SITE}/checkin"


def video_url(video_key: str, *, locale: str = "en") -> str:
    return _app_qr_url(locale, v=str(video_key))


def activity_url(activity_key: str, *, locale: str = "en") -> str:
    return _app_qr_url(locale, a=str(activity_key))
