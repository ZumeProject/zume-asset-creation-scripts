"""Download and resolve presenter diagram images for Typst guidebooks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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


def ensure_image(
    build_dir: Path,
    image_key: str,
    images: dict[str, Any],
) -> dict[str, str] | None:
    """Download presenter image into build_dir/images/ and return Typst segment dict."""
    meta = images.get(image_key) or {}
    url = str(meta.get("url") or "").strip()
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
) -> list[str | dict[str, str]]:
    """Turn text paragraphs and ``{{ *_image }}`` shortcodes into Typst content items."""
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
        # Drop unresolved shortcodes so they never leak as literal {{ … }}
    return out
