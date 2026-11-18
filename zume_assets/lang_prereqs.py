"""Checklist blockers for full language packs (PDF + videos + Keynote).

PDF-only Typst builds can succeed while Keynote/videos are still impossible.
Call this when the user expects a full pack so missing map/pack/folder fails
loudly with exact next human steps instead of a silent PDF-only “success”.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .api import load_repo_root

COURSE_TYPES = ("10", "20", "intensive")
EN_VIMEO_USER_ID = "75461893"
# Proven production folder ids (also in slide-builder/parts/vimeo-folders.json).
KNOWN_FOLDER_IDS = {
    "en": "21862752",
    "es": "269525",
}


@dataclass
class PrereqIssue:
    id: str
    blocking: bool
    message: str
    next_steps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "blocking": self.blocking,
            "message": self.message,
            "next_steps": list(self.next_steps),
        }


def vimeo_folders_path(root: Path | None = None) -> Path:
    return (root or load_repo_root()) / "slide-builder" / "parts" / "vimeo-folders.json"


def folder_id_for_language(lang: str, root: Path | None = None) -> tuple[str, str] | None:
    path = vimeo_folders_path(root)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    code = lang.strip().lower()
    for language in data.get("languages") or []:
        if str(language.get("language_code", "")).lower() == code:
            return str(language["folder_id"]), str(language.get("name") or code)
    return None


def default_capture_pack_dir(lang: str, course_type: str, store: Path | None = None) -> Path:
    """Agent Store media pack path used by slides/assemble-keynote drivers."""
    if store is None:
        # Match assemble-keynote defaults when running on Creator Studio.
        store = Path(
            "/Users/chris/Library/Application Support/Cursor/AgentStores/"
            "cursor_agent_stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/files"
        )
        cloud = Path("/cursor/stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f")
        if cloud.exists():
            store = cloud
    return store / "media" / f"{lang}-{course_type}-presenter-captures"


def check_language_pack_prereqs(
    lang: str,
    *,
    course_types: tuple[str, ...] = COURSE_TYPES,
    root: Path | None = None,
    store: Path | None = None,
    require_videos: bool = True,
    require_capture_packs: bool = True,
) -> list[PrereqIssue]:
    """Return blocking/non-blocking issues for a full language pack."""
    lang = lang.strip().lower()
    root = root or load_repo_root()
    issues: list[PrereqIssue] = []

    if require_videos:
        mapped = folder_id_for_language(lang, root)
        if mapped is None:
            known = ", ".join(f"{k}→{v}" for k, v in sorted(KNOWN_FOLDER_IDS.items()))
            issues.append(
                PrereqIssue(
                    id="vimeo_folder_map",
                    blocking=True,
                    message=(
                        f"Language {lang!r} is not in "
                        f"{vimeo_folders_path(root).relative_to(root)}. "
                        f"Known production mappings: {known}. Do not invent a folder id."
                    ),
                    next_steps=[
                        f"Ask Chris for the Vimeo folder URL/id for {lang} "
                        f"(user {EN_VIMEO_USER_ID}).",
                        "Add {language_code, folder_id, name} to "
                        "slide-builder/parts/vimeo-folders.json.",
                        f"Then download: python3 slides/videos/download_lang_vimeo.py "
                        f"--lang {lang}",
                    ],
                )
            )
        else:
            folder_id, display = mapped
            videos_dir = root / "output" / lang / "videos"
            source = videos_dir / "SOURCE.json"
            if not source.exists() or not any(videos_dir.glob("*.mp4")):
                issues.append(
                    PrereqIssue(
                        id="local_videos",
                        blocking=True,
                        message=(
                            f"No local Vimeo download under output/{lang}/videos "
                            f"(mapped folder_id={folder_id}, name={display!r})."
                        ),
                        next_steps=[
                            "pip install -r slide-builder/requirements.txt",
                            "Ensure VIMEO_ACCESS_TOKEN (or VIMEO_PERSONAL_ACCESS_TOKEN) "
                            "is set.",
                            f"python3 slides/videos/download_lang_vimeo.py --lang {lang}",
                            "Sync numbered MP4s into each capture pack’s videos/ "
                            "before Keynote embed.",
                        ],
                    )
                )

    if require_capture_packs:
        for course_type in course_types:
            pack = default_capture_pack_dir(lang, course_type, store=store)
            manifest = pack / "manifest.json"
            if not manifest.exists():
                issues.append(
                    PrereqIssue(
                        id=f"capture_pack_{course_type}",
                        blocking=True,
                        message=(
                            f"Missing presenter capture pack for {lang}/{course_type}: "
                            f"{pack} (need manifest.json + PNGs)."
                        ),
                        next_steps=[
                            "Capture on Creator Studio via slides/capture/capture_presenter.py "
                            f"--lang {lang} --type {course_type}",
                            "Or copy an approved pack into Agent Store "
                            f"media/{lang}-{course_type}-presenter-captures/",
                        ],
                    )
                )

    return issues


def format_prereq_report(lang: str, issues: list[PrereqIssue]) -> str:
    lines = [f"Language pack prerequisites for {lang!r}:"]
    if not issues:
        lines.append("  OK — Vimeo map, local videos (if required), and capture packs look present.")
        return "\n".join(lines) + "\n"
    for issue in issues:
        tag = "BLOCK" if issue.blocking else "NOTE"
        lines.append(f"  [{tag}] {issue.id}: {issue.message}")
        for step in issue.next_steps:
            lines.append(f"         → {step}")
    lines.append(
        "PDF-only Typst can still build; do not treat PDF success as a finished Keynote pack "
        "while any [BLOCK] remains."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", required=True)
    parser.add_argument(
        "--types",
        default="10,20,intensive",
        help="Comma-separated course types to check for capture packs",
    )
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Skip video/capture checks (Typst PDF does not need them)",
    )
    args = parser.parse_args(argv)
    types = tuple(t.strip() for t in args.types.split(",") if t.strip())
    issues = check_language_pack_prereqs(
        args.lang,
        course_types=types or COURSE_TYPES,
        require_videos=not args.pdf_only,
        require_capture_packs=not args.pdf_only,
    )
    sys.stdout.write(format_prereq_report(args.lang, issues))
    return 1 if any(i.blocking for i in issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
