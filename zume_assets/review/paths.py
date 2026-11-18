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


def default_pack_dir(lang: str, course_type: str, root: Path | None = None) -> Path:
    """Best-effort Keynote capture pack under repo output (mac packs may live elsewhere)."""
    return output_root(root) / lang / f"pack-{course_type}"
