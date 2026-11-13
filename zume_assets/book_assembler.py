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
from .html_text import (
    fix_zume_brand_spacing,
    html_to_text,
    paragraphs,
    strip_markdown,
    unescape_markdown,
)
from .images import ensure_image, resolve_image_key, resolve_paragraph_items
from .qr import activity_url, checkin_url, make_qr_png, video_url


def _sanitize_plain(value: Any) -> Any:
    """Drop Markdown escapes and fix Zúme brand gaps in every Typst string."""
    if isinstance(value, str):
        return fix_zume_brand_spacing(unescape_markdown(value))
    if isinstance(value, list):
        return [_sanitize_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_plain(v) for k, v in value.items()}
    return value

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

# Map zume site/API locale codes → Typst ISO 639 lang (+ optional region).
_TYPST_LANG_MAP: dict[str, tuple[str, str | None]] = {
    "zhtw": ("zh", "TW"),
    "zh-tw": ("zh", "TW"),
    "zh_tw": ("zh", "TW"),
    "cntw": ("zh", "TW"),
    "zhcn": ("zh", "CN"),
    "zh-cn": ("zh", "CN"),
    "zhhk": ("zh", "HK"),
    "zh-hk": ("zh", "HK"),
    "zh": ("zh", None),
    "ar_jo": ("ar", "JO"),
    "ar_tn": ("ar", "TN"),
    "pa_pk": ("pa", "PK"),
}


def _typst_lang_region(lang: str) -> tuple[str, str | None]:
    key = (lang or "en").strip().lower().replace(" ", "")
    if key in _TYPST_LANG_MAP:
        return _TYPST_LANG_MAP[key]
    # Already ISO-ish (en, de, ar, …) — Typst accepts 2–3 letter codes.
    if 2 <= len(key) <= 3 and key.isalpha():
        return key, None
    return "en", None


def _listof100_worksheet_title(presenter: dict[str, Any], activity: dict[str, Any]) -> str:
    """Short localized 'List of 100' heading for the printable worksheet."""
    videos = presenter.get("videos") or {}
    video_title = str((videos.get("8") or videos.get(8) or {}).get("title") or "")
    for sep in ("──", "–", "—", " - ", "-"):
        if sep in video_title:
            short = video_title.split(sep)[-1].strip().strip("「」『』\"“”«»")
            if short:
                return short
    # Fall back to activity title (e.g. «قائمة المئة» / 「百人關注名單」).
    title = str(activity.get("title") or "")
    for left, right in (("「", "」"), ("『", "』"), ("“", "”"), ("«", "»"), ('"', '"')):
        if left in title and right in title:
            inner = title.split(left, 1)[1].split(right, 1)[0].strip()
            if inner:
                return inner
    return title or "List of 100"


def _listof100_mark_labels(instruction: str) -> list[str]:
    """Parse Disciple / Unbeliever / Unknown labels from the localized mark instruction."""
    defaults = ["Disciple", "Unbeliever", "Unknown"]
    text = (instruction or "").strip()
    if not text:
        return defaults
    if "：" in text:
        tail = text.rsplit("：", 1)[-1]
    elif ":" in text:
        tail = text.rsplit(":", 1)[-1]
    else:
        tail = text
    tail = tail.strip().rstrip(".。")
    for sep in ("، أو ", " أو ", ", or ", " or ", "、", "或", "، ", ", "):
        tail = tail.replace(sep, "|")
    parts = [p.strip().strip("«»\"“”「」") for p in tail.split("|") if p.strip()]
    if len(parts) >= 3:
        parts = parts[:3]
        # Title-case Latin labels (instruction text is often lowercase).
        if all(p.isascii() for p in parts):
            parts = [p[:1].upper() + p[1:] for p in parts]
        return parts
    return defaults


def _repo() -> Path:
    return load_repo_root()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


MANIFEST_FILES = {
    "10": "ten_session.json",
    "20": "twenty_session.json",
    "intensive": "intensive_session.json",
}


def load_course_manifest(course_type: str) -> list[dict[str, Any]]:
    name = MANIFEST_FILES.get(course_type)
    if not name:
        raise NotImplementedError(f"No course manifest for type={course_type}")
    path = _repo() / "manifest" / name
    if not path.exists():
        raise FileNotFoundError(f"Missing course manifest: {path}")
    return _load_json(path)


