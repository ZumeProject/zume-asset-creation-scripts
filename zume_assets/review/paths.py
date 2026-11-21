"""Review path helpers. Canonical definitions live in ``zume_assets.paths``."""

from __future__ import annotations

from pathlib import Path

from ..paths import (
    book_path,
    build_dir,
    capture_pack_dir,
    output_root,
    qr_dir,
    report_dir,
    source_json,
    videos_dir,
)

__all__ = [
    "book_path",
    "build_dir",
    "capture_pack_dir",
    "default_pack_dir",
    "output_root",
    "pack_has_embed_sources",
    "qr_dir",
    "report_dir",
    "source_json",
    "videos_dir",
]


def pack_has_embed_sources(pack: Path) -> bool:
    """True when a pack dir can drive video review (replace-list or manifest)."""
    if not pack.is_dir():
        return False
    if (pack / "work" / "video-replace-list.json").is_file():
        return True
    return (pack / "manifest.json").is_file()


def default_pack_dir(
    lang: str,
    course_type: str,
    root: Path | None = None,
    store: Path | None = None,
) -> Path:
    """Presenter capture pack: ``build/{lang}/captures/{type}``.

    ``store`` is ignored. Packs are not read from an Agent Store.
    """
    del store
    return capture_pack_dir(lang, course_type, root)
