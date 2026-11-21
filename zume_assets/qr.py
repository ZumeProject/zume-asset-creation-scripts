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

# Local presenter captures bake QR payloads with these origins; production
# Keynote/PPTX must use SITE instead.
_LOCAL_QR_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
)


def rewrite_localhost_qr_url(url: str, *, site: str = SITE) -> str | None:
    """If ``url`` is a localhost app QR payload, return the production rewrite.

    Returns ``None`` when the URL does not use a known local presenter origin.
    Path and query are preserved (``/app/qr/?l=…&…``).
    """
    text = (url or "").strip()
    if not text:
        return None
    for origin in _LOCAL_QR_ORIGINS:
        if text.startswith(origin):
            return site.rstrip("/") + text[len(origin) :]
    return None


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
