"""Repo paths for finished uploads and gitignored working files.

Finished files (the nine PDF / Keynote / PPTX names publish uploads):

    <repo>/output/{lang}/

Working files (safe to delete after a verified upload):

    <repo>/build/{lang}/videos/
    <repo>/build/{lang}/{type}/          Typst intermediates
    <repo>/build/{lang}/review/
    <repo>/build/{lang}/captures/{type}/
    <repo>/build/reference/
    <repo>/build/legacy/{lang}/           old slide-builder packer

``images/`` at the repo root stays tracked source art for gap fillers.
"""

from __future__ import annotations

import os
from pathlib import Path

from .api import load_repo_root


def repo_root(root: Path | None = None) -> Path:
    return root or load_repo_root()


def output_root(root: Path | None = None) -> Path:
    """Finished-asset root. Holds PDF, Keynote, and PPTX only."""
    return repo_root(root) / "output"


def finished_dir(lang: str, root: Path | None = None) -> Path:
    return output_root(root) / lang.strip().lower()


def working_root(root: Path | None = None) -> Path:
    """Gitignored pipeline working tree (also the setuptools build/ name)."""
    return repo_root(root) / "build"


def lang_working_dir(lang: str, root: Path | None = None) -> Path:
    return working_root(root) / lang.strip().lower()


def videos_dir(lang: str, root: Path | None = None) -> Path:
    return lang_working_dir(lang, root) / "videos"


def source_json(lang: str, root: Path | None = None) -> Path:
    return videos_dir(lang, root) / "SOURCE.json"


def typst_build_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    """Typst intermediates: book.json, qr/, cache/, downloaded diagrams."""
    return lang_working_dir(lang, root) / course_type


def build_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    """Alias of ``typst_build_dir`` kept for existing callers."""
    return typst_build_dir(lang, course_type, root)


def qr_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    return typst_build_dir(lang, course_type, root) / "qr"


def book_path(lang: str, course_type: str, root: Path | None = None) -> Path:
    return typst_build_dir(lang, course_type, root) / "book.json"


def report_dir(lang: str, root: Path | None = None) -> Path:
    return lang_working_dir(lang, root) / "review"


def capture_pack_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    return lang_working_dir(lang, root) / "captures" / course_type


def reference_dir(root: Path | None = None) -> Path:
    return working_root(root) / "reference"


def legacy_project_dir(lang: str, root: Path | None = None) -> Path:
    """Default project path for the legacy slide-builder packer."""
    return working_root(root) / "legacy" / lang.strip().lower()


def ensure_capture_videos_link(pack: Path, videos: Path) -> Path:
    """Point ``pack/videos`` at the language MP4 directory.

    The link is relative (``../../videos`` when the pack lives at
    ``build/{lang}/captures/{type}``). A non-empty real directory is left
    alone so existing files are not deleted.
    """
    videos.mkdir(parents=True, exist_ok=True)
    pack.mkdir(parents=True, exist_ok=True)
    link = pack / "videos"
    target = Path(os.path.relpath(videos, pack))
    if link.is_symlink():
        if link.readlink() == target:
            return link
        link.unlink()
    elif link.is_dir():
        if any(link.iterdir()):
            return link
        link.rmdir()
    elif link.exists():
        link.unlink()
    link.symlink_to(target, target_is_directory=True)
    return link
