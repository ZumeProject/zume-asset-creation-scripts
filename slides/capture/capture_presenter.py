#!/usr/bin/env python3
"""Capture presenter slides for course type 10/20/intensive.

Production Keynote packs must be captured from https://zume.training so QR
payloads bake production hosts (not localhost). Local zume6 is only for
dev/smoke captures with --allow-localhost.

Writes a pack under the repo working tree:
  build/{lang}/captures/{10|20|intensive}/
  videos/ is a symlink to build/{lang}/videos (one MP4 set per language).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
# Course structure lives in this repo. Presenter slide keys are derived from
# those manifests (overrideKey, or t{videoKey}_a/_b for watch/video). Each
# session also ends with the live presenter's closing "final" slide, and the
# 10-session course adds "congratulations" when the manifest does not.
MANIFEST_FILES = {
    "10": "ten_session.json",
    "20": "twenty_session.json",
    "intensive": "intensive_session.json",
}
# Production default — localhost presenter QRs encode http://localhost:3000/app/qr/...
# which then get baked into Keynote. Use --allow-localhost only for local smoke tests.
PROD_BASE = "https://zume.training"
BASE_DEFAULT = os.environ.get("PRESENTER_BASE_URL", PROD_BASE).rstrip("/")
VIEWPORT = {"width": 1920, "height": 1080}
DEVICE_SCALE = 2
_NONPROD_HOST_RE = re.compile(
    r"^(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::\d+)?$", re.IGNORECASE
)

COURSE = {
    "10": {
        "type_param": "10",
        "label": "10-Session",
    },
    "20": {
        "type_param": "20",
        "label": "20-Session",
    },
    "intensive": {
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


def presenter_slide_key(slide: dict) -> str:
    """Presenter query key for one manifest slide."""
    override = slide.get("overrideKey")
    if override:
        return str(override)
    stype = slide.get("type") or ""
    if stype == "watch":
        return f"t{slide['videoKey']}_a"
    if stype == "video":
        return f"t{slide['videoKey']}_b"
    if stype == "break":
        return "break"
    raise ValueError(f"Cannot derive a presenter slide key from {slide!r}")


def load_presenter_sessions(course_type: str, root: Path | None = None) -> list[list[dict]]:
    """Slide lists for one course, in presenter order, from ``manifest/``."""
    name = MANIFEST_FILES[course_type]
    path = (root or REPO_ROOT) / "manifest" / name
    sessions = json.loads(path.read_text(encoding="utf-8"))
    out: list[list[dict]] = []
    last = len(sessions) - 1
    for index, session in enumerate(sessions):
        slides: list[dict] = []
        for slide in session.get("slides") or []:
            slides.append(
                {
                    "key": presenter_slide_key(slide),
                    "type": slide.get("type") or "",
                    "videoKey": slide.get("videoKey"),
                }
            )
        keys = [s["key"] for s in slides]
        if index == last and "congratulations" not in keys:
            slides.append({"key": "congratulations", "type": "congratulations"})
        slides.append({"key": "final", "type": "final"})
        out.append(slides)
    return out


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
    sessions = load_presenter_sessions(course_type)
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


def is_nonprod_base(base: str) -> bool:
    """True when the presenter origin would bake non-production QR hosts."""
    host = urlparse(base.rstrip("/") + "/").hostname or ""
    if not host:
        return True
    if _NONPROD_HOST_RE.match(host):
        return True
    return host.endswith(".local")


def decode_qr_payloads(png: Path) -> list[str]:
    """Decode QR payloads from a PNG via zbarimg when available."""
    try:
        out = subprocess.check_output(
            ["zbarimg", "-q", "--raw", str(png)],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def invalidate_nonprod_qr_pngs(png_dir: Path, items: list[dict]) -> list[str]:
    """Delete PNGs whose decoded QR payload points at a non-production host.

    Returns invalidated slide keys so capture will re-fetch them.
    """
    invalidated: list[str] = []
    for item in items:
        dest = png_dir / item["png"]
        if not dest.exists():
            continue
        payloads = decode_qr_payloads(dest)
        if not payloads:
            continue
        bad = False
        for payload in payloads:
            host = urlparse(payload).hostname or ""
            # Production packs must encode zume.training only.
            if host != "zume.training":
                bad = True
                break
        if not bad:
            continue
        dest.unlink()
        item["status"] = "pending"
        item["bytes"] = None
        item["captured_at"] = None
        invalidated.append(str(item.get("key") or item["png"]))
    return invalidated


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
    parser.add_argument(
        "--base",
        default=BASE_DEFAULT,
        help=f"Presenter origin (default: {BASE_DEFAULT} / $PRESENTER_BASE_URL)",
    )
    parser.add_argument(
        "--allow-localhost",
        action="store_true",
        help="Allow http://localhost:3000 (or similar) for local smoke captures only",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-capture every slide even when a PNG already exists",
    )
    parser.add_argument(
        "--invalidate-nonprod-qr",
        action="store_true",
        help="Delete PNGs whose QR payload is not https://zume.training/… before capture",
    )
    parser.add_argument("--limit", type=int, default=0, help="Capture only first N (smoke)")
    args = parser.parse_args(argv)

    base = args.base.rstrip("/")
    if is_nonprod_base(base) and not args.allow_localhost:
        raise SystemExit(
            f"Refusing non-production presenter base {base!r}. "
            f"Capture production packs from {PROD_BASE} "
            "(or pass --allow-localhost for local smoke tests only)."
        )

    lang = args.lang.strip().lower()
    meta = COURSE[args.type]
    from zume_assets.paths import capture_pack_dir, ensure_capture_videos_link, videos_dir

    cap = capture_pack_dir(lang, args.type)
    ensure_capture_videos_link(cap, videos_dir(lang))
    png_dir = cap / "pngs"
    png_dir.mkdir(parents=True, exist_ok=True)
    (cap / "work").mkdir(parents=True, exist_ok=True)

    items = build_items(args.type, base, lang)
    if args.limit > 0:
        items = items[: args.limit]

    if args.invalidate_nonprod_qr:
        dropped = invalidate_nonprod_qr_pngs(png_dir, items)
        print(
            f"invalidate-nonprod-qr removed {len(dropped)} PNG(s): "
            f"{', '.join(dropped[:20])}{'…' if len(dropped) > 20 else ''}",
            flush=True,
        )

    for item in items:
        dest = png_dir / item["png"]
        if args.force and dest.exists():
            dest.unlink()
            item["status"] = "pending"
            item["bytes"] = None
            item["captured_at"] = None
            continue
        if dest.exists() and dest.stat().st_size > 5000:
            item["status"] = "done"
            item["bytes"] = dest.stat().st_size
            item["captured_at"] = item.get("captured_at") or "existing"

    write_manifest(
        cap, items, base=base, course_type=args.type, lang=lang, phase="resume"
    )
    first_missing = next((i["index"] for i in items if i["status"] != "done"), None)
    print(
        f"{lang} {meta['label']} base={base} resume first_missing={first_missing} "
        f"done={sum(1 for i in items if i['status']=='done')}/{len(items)} → {png_dir}",
        flush=True,
    )

    # Lazy import so unit tests can load helpers without Playwright installed (CI).
    from playwright.sync_api import sync_playwright

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
                base=base,
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
        cap, items, base=base, course_type=args.type, lang=lang, phase="complete"
    )
    print(
        f"DONE {lang} {meta['label']} captured="
        f"{sum(1 for i in items if i['status']=='done')}/{len(items)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
