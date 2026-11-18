"""gcloud storage helpers for zume-file-mirror (no credential printing)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

BUCKET = "zume-file-mirror"
PUBLIC_BASE = f"https://storage.googleapis.com/{BUCKET}"
GS_PREFIX = f"gs://{BUCKET}"


@dataclass(frozen=True)
class UploadItem:
    local_path: Path
    object_name: str  # relative under {lang}/
    gs_uri: str
    public_url: str
    kind: str  # pdf | keynote | pptx | video | other
    course_type: str | None = None
    missing: bool = False


def object_uri(lang: str, filename: str) -> str:
    return f"{GS_PREFIX}/{lang}/{filename}"


def public_url(lang: str, filename: str) -> str:
    return f"{PUBLIC_BASE}/{lang}/{filename}"


def gcloud_available() -> bool:
    return shutil.which("gcloud") is not None


def require_gcloud() -> str:
    path = shutil.which("gcloud")
    if not path:
        raise RuntimeError(
            "gcloud CLI not found on PATH. Install Google Cloud SDK and run "
            "`gcloud auth application-default login` (or `gcloud auth login`) "
            "before --execute uploads."
        )
    return path


def run_gcloud(
    args: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `gcloud …`. Never logs auth tokens; only forwards argv as given."""
    require_gcloud()
    cmd = ["gcloud", *args]
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def storage_cp(local: Path, gs_uri: str, *, execute: bool) -> list[str]:
    """
    Copy one local file to a gs:// URI via `gcloud storage cp`.

    Overwrite is the normal path: if the object already exists, `cp` replaces it.
    No existence check and no second confirmation after `--execute` is authorized.
    When execute is False, returns the command that would run (dry-run).
    """
    args = ["storage", "cp", str(local), gs_uri]
    if not execute:
        return ["gcloud", *args]
    run_gcloud(args, check=True, capture_output=True)
    return ["gcloud", *args]
