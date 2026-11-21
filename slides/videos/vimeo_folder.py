"""Canonical Vimeo folder IDs and provenance helpers for training MP4s."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
VIMEO_FOLDERS_JSON = REPO_ROOT / "slide-builder" / "parts" / "vimeo-folders.json"

# https://vimeo.com/user/75461893/folder/21862752
EN_VIMEO_USER_ID = "75461893"
EN_VIMEO_FOLDER_ID = "21862752"
EN_VIMEO_FOLDER_URL = (
    f"https://vimeo.com/user/{EN_VIMEO_USER_ID}/folder/{EN_VIMEO_FOLDER_ID}"
)
PROVENANCE_NAME = "SOURCE.json"


def folder_id_for_language(language_code: str = "en") -> tuple[str, str]:
    """Return (folder_id, display_name) from slide-builder/parts/vimeo-folders.json."""
    data = json.loads(VIMEO_FOLDERS_JSON.read_text(encoding="utf-8"))
    languages = data.get("languages") or []
    code = language_code.lower()
    for language in languages:
        if str(language.get("language_code", "")).lower() == code:
            folder_id = str(language["folder_id"])
            name = str(language.get("name") or folder_id)
            return folder_id, name
    raise KeyError(f"No Vimeo folder for language_code={language_code!r} in {VIMEO_FOLDERS_JSON}")


def assert_en_folder_id() -> str:
    """Ensure the checked-in EN mapping still points at folder 21862752."""
    folder_id, _name = folder_id_for_language("en")
    if folder_id != EN_VIMEO_FOLDER_ID:
        raise RuntimeError(
            f"EN Vimeo folder_id is {folder_id!r}, expected {EN_VIMEO_FOLDER_ID!r} "
            f"({EN_VIMEO_FOLDER_URL})"
        )
    return folder_id


def numeric_id_from_title(title: str) -> int | None:
    """Extract the training video number from a Vimeo title.

    Supports titles like ``(01) God Uses…``, ``01_God…``, ``1. God…``, ``1 God…``.
    """
    text = (title or "").strip()
    if not text:
        return None
    match = re.match(r"^\((\d+)\)", text)
    if match:
        return int(match.group(1))
    match = re.match(r"^(\d+)\s*[_\-.\s]", text)
    if match:
        return int(match.group(1))
    match = re.match(r"^(\d+)$", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def provenance_path(video_dir: Path) -> Path:
    return Path(video_dir) / PROVENANCE_NAME


def load_provenance(video_dir: Path) -> dict[str, Any] | None:
    path = provenance_path(video_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def provenance_matches_folder(
    video_dir: Path,
    *,
    folder_id: str = EN_VIMEO_FOLDER_ID,
) -> bool:
    data = load_provenance(video_dir)
    if not data:
        return False
    return str(data.get("folder_id") or "") == str(folder_id)


def write_provenance(video_dir: Path, payload: dict[str, Any]) -> Path:
    video_dir.mkdir(parents=True, exist_ok=True)
    path = provenance_path(video_dir)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
