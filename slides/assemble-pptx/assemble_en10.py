#!/usr/bin/env python3
"""Assemble EN 10-session PPTX from presenter PNG pack + MP4s.

Works with the Mac worker capture pack layout:
  media/en-10-presenter-captures/
    manifest.json   # {base, slides:[{index,session,key,kind,video_key,png,mp4},...]}
    pngs/*.png
    videos/*.mp4

Supports placeholder PNGs while the pack is still filling in.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Emu, Inches

# Reference PPSX uses 2× standard 16:9 (26.666" × 15")
SLIDE_WIDTH = Inches(26.666666666666668)
SLIDE_HEIGHT = Inches(15.0)
PNG_PX = (3692, 2068)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = Path(
    "/cursor/stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/media/en-10-presenter-captures"
)
# Finished decks always land under the repo checkout, never Agent Store docs/.
DEFAULT_VIDEOS = REPO_ROOT / "output" / "en" / "videos"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "en" / "Zume-Training-10-Session-en.pptx"
GCS_MP4 = "https://storage.googleapis.com/zume-file-mirror/en/{video_id}.mp4"
MIN_PNG_BYTES = 1000
MIN_MP4_BYTES = 100_000


def load_manifest(pack: Path) -> dict[str, Any]:
    path = pack / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# Known thought-video keys the Mac capture pack sometimes marks kind=image
# (type=video) without video_key/mp4. From ten_session.json / parts/10.json.
THOUGHT_VIDEO_KEY_TO_ID: dict[str, str] = {
    "t10_e": "10",
    "t10_g": "33",
}


def normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Normalize Mac or legacy manifest shapes into a common structure."""
    slides_in = list(manifest.get("slides") or [])
    slides: list[dict[str, Any]] = []
    for s in slides_in:
        key = str(s.get("key") or "")
        slide_type = s.get("type")
        kind = s.get("kind")
        video_id = s.get("video_id") or s.get("video_key")
        # Treat presenter "video" thoughts as embeds even if capture kind=image
        if slide_type == "video" or key in THOUGHT_VIDEO_KEY_TO_ID:
            kind = "video"
        if not kind:
            kind = "video" if slide_type == "video" else "image"
        if not video_id and key in THOUGHT_VIDEO_KEY_TO_ID:
            video_id = THOUGHT_VIDEO_KEY_TO_ID[key]
        if kind == "video" and not video_id and s.get("mp4"):
            video_id = Path(str(s["mp4"])).stem
        # Derive t{N}_b → N when still missing
        if kind == "video" and not video_id and key.startswith("t") and key.endswith("_b"):
            mid = key[1:-2]
            if mid.isdigit():
                video_id = mid
        png = s.get("png") or ""
        mp4 = s.get("mp4") or (f"{video_id}.mp4" if video_id else None)
        slides.append(
            {
                **s,
                "kind": kind,
                "video_id": str(video_id) if video_id else None,
                "png": png,
                "mp4": mp4,
            }
        )
    video_slots = [s for s in slides if s.get("kind") == "video"]
    out = dict(manifest)
    out["slides"] = slides
    out["slide_count"] = len(slides)
    out["video_slots"] = video_slots
    # Preserve viewport hints when present; default to reference size
    out.setdefault("expected_png_px", list(PNG_PX))
    out.setdefault(
        "viewport",
        {"width": PNG_PX[0] // 2, "height": PNG_PX[1] // 2, "deviceScaleFactor": 2},
    )
    return out


def slide_png_path(pack: Path, slide: dict[str, Any]) -> Path:
    rel = str(slide.get("png") or "")
    candidates = [
        pack / rel,
        pack / "pngs" / Path(rel).name,
        pack / "pngs" / rel,
    ]
    for c in candidates:
        if c.exists():
            return c
    # Prefer pngs/ for newly written placeholders
    return pack / "pngs" / Path(rel).name


def count_present_pngs(manifest: dict[str, Any], pack: Path) -> tuple[int, int, list[str]]:
    slides = manifest.get("slides") or []
    missing: list[str] = []
    present = 0
    for s in slides:
        path = slide_png_path(pack, s)
        if path.exists() and path.stat().st_size >= MIN_PNG_BYTES:
            present += 1
        else:
            missing.append(str(s.get("png")))
    return present, len(slides), missing


def pack_ready(manifest: dict[str, Any], pack: Path) -> tuple[bool, str]:
    slides = manifest.get("slides") or []
    if not slides:
        return False, "manifest has no slides"
    present, total, missing = count_present_pngs(manifest, pack)
    status = manifest.get("status")
    if present >= total:
        return True, f"all pngs present ({present}/{total})"
    return (
        False,
        f"status={status} present_pngs={present}/{total} missing={len(missing)}",
    )


def make_placeholder_png(
    dest: Path,
    *,
    index: int,
    key: str,
    session: int,
    size: tuple[int, int] = PNG_PX,
) -> Path:
    """Write a compact 16:9 placeholder (palette PNG) labeled with slide identity.

    Full 3692×2068 RGB placeholders balloon partial decks past store size
    limits; palette + optimize keeps smoke PPTXs small while preserving aspect.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Draw at modest res then scale up for correct aspect without huge files
    sketch = Image.new("RGB", (640, 360), color=(32, 48, 72))
    draw = ImageDraw.Draw(sketch)
    label = f"PLACEHOLDER  #{index}  s{session}/{key}"
    draw.rectangle([(8, 8), (632, 352)], outline=(220, 220, 220), width=3)
    draw.text((16, 170), label[:60], fill=(240, 240, 240))
    img = sketch.resize(size, Image.Resampling.NEAREST).convert("P", palette=Image.Palette.ADAPTIVE)
    img.save(dest, format="PNG", optimize=True)
    return dest


def resolve_slide_image(
    pack: Path,
    slide: dict[str, Any],
    *,
    allow_placeholders: bool,
    placeholder_dir: Path | None = None,
) -> tuple[Path, bool]:
    png = slide_png_path(pack, slide)
    if png.exists() and png.stat().st_size >= MIN_PNG_BYTES:
        return png, False
    if not allow_placeholders:
        raise FileNotFoundError(f"Missing PNG: {png}")
    ph_root = placeholder_dir or (pack / "_placeholders")
    dest = ph_root / Path(str(slide.get("png") or "missing.png")).name
    if not dest.exists() or dest.stat().st_size < MIN_PNG_BYTES:
        make_placeholder_png(
            dest,
            index=int(slide.get("index") or 0),
            key=str(slide.get("key") or ""),
            session=int(slide.get("session") or 0),
        )
    return dest, True


def find_local_mp4(pack: Path, video_dir: Path, slide: dict[str, Any]) -> Path | None:
    vid = str(slide.get("video_id") or "")
    names = []
    if slide.get("mp4"):
        names.append(Path(str(slide["mp4"])).name)
    if vid:
        names.append(f"{vid}.mp4")
    dirs = [pack / "videos", video_dir, pack]
    for name in names:
        for d in dirs:
            cand = d / name
            if cand.exists() and cand.stat().st_size > MIN_MP4_BYTES:
                return cand
    return None


def ensure_videos(
    manifest: dict[str, Any],
    video_dir: Path,
    *,
    pack: Path | None = None,
    download: bool = True,
) -> dict[str, Path]:
    video_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Path] = {}
    slots = manifest.get("video_slots") or [
        s for s in manifest.get("slides", []) if s.get("kind") == "video"
    ]
    pack = pack or DEFAULT_PACK
    for slot in slots:
        vid = str(slot.get("video_id") or "")
        if not vid:
            continue
        local = find_local_mp4(pack, video_dir, slot)
        if local:
            mapping[vid] = local
            print(f"video cached {local} ({local.stat().st_size})", flush=True)
            continue
        dest = video_dir / f"{vid}.mp4"
        if not download:
            print(f"video missing (no download): {vid}", flush=True)
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
        mapping[vid] = dest
        print(f"  wrote {dest} ({dest.stat().st_size})", flush=True)
    return mapping


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
            elif skip_missing_videos or allow_placeholders:
                slide.shapes.add_picture(
                    str(png_path), Emu(0), Emu(0), width=SLIDE_WIDTH, height=SLIDE_HEIGHT
                )
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
        "slide_width_emu": int(prs.slide_width),
        "slide_height_emu": int(prs.slide_height),
        "video_slot_count": len(manifest["video_slots"]),
    }


def poll_and_assemble(
    pack: Path,
    video_dir: Path,
    output: Path,
    *,
    interval_s: float = 30.0,
    max_wait_s: float = 7200.0,
) -> dict[str, Any]:
    start = time.time()
    last_present = -1
    final_stats: dict[str, Any] | None = None
    while True:
        raw = load_manifest(pack)
        manifest = normalize_manifest(raw)
        present, total, _ = count_present_pngs(manifest, pack)
        ready, reason = pack_ready(manifest, pack)
        print(f"poll: {reason}", flush=True)
        videos = ensure_videos(manifest, video_dir, pack=pack, download=True)

        if present != last_present and present >= 1:
            if ready:
                out = output
            else:
                stem = output.stem
                out = (
                    output
                    if stem.endswith(".partial")
                    else output.with_name(stem + ".partial.pptx")
                )
            stats = build_pptx(
                manifest,
                pack,
                videos,
                out,
                allow_placeholders=not ready,
                skip_missing_videos=True,
            )
            print(
                f"assembled {stats['output']} slides={stats['slide_count']} "
                f"ph={stats['placeholders']} vids={stats['video_embedded']} present={present}",
                flush=True,
            )
            final_stats = stats
            last_present = present

        if ready:
            stats = build_pptx(
                manifest,
                pack,
                videos,
                output,
                allow_placeholders=False,
                skip_missing_videos=False,
            )
            print(f"FINAL {stats}", flush=True)
            return stats

        if time.time() - start >= max_wait_s:
            if final_stats:
                return final_stats
            raise TimeoutError(f"Pack not ready after {max_wait_s}s ({reason})")
        time.sleep(interval_s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--videos", type=Path, default=DEFAULT_VIDEOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download-videos-only", action="store_true")
    parser.add_argument("--allow-placeholders", action="store_true")
    parser.add_argument("--skip-missing-videos", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--poll-max-wait", type=float, default=7200.0)
    args = parser.parse_args(argv)

    raw = load_manifest(args.pack)
    manifest = normalize_manifest(raw)
    ready, reason = pack_ready(manifest, args.pack)
    print(f"pack: {reason}", flush=True)
    print(
        f"manifest slides={manifest['slide_count']} video_slots={len(manifest['video_slots'])}",
        flush=True,
    )

    videos = ensure_videos(manifest, args.videos, pack=args.pack, download=True)
    print(f"videos ready: {len(videos)}", flush=True)
    if args.download_videos_only:
        return 0

    if args.poll:
        stats = poll_and_assemble(
            args.pack,
            args.videos,
            args.output,
            interval_s=args.poll_interval,
            max_wait_s=args.poll_max_wait,
        )
        print(f"Wrote {stats['output']}")
        return 0

    if not ready and not args.allow_placeholders:
        print(
            "PNG pack not ready; refusing assemble (pass --allow-placeholders or --poll)",
            file=sys.stderr,
        )
        return 2

    if ready:
        out = args.output
    else:
        stem = args.output.stem
        if stem.endswith(".partial"):
            out = args.output
        else:
            out = args.output.with_name(stem + ".partial.pptx")
    stats = build_pptx(
        manifest,
        args.pack,
        videos,
        out,
        allow_placeholders=args.allow_placeholders and not ready,
        skip_missing_videos=args.skip_missing_videos or args.allow_placeholders,
    )
    print(
        f"Wrote {stats['output']} ({stats['bytes']} bytes, "
        f"{stats['slide_count']} slides, placeholders={stats['placeholders']}, "
        f"videos={stats['video_embedded']})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
