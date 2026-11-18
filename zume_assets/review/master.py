"""On-demand master list from api.zume.training + course manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..api import API_BASE, SITE_BASE, cache_json, fetch_presenter_content, load_repo_root
from ..book_assembler import MANIFEST_FILES, load_course_manifest
from ..qr import activity_url, checkin_url, video_url
from .report import utc_now_iso

EXPECTED_REDIRECT = {
    "c": "/checkin?code={id}",
    "v": "/app/video?v={id}&l={locale}",
    "a": "/activities/{id}",
}

# Activities whose live destination is intentionally not /activities/{id}.
# Live QR checks use a stricter allowlist in qr_check.live_redirect_ok (path + query).
# Do not add getacoach / join_the_community / next_steps here without evidence.
ACTIVITY_EXPECTED_REDIRECT_OVERRIDES = {
    # create-your-plan requires login → …/auth/login?redirect=…/create-your-plan
    "3monthplan": "/auth/login",
}


def default_master_path(lang: str, course_type: str, root: Path | None = None) -> Path:
    repo = root or load_repo_root()
    return repo / "manifest" / "review" / f"{lang}-{course_type}.json"


def collect_keys_from_manifest(sessions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    """Return (checkins, video_keys, activity_keys) from a course manifest."""
    checkins: list[dict[str, Any]] = []
    video_keys: set[str] = set()
    activity_keys: set[str] = set()
    for session in sessions:
        code = session.get("checkinCode")
        if code is not None and str(code):
            checkins.append({"session": session.get("session"), "code": str(code)})
        for slide in session.get("slides") or []:
            stype = slide.get("type")
            if stype in {"watch", "video"} and slide.get("videoKey") is not None:
                video_keys.add(str(slide["videoKey"]))
            if stype == "activity" and slide.get("activityKey"):
                activity_keys.add(str(slide["activityKey"]))
            # Some discuss/tool slides also carry activityKey.
            if slide.get("activityKey") and stype != "activity":
                activity_keys.add(str(slide["activityKey"]))
    # Workbook always appends community QR after the final session.
    activity_keys.add("join_the_community")
    return checkins, video_keys, activity_keys


def expected_redirect_path(kind: str, content_id: str, locale: str) -> str:
    if kind == "a" and content_id in ACTIVITY_EXPECTED_REDIRECT_OVERRIDES:
        return ACTIVITY_EXPECTED_REDIRECT_OVERRIDES[content_id]
    template = EXPECTED_REDIRECT[kind]
    return template.format(id=content_id, locale=locale)


def probe_final_url(url: str, *, timeout: int = 30) -> str | None:
    """Follow redirects (GET) and return the final URL, or None on failure."""
    req = Request(url, headers={"User-Agent": "zume-assets-review/0.1", "Accept": "*/*"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return str(resp.geturl())
    except (HTTPError, URLError, TimeoutError, OSError):
        return None


def _path_and_query(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


def build_master(
    lang: str,
    course_type: str,
    *,
    presenter: dict[str, Any] | None = None,
    follow_redirects: bool = False,
    sessions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build master review JSON (pure data; optional live redirect probes)."""
    if course_type not in MANIFEST_FILES:
        raise ValueError(f"Unsupported course type: {course_type}")
    sessions = sessions if sessions is not None else load_course_manifest(course_type)
    presenter = presenter if presenter is not None else fetch_presenter_content(locale=lang)
    locale = str(presenter.get("locale") or lang)
    videos_api: dict[str, Any] = presenter.get("videos") or {}
    activities_api: dict[str, Any] = presenter.get("activities") or {}

    checkins_raw, video_keys, activity_keys = collect_keys_from_manifest(sessions)

    checkins: list[dict[str, Any]] = []
    for item in checkins_raw:
        code = item["code"]
        qr = checkin_url(code, locale=locale)
        entry: dict[str, Any] = {
            "session": item["session"],
            "code": code,
            "kind": "c",
            "qr_url": qr,
            "expected_redirect": expected_redirect_path("c", code, locale),
            "png_stem": f"checkin-{code}",
        }
        if follow_redirects:
            final = probe_final_url(qr)
            entry["live_final_url"] = final
            entry["live_path"] = _path_and_query(final) if final else None
        checkins.append(entry)

    videos: list[dict[str, Any]] = []
    for key in sorted(video_keys, key=lambda k: (0, int(k)) if k.isdigit() else (1, k)):
        meta = videos_api.get(key)
        if meta is None and key.isdigit():
            meta = videos_api.get(int(key))
        if not isinstance(meta, dict):
            meta = {}
        qr = video_url(key, locale=locale)
        entry = {
            "key": key,
            "kind": "v",
            "title": meta.get("title"),
            "vimeoId": meta.get("vimeoId") or meta.get("vimeo_id"),
            "youtubeId": meta.get("youtubeId") or meta.get("youtube_id"),
            "qr_url": qr,
            "expected_redirect": expected_redirect_path("v", key, locale),
            "png_stem": f"video-{key}",
        }
        if follow_redirects:
            final = probe_final_url(qr)
            entry["live_final_url"] = final
            entry["live_path"] = _path_and_query(final) if final else None
        videos.append(entry)

    activities: list[dict[str, Any]] = []
    for key in sorted(activity_keys):
        meta = activities_api.get(key) or {}
        if not isinstance(meta, dict):
            meta = {}
        qr = activity_url(key, locale=locale)
        entry = {
            "key": key,
            "kind": "a",
            "title": meta.get("title"),
            "qr_url": qr,
            "expected_redirect": expected_redirect_path("a", key, locale),
            "png_stem": f"activity-{key}",
        }
        if follow_redirects:
            final = probe_final_url(qr)
            entry["live_final_url"] = final
            entry["live_path"] = _path_and_query(final) if final else None
        activities.append(entry)

    return {
        "lang": lang,
        "type": course_type,
        "locale": locale,
        "fetched_at": utc_now_iso(),
        "api_base": API_BASE,
        "site_base": SITE_BASE,
        "manifest": MANIFEST_FILES[course_type],
        "follow_redirects": follow_redirects,
        "checkins": checkins,
        "videos": videos,
        "activities": activities,
        "counts": {
            "checkins": len(checkins),
            "videos": len(videos),
            "activities": len(activities),
        },
    }


def fetch_master(
    lang: str,
    course_type: str,
    *,
    output: Path | None = None,
    follow_redirects: bool = False,
    root: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    """Fetch presenter content, build master, write JSON. Returns (data, path)."""
    path = output or default_master_path(lang, course_type, root)
    data = build_master(lang, course_type, follow_redirects=follow_redirects)
    cache_json(data, path)
    return data, path


def load_master(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def master_entries_by_png_stem(master: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index all QR-bearing master rows by png_stem."""
    out: dict[str, dict[str, Any]] = {}
    for section in ("checkins", "videos", "activities"):
        for entry in master.get(section) or []:
            stem = entry.get("png_stem")
            if stem:
                out[str(stem)] = entry
    return out


def master_video_map(master: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map training video key → master video entry."""
    return {str(v["key"]): v for v in (master.get("videos") or []) if "key" in v}
