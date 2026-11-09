#!/usr/bin/env python3
"""Bulk-capture EN 10-session presenter slides to ordered PNG pack."""
from __future__ import annotations

import json
import sys
import time
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

PRESENTER_BASE = os.environ.get("PRESENTER_BASE_URL", "http://127.0.0.1:3000").rstrip("/")

# Legacy ordered keys from slide-builder/parts/3-slides-download.py (ten_session)
# Includes per-session `final` plus S10 congratulations → ~189 slides.
TEN_SESSION = {
    "1": ["s1_1_1", "s1_1_2", "s1_1_3", "s1_1_4", "t1_a", "t1_b", "t1_c", "t2_a", "t2_b", "t2_c", "t3_a", "t3_b", "t3_c", "t4_a", "t4_b", "t4_c", "t5_a", "t5_b", "t5_c", "s1_1_20", "s1_1_21", "final"],
    "2": ["s1_2_1", "s1_2_2", "s1_2_3", "s1_2_4", "s1_2_5", "t6_a", "t6_b", "t6_c", "t7_a", "t7_b", "t7_c", "t7_d", "t8_a", "t8_b", "t8_c", "s1_2_6", "s1_2_7", "final"],
    "3": ["s1_3_1", "s1_3_2", "s1_3_3", "s1_3_4", "s1_3_5", "t9_a", "t9_b", "t9_c", "t10_a", "t10_b", "t10_c", "t10_d", "t10_e", "t10_f", "t10_g", "s1_3_8", "t11_a", "t11_b", "t11_c", "t11_d", "s1_3_10", "s1_3_11", "s1_3_12", "final"],
    "4": ["s1_4_1", "s1_4_2", "s1_4_3", "s1_4_4", "s1_4_5", "t12_a", "t12_b", "t12_c", "t13_a", "t13_b", "t13_c", "t14_a", "t14_b", "t14_c", "t15_a", "t15_b", "t15_c", "t16_a", "t16_b", "t16_c", "s1_4_6", "s1_4_7", "final"],
    "5": ["s1_5_1", "s1_5_2", "s1_5_3", "s1_5_4", "s1_5_5", "t17_a", "t17_b", "t18_a", "t18_b", "t18_c", "t19_a", "t17_d", "t17_e", "final"],
    "6": ["s1_6_1", "s1_6_2", "s1_6_3", "s1_6_4", "s1_6_5", "t20_a", "t20_b", "t20_c", "t21_a", "t21_b", "t21_c", "s1_6_6", "s1_6_7", "final"],
    "7": ["s1_7_1", "s1_7_2", "s1_7_3", "s1_7_4", "s1_7_5", "t22_a", "t22_b", "t22_c", "s1_7_6", "s1_7_7", "s1_7_8", "s1_7_9", "final"],
    "8": ["s1_8_1", "s1_8_2", "s1_8_3", "s1_8_4", "s1_8_5", "t23_a", "t23_b", "t23_c", "s1_8_6", "s1_8_7", "s1_8_8", "final"],
    "9": ["s1_9_1", "s1_9_2", "s1_9_3", "s1_9_4", "s1_9_5", "t24_a", "t24_b", "t24_c", "t25_a", "t25_b", "t25_c", "t26_a", "t26_b", "t26_c", "t28_a", "t28_b", "t28_c", "t28_d", "t28_e", "t31_a", "t31_b", "t31_c", "t31_d", "t31_e", "t32_a", "t32_b", "t32_c", "s1_9_9", "s1_9_10", "final"],
    "10": ["s1_10_1", "s1_10_2", "s1_10_3", "s1_10_4", "s1_10_5", "s1_10_6", "t29_a", "t29_b", "t29_c", "t30_a", "t30_b", "t30_c", "t27_a", "t27_b", "t27_c", "s1_10_7", "next_steps", "congratulations", "final"],
}

# Video keys are *_b (type video in course). Match legacy parts/10.json video ids.
# Video ids present in legacy slide-builder/parts/10.json (28 slots; matches reference PPSX)
VIDEO_KEYS = {
    f"t{n}_b"
    for n in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30]
}

HIDE_CSS = """
nav, header, footer,
[class*="PresenterChrome"], [class*="presenter-chrome"],
[class*="SlideControls"], [class*="slide-controls"],
[class*="Toolbar"], [class*="toolbar"],
[class*="BottomBar"], [class*="bottom-bar"],
[class*="TopBar"], [class*="top-bar"],
[class*="progress"], [data-testid*="nav"],
button[aria-label*="Previous"], button[aria-label*="Next"],
button[aria-label*="previous"], button[aria-label*="next"],
[class*="SessionPicker"], [class*="session-picker"],
[class*="KeyboardHints"], [class*="keyboard"],
[class*="FloatingControls"], [class*="floating-controls"]
{ display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
"""

