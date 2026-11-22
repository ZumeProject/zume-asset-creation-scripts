#!/usr/bin/env python3
"""Embed MP4s into a Keynote via Insert > Choose File (Creator Studio).

Generalized from the EN10 driver. Expects:
  pack/work/<stem>-images.key  (or --doc)
  pack/manifest.json with kind/type=video slides
  pack/videos/<id>.mp4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keynote_health as kh  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_OUT = REPO_ROOT / "output"
VIDEO_ICON = REPO_ROOT / "slides" / "assets" / "video-play-icon.png"
# Match left inset to the tight top margin so the icon sits balanced in the corner.
VIDEO_ICON_X = 5
VIDEO_ICON_Y = 5
VIDEO_ICON_SIZE = 113

COURSE = {
    "10": {"stem": "Zume-Training-10-Session-{lang}", "expected_slides": 189},
    "20": {"stem": "Zume-Training-20-Session-{lang}", "expected_slides": 268},
    "intensive": {"stem": "Zume-Training-Intensive-{lang}", "expected_slides": 158},
}


def pack_dir(lang: str, course_type: str) -> Path:
    sys.path.insert(0, str(REPO_ROOT))
    from zume_assets.paths import capture_pack_dir, ensure_capture_videos_link, videos_dir

    pack = capture_pack_dir(lang, course_type, REPO_ROOT)
    ensure_capture_videos_link(pack, videos_dir(lang, REPO_ROOT))
    return pack


def log(path: Path, msg: str) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
    print(msg, flush=True)


def run_osascript(script: str, timeout: int = 180) -> tuple[int, str, str]:
    return kh.run_osascript(script, timeout=timeout)


def dismiss_ui() -> None:
    # Prefer Save Anyway over Escape so unattended builds keep the deck.
    kh.dismiss_modified_dialogs(timeout=15)
    run_osascript(
        '''
tell application "System Events"
  if exists process "Keynote" then
    tell process "Keynote"
      set frontmost to true
      repeat 4 times
        key code 53
        delay 0.12
      end repeat
    end tell
  end if
end tell
''',
        timeout=20,
    )


def package_mp4_names(doc: Path) -> list[str]:
    if not doc.exists():
        return []
    try:
        with zipfile.ZipFile(doc) as z:
            return [n for n in z.namelist() if n.lower().endswith(".mp4")]
    except Exception:
        return []


def movie_count(doc_name: str, expected: int, slide_index: int) -> int:
    script = f'''
tell application "Keynote"
  set targetDoc to missing value
  repeat with d in documents
    set nm to name of d as text
    try
      set sc to count of slides of d
      if sc is {expected} then set targetDoc to d
    end try
    if nm contains "{doc_name}" then set targetDoc to d
  end repeat
  if targetDoc is missing value then return "-1"
  return (count of movies of slide {slide_index} of targetDoc) as text
end tell
'''
    code, out, err = run_osascript(script, timeout=60)
    if code == 0 and out.lstrip("-").isdigit():
        return int(out)
    return -1


def open_doc(doc: Path, expected: int, doc_name: str, logf: Path) -> None:
    dismiss_ui()
    run_osascript(
        '''
tell application "Keynote"
  activate
  try
    repeat with d in (get documents)
      try
        close d saving no
      end try
    end repeat
  end try
end tell
''',
        timeout=60,
    )
    time.sleep(1)
    script = f'''
tell application "Keynote"
  activate
  open POSIX file "{doc}"
  delay 6
  set targetDoc to missing value
  repeat with d in documents
    set nm to name of d as text
    if nm contains "{doc_name}" then set targetDoc to d
  end repeat
  if targetDoc is missing value then
    repeat with d in documents
      try
        if (count of slides of d) is {expected} then set targetDoc to d
      end try
    end repeat
  end if
  if targetDoc is missing value then error "target not open"
  return (count of slides of targetDoc) as text
end tell
'''
    code, out, err = run_osascript(script, timeout=180)
    if code != 0 or not out.isdigit() or int(out) != expected:
        raise RuntimeError(f"open failed: {code} {out} {err}")
    log(logf, f"opened slides={out}")


def embed_one(
    *,
    doc: Path,
    doc_name: str,
    expected: int,
    slide_index: int,
    mp4: Path,
    logf: Path,
) -> bool:
    prep = f'''
tell application "Keynote"
  activate
  set targetDoc to missing value
  repeat with d in documents
    set nm to name of d as text
    try
      if (count of slides of d) is {expected} then set targetDoc to d
    end try
    if nm contains "{doc_name}" then set targetDoc to d
  end repeat
  if targetDoc is missing value then error "no target"
  set current slide of targetDoc to slide {slide_index} of targetDoc
  tell slide {slide_index} of targetDoc
    try
      delete every image
    end try
    try
      delete every movie
    end try
  end tell
end tell
'''
    code, out, err = run_osascript(prep, timeout=60)
    if code != 0:
        log(logf, f"prep fail slide={slide_index}: {err or out}")
        return False
    time.sleep(0.4)
    clip = subprocess.run(["pbcopy"], input=str(mp4), text=True, capture_output=True)
    if clip.returncode != 0:
        log(logf, f"pbcopy fail slide={slide_index}")
        return False
    dismiss_ui()
    choose = '''
tell application "Keynote" to activate
delay 0.4
tell application "System Events"
  tell process "Keynote"
    set frontmost to true
    click menu item "Choose File" of menu "Insert" of menu bar 1
  end tell
end tell
delay 1.4
tell application "System Events"
  keystroke "g" using {command down, shift down}
end tell
delay 0.9
tell application "System Events"
  keystroke "a" using {command down}
  delay 0.15
  keystroke "v" using {command down}
  delay 0.35
  keystroke return
end tell
delay 1.0
tell application "System Events"
  keystroke return
end tell
'''
    code, out, err = run_osascript(choose, timeout=90)
    if code != 0:
        log(logf, f"choose fail slide={slide_index}: {err or out}")
        dismiss_ui()
        return False
    time.sleep(1.0)
    run_osascript('tell application "System Events" to keystroke return', timeout=10)
    mb = max(1.0, mp4.stat().st_size / (1024 * 1024))
    wait_s = int(min(120, max(8, mb * 2.5)))
    ok = False
    for i in range(wait_s):
        time.sleep(1)
        if i in (3, 8, 15):
            run_osascript(
                '''
tell application "System Events"
  if exists process "Keynote" then
    tell process "Keynote"
      try
        if (count of sheets of front window) > 0 then keystroke return
      end try
    end tell
  end if
end tell
''',
                timeout=15,
            )
        n = movie_count(doc_name, expected, slide_index)
        if n >= 1:
            ok = True
            break
        if i >= 6 and mp4.name.split(".")[0] in {
            Path(x).name.split("-")[0] for x in package_mp4_names(doc)
        }:
            ok = True
            log(logf, f"package-has {mp4.name} slide={slide_index} t={i}s")
            break
    if not ok:
        log(logf, f"TIMEOUT waiting movie slide={slide_index}")
        dismiss_ui()
        return False
    dismiss_ui()
    size = f'''
tell application "Keynote"
  set targetDoc to missing value
  repeat with d in documents
    set nm to name of d as text
    try
      if (count of slides of d) is {expected} then set targetDoc to d
    end try
    if nm contains "{doc_name}" then set targetDoc to d
  end repeat
  tell slide {slide_index} of targetDoc
    if (count of movies) < 1 then error "no movie"
    set m to movie 1
    set position of m to {{0, 0}}
    set width of m to 1920
    set height of m to 1080
    try
      set movie volume of m to 100
    end try
    -- Restore upper-left video/thumbnail chrome (legacy copy-paste icon).
    set img to make new image with properties {{file:POSIX file "{VIDEO_ICON}"}}
    set position of img to {{{VIDEO_ICON_X}, {VIDEO_ICON_Y}}}
    set width of img to {VIDEO_ICON_SIZE}
    set height of img to {VIDEO_ICON_SIZE}
    return (count of movies) as text
  end tell
end tell
'''
    code, out, err = run_osascript(size, timeout=60)
    if code != 0:
        if mp4.name.split(".")[0] in {
            Path(x).name.split("-")[0] for x in package_mp4_names(doc)
        }:
            log(logf, f"ok-package slide={slide_index} size_err={(err or out)[:120]}")
            return True
        log(logf, f"size fail slide={slide_index}: {err or out}")
        return False
    log(logf, f"ok slide={slide_index} movies={out} file={mp4.name}")
    return True


def save_doc(doc: Path, doc_name: str, expected: int, logf: Path) -> None:
    before = doc.stat().st_size if doc.exists() else 0
    script = f'''
tell application "Keynote"
  set targetDoc to missing value
  repeat with d in documents
    set nm to name of d as text
    try
      if (count of slides of d) is {expected} then set targetDoc to d
    end try
    if nm contains "{doc_name}" then set targetDoc to d
  end repeat
  save targetDoc in POSIX file "{doc}"
end tell
'''
    code, out, err = run_osascript(script, timeout=600)
    after = doc.stat().st_size if doc.exists() else 0
    log(logf, f"save code={code} size={after} delta={after - before} note={(err or out)[:160]}")


def video_list(manifest: dict, pack: Path) -> list[dict]:
    slides = manifest.get("slides") or []
    items = []
    for s in slides:
        kind = s.get("kind")
        stype = s.get("type")
        vid = s.get("video_id") or s.get("video_key")
        key = str(s.get("key") or "")
        if stype == "video" or kind == "video":
            special = {"t10_e": "10", "t10_g": "33"}
            if not vid:
                vid = special.get(key)
            if not vid and key.startswith("t") and key.endswith("_b"):
                mid = key[1:-2]
                if mid.isdigit():
                    vid = mid
            if not vid:
                continue
            mp4 = pack / "videos" / f"{vid}.mp4"
            items.append(
                {
                    "index": int(s["index"]),
                    "key": key,
                    "path": str(mp4),
                    "video_id": str(vid),
                }
            )
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=sorted(COURSE), required=True)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--promote", action="store_true")
    args = ap.parse_args()
    lang = args.lang.strip().lower()
    cfg = COURSE[args.type]
    pack = pack_dir(lang, args.type)
    stem = cfg["stem"].format(lang=lang)
    expected = cfg["expected_slides"]
    images = pack / "work" / f"{stem}-images.key"
    with_videos = pack / "work" / f"{stem}-with-videos.key"
    logf = pack / "work" / "embed-videos.log"
    if not images.exists():
        raise SystemExit(f"missing images deck {images}")
    # Start from a fresh copy so resume skips based on package contents
    if not with_videos.exists() or with_videos.stat().st_size < images.stat().st_size * 0.5:
        subprocess.run(["cp", "-f", str(images), str(with_videos)], check=True)

    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    videos = video_list(manifest, pack)
    (pack / "work" / "video-replace-list.json").write_text(
        json.dumps(videos, indent=2), encoding="utf-8"
    )
    logf.write_text(
        f"EMBED_START {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} "
        f"lang={lang} type={args.type} videos={len(videos)}\n",
        encoding="utf-8",
    )
    if len(videos) != 29:
        log(logf, f"warn expected 29 videos got {len(videos)}")

    if not VIDEO_ICON.exists():
        raise SystemExit(f"missing video icon asset: {VIDEO_ICON}")

    def _log(msg: str) -> None:
        log(logf, msg)

    health = kh.ensure_healthy(log=_log)
    if not health.ok:
        raise SystemExit(f"Keynote unhealthy before embed: {health.detail}")

    doc_name = with_videos.stem
    open_doc(with_videos, expected, doc_name, logf)
    failures: list[int] = []
    for i, item in enumerate(videos, start=1):
        # Periodic health ping — recover instead of hammering a stuck app.
        if i == 1 or i % 4 == 0:
            ping = kh.ping(timeout=12)
            if not ping.ok:
                _log(f"health fail at slide loop i={i}: {ping.detail}")
                try:
                    save_doc(with_videos, doc_name, expected, logf)
                except Exception as exc:  # noqa: BLE001
                    _log(f"save before recovery failed: {exc}")
                recovered = kh.ensure_healthy(log=_log, max_restarts=2)
                if not recovered.ok:
                    failures.append(int(item["index"]))
                    _log("aborting embed loop; Keynote still unhealthy")
                    break
                open_doc(with_videos, expected, doc_name, logf)

        idx = int(item["index"])
        mp4 = Path(item["path"])
        if not mp4.exists() or mp4.stat().st_size < 1000:
            log(logf, f"MISSING mp4 slide={idx} path={mp4}")
            failures.append(idx)
            continue
        existing = movie_count(doc_name, expected, idx)
        pkg_bases = {Path(n).name.split("-")[0] for n in package_mp4_names(with_videos)}
        if existing >= 1 or mp4.name.split(".")[0] in pkg_bases:
            log(
                logf,
                f"skip slide={idx} already movies={existing} "
                f"pkg={'yes' if mp4.name.split('.')[0] in pkg_bases else 'no'}",
            )
            # Still ensure upper-left chrome exists on already-embedded slides.
            # embed_one sizes+icons new inserts; skipped slides get icon via overlay path.
        else:
            ok = embed_one(
                doc=with_videos,
                doc_name=doc_name,
                expected=expected,
                slide_index=idx,
                mp4=mp4,
                logf=logf,
            )
            if not ok:
                time.sleep(1)
                dismiss_ui()
                ping = kh.ping(timeout=10)
                if not ping.ok:
                    _log(f"embed retry after health recovery slide={idx}")
                    kh.ensure_healthy(log=_log, max_restarts=1)
                    open_doc(with_videos, expected, doc_name, logf)
                ok = embed_one(
                    doc=with_videos,
                    doc_name=doc_name,
                    expected=expected,
                    slide_index=idx,
                    mp4=mp4,
                    logf=logf,
                )
            if not ok:
                failures.append(idx)
        if i % 3 == 0 or i == len(videos):
            save_doc(with_videos, doc_name, expected, logf)
            log(
                logf,
                f"hb done={i}/{len(videos)} fails={failures} "
                f"ts={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            )
            time.sleep(0.8)  # gentle pacing

    save_doc(with_videos, doc_name, expected, logf)
    pkg = len(package_mp4_names(with_videos))
    log(logf, f"FINAL package_mp4={pkg} failures={failures} out={with_videos}")
    # Always run icon overlay so skipped-already-embedded slides get chrome too.
    try:
        from overlay_video_icons import main as overlay_main

        overlay_rc = overlay_main(
            [
                "--type",
                args.type,
                "--lang",
                lang,
                "--doc",
                str(with_videos),
            ]
        )
        log(logf, f"overlay_video_icons rc={overlay_rc}")
        if overlay_rc != 0 and not failures:
            return 2
    except Exception as exc:  # noqa: BLE001
        log(logf, f"overlay_video_icons error: {exc}")
        if not failures:
            return 2
    if args.promote and not failures and pkg >= len(videos):
        dest = MAIN_OUT / lang / f"{stem}.key"
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-f", str(with_videos), str(dest)], check=True)
        log(logf, f"promoted {dest} size={dest.stat().st_size}")
    return 0 if not failures and pkg >= len(videos) else 2


if __name__ == "__main__":
    raise SystemExit(main())
