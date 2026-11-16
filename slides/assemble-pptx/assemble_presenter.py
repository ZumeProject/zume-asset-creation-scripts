#!/usr/bin/env python3
"""Assemble EN presenter PPTX (10/20/intensive) from capture pack + MP4s.

Reuse the EN10 OOXML layout: 16:9 double-wide slides, full-bleed PNG or
embedded MP4 + poster on every kind=video / type=video slide.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import requests
from pptx import Presentation
from pptx.util import Emu

# Import helpers from sibling assemble_en10 when available
sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble_en10 import (  # noqa: E402
    MIN_MP4_BYTES,
    PNG_PX,
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    add_video_icon,
    ensure_videos,
    find_local_mp4,
    normalize_manifest,
    pack_ready,
    resolve_slide_image,
)

STORE = Path(
    "/Users/chris/Library/Application Support/Cursor/AgentStores/"
    "cursor_agent_stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/files"
)
REPO_ROOT = Path(__file__).resolve().parents[2]

PACKS = {
    "10": {
        "pack": STORE / "media" / "en-10-presenter-captures",
        "output": REPO_ROOT / "output" / "en" / "Zume-Training-10-Session-en.pptx",
    },
    "20": {
        "pack": STORE / "media" / "en-20-presenter-captures",
        "output": REPO_ROOT / "output" / "en" / "Zume-Training-20-Session-en.pptx",
    },
    "intensive": {
        "pack": STORE / "media" / "en-intensive-presenter-captures",
        "output": REPO_ROOT / "output" / "en" / "Zume-Training-Intensive-en.pptx",
    },
}
DEFAULT_VIDEOS = REPO_ROOT / "output" / "en" / "videos"
EN10_VIDEOS = STORE / "media" / "en-10-presenter-captures" / "videos"
GCS_MP4 = "https://storage.googleapis.com/zume-file-mirror/en/{video_id}.mp4"


def load_manifest(pack: Path) -> dict[str, Any]:
    path = pack / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def seed_videos_from_en10(pack: Path, video_dir: Path) -> None:
    """Copy shared EN MP4s from the EN10 pack when present."""
    dest_videos = pack / "videos"
    dest_videos.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)
    sources = [EN10_VIDEOS, video_dir]
    for src_root in sources:
        if not src_root.exists():
            continue
        for mp4 in src_root.glob("*.mp4"):
            for target in (dest_videos / mp4.name, video_dir / mp4.name):
                if not target.exists() or target.stat().st_size < MIN_MP4_BYTES:
                    shutil.copy2(mp4, target)


def build_pptx(
    manifest: dict[str, Any],
    pack: Path,
    videos: dict[str, Path],
    output: Path,
    *,
    allow_placeholders: bool = False,
    skip_missing_videos: bool = False,
) -> dict[str, Any]:
    manifest = normalize_manifest(manifest)
    slides = list(manifest["slides"])
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank = prs.slide_layouts[6]

    placeholder_count = 0
    video_embedded = 0
    video_skipped = 0
    video_icons = 0

    for s in slides:
        slide = prs.slides.add_slide(blank)
        png_path, is_ph = resolve_slide_image(pack, s, allow_placeholders=allow_placeholders)
        if is_ph:
            placeholder_count += 1

        if s.get("kind") == "video":
            vid = str(s.get("video_id") or "")
            mp4 = videos.get(vid)
            if mp4 is None and not skip_missing_videos:
                mp4 = find_local_mp4(pack, Path("."), s)
            if mp4 and mp4.exists() and mp4.stat().st_size > MIN_MP4_BYTES:
                slide.shapes.add_movie(
                    str(mp4),
                    Emu(0),
                    Emu(0),
                    SLIDE_WIDTH,
                    SLIDE_HEIGHT,
                    poster_frame_image=str(png_path),
                    mime_type="video/mp4",
                )
                video_embedded += 1
                if add_video_icon(slide):
                    video_icons += 1
            elif skip_missing_videos or allow_placeholders:
                slide.shapes.add_picture(
                    str(png_path), Emu(0), Emu(0), width=SLIDE_WIDTH, height=SLIDE_HEIGHT
                )
                if add_video_icon(slide):
                    video_icons += 1
                video_skipped += 1
            else:
                raise FileNotFoundError(f"Missing MP4 for video_id={vid}")
        else:
            slide.shapes.add_picture(
                str(png_path), Emu(0), Emu(0), width=SLIDE_WIDTH, height=SLIDE_HEIGHT
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))
    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "slide_count": len(slides),
        "placeholders": placeholder_count,
        "video_embedded": video_embedded,
        "video_skipped": video_skipped,
        "video_icons": video_icons,
        "slide_width_emu": int(prs.slide_width),
        "slide_height_emu": int(prs.slide_height),
        "video_slot_count": len(manifest["video_slots"]),
        "expected_png_px": manifest.get("expected_png_px", list(PNG_PX)),
    }


def download_missing(video_ids: list[str], video_dir: Path) -> None:
    video_dir.mkdir(parents=True, exist_ok=True)
    for vid in video_ids:
        dest = video_dir / f"{vid}.mp4"
        if dest.exists() and dest.stat().st_size > MIN_MP4_BYTES:
            continue
        url = GCS_MP4.format(video_id=vid)
        print(f"download {url}", flush=True)
        with requests.get(url, stream=True, timeout=180) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(".partial")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            tmp.replace(dest)
        print(f"  wrote {dest} ({dest.stat().st_size})", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=sorted(PACKS), required=True)
    parser.add_argument("--pack", type=Path, default=None)
    parser.add_argument("--videos", type=Path, default=DEFAULT_VIDEOS)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--skip-missing-videos", action="store_true")
    parser.add_argument("--download-videos-only", action="store_true")
    args = parser.parse_args(argv)

    cfg = PACKS[args.type]
    pack = args.pack or cfg["pack"]
    output = args.output or cfg["output"]
    # Prefer writing into the main checkout output/ if worktree path differs
    main_out = Path(
        "/Users/chris/Documents/ZUME/zume-asset-creation-scripts-1/output/en"
    ) / output.name
    if output.parent.name == "en" and "wt-" in str(REPO_ROOT):
        output = main_out

    seed_videos_from_en10(pack, args.videos)
    raw = load_manifest(pack)
    manifest = normalize_manifest(raw)
    ready, reason = pack_ready(manifest, pack)
    print(f"pack: {reason}", flush=True)
    print(
        f"manifest slides={manifest['slide_count']} "
        f"video_slots={len(manifest['video_slots'])}",
        flush=True,
    )

    vids = [
        str(s.get("video_id"))
        for s in manifest["video_slots"]
        if s.get("video_id")
    ]
    download_missing(vids, args.videos)
    download_missing(vids, pack / "videos")
    videos = ensure_videos(manifest, args.videos, pack=pack, download=True)
    print(f"videos ready: {len(videos)}", flush=True)
    if args.download_videos_only:
        return 0

    if not ready and not args.allow_placeholders:
        print("PNG pack not ready", file=sys.stderr)
        return 2

    stats = build_pptx(
        manifest,
        pack,
        videos,
        output,
        allow_placeholders=args.allow_placeholders and not ready,
        skip_missing_videos=args.skip_missing_videos or args.allow_placeholders,
    )
    print(
        f"Wrote {stats['output']} ({stats['bytes']} bytes, "
        f"{stats['slide_count']} slides, placeholders={stats['placeholders']}, "
        f"videos={stats['video_embedded']}, icons={stats.get('video_icons', 0)})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
