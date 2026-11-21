#!/usr/bin/env python3
"""Restore upper-left video/thumbnail chrome on Keynote video slides.

Part of the normal Keynote assemble path: `embed_videos_choose.py` calls this
after MP4 embeds so every language/course rebuild gets the play-icon chrome.
Also usable alone to backfill an existing with-videos `.key`.

Uses keynote_health to ping/quit/relaunch instead of hammering a stuck app.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keynote_health as kh  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ICON = REPO_ROOT / "slides" / "assets" / "video-play-icon.png"
MAIN_OUT = REPO_ROOT / "output"

# Tight upper-left corner on a 1920×1080 slide (left inset matches top).
ICON_X = 5
ICON_Y = 5
ICON_SIZE = 113

COURSE = {
    "10": {"stem": "Zume-Training-10-Session-{lang}", "expected": 189},
    "20": {"stem": "Zume-Training-20-Session-{lang}", "expected": 268},
    "intensive": {"stem": "Zume-Training-Intensive-{lang}", "expected": 158},
}


def pack_dir(lang: str, course_type: str) -> Path:
    sys.path.insert(0, str(REPO_ROOT))
    from zume_assets.paths import capture_pack_dir, ensure_capture_videos_link, videos_dir

    pack = capture_pack_dir(lang, course_type, REPO_ROOT)
    ensure_capture_videos_link(pack, videos_dir(lang, REPO_ROOT))
    return pack


def run_osascript(script: str, timeout: int = 90) -> tuple[int, str, str]:
    return kh.run_osascript(script, timeout=timeout)


def video_indexes(manifest: dict) -> list[int]:
    items: list[int] = []
    special = {"t10_e": "10", "t10_g": "33"}
    for s in manifest.get("slides") or []:
        kind = s.get("kind")
        stype = s.get("type")
        key = str(s.get("key") or "")
        vid = s.get("video_id") or s.get("video_key")
        if stype == "video" or kind == "video" or key in special:
            if not vid:
                vid = special.get(key)
            if not vid and key.startswith("t") and key.endswith("_b"):
                mid = key[1:-2]
                if mid.isdigit():
                    vid = mid
            if vid:
                items.append(int(s["index"]))
    return items


def open_doc(doc: Path, expected: int) -> None:
    code, out, err = run_osascript(
        f'''
tell application "Keynote"
  activate
  try
    repeat with d in (get documents)
      try
        close d saving no
      end try
    end repeat
  end try
  open POSIX file "{doc}"
  delay 5
  set n to count of slides of front document
  if n is not {expected} then error "slide count " & n
  return n as text
end tell
''',
        timeout=120,
    )
    if code != 0:
        raise RuntimeError(f"open failed: {err or out}")


def image_count(slide_index: int) -> int:
    code, out, _ = run_osascript(
        f'''
tell application "Keynote"
  return (count of images of slide {slide_index} of front document) as text
end tell
''',
        timeout=30,
    )
    return int(out) if code == 0 and out.isdigit() else -1


def ensure_icon(slide_index: int) -> str:
    """Return 'ok', 'moved', or 'fail'. Repositions an existing corner icon."""
    code, out, err = run_osascript(
        f'''
tell application "Keynote"
  tell slide {slide_index} of front document
    set targetImg to missing value
    repeat with im in images
      try
        set p to position of im
        set w to width of im
        if (item 1 of p) < 500 and (item 2 of p) < 200 and w <= 200 then
          set targetImg to im
        end if
      end try
    end repeat
    if targetImg is not missing value then
      set position of targetImg to {{{ICON_X}, {ICON_Y}}}
      set width of targetImg to {ICON_SIZE}
      set height of targetImg to {ICON_SIZE}
      return "moved"
    end if
    set img to make new image with properties {{file:POSIX file "{ICON}"}}
    set position of img to {{{ICON_X}, {ICON_Y}}}
    set width of img to {ICON_SIZE}
    set height of img to {ICON_SIZE}
    return "ok"
  end tell
end tell
''',
        timeout=45,
    )
    if code != 0:
        print(f"fail slide={slide_index}: {err or out}", flush=True)
        return "fail"
    print(f"{out} slide={slide_index} images={image_count(slide_index)}", flush=True)
    return out if out in {"ok", "moved"} else "fail"


def save_doc(doc: Path) -> None:
    run_osascript(
        f'''
tell application "Keynote"
  save front document in POSIX file "{doc}"
end tell
''',
        timeout=180,
    )


def close_all() -> None:
    run_osascript(
        '''
tell application "Keynote"
  try
    repeat with d in (get documents)
      try
        close d saving yes
      end try
    end repeat
  end try
end tell
''',
        timeout=90,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--type", choices=sorted(COURSE), required=True)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--doc", type=Path, default=None)
    ap.add_argument("--promote", action="store_true")
    args = ap.parse_args(argv)

    if not ICON.exists():
        raise SystemExit(f"missing icon asset: {ICON}")

    lang = args.lang.strip().lower()
    cfg = COURSE[args.type]
    pack = pack_dir(lang, args.type)
    stem = cfg["stem"].format(lang=lang)
    expected = cfg["expected"]
    doc = args.doc or (pack / "work" / f"{stem}-with-videos.key")
    if not doc.exists():
        raise SystemExit(f"missing keynote: {doc}")

    def _log(msg: str) -> None:
        print(msg, flush=True)

    health = kh.ensure_healthy(log=_log)
    if not health.ok:
        print(f"Keynote unhealthy: {health.detail}", flush=True)
        return 2

    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    indexes = video_indexes(manifest)
    print(f"overlay icons={len(indexes)} doc={doc}", flush=True)
    open_doc(doc, expected)
    failures: list[int] = []
    for i, idx in enumerate(indexes, start=1):
        if i == 1 or i % 5 == 0:
            ping = kh.ping(timeout=12)
            if not ping.ok:
                _log(f"health fail before slide={idx}: {ping.detail}")
                try:
                    save_doc(doc)
                except Exception as exc:  # noqa: BLE001
                    _log(f"save before recovery failed: {exc}")
                recovered = kh.ensure_healthy(log=_log, max_restarts=2)
                if not recovered.ok:
                    failures.append(idx)
                    _log("aborting overlay; Keynote still unhealthy")
                    break
                open_doc(doc, expected)

        status = ensure_icon(idx)
        if status == "fail":
            # One gentle retry after health check
            time.sleep(1.0)
            if not kh.ping(timeout=10).ok:
                kh.ensure_healthy(log=_log, max_restarts=1)
                open_doc(doc, expected)
            status = ensure_icon(idx)
        if status == "fail":
            failures.append(idx)
        if i % 5 == 0 or i == len(indexes):
            save_doc(doc)
            time.sleep(1.0)  # gentle pacing — avoid locking Keynote
    try:
        save_doc(doc)
        close_all()
    except Exception as exc:  # noqa: BLE001
        _log(f"final save/close: {exc}")
        kh.kill_osascript()
    if failures:
        print(f"FAILED slides={failures}", flush=True)
        return 2
    if args.promote:
        dest = MAIN_OUT / lang / f"{stem}.key"
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-f", str(doc), str(dest)], check=True)
        print(f"promoted {dest} size={dest.stat().st_size}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
