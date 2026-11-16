#!/usr/bin/env python3
"""Capture presenter slides for course type 10/20/intensive from local zume6.

Writes a pack under the Project Agent Store media/ tree:
  media/{lang}-{10|20|intensive}-presenter-captures/
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

STORE = Path(
    "/Users/chris/Library/Application Support/Cursor/AgentStores/"
    "cursor_agent_stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/files"
)
SESSIONS_DIR = Path(
    "/Users/chris/Documents/ZUME/zume6/platform/docs/core/sessions"
)
# Prefer hostname "localhost" — Next.js 16 blocks 127.0.0.1 for HMR/dev assets
# unless allowedDevOrigins is set, which leaves the presenter stuck on Loading.
BASE_DEFAULT = "http://localhost:3000"
VIEWPORT = {"width": 1920, "height": 1080}
DEVICE_SCALE = 2

COURSE = {
    "10": {
        "sessions": "10session.json",
        "type_param": "10",
        "label": "10-Session",
    },
    "20": {
        "sessions": "20session.json",
        "type_param": "20",
        "label": "20-Session",
    },
    "intensive": {
        "sessions": "intensive.json",
        "type_param": "intensive",
        "label": "Intensive",
    },
}

HIDE_CSS = """
.hamburger-menu-btn,
.navigation-controls,
.nav-arrow,
.pill-progress-container,
[data-tour="progress-bar"],
#dev-feedback-bubble,
[data-feedback-bubble],
iframe[title*='feedback' i],
[id*='cookie' i],
[class*='Cookie'],
nextjs-portal,
[data-nextjs-toast],
[data-nextjs-toast-wrapper],
[data-next-mark],
[data-next-badge],
[data-nextjs-dev-indicator],
#__next-build-watcher {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
"""

HIDE_INIT_JS = """
() => {
  const kill = () => {
    const selectors = [
      '.hamburger-menu-btn',
      '.navigation-controls',
      '.nav-arrow',
      '.pill-progress-container',
      '[data-tour="progress-bar"]',
      'nextjs-portal',
      '[data-nextjs-toast]',
      '[data-next-mark]',
      '[data-next-badge]',
      '[data-nextjs-dev-indicator]',
      '#__next-build-watcher',
    ];
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        try { el.remove(); } catch (_) {
          el.style.setProperty('display', 'none', 'important');
        }
      });
    }
    for (const el of document.querySelectorAll('button,div,a,span')) {
      const s = getComputedStyle(el);
      if (s.position !== 'fixed') continue;
      const r = el.getBoundingClientRect();
      const t = (el.innerText || '').trim();
      if (
        r.width > 0 &&
        r.height > 0 &&
        r.left < 120 &&
        r.bottom > window.innerHeight - 120 &&
        r.width <= 80 &&
        r.height <= 80 &&
        (t === 'N' || t === '' || t.length <= 2)
      ) {
        el.style.setProperty('display', 'none', 'important');
      }
    }
  };
  const start = () => {
    kill();
    try {
      new MutationObserver(kill).observe(document.documentElement, {
        childList: true,
        subtree: true,
      });
    } catch (_) {}
    setInterval(kill, 400);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}
