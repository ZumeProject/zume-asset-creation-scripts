"""Discover local approved pack files under output/{lang}/."""

from __future__ import annotations

from pathlib import Path

from ..api import load_repo_root
from ..paths import videos_dir
from .gcs import UploadItem, object_uri, public_url
from .names import COURSE_TYPES, expected_filenames


def default_lang_dir(lang: str, root: Path | None = None) -> Path:
    return (root or load_repo_root()) / "output" / lang


def discover_pack(
    lang: str,
    *,
    course_types: tuple[str, ...] | list[str] | None = None,
    lang_dir: Path | None = None,
    include_videos: bool = False,
    root: Path | None = None,
) -> list[UploadItem]:
    """
    List PDF + Keynote + PPTX (and optionally videos/) files to publish.

    Missing production files are included with missing=True so dry-run / verify
    can report them; upload --execute refuses missing required assets.
    """
    types = tuple(course_types) if course_types else COURSE_TYPES
    base = lang_dir or default_lang_dir(lang, root)
    items: list[UploadItem] = []

    for asset in expected_filenames(lang, types):
        path = base / asset.filename
        items.append(
            UploadItem(
                local_path=path,
                object_name=asset.filename,
                gs_uri=object_uri(lang, asset.filename),
                public_url=public_url(lang, asset.filename),
                kind=asset.kind,
                course_type=asset.course_type,
                missing=not path.is_file(),
            )
        )

    if include_videos:
        downloaded = videos_dir(lang, root)
        if downloaded.is_dir():
            for path in sorted(downloaded.iterdir()):
                if not path.is_file():
                    continue
                if path.name == "SOURCE.json":
                    continue
                if path.suffix.lower() not in {".mp4", ".m4v", ".mov"}:
                    continue
                rel = f"videos/{path.name}"
                items.append(
                    UploadItem(
                        local_path=path,
                        object_name=rel,
                        gs_uri=object_uri(lang, rel),
                        public_url=public_url(lang, rel),
                        kind="video",
                        course_type=None,
                        missing=False,
                    )
                )

    return items


def plan_uploads(items: list[UploadItem]) -> dict[str, object]:
    """Summary dict for dry-run / reports (no secrets)."""
    present = [i for i in items if not i.missing]
    missing = [i for i in items if i.missing]
    return {
        "count": len(items),
        "present": len(present),
        "missing": len(missing),
        "files": [
            {
                "local": str(i.local_path),
                "gs_uri": i.gs_uri,
                "kind": i.kind,
                "course_type": i.course_type,
                "missing": i.missing,
                "bytes": i.local_path.stat().st_size if i.local_path.is_file() else None,
            }
            for i in items
        ],
    }
