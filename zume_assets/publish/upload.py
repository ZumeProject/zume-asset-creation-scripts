"""Upload approved packs to gs://zume-file-mirror/{lang}/ via gcloud."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .gcs import UploadItem, gcloud_available, storage_cp
from .pack import discover_pack, plan_uploads

CpFn = Callable[[Path, str], None]


def upload_pack(
    lang: str,
    *,
    course_types: tuple[str, ...] | list[str] | None = None,
    lang_dir: Path | None = None,
    include_videos: bool = False,
    execute: bool = False,
    require_all: bool = True,
    cp_fn: CpFn | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Plan or execute upload of PDF + Keynote (optionally videos) for a language.

    Dry-run is the default (execute=False): returns the plan and commands that
    would run. With execute=True, copies via gcloud storage cp (or cp_fn).
    """
    items = discover_pack(
        lang,
        course_types=course_types,
        lang_dir=lang_dir,
        include_videos=include_videos,
        root=root,
    )
    plan = plan_uploads(items)
    missing_required = [
        i for i in items if i.missing and i.kind in {"pdf", "keynote"}
    ]

    result: dict[str, Any] = {
        "lang": lang,
        "bucket": "zume-file-mirror",
        "execute": execute,
        "include_videos": include_videos,
        "plan": plan,
        "commands": [],
        "uploaded": [],
        "status": "dry-run",
    }

    if missing_required and (execute or require_all):
        names = ", ".join(i.object_name for i in missing_required)
        if execute:
            raise FileNotFoundError(
                f"Cannot upload — missing required local assets for {lang}: {names}"
            )
        result["status"] = "incomplete"
        result["error"] = f"Missing required local assets: {names}"
        result["commands"] = [
            ["gcloud", "storage", "cp", str(i.local_path), i.gs_uri]
            for i in items
            if not i.missing
        ]
        return result

    to_upload = [i for i in items if not i.missing]
    if not execute:
        result["commands"] = [
            ["gcloud", "storage", "cp", str(i.local_path), i.gs_uri] for i in to_upload
        ]
        if missing_required:
            result["status"] = "incomplete"
        return result

    if not gcloud_available() and cp_fn is None:
        raise RuntimeError(
            "gcloud CLI not found on PATH. Install Google Cloud SDK and authenticate "
            "before --execute uploads."
        )

    uploaded: list[dict[str, str]] = []
    commands: list[list[str]] = []
    for item in to_upload:
        cmd = _copy_one(item, cp_fn=cp_fn)
        commands.append(cmd)
        uploaded.append(
            {
                "local": str(item.local_path),
                "gs_uri": item.gs_uri,
                "public_url": item.public_url,
                "kind": item.kind,
            }
        )

    result["commands"] = commands
    result["uploaded"] = uploaded
    result["status"] = "uploaded"
    return result


def _copy_one(item: UploadItem, *, cp_fn: CpFn | None) -> list[str]:
    if cp_fn is not None:
        cp_fn(item.local_path, item.gs_uri)
        return ["gcloud", "storage", "cp", str(item.local_path), item.gs_uri]
    return storage_cp(item.local_path, item.gs_uri, execute=True)