STORE = Path("/cursor/stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/media/en-10-presenter-captures")
PNG_DIR = STORE / "pngs"
MANIFEST = STORE / "manifest.json"
VIEWPORT = {"width": 1846, "height": 1034}
DEVICE_SCALE = 2
GOTO_TIMEOUT_MS = 120_000


def build_slides() -> list[dict]:
    slides = []
    idx = 0
    for session, keys in TEN_SESSION.items():
        for key in keys:
            idx += 1
            video_id = None
            kind = "image"
            if key in VIDEO_KEYS and key.startswith("t") and key.endswith("_b"):
                kind = "video"
                video_id = key[1:-2]  # t12_b -> 12
            slides.append(
                {
                    "index": idx,
                    "session": int(session),
                    "key": key,
                    "kind": kind,
                    "video_id": video_id,
                    "png": f"pngs/{idx:04d}_s{session}_{key}.png",
                    "url": (
                        f"{PRESENTER_BASE}/presenter"
                        f"?session={session}&type=10&view=slideshow&slide={key}"
                    ),
                }
            )
    return slides


def write_manifest(slides: list[dict], captured: int, status: str) -> None:
    payload = {
        "locale": "en",
        "presenter_base": PRESENTER_BASE,
        "course_type": "10",
        "viewport": {**VIEWPORT, "deviceScaleFactor": DEVICE_SCALE},
        "expected_png_px": [VIEWPORT["width"] * DEVICE_SCALE, VIEWPORT["height"] * DEVICE_SCALE],
        "slide_count": len(slides),
        "video_slots": [s for s in slides if s["kind"] == "video"],
        "captured": captured,
        "status": status,
        "slides": slides,
    }
    STORE.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def capture_one(page, slide: dict, out_path: Path) -> None:
    page.goto(slide["url"], wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
    # Wait for slide content — main/article/text; fall back to fixed delay
    try:
        page.wait_for_selector("main, [class*='Slide'], [class*='slide'], article", timeout=30_000)
    except Exception:
        pass
    page.wait_for_timeout(2500)
    page.add_style_tag(content=HIDE_CSS)
    page.wait_for_timeout(200)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out_path), full_page=False, type="png")


def main() -> int:
    slides = build_slides()
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest(slides, 0, "starting")
    print(f"Capturing {len(slides)} slides → {PNG_DIR}", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=DEVICE_SCALE,
        )
        page = context.new_page()

        # One successful probe first
        probe = slides[0]
        probe_path = STORE / probe["png"]
        print(f"PROBE {probe['index']}/{len(slides)} {probe['key']}", flush=True)
        capture_one(page, probe, probe_path)
        if not probe_path.exists() or probe_path.stat().st_size < 10_000:
            print("Probe failed: empty/missing PNG", file=sys.stderr)
            write_manifest(slides, 0, "probe_failed")
            return 1
        print(f"PROBE OK {probe_path} ({probe_path.stat().st_size} bytes)", flush=True)
        slides[0]["captured"] = True
        slides[0]["bytes"] = probe_path.stat().st_size
        write_manifest(slides, 1, "running")

        for slide in slides[1:]:
            out_path = STORE / slide["png"]
            if out_path.exists() and out_path.stat().st_size > 10_000:
                print(f"SKIP {slide['index']}/{len(slides)} {slide['key']}", flush=True)
                slide["captured"] = True
                slide["bytes"] = out_path.stat().st_size
                write_manifest(slides, slide["index"], "running")
                continue
            print(f"CAP {slide['index']}/{len(slides)} {slide['key']}", flush=True)
            for attempt in range(1, 4):
                try:
                    capture_one(page, slide, out_path)
                    if out_path.exists() and out_path.stat().st_size > 10_000:
                        break
                except Exception as exc:
                    print(f"  attempt {attempt} failed: {exc}", flush=True)
                    time.sleep(2)
            else:
                print(f"FAIL {slide['key']}", flush=True)
                write_manifest(slides, slide["index"] - 1, f"failed_at_{slide['key']}")
                return 1
            slide["captured"] = True
            slide["bytes"] = out_path.stat().st_size
            write_manifest(slides, slide["index"], "running")

        browser.close()

    write_manifest(slides, len(slides), "complete")
    print(f"DONE {len(slides)} slides", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
