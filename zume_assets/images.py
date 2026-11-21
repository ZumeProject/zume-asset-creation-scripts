"""Download and resolve presenter diagram images for Typst guidebooks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

# Relative presenter image paths (e.g. /uploads/training-images/…) are served
# from the API host, not the public site origin.
UPLOADS_BASE = "https://api.zume.training"

# Manifest left_image contentKey → presenter.images key
CONTENT_KEY_TO_IMAGE = {
    "fourfields_example": "image_fourfields",
    "genmapping_example": "image_genmap",
}

# Activity keys on left_image slides → presenter.images key
ACTIVITY_KEY_TO_IMAGE = {
    "4fields": "image_fourfields",
    "genmapping": "image_genmap",
}

# Standalone paragraph that is only an image shortcode, e.g. {{ pace1_image }}
_IMAGE_PLACEHOLDER = re.compile(r"^\{\{\s*([A-Za-z0-9_]+)\s*\}\}$")


def is_image_shortcode(text: str) -> bool:
    return bool(_IMAGE_PLACEHOLDER.match((text or "").strip()))


def merge_script_paragraphs_with_en_shortcodes(
    locale_paras: list[str],
    en_paras: list[str],
) -> list[str]:
    """Restore ``{{ *_image }}`` slots from English when a locale script omitted them.

    Translated scripts (e.g. Pashto video 24) often drop pace shortcodes. Keep
    locale prose and splice EN shortcode paragraphs in EN order so Typst still
    gets the same diagram slots as English.
    """
    if any(is_image_shortcode(p) for p in locale_paras):
        return locale_paras
    if not any(is_image_shortcode(p) for p in en_paras):
        return locale_paras

    locale_text = [p for p in locale_paras if (p or "").strip()]
    out: list[str] = []
    text_i = 0
    for en_p in en_paras:
        if is_image_shortcode(en_p):
            out.append(en_p.strip())
            continue
        if text_i < len(locale_text):
            out.append(locale_text[text_i])
            text_i += 1
    while text_i < len(locale_text):
        out.append(locale_text[text_i])
        text_i += 1
    return out


def placeholder_to_image_key(name: str) -> str | None:
    """Map shortcode name to presenter.images key.

    ``pace1_image`` → ``image_pace1``; ``image_fourfields`` stays as-is.
    """
    name = (name or "").strip()
    if not name:
        return None
    if name.startswith("image_"):
        return name
    if name.endswith("_image"):
        return "image_" + name[: -len("_image")]
    return None


def resolve_image_key(
    *,
    content_key: str | None = None,
    activity_key: str | None = None,
    placeholder: str | None = None,
) -> str | None:
    if placeholder:
        return placeholder_to_image_key(placeholder)
    if content_key and content_key in CONTENT_KEY_TO_IMAGE:
        return CONTENT_KEY_TO_IMAGE[content_key]
    if activity_key and activity_key in ACTIVITY_KEY_TO_IMAGE:
        return ACTIVITY_KEY_TO_IMAGE[activity_key]
    return None


def _extension_from_url(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return suffix
    return ".png"


def absolutize_image_url(url: str) -> str:
    """Turn site-relative upload paths into absolute download URLs."""
    url = (url or "").strip()
    if not url:
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(UPLOADS_BASE + "/", url.lstrip("/"))
    return url


def ensure_image(
    build_dir: Path,
    image_key: str,
    images: dict[str, Any],
) -> dict[str, str] | None:
    """Download presenter image into build_dir/images/ and return Typst segment dict."""
    meta = images.get(image_key) or {}
    url = absolutize_image_url(str(meta.get("url") or ""))
    if not url:
        return None
    ext = _extension_from_url(url)
    rel = f"images/{image_key}{ext}"
    dest = build_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.stat().st_size == 0:
        req = Request(url, headers={"User-Agent": "zume-assets/0.1"})
        with urlopen(req, timeout=90) as resp:
            dest.write_bytes(resp.read())
    return {
        "image": rel,
        "alt": str(meta.get("alt") or image_key),
    }


def resolve_paragraph_items(
    paragraphs: list[str],
    images: dict[str, Any],
    build_dir: Path,
    *,
    missing: list[str] | None = None,
) -> list[str | dict[str, str]]:
    """Turn text paragraphs and ``{{ *_image }}`` shortcodes into Typst content items.

    Unresolved shortcodes are never leaked as literal ``{{ … }}``. When
    ``missing`` is provided, image keys that cannot be downloaded are appended
    so the caller can hard-fail instead of leaving blank slots.
    """
    out: list[str | dict[str, str]] = []
    for para in paragraphs:
        text = (para or "").strip()
        match = _IMAGE_PLACEHOLDER.match(text)
        if not match:
            if text:
                out.append(para)
            continue
        key = placeholder_to_image_key(match.group(1))
        if not key:
            continue
        item = ensure_image(build_dir, key, images)
        if item:
            out.append(item)
        elif missing is not None:
            missing.append(key)
    return out