"""


def pack_name(lang: str, course_type: str) -> str:
    return f"{lang}-{course_type}-presenter-captures"


def video_id_for(slide: dict) -> str | None:
    """Derive tN_b → N; specials t10_e/t10_g. Prefer key over alt_video_id."""
    if (slide.get("type") or "") != "video":
        return None
    key = slide.get("key") or ""
    special = {"t10_e": "10", "t10_g": "33"}
    if key in special:
        return special[key]
    if key.startswith("t") and key.endswith("_b"):
        mid = key[1:-2]
        if mid.isdigit():
            return mid
    alt = slide.get("alt_video_id")
    if alt is not None:
        return str(alt)
    return None


def build_items(course_type: str, base: str, lang: str) -> list[dict]:
    meta = COURSE[course_type]
    sessions = json.loads((SESSIONS_DIR / meta["sessions"]).read_text(encoding="utf-8"))
    items: list[dict] = []
    idx = 0
    root = base.rstrip("/")
    for session_num, slides in enumerate(sessions, start=1):
        for slide in slides:
            idx += 1
            key = slide["key"]
            stype = slide.get("type") or ""
            vid = video_id_for(slide)
            items.append(
                {
                    "index": idx,
                    "session": session_num,
                    "key": key,
                    "type": stype,
                    "kind": "video" if vid else "image",
                    "video_key": vid,
                    "video_id": vid,
                    "url": (
                        f"{root}/{lang}/presenter?session={session_num}"
                        f"&type={meta['type_param']}&view=slideshow&slide={key}"
                    ),
                    "png": f"{idx:03d}_{key}.png",
                    "mp4": f"{vid}.mp4" if vid else None,
                    "status": "pending",
                    "captured_at": None,
                    "bytes": None,
                }
            )
    return items


def write_manifest(
    cap: Path, items: list[dict], *, base: str, course_type: str, lang: str, **extra
) -> None:
    have = sum(1 for i in items if i.get("status") == "done")
    payload = {
        "locale": lang,
        "base": base,
        "presenter_base": base,
        "course_type": course_type,
        "viewport": {**VIEWPORT, "deviceScaleFactor": DEVICE_SCALE},
        "expected_png_px": [VIEWPORT["width"] * DEVICE_SCALE, VIEWPORT["height"] * DEVICE_SCALE],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "slide_count": len(items),
        "done": have,
        "remaining": len(items) - have,
        "video_slots": [s for s in items if s.get("kind") == "video"],
        **extra,
        "slides": items,
    }
    (cap / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def capture_one(page, item: dict, dest: Path, retries: int = 2) -> None:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            page.goto(item["url"], wait_until="domcontentloaded", timeout=90000)
            page.wait_for_function(
                "() => !document.body.innerText.includes('Loading course content')",
                timeout=60000,
            )
            page.wait_for_selector(".slide-container", timeout=45000)
            page.wait_for_timeout(1100 if item["kind"] == "image" else 700)
            page.add_style_tag(content=HIDE_CSS)
            page.evaluate(
                """() => {
                  document.querySelectorAll(
                    '.pill-progress-container,[data-tour="progress-bar"],nextjs-portal,[data-next-mark],[data-next-badge],[data-nextjs-dev-indicator],#__next-build-watcher'
                  ).forEach((el) => { try { el.remove(); } catch (_) {} });
                }"""
            )
            page.wait_for_timeout(150)
            page.screenshot(path=str(dest), full_page=False)
            if dest.stat().st_size < 5000:
                raise RuntimeError(f"screenshot too small: {dest.stat().st_size}")
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"failed {item['key']}: {last_err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=sorted(COURSE), required=True)
    parser.add_argument("--lang", default="en", help="Locale code (en, ky, ms, …)")
    parser.add_argument("--base", default=BASE_DEFAULT)
    parser.add_argument("--limit", type=int, default=0, help="Capture only first N (smoke)")
    args = parser.parse_args(argv)

    lang = args.lang.strip().lower()
    meta = COURSE[args.type]
    cap = STORE / "media" / pack_name(lang, args.type)
    png_dir = cap / "pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    (cap / "videos").mkdir(parents=True, exist_ok=True)
    (cap / "work").mkdir(parents=True, exist_ok=True)

    items = build_items(args.type, args.base.rstrip("/"), lang)
    if args.limit > 0:
        items = items[: args.limit]

    for item in items:
        dest = png_dir / item["png"]
        if dest.exists() and dest.stat().st_size > 5000:
            item["status"] = "done"
            item["bytes"] = dest.stat().st_size
            item["captured_at"] = item.get("captured_at") or "existing"

    write_manifest(
        cap, items, base=args.base.rstrip("/"), course_type=args.type, lang=lang, phase="resume"
    )
    first_missing = next((i["index"] for i in items if i["status"] != "done"), None)
    print(
        f"{lang} {meta['label']} resume first_missing={first_missing} "
        f"done={sum(1 for i in items if i['status']=='done')}/{len(items)} → {png_dir}",
        flush=True,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=DEVICE_SCALE)
        context.add_init_script(HIDE_INIT_JS)
        page = context.new_page()
        for item in items:
            dest = png_dir / item["png"]
            if item["status"] == "done":
                print(f"skip {item['index']:03d}/{len(items)} {item['key']}", flush=True)
                continue
            t0 = time.time()
            capture_one(page, item, dest)
            item["status"] = "done"
            item["bytes"] = dest.stat().st_size
            item["captured_at"] = datetime.now(timezone.utc).isoformat()
            write_manifest(
                cap,
                items,
                base=args.base.rstrip("/"),
                course_type=args.type,
                lang=lang,
                phase="capturing",
                last_key=item["key"],
            )
            print(
                f"ok {item['index']:03d}/{len(items)} {item['key']} "
                f"{dest.stat().st_size}b {time.time()-t0:.1f}s",
                flush=True,
            )
        browser.close()

    write_manifest(
        cap, items, base=args.base.rstrip("/"), course_type=args.type, lang=lang, phase="complete"
    )
    print(
        f"DONE {lang} {meta['label']} captured="
        f"{sum(1 for i in items if i['status']=='done')}/{len(items)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
