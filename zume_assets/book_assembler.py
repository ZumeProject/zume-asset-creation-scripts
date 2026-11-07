"""Assemble normalized book JSON for Typst from live APIs + course manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import (
    SITE_BASE,
    cache_json,
    fetch_activity,
    fetch_presenter_content,
    fetch_script_by_video,
    load_repo_root,
)
from .html_text import html_to_text, paragraphs
from .qr import activity_url, checkin_url, make_qr_png, video_url

UI_PREFIX = {
    "10": "s1",
    "20": "s2",
    "intensive": "s3",
}

COURSE_LABELS = {
    "10": "10-Session Course",
    "20": "20-Session Course",
    "intensive": "Intensive Course",
}

OUTPUT_NAMES = {
    "10": "Zume-Training-10-Session-{lang}.pdf",
    "20": "Zume-Training-20-Session-{lang}.pdf",
    "intensive": "Zume-Training-Intensive-{lang}.pdf",
}


def _repo() -> Path:
    return load_repo_root()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ten_session_manifest() -> list[dict[str, Any]]:
    return _load_json(_repo() / "manifest" / "ten_session.json")


def ui_get(ui: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in ui and ui[key]:
            return str(ui[key])
    return default


def ui_list(ui: dict[str, str], prefix: str) -> list[str]:
    items: list[tuple[int, str]] = []
    for key, value in ui.items():
        if not key.startswith(prefix):
            continue
        suffix = key[len(prefix) :]
        if suffix.isdigit():
            items.append((int(suffix), str(value)))
    return [v for _, v in sorted(items)]


def format_duration(minutes: int | None) -> str | None:
    if minutes is None or minutes <= 0:
        return None
    return f"{minutes} min"


def concept_title(presenter: dict[str, Any], key: int | str) -> str:
    concepts = presenter.get("concepts") or {}
    videos = presenter.get("videos") or {}
    k = str(key)
    if k in concepts:
        return str(concepts[k])
    video = videos.get(k) or {}
    return str(video.get("title") or f"Concept {k}")


def collect_pray_text(ui: dict[str, str], prefix: str, pray_id: int | None = None) -> list[str]:
    if pray_id and pray_id != 1:
        lines = ui_list(ui, f"{prefix}.pray.{pray_id}.")
        if lines:
            return lines
        single = ui_get(ui, f"{prefix}.pray.{pray_id}")
        return [single] if single else []
    # default pray
    lines = ui_list(ui, f"{prefix}.pray.")
    if lines:
        # filter out nested pray.2.* already handled elsewhere when pray_id set
        filtered = []
        for key_suffix_and_val in sorted(
            ((k[len(f"{prefix}.pray.") :], v) for k, v in ui.items() if k.startswith(f"{prefix}.pray.")),
            key=lambda x: x[0],
        ):
            suffix, val = key_suffix_and_val
            if "." in suffix:
                # nested like 2.0 — skip for default pray block
                continue
            filtered.append(str(val))
        if filtered:
            return filtered
    single = ui_get(ui, f"{prefix}.pray")
    return [single] if single else []


def overview_block(
    session: dict[str, Any],
    presenter: dict[str, Any],
    ui: dict[str, str],
    duration: int | None,
) -> dict[str, Any]:
    concept_keys = session.get("conceptKeys") or []
    tool_keys = session.get("toolKeys") or []
    concepts = [concept_title(presenter, k) for k in concept_keys]
    tools = [concept_title(presenter, k) for k in tool_keys]

    if len(concepts) == 1:
        concepts_intro = ui_get(ui, "instruction.concept_intro")
    else:
        concepts_intro = ui_get(ui, "instruction.concepts_intro")
    if len(tools) == 1:
        tools_intro = ui_get(ui, "instruction.tool_intro")
    else:
        tools_intro = ui_get(ui, "instruction.tools_intro")

    # Some sessions are tool-practice only (no concepts)
    if not concepts and tools:
        if len(tools) == 1:
            concepts_intro = ui_get(ui, "instruction.tool_session_intro", "instruction.tool_practice_session_intro")
        else:
            concepts_intro = ui_get(ui, "instruction.tools_session_intro")
        return {
            "kind": "overview",
            "duration": format_duration(duration),
            "concepts_intro": concepts_intro,
            "concepts": tools,
            "tools_intro": "",
            "tools": [],
        }

    return {
        "kind": "overview",
        "duration": format_duration(duration),
        "concepts_intro": concepts_intro if concepts else "",
        "concepts": concepts,
        "tools_intro": tools_intro if tools else "",
        "tools": tools,
    }


def center_paragraphs(ui: dict[str, str], prefix: str, content_key: str) -> tuple[str | None, list[str]]:
    base = f"{prefix}.center.{content_key}"
    title = None
    paras: list[str] = []
    # numbered paragraphs .0 .1 ...
    numbered = ui_list(ui, f"{base}.")
    if numbered:
        # first item often title-like short heading
        if len(numbered[0].split()) <= 6 and len(numbered) > 1:
            title = numbered[0]
            paras = numbered[1:]
        else:
            paras = numbered
        # also pick up .list.*
        list_items = ui_list(ui, f"{base}.list.")
        paras.extend(list_items)
        return title, paras
    single = ui_get(ui, base)
    if single:
        return None, [single]
    return None, []


def ensure_qr(build_dir: Path, name: str, url: str) -> str:
    rel = f"qr/{name}.png"
    make_qr_png(url, build_dir / rel)
    return rel


def assemble_session_blocks(
    session: dict[str, Any],
    *,
    course_type: str,
    presenter: dict[str, Any],
    build_dir: Path,
    script_cache: dict[str, dict[str, Any] | None],
    activity_cache: dict[str, dict[str, Any] | None],
) -> list[dict[str, Any]]:
    ui: dict[str, str] = presenter.get("ui") or {}
    videos: dict[str, Any] = presenter.get("videos") or {}
    prefix = f"{UI_PREFIX[course_type]}.session.{session['session']}"
    blocks: list[dict[str, Any]] = []
    pending_video: str | None = None

    for slide in session.get("slides") or []:
        stype = slide.get("type")
        duration = slide.get("duration")

        if stype == "title":
            continue

        if stype == "checkin":
            code = str(session.get("checkinCode") or "")
            qr = ensure_qr(build_dir, f"checkin-{code or 'open'}", checkin_url(code or None))
            blocks.append(
                {
                    "kind": "checkin",
                    "label": ui_get(ui, "label.checkin", default="CHECK-IN"),
                    "duration": format_duration(duration),
                    "instruction": ui_get(ui, "instruction.checkin"),
                    "url_hint": ui_get(ui, "instruction.checkin_url", default="Or zume.training/checkin and use code:"),
                    "code": code,
                    "qr": qr,
                    "qr_url": checkin_url(code or None),
                }
            )
            continue

        if stype == "pray":
            pray_id = slide.get("prayId")
            blocks.append(
                {
                    "kind": "pray",
                    "label": ui_get(ui, "label.pray", default="PRAY"),
                    "duration": format_duration(duration),
                    "paragraphs": collect_pray_text(ui, prefix, pray_id),
                }
            )
            continue

        if stype == "look_back":
            blocks.append(
                {
                    "kind": "look_back",
                    "label": ui_get(ui, "label.look_back", default="LOOK BACK"),
                    "duration": format_duration(duration),
                    "paragraphs": ui_list(ui, f"{prefix}.look_back."),
                }
            )
            continue

        if stype == "overview":
            blocks.append(overview_block(session, presenter, ui, duration))
            continue

        if stype == "watch":
            # Workbook collapses watch+video into a single READ with script.
            pending_video = str(slide.get("videoKey"))
            continue

        if stype == "video":
            video_key = str(slide.get("videoKey") or pending_video or "")
            pending_video = None
            if not video_key:
                continue
            if video_key not in script_cache:
                script_cache[video_key] = fetch_script_by_video(video_key, presenter.get("locale") or "en")
            script = script_cache[video_key] or {}
            title = (videos.get(video_key) or {}).get("title") or concept_title(presenter, video_key)
            body = paragraphs(script.get("content") or "")
            qr = ensure_qr(build_dir, f"video-{video_key}", video_url(video_key))
            blocks.append(
                {
                    "kind": "read",
                    "label": "READ",
                    "duration": format_duration(duration if duration and duration <= 10 else 5),
                    "title": title,
                    "paragraphs": body,
                    "qr": qr,
                    "qr_caption": f"Watch: {title}",
                    "qr_url": video_url(video_key),
                    "video_key": video_key,
                }
            )
            continue

        if stype == "discuss":
            discussion_id = slide.get("discussionId") or 1
            questions = ui_list(ui, f"{prefix}.discuss.{discussion_id}.question.")
            intro = ui_get(ui, f"{prefix}.discuss.{discussion_id}.intro")
            blocks.append(
                {
                    "kind": "discuss",
                    "label": ui_get(ui, "label.discuss", default="DISCUSS"),
                    "duration": format_duration(duration),
                    "intro": intro,
                    "questions": questions,
                }
            )
            continue

        if stype == "activity":
            activity_key = str(slide.get("activityKey") or "")
            instance = slide.get("activityInstance") or 1
            if activity_key not in activity_cache:
                # coachingchecklist / getacoach / next_steps may 404 on activities API
                activity_cache[activity_key] = fetch_activity(
                    activity_key, presenter.get("locale") or "en"
                )
            activity = activity_cache[activity_key] or {}
            instructions = ui_list(ui, f"{prefix}.activity.{activity_key}.{instance}.instruction.")
            body_title = ui_get(
                ui,
                f"{prefix}.activity.{activity_key}.{instance}.body_title",
                default=activity.get("body_title") or activity.get("title") or activity_key,
            )
            activity_body = html_to_text(activity.get("content"))
            qr = ensure_qr(build_dir, f"activity-{activity_key}", activity_url(activity_key))
            block: dict[str, Any] = {
                "kind": "activity",
                "label": ui_get(ui, "label.activity", default="ACTIVITY"),
                "duration": format_duration(duration),
                "title": body_title,
                "instructions": instructions,
                "paragraphs": paragraphs(activity_body),
                "qr": qr,
                "qr_caption": body_title,
                "qr_url": activity_url(activity_key),
                "activity_key": activity_key,
            }
            if activity_key == "listof100":
                block["worksheet"] = "listof100"
                block["worksheet_count"] = 100
            blocks.append(block)
            continue

        if stype == "center":
            content_key = str(slide.get("contentKey") or "")
            title, paras = center_paragraphs(ui, prefix, content_key)
            blocks.append(
                {
                    "kind": "center",
                    "title": title,
                    "paragraphs": paras,
                    "content_key": content_key,
                }
            )
            continue

        if stype == "left_image":
            content_key = str(slide.get("contentKey") or "")
            title = ui_get(ui, f"{prefix}.left_image.{content_key}.title", default=content_key)
            activity_key = slide.get("activityKey")
            block = {
                "kind": "image_note",
                "title": title,
                "paragraphs": [
                    f"(See the {title} diagram in the online workbook or activity resource.)"
                ],
                "content_key": content_key,
            }
            if activity_key:
                qr = ensure_qr(
                    build_dir, f"activity-{activity_key}", activity_url(str(activity_key))
                )
                block["qr"] = qr
                block["qr_caption"] = title
                block["qr_url"] = activity_url(str(activity_key))
            blocks.append(block)
            continue

        if stype == "review":
            # Guidebook mirrors challenges under OBEY; skip standalone review slide text.
            continue

        if stype == "obey":
            obey_id = slide.get("obeyId") or 1
            challenges = ui_list(ui, f"{prefix}.obey.{obey_id}.challenge.")
            blocks.append(
                {
                    "kind": "obey",
                    "label": ui_get(ui, "label.obey", default="OBEY"),
                    "challenges": challenges,
                }
            )
            continue

        if stype == "congratulations":
            blocks.append(
                {
                    "kind": "congratulations",
                    "label": ui_get(ui, "label.congratulations", default="CONGRATULATIONS"),
                    "paragraphs": [
                        "Congratulations on completing Zúme Training!",
                        "Join the Zúme community using the QR code.",
                    ],
                    "qr": ensure_qr(
                        build_dir, "activity-join_the_community", activity_url("join_the_community")
                    ),
                }
            )
            continue

    # Session 10 next_steps already in slides; ensure congratulations after last session
    return blocks


def assemble_book(
    *,
    lang: str = "en",
    course_type: str = "10",
    build_dir: Path | None = None,
    cache_api: bool = True,
) -> dict[str, Any]:
    if course_type != "10":
        raise NotImplementedError("Phase 1 only implements course type=10")

    root = _repo()
    build_dir = build_dir or (root / "output" / lang / "build-10")
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "qr").mkdir(parents=True, exist_ok=True)

    presenter = fetch_presenter_content(lang)
    if cache_api:
        cache_json(presenter, build_dir / "cache" / "presenter.json")

    sessions_manifest = load_ten_session_manifest()
    script_cache: dict[str, dict[str, Any] | None] = {}
    activity_cache: dict[str, dict[str, Any] | None] = {}

    sessions_out: list[dict[str, Any]] = []
    for session in sessions_manifest:
        title = ui_get(
            presenter.get("ui") or {},
            f"{UI_PREFIX[course_type]}.session.{session['session']}.title",
            default=f"SESSION {session['session']}",
        )
        blocks = assemble_session_blocks(
            session,
            course_type=course_type,
            presenter=presenter,
            build_dir=build_dir,
            script_cache=script_cache,
            activity_cache=activity_cache,
        )
        sessions_out.append(
            {
                "number": session["session"],
                "title": title,
                "checkin_code": session.get("checkinCode"),
                "concept_keys": session.get("conceptKeys") or [],
                "tool_keys": session.get("toolKeys") or [],
                "blocks": blocks,
            }
        )

    # Append congratulations after final session if not already present
    if sessions_out and not any(b.get("kind") == "congratulations" for b in sessions_out[-1]["blocks"]):
        sessions_out[-1]["blocks"].append(
            {
                "kind": "congratulations",
                "label": ui_get(presenter.get("ui") or {}, "label.congratulations", default="CONGRATULATIONS"),
                "paragraphs": [
                    "Congratulations on completing Zúme Training!",
                    "Join the Zúme community using the QR code.",
                ],
                "qr": ensure_qr(
                    build_dir, "activity-join_the_community", activity_url("join_the_community")
                ),
            }
        )

    if cache_api:
        cache_json(
            {k: (v or {}) for k, v in script_cache.items()},
            build_dir / "cache" / "scripts.json",
        )
        cache_json(
            {k: (v or {}) for k, v in activity_cache.items()},
            build_dir / "cache" / "activities.json",
        )

    book = {
        "lang": lang,
        "type": course_type,
        "title": "Zúme Training",
        "subtitle": COURSE_LABELS[course_type],
        "version_label": f"v6.0 - {course_type}",
        "site": SITE_BASE,
        "direction": "ltr",
        "output_name": OUTPUT_NAMES[course_type].format(lang=lang),
        "sessions": sessions_out,
        "meta": {
            "source": "live api.zume.training + manifest/ten_session.json",
            "presenter_locale": presenter.get("locale"),
            "session_count": len(sessions_out),
            "block_count": sum(len(s["blocks"]) for s in sessions_out),
        },
    }
    cache_json(book, build_dir / "book.json")
    return book
