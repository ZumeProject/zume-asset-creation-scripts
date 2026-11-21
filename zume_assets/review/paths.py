"""Shared review path helpers (avoid importing cli to prevent cycles)."""

from __future__ import annotations

from pathlib import Path

from ..api import load_repo_root


def output_root(root: Path | None = None) -> Path:
    return (root or load_repo_root()) / "output"


def build_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    return output_root(root) / lang / f"build-{course_type}"


def qr_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    return build_dir(lang, course_type, root) / "qr"


def book_path(lang: str, course_type: str, root: Path | None = None) -> Path:
    return build_dir(lang, course_type, root) / "book.json"


def report_dir(lang: str, root: Path | None = None) -> Path:
    return output_root(root) / lang / "review"


def videos_dir(lang: str, root: Path | None = None) -> Path:
    return output_root(root) / lang / "videos"


def source_json(lang: str, root: Path | None = None) -> Path:
    return videos_dir(lang, root) / "SOURCE.json"


def local_pack_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    """Repo-local Keynote pack path: output/{lang}/pack-{type}."""
    return output_root(root) / lang / f"pack-{course_type}"


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
    """Prefer Agent Store presenter capture pack, else output/{lang}/pack-{type}.

    Mac / Creator Studio packs live under Agent Store
    ``media/{lang}-{type}-presenter-captures/``. ``review videos`` / ``review all``
    should find those without a manual ``--pack`` when present.
    """
    # Local import avoids a paths ↔ lang_prereqs cycle at module load.
    from ..lang_prereqs import default_capture_pack_dir

    capture = default_capture_pack_dir(lang, course_type, store=store)
    local = local_pack_dir(lang, course_type, root)
    candidates = (capture, local)
    for cand in candidates:
        if pack_has_embed_sources(cand):
            return cand
    for cand in candidates:
        if cand.is_dir():
            return cand
    # Prefer the Agent Store path in "not found" notes (where packs usually live).
    return capture