#!/usr/bin/env python3
"""Assemble a full-bleed image Keynote via Keynote Creator Studio AppleScript.

Resumes from an existing partial .key when present. Relaunches Keynote on
connection errors (-609).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keynote_health as kh  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_OUT = REPO_ROOT / "output"

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


def run_osascript(script: str, timeout: int = 600) -> tuple[int, str, str]:
    return kh.run_osascript(script, timeout=timeout)


def relaunch_keynote() -> None:
    result = kh.ensure_healthy(max_restarts=2)
    if not result.ok:
        raise RuntimeError(f"Keynote unhealthy: {result.detail}")


def resolve_png(pack: Path, slide: dict) -> Path:
    rel = str(slide.get("png") or "")
    for cand in (
        pack / "pngs" / Path(rel).name,
        pack / "pngs-1080" / Path(rel).name,
        pack / rel,
        pack / "pngs" / rel,
    ):
        if cand.exists() and cand.stat().st_size > 1000:
            return cand
    raise FileNotFoundError(f"missing png for {slide.get('index')} {rel}")


def open_count(out_path: Path) -> int:
    if not out_path.exists() or out_path.stat().st_size < 10_000:
        return 0
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
  open POSIX file "{out_path}"
  delay 3
  set n to count of slides of front document
  return n as text
end tell
''',
        timeout=180,
    )
    if code == 0 and out.isdigit():
        return int(out)
    return 0


def create_new(out_path: Path, first_png: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
  set theDoc to make new document with properties {{document theme:theme "White", width:1920, height:1080}}
  delay 0.5
  tell slide 1 of theDoc
    try
      delete every image
    end try
    try
      delete every text item
    end try
    set img to make new image with properties {{file:POSIX file "{first_png}"}}
    set position of img to {{0, 0}}
    set width of img to 1920
    set height of img to 1080
  end tell
  save theDoc in POSIX file "{out_path}"
  return (count of slides of theDoc) as text
end tell
''',
        timeout=180,
    )
    if code != 0:
        raise RuntimeError(f"create failed: {err or out}")


def append_one(out_path: Path, png: str) -> int:
    code, out, err = run_osascript(
        f'''
tell application "Keynote"
  activate
  set theDoc to missing value
  if (count of documents) > 0 then
    set theDoc to front document
  else
    open POSIX file "{out_path}"
    delay 2
    set theDoc to front document
  end if
  set newSlide to make new slide at end of slides of theDoc with properties {{base slide:master slide "Blank" of theDoc}}
  tell newSlide
    try
      delete every image
    end try
    try
      delete every text item
    end try
    set img to make new image with properties {{file:POSIX file "{png}"}}
    set position of img to {{0, 0}}
    set width of img to 1920
    set height of img to 1080
  end tell
  return (count of slides of theDoc) as text
end tell
''',
        timeout=120,
    )
    if code != 0 or not out.isdigit():
        raise RuntimeError(err or out or "append failed")
    return int(out)


def save_doc(out_path: Path) -> None:
    kh.dismiss_modified_dialogs(timeout=15)
    code, out, err = run_osascript(
        f'''
tell application "Keynote"
  if (count of documents) < 1 then
    open POSIX file "{out_path}"
    delay 2
  end if
  save front document in POSIX file "{out_path}"
end tell
''',
        timeout=90,
    )
    if code != 0:
        kh.dismiss_modified_dialogs(timeout=15)
        code, out, err = run_osascript(
            f'''
tell application "Keynote"
  if (count of documents) < 1 then
    open POSIX file "{out_path}"
    delay 2
  end if
  save front document in POSIX file "{out_path}"
end tell
''',
            timeout=90,
        )
    if code != 0:
        raise RuntimeError(err or out or "save failed")


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
        timeout=180,
    )


def assemble(paths: list[str], out_path: Path, save_every: int = 5) -> None:
    have = open_count(out_path)
    print(f"resume have={have}/{len(paths)}", flush=True)
    if have <= 0:
        relaunch_keynote()
        create_new(out_path, paths[0])
        have = 1
        print("created slides=1", flush=True)
        close_all()
        time.sleep(1)
        open_count(out_path)

    i = have
    failures = 0
    while i < len(paths):
        try:
            n = append_one(out_path, paths[i])
            i = n
            failures = 0
            if i % save_every == 0 or i == len(paths):
                save_doc(out_path)
                print(f"assembled {i}/{len(paths)}", flush=True)
                if i < len(paths) and i % (save_every * 4) == 0:
                    close_all()
                    time.sleep(1)
                    relaunch_keynote()
                    have2 = open_count(out_path)
                    print(f"checkpoint reopen have={have2}", flush=True)
                    i = have2
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"append fail at {i}: {exc}", flush=True)
            kh.dismiss_modified_dialogs(timeout=15)
            try:
                save_doc(out_path)
            except Exception:
                pass
            close_all()
            relaunch_keynote()
            have = open_count(out_path)
            print(f"reopened have={have}", flush=True)
            i = have
            if failures >= 8:
                raise RuntimeError(f"too many failures near slide {i}")
            time.sleep(1)
    save_doc(out_path)
    close_all()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=sorted(COURSE), required=True)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--save-every", type=int, default=5)
    args = ap.parse_args()
    lang = args.lang.strip().lower()
    cfg = COURSE[args.type]
    # Full-pack readiness before Keynote (map / videos / capture pack).
    sys.path.insert(0, str(REPO_ROOT))
    from zume_assets.lang_prereqs import (  # noqa: E402
        blocking_issues,
        check_build_readiness,
        format_prereq_report,
    )

    issues = check_build_readiness(lang, mode="full", course_type=args.type)
    blocked = blocking_issues(issues)
    if blocked:
        raise SystemExit(
            format_prereq_report(lang, issues, aborted=True, mode="full").rstrip()
            + "\nKeynote assemble aborted."
        )

    pack = pack_dir(lang, args.type)
    stem = cfg["stem"].format(lang=lang)
    manifest_path = pack / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(
            f"Missing presenter capture pack for {lang}/{args.type}: {manifest_path}. "
            "Capture via slides/capture/capture_presenter.py. "
            f"Packs live at build/{lang}/captures/{args.type}/. "
            f"Also run: python3 -m zume_assets prereqs --lang {lang}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    slides = list(manifest.get("slides") or [])
    paths = [str(resolve_png(pack, s)) for s in slides]
    out = pack / "work" / f"{stem}-images.key"
    health = kh.ensure_healthy()
    if not health.ok:
        raise SystemExit(f"Keynote unhealthy before assemble: {health.detail}")
    print(f"building {out} from {len(paths)} pngs", flush=True)
    assemble(paths, out, save_every=args.save_every)
    code, out_s, err = run_osascript(
        f'''
tell application "Keynote"
  if (count of documents) < 1 then
    open POSIX file "{out}"
    delay 2
  end if
  set n to count of slides of front document
  save front document in POSIX file "{out}"
  return n as text
end tell
''',
        timeout=300,
    )
    print(f"verify slides={out_s} code={code} err={err}", flush=True)
    if not (out_s.isdigit() and int(out_s) == len(paths)):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
