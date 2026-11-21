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

# Pack training ids that officially reuse another online video (course reformat).
# Download writes SOURCE.json aliases + copies the MP4; review must PASS these.
# Evidence (2026-11-18): t20_b / Faithfulness — no distinct Vimeo for 20; alias of 19.
OFFICIAL_VIDEO_ALIASES: dict[str, str] = {
    "20": "19",
}


def training_id_from_slide_key(key: str) -> str | None:
    """Map Keynote slide keys like t3_b → training id 3; special-cases t10_e / t10_g."""
    special = {"t10_e": "10", "t10_g": "33"}
    if key in special:
        return special[key]
    match = _SLIDE_KEY_RE.match(key)
    if match:
        return match.group(1)
    return None


def source_alias_target(
    training_id: str,
    source_videos: dict[str, Any],
    provenance_aliases: dict[str, Any] | None,
) -> str | None:
    """Return canonical training id if SOURCE records an official allowlisted alias.

    Accepts either top-level ``aliases`` (``{"20": {"from": "19", ...}}``) or a
    ``videos[id].status == "aliased"`` entry whose ``from`` / implied target matches
    :data:`OFFICIAL_VIDEO_ALIASES`.
    """
    expected = OFFICIAL_VIDEO_ALIASES.get(training_id)
    if expected is None:
        return None

    aliases = provenance_aliases or {}
    entry = aliases.get(training_id)
    if isinstance(entry, dict):
        from_id = str(entry.get("from") or "").strip()
        if from_id == expected:
            return expected

    meta = source_videos.get(training_id)
    if isinstance(meta, dict) and str(meta.get("status") or "").casefold() == "aliased":
        from_id = str(meta.get("from") or "").strip()
        # Download copies into videos[20] without embedding "from"; top-level
        # aliases carry it. If status is aliased and no conflicting from, trust
        # the official map when expected target is present in SOURCE.
        if from_id == expected or (not from_id and expected in source_videos):
            return expected

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
    store: Path | None = None,
) -> dict[str, Any]:
    """Compare pack/SOURCE video ids + titles to the online master video map."""
    repo = root or load_repo_root()
    master_path = master_path or default_master_path(lang, course_type, repo)
    source_path = source_path or source_json(lang, repo)
    pack = (
        pack
        if pack is not None
        else default_pack_dir(lang, course_type, repo, store=store)
    )
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
    provenance_aliases: dict[str, Any] = {}
    if source_path.is_file():
        provenance = json.loads(source_path.read_text(encoding="utf-8"))
        raw = provenance.get("videos") or {}
        if isinstance(raw, dict):
            source_videos = {str(k): v for k, v in raw.items()}
        raw_aliases = provenance.get("aliases") or {}
        if isinstance(raw_aliases, dict):
            provenance_aliases = {str(k): v for k, v in raw_aliases.items()}
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

        alias_of = None
        if online_meta is None:
            alias_of = source_alias_target(training_id, source_videos, provenance_aliases)
            if alias_of is not None:
                online_meta = online.get(alias_of)
                row["alias_of"] = alias_of
                if online_meta is None:
                    failures.append(
                        {
                            "id": f"{training_id}:alias-target-missing",
                            "message": (
                                f"training id {training_id} aliases {alias_of}, "
                                f"but {alias_of} is not in master videos for {lang}/{course_type}"
                            ),
                        }
                    )
                    row["status"] = "fail"
                    results.append(row)
                    return
                notes.append(
                    f"id {training_id}: official alias of {alias_of} "
                    f"(SOURCE + OFFICIAL_VIDEO_ALIASES)"
                )
            else:
                failures.append(
                    {
                        "id": training_id,
                        "message": (
                            f"training id {training_id} not in master videos "
                            f"for {lang}/{course_type}"
                        ),
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
        if alias_of is not None:
            row["compared_to_training_id"] = alias_of

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
                compare_label = (
                    f"online {alias_of} vimeoId" if alias_of else "online vimeoId"
                )
                failures.append(
                    {
                        "id": f"{training_id}:vimeo",
                        "message": (
                            f"id {training_id}: SOURCE vimeo_id {source_vimeo!r} "
                            f"!= {compare_label} {online_vimeo!r}"
                        ),
                    }
                )
            # Title strings are informational only: SOURCE uses Vimeo filenames;
            # the API returns display titles. Matching vimeo_id is the embed gate.
            elif (
                source_title
                and online_title
                and _norm_title(source_title) != _norm_title(online_title)
            ):
                st = _norm_title(source_title)
                ot = _norm_title(online_title)
                if ot not in st and st not in ot:
                    row["title_note"] = "mismatch"
                    notes.append(
                        f"id {training_id}: title differs "
                        f"(SOURCE {source_title!r} vs online {online_title!r}); "
                        f"ignored — vimeo_id is authoritative"
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

    def _id_sort_key(k: str) -> tuple[int, int | str]:
        return (0, int(k)) if k.isdigit() else (1, k)

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
        # SOURCE-only: gate on course master ids. Vimeo-folder extras (e.g. 31/32/68)
        # are notes only — never FAIL solely for ids outside the course master.
        for tid in sorted(online, key=_id_sort_key):
            check_one(tid)
    else:
        # Still verify master has videos; nothing local to compare.
        for tid in sorted(online, key=_id_sort_key):
            failures.append(
                {
                    "id": f"{tid}:no-local",
                    "message": f"no SOURCE.json / pack data to verify training id {tid}",
                }
            )

    # SOURCE keys beyond pack embeds / course master are informational only.
    if source_videos:
        if embed_items:
            extra = sorted(set(source_videos) - checked_ids, key=_id_sort_key)
            if extra:
                notes.append(
                    f"SOURCE.json keys not in embed list (ignored): {', '.join(extra)}"
                )
        else:
            extra = sorted(set(source_videos) - set(online), key=_id_sort_key)
            if extra:
                notes.append(
                    f"SOURCE.json keys not in course master (ignored): {', '.join(extra)}"
                )

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
