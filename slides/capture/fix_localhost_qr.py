#!/usr/bin/env python3
"""Rewrite localhost QR payloads in presenter capture PNGs to zume.training.

Keynote/PPTX decks assemble from capture packs under ``build/{lang}/captures/{type}/``.
Those packs were often screenshot from ``http://localhost:3000``, so QR codes in
the PNGs encode localhost. Typst PDF QRs (``zume_assets.qr``) are already production.

Requires system ``zbarimg`` (Homebrew ``zbar``) for decode + bounding box.

Examples::

    python3 slides/capture/fix_localhost_qr.py --audit
    python3 slides/capture/fix_localhost_qr.py --lang pus --apply
    python3 slides/capture/fix_localhost_qr.py --apply
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from zume_assets.qr import SITE, make_qr_png, rewrite_localhost_qr_url  # noqa: E402

DEFAULT_BUILD = REPO_ROOT / "build"

COURSE_TYPES = ("10", "20", "intensive")
_POLYGON_RE = re.compile(
    r"^\+(?P<x1>\d+),\+(?P<y1>\d+)\s+\+(?P<x2>\d+),\+(?P<y2>\d+)\s+"
    r"\+(?P<x3>\d+),\+(?P<y3>\d+)\s+\+(?P<x4>\d+),\+(?P<y4>\d+):(?P<payload>.*)$"
)


@dataclass
class QrHit:
    path: Path
    payload: str
    rewritten: str
    box: tuple[int, int, int, int]  # left, top, right, bottom


def pack_dir(build_root: Path, lang: str, course_type: str) -> Path:
    return build_root / lang / "captures" / course_type


def discover_langs(build_root: Path) -> list[str]:
    if not build_root.is_dir():
        return []
    langs: list[str] = []
    for path in sorted(build_root.iterdir()):
        if not path.is_dir() or path.name in {"reference", "legacy"}:
            continue
        captures = path / "captures"
        if not captures.is_dir():
            continue
        if any((captures / course_type).is_dir() for course_type in COURSE_TYPES):
            langs.append(path.name)
    return langs


def _require_zbarimg() -> str:
    path = shutil.which("zbarimg")
    if not path:
        raise SystemExit(
            "zbarimg not found on PATH. Install with: brew install zbar"
        )
    return path


def scan_png(path: Path) -> list[QrHit]:
    """Return localhost QR hits on one PNG (may be empty)."""
    zbar = _require_zbarimg()
    result = subprocess.run(
        [zbar, "--quiet", "--polygon", "--raw", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    hits: list[QrHit] = []
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        match = _POLYGON_RE.match(line)
        if not match:
            # Fallback: raw payload only (no box) — skip apply for this symbol
            payload = line
            rewritten = rewrite_localhost_qr_url(payload)
            if rewritten:
                raise SystemExit(
                    f"zbarimg returned payload without polygon for {path}: {payload!r}"
                )
            continue
        payload = match.group("payload").strip()
        rewritten = rewrite_localhost_qr_url(payload)
        if not rewritten:
            continue
        xs = [int(match.group(g)) for g in ("x1", "x2", "x3", "x4")]
        ys = [int(match.group(g)) for g in ("y1", "y2", "y3", "y4")]
        pad = 4
        box = (
            max(0, min(xs) - pad),
            max(0, min(ys) - pad),
            max(xs) + pad,
            max(ys) + pad,
        )
        hits.append(QrHit(path=path, payload=payload, rewritten=rewritten, box=box))
    return hits


def patch_png(hit: QrHit, *, dry_run: bool = False) -> None:
    left, top, right, bottom = hit.box
    width = max(8, right - left)
    height = max(8, bottom - top)
    side = max(width, height)
    if dry_run:
        return
    with tempfile.TemporaryDirectory() as tmp:
        qr_path = Path(tmp) / "qr.png"
        # Generate denser QR then scale to the on-slide square.
        make_qr_png(hit.rewritten, qr_path, box_size=12, border=2)
        qr = Image.open(qr_path).convert("RGB")
        qr = qr.resize((side, side), Image.Resampling.NEAREST)
        slide = Image.open(hit.path).convert("RGB")
        # Center in the detected box (handles non-square detections).
        paste_x = left + (width - side) // 2
        paste_y = top + (height - side) // 2
        # White pad under QR for quiet zone cleanliness.
        pad_box = Image.new("RGB", (width, height), (255, 255, 255))
        slide.paste(pad_box, (left, top))
        slide.paste(qr, (paste_x, paste_y))
        slide.save(hit.path)


def audit_or_fix(
    *,
    store: Path,
    langs: list[str],
    course_types: tuple[str, ...],
    apply: bool,
) -> int:
    total_hits = 0
    files_touched = 0
    for lang in langs:
        for course_type in course_types:
            pack = pack_dir(store, lang, course_type)
            png_dir = pack / "pngs"
            if not png_dir.is_dir():
                print(f"[skip] missing {png_dir}")
                continue
            pack_hits = 0
            for png in sorted(png_dir.glob("*.png")):
                hits = scan_png(png)
                if not hits:
                    continue
                pack_hits += len(hits)
                total_hits += len(hits)
                files_touched += 1
                for hit in hits:
                    action = "FIX" if apply else "FOUND"
                    print(
                        f"[{action}] {lang}/{course_type}/{png.name}: "
                        f"{hit.payload} -> {hit.rewritten}"
                    )
                    if apply:
                        patch_png(hit)
            if pack_hits:
                print(f"[{lang} {course_type}] localhost QR symbols: {pack_hits}")
            else:
                print(f"[{lang} {course_type}] OK (no localhost QR)")
    mode = "applied" if apply else "audit"
    print(
        f"Done ({mode}): files={files_touched} localhost_symbols={total_hits} site={SITE}"
    )
    return 0 if apply or total_hits == 0 else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_BUILD,
        help="Working-tree root (default: <repo>/build). Packs are {lang}/captures/{type}/",
    )
    parser.add_argument(
        "--lang",
        action="append",
        dest="langs",
        help="Locale code (repeatable). Default: every language under the working tree",
    )
    parser.add_argument(
        "--type",
        action="append",
        dest="types",
        choices=COURSE_TYPES,
        help="Course type (repeatable). Default: 10 20 intensive",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Report only (default when --apply is omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite localhost QR payloads in place on capture PNGs",
    )
    args = parser.parse_args(argv)
    store = args.store.expanduser().resolve()
    langs = args.langs or discover_langs(store)
    if not langs:
        raise SystemExit(f"No presenter-capture packs found under {store}")
    types = tuple(args.types) if args.types else COURSE_TYPES
    apply = bool(args.apply)
    if args.audit and args.apply:
        raise SystemExit("Use either --audit or --apply, not both")
    return audit_or_fix(store=store, langs=langs, course_types=types, apply=apply)


if __name__ == "__main__":
    raise SystemExit(main())