def load_ten_session_manifest() -> list[dict[str, Any]]:
    return load_course_manifest("10")


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
    overview_label = ui_get(ui, "label.overview", default="OVERVIEW")

    if not concepts and tools:
        if len(tools) == 1:
            concepts_intro = ui_get(ui, "instruction.tool_session_intro", "instruction.tool_practice_session_intro")
        else:
            concepts_intro = ui_get(ui, "instruction.tools_session_intro")
        return {
            "kind": "overview",
            "label": overview_label,
            "duration": format_duration(duration),
            "concepts_intro": concepts_intro,
            "concepts": tools,
            "tools_intro": "",
            "tools": [],
        }

    return {
        "kind": "overview",
        "label": overview_label,
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
            title = strip_markdown(numbered[0])
            paras = [strip_markdown(p) for p in numbered[1:]]
        else:
            paras = [strip_markdown(p) for p in numbered]
        # also pick up .list.*
        list_items = ui_list(ui, f"{base}.list.")
        paras.extend(strip_markdown(p) for p in list_items)
        return title, paras
    single = ui_get(ui, base)
    if single:
        return None, [strip_markdown(single)]
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
    locale = str(presenter.get("locale") or "en")
    prefix = f"{UI_PREFIX[course_type]}.session.{session['session']}"
    blocks: list[dict[str, Any]] = []
    pending_video: str | None = None

    for slide in session.get("slides") or []:
        stype = slide.get("type")
        duration = slide.get("duration")

        if stype == "title":
            continue

        if stype == "break":
            blocks.append(
                {
                    "kind": "break",
                    # API key is label.take_a_break (label.break is absent).
                    "label": ui_get(ui, "label.take_a_break", "label.break", default="BREAK"),
                    "paragraphs": [
                        ui_get(
                            ui,
                            "instruction.break",
                            default="Take a short break, then continue with the next section.",
                        )
                    ],
                }
            )
            continue

        if stype == "checkin":
            code = str(session.get("checkinCode") or "")
            qr_target = checkin_url(code or None, locale=locale)
            qr = ensure_qr(build_dir, f"checkin-{code or 'open'}", qr_target)
            blocks.append(
                {
                    "kind": "checkin",
                    "label": ui_get(ui, "label.checkin", default="CHECK-IN"),
                    "duration": format_duration(duration),
                    "instruction": ui_get(ui, "instruction.checkin"),
                    "url_hint": ui_get(ui, "instruction.checkin_url", default="Or zume.training/checkin and use code:"),
                    "code": code,
                    "qr": qr,
                    "qr_url": qr_target,
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
            body = resolve_paragraph_items(
                paragraphs(script.get("content") or ""),
                presenter.get("images") or {},
                build_dir,
            )
            qr_target = video_url(video_key, locale=locale)
            qr = ensure_qr(build_dir, f"video-{video_key}", qr_target)
            # Workbook chrome historically said "READ"; zume6 UI has no label.read —
            # only label.watch (the slide type being collapsed). Use that so locales translate.
            watch_label = ui_get(ui, "label.watch", default="READ")
            blocks.append(
                {
                    "kind": "read",
                    "label": watch_label,
                    "duration": format_duration(duration if duration and duration <= 10 else 5),
                    "title": title,
                    "paragraphs": body,
                    "qr": qr,
                    "qr_caption": f"{watch_label}: {title}",
                    "qr_url": qr_target,
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
            qr_target = activity_url(activity_key, locale=locale)
            qr = ensure_qr(build_dir, f"activity-{activity_key}", qr_target)
            block: dict[str, Any] = {
                "kind": "activity",
                "label": ui_get(ui, "label.activity", default="ACTIVITY"),
                "duration": format_duration(duration),
                "title": body_title,
                "instructions": instructions,
                "paragraphs": resolve_paragraph_items(
                    paragraphs(activity_body),
                    presenter.get("images") or {},
                    build_dir,
                ),
                "qr": qr,
                "qr_caption": body_title,
                "qr_url": qr_target,
                "activity_key": activity_key,
            }
            if activity_key == "listof100":
                block["worksheet"] = "listof100"
                block["worksheet_count"] = 100
                # Typst worksheet heading was hard-coded "List of 100"; prefer the
                # short tool name from video 8, else the localized activity title.
                block["worksheet_title"] = _listof100_worksheet_title(presenter, activity)
                # Session UI instruction.2 is the "mark disciple / unbeliever / unknown" line.
                mark_src = instructions[2] if len(instructions) > 2 else (
                    next(
                        (
                            s
                            for s in instructions
                            if "disciple" in s.lower() or "تلميذ" in s or "門徒" in s
                        ),
                        instructions[-1] if instructions else "",
                    )
                )
                block["worksheet_hint"] = mark_src or "Write names below. Mark Disciple / Unbeliever / Unknown."
                block["worksheet_marks"] = _listof100_mark_labels(mark_src)
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
            image_key = resolve_image_key(
                content_key=content_key or None,
                activity_key=str(activity_key) if activity_key else None,
            )
            image_item = (
                ensure_image(build_dir, image_key, presenter.get("images") or {})
                if image_key
                else None
            )
            block = {
                "kind": "image_note",
                "title": title,
                "paragraphs": [],
                "content_key": content_key,
            }
            if image_item:
                block["image"] = image_item["image"]
                block["image_alt"] = image_item.get("alt") or title
            else:
                # Fallback only when the presenter has no matching asset.
                block["paragraphs"] = [
                    f"(See the {title} diagram in the online workbook or activity resource.)"
                ]
            if activity_key:
                qr_target = activity_url(str(activity_key), locale=locale)
                qr = ensure_qr(build_dir, f"activity-{activity_key}", qr_target)
                block["qr"] = qr
                block["qr_caption"] = title
                block["qr_url"] = qr_target
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
            qr_target = activity_url("join_the_community", locale=locale)
            blocks.append(
                {
                    "kind": "congratulations",
                    "label": ui_get(ui, "label.congratulations", default="CONGRATULATIONS"),
                    "paragraphs": [
                        "Congratulations on completing Zúme Training!",
                        "Join the Zúme community using the QR code.",
                    ],
                    "qr": ensure_qr(build_dir, "activity-join_the_community", qr_target),
                    "qr_url": qr_target,
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
    if course_type not in MANIFEST_FILES:
        raise NotImplementedError(f"Unsupported course type={course_type}")

    root = _repo()
    build_dir = build_dir or (root / "output" / lang / f"build-{course_type}")
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "qr").mkdir(parents=True, exist_ok=True)

    presenter = fetch_presenter_content(lang)
    if cache_api:
        cache_json(presenter, build_dir / "cache" / "presenter.json")

    sessions_manifest = load_course_manifest(course_type)
    script_cache: dict[str, dict[str, Any] | None] = {}
    activity_cache: dict[str, dict[str, Any] | None] = {}
    locale = str(presenter.get("locale") or lang or "en")
    # Known RTL locale codes on zume6 (site display_code). Typst mirrors the
    # two-column guidebook chrome when direction is rtl (QR/rail on the right).
    rtl_locales = {"ar", "ar_jo", "ar_tn", "fa", "ur", "ps", "pus", "he", "ckb", "ku"}
    text_direction = "rtl" if locale.lower() in rtl_locales or lang.lower() in rtl_locales else "ltr"
    # Typst #set text(lang: …) requires ISO 639-1/2/3; zume site codes like
    # zhtw/zhcn are not valid. Keep book.lang as the site/API code for QR + filenames.
    typst_lang, typst_region = _typst_lang_region(lang)

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
        qr_target = activity_url("join_the_community", locale=locale)
        sessions_out[-1]["blocks"].append(
            {
                "kind": "congratulations",
                "label": ui_get(presenter.get("ui") or {}, "label.congratulations", default="CONGRATULATIONS"),
                "paragraphs": [
                    "Congratulations on completing Zúme Training!",
                    "Join the Zúme community using the QR code.",
                ],
                "qr": ensure_qr(build_dir, "activity-join_the_community", qr_target),
                "qr_url": qr_target,
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

    book = _sanitize_plain(
        {
            "lang": lang,
            "typst_lang": typst_lang,
            "typst_region": typst_region,
            "type": course_type,
            "title": "Zúme Training",
            "subtitle": COURSE_LABELS[course_type],
            "version_label": f"v6.0 - {course_type}",
            "site": SITE_BASE,
            "direction": text_direction,
            "output_name": OUTPUT_NAMES[course_type].format(lang=lang),
            "sessions": sessions_out,
            "meta": {
                "source": f"live api.zume.training + manifest/{MANIFEST_FILES[course_type]}",
                "presenter_locale": presenter.get("locale"),
                "session_count": len(sessions_out),
                "block_count": sum(len(s["blocks"]) for s in sessions_out),
            },
        }
    )
    cache_json(book, build_dir / "book.json")
    return book
