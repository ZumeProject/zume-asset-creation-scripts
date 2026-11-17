"""Keynote / pack video mapping vs online master + SOURCE.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..api import load_repo_root
from .master import default_master_path, load_master, master_video_map
from .paths import default_pack_dir, report_dir, source_json
from .report import exit_code_for, utc_now_iso, write_report

_SLIDE_KEY_RE = re.compile(r"^t(\d+)_b$")


def training_id_from_slide_key(key: str) -> str | None:
    """Map Keynote slide keys like t3_b → training id 3; special-cases t10_e / t10_g."""
    special = {"t10_e": "10", "t10_g": "33"}
    if key in special:
        return special[key]
    match = _SLIDE_KEY_RE.match(key)
    if match:
        return match.group(1)
    return None


def load_video_replace_list(pack: Path) -> list[dict[str, Any]]:
    path = pack / "work" / "video-replace-list.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []
    return []


def video_list_from_manifest(manifest: dict[str, Any], pack: Path) -> list[dict[str, Any]]:
    """Mirror slides/assemble-keynote/embed_videos_choose.video_list (no Keynote deps)."""
    slides = manifest.get("slides") or []
    items: list[dict[str, Any]] = []
    for slide in slides:
        kind = slide.get("kind")
        stype = slide.get("type")
        vid = slide.get("video_id") or slide.get("video_key")
        key = str(slide.get("key") or "")
        if stype == "video" or kind == "video":
            if not vid:
                vid = training_id_from_slide_key(key)
            if not vid:
                continue
            mp4 = pack / "videos" / f"{vid}.mp4"
            items.append(
                {
                    "index": int(slide["index"]),
                    "key": key,
                    "path": str(mp4),
                    "video_id": str(vid),
                }
            )
    return items


def resolve_embed_list(pack: Path | None) -> list[dict[str, Any]]:
    if pack is None or not pack.is_dir():
        return []
    items = load_video_replace_list(pack)
    if items:
        return items
    manifest_path = pack / "manifest.json"
    if manifest_path.is_file():
        return video_list_from_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")),
            pack,
        )
    return []


def _norm_title(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _norm_vimeo(value: Any) -> str:
    text = str(value or "").strip()
    if text.isdigit():
        return text
    # Accept URLs like https://vimeo.com/247062938
    match = re.search(r"(\d{6,})", text)
    return match.group(1) if match else text


def check_videos(
    lang: str,
    course_type: str,
    *,
    master_path: Path | None = None,
    source_path: Path | None = None,
    pack: Path | None = None,
    report_dir_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Compare pack/SOURCE video ids + titles to the online master video map."""
    repo = root or load_repo_root()
    master_path = master_path or default_master_path(lang, course_type, repo)
    source_path = source_path or source_json(lang, repo)
    pack = pack if pack is not None else default_pack_dir(lang, course_type, repo)
    report_dir_path = report_dir_path or report_dir(lang, repo)

    failures: list[dict[str, Any]] = []
    notes: list[str] = []
    results: list[dict[str, Any]] = []

    if not master_path.is_file():
        report = {
            "kind": "videos",
            "status": "error",
            "lang": lang,
            "type": course_type,
            "generated_at": utc_now_iso(),
            "summary": {"error": "master_missing"},
            "failures": [
                {
                    "id": "master",
                    "message": f"Master list not found: {master_path}. Run: review fetch-master",
                }
            ],
            "notes": notes,
            "results": results,
        }
        write_report(report, report_dir_path, stem=f"videos-{course_type}")
        return report

    master = load_master(master_path)
    online = master_video_map(master)

    source_videos: dict[str, Any] = {}
    if source_path.is_file():
        provenance = json.loads(source_path.read_text(encoding="utf-8"))
        raw = provenance.get("videos") or {}
        if isinstance(raw, dict):
            source_videos = {str(k): v for k, v in raw.items()}
        notes.append(f"SOURCE.json: {source_path}")
    else:
        notes.append(f"SOURCE.json not found at {source_path}")

    embed_items = resolve_embed_list(pack if pack.is_dir() else None)
    if pack.is_dir():
        notes.append(f"pack: {pack} ({len(embed_items)} video slides)")
    else:
        notes.append(
            f"pack not found at {pack}; checking SOURCE.json keys against master only"
        )

    checked_ids: set[str] = set()

    def check_one(training_id: str, *, slide_key: str | None = None, mp4: Path | None = None) -> None:
        checked_ids.add(training_id)
        online_meta = online.get(training_id)
        source_meta = source_videos.get(training_id) or {}
        if not isinstance(source_meta, dict):
            source_meta = {}

        row: dict[str, Any] = {
            "training_id": training_id,
            "slide_key": slide_key,
            "mp4": str(mp4) if mp4 else None,
        }

        if online_meta is None:
            failures.append(
                {
                    "id": training_id,
                    "message": f"training id {training_id} not in master videos for {lang}/{course_type}",
                }
            )
            row["status"] = "fail"
            results.append(row)
            return

        online_vimeo = _norm_vimeo(online_meta.get("vimeoId"))
        online_title = online_meta.get("title")
        source_vimeo = _norm_vimeo(source_meta.get("vimeo_id") or source_meta.get("vimeoId"))
        source_title = source_meta.get("title")

        row["online_vimeoId"] = online_vimeo or None
        row["online_title"] = online_title
        row["source_vimeo_id"] = source_vimeo or None
        row["source_title"] = source_title

        ok = True
        if source_path.is_file():
            if training_id not in source_videos:
                ok = False
                failures.append(
                    {
                        "id": f"{training_id}:source-missing",
                        "message": f"training id {training_id} missing from SOURCE.json",
                    }
                )
            elif online_vimeo and source_vimeo and online_vimeo != source_vimeo:
                ok = False
                failures.append(
                    {
                        "id": f"{training_id}:vimeo",
                        "message": (
                            f"id {training_id}: SOURCE vimeo_id {source_vimeo!r} "
                            f"!= online vimeoId {online_vimeo!r}"
                        ),
                    }
                )
            if source_title and online_title and _norm_title(source_title) != _norm_title(online_title):
                # Titles from Vimeo folder often include "(01) …" while API is short;
                # only fail when neither contains the other.
                st = _norm_title(source_title)
                ot = _norm_title(online_title)
                if ot not in st and st not in ot:
                    ok = False
                    failures.append(
                        {
                            "id": f"{training_id}:title",
                            "message": (
                                f"id {training_id}: SOURCE title {source_title!r} "
                                f"does not match online {online_title!r}"
                            ),
                        }
                    )

        if mp4 is not None and not mp4.is_file():
            ok = False
            failures.append(
                {
                    "id": f"{training_id}:mp4",
                    "message": f"id {training_id}: missing MP4 at {mp4}",
                }
            )

        row["status"] = "pass" if ok else "fail"
        results.append(row)

    if embed_items:
        for item in embed_items:
            tid = str(item.get("video_id") or "")
            key = str(item.get("key") or "")
            if not tid:
                derived = training_id_from_slide_key(key)
                tid = derived or ""
            if not tid:
                failures.append(
                    {
                        "id": key or "unknown",
                        "message": f"embed item missing video_id: {item!r}",
                    }
                )
                continue
            mp4_path = Path(str(item.get("path") or "")) if item.get("path") else None
            check_one(tid, slide_key=key or None, mp4=mp4_path)
    elif source_videos:
        for tid in sorted(source_videos, key=lambda k: (0, int(k)) if k.isdigit() else (1, k)):
            check_one(tid)
    else:
        # Still verify master has videos; nothing local to compare.
        for tid in sorted(online, key=lambda k: (0, int(k)) if k.isdigit() else (1, k)):
            failures.append(
                {
                    "id": f"{tid}:no-local",
                    "message": f"no SOURCE.json / pack data to verify training id {tid}",
                }
            )

    # SOURCE keys not referenced by pack (informational note only if pack present).
    if embed_items and source_videos:
        extra = sorted(set(source_videos) - checked_ids)
        if extra:
            notes.append(f"SOURCE.json keys not in embed list: {', '.join(extra)}")

    status = "pass" if not failures else "fail"
    report = {
        "kind": "videos",
        "status": status,
        "lang": lang,
        "type": course_type,
        "generated_at": utc_now_iso(),
        "master_path": str(master_path),
        "source_path": str(source_path) if source_path.is_file() else None,
        "pack": str(pack) if pack.is_dir() else None,
        "summary": {
            "online_videos": len(online),
            "source_videos": len(source_videos),
            "embed_items": len(embed_items),
            "checked": len(checked_ids),
            "failure_count": len(failures),
        },
        "failures": failures,
        "notes": notes,
        "results": results,
    }
    write_report(report, report_dir_path, stem=f"videos-{course_type}")
    return report


def run_videos_cli(**kwargs: Any) -> int:
    report = check_videos(**kwargs)
    return exit_code_for(report)
