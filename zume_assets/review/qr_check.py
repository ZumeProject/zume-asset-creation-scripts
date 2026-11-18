"""Independent QR PNG decode checks against the review master list."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ..api import load_repo_root
from .decode import QrDecodeError, backend_name, decode_qr_png
from .master import (
    ACTIVITY_EXPECTED_REDIRECT_OVERRIDES,
    default_master_path,
    load_master,
    master_entries_by_png_stem,
    probe_final_url,
)
from .paths import book_path as default_book_path
from .paths import qr_dir as default_qr_dir
from .paths import report_dir as default_report_dir
from .report import exit_code_for, utc_now_iso, write_report


def normalize_qr_url(url: str) -> str:
    """Normalize for comparison (strip fragment; keep query order as encoded)."""
    return (url or "").strip()


def urls_equivalent(a: str, b: str) -> bool:
    """Compare QR payloads: same path + same query params (order-insensitive)."""
    pa, pb = urlparse(normalize_qr_url(a)), urlparse(normalize_qr_url(b))
    if pa.scheme != pb.scheme or pa.netloc != pb.netloc or pa.path != pb.path:
        return False
    return parse_qs(pa.query, keep_blank_values=True) == parse_qs(pb.query, keep_blank_values=True)


def book_qr_urls(book: dict[str, Any]) -> dict[str, str]:
    """Map relative qr path stem (e.g. checkin-5678) → qr_url from book.json."""
    out: dict[str, str] = {}
    for session in book.get("sessions") or []:
        for block in session.get("blocks") or []:
            qr = block.get("qr")
            qr_url = block.get("qr_url")
            if not qr or not qr_url:
                continue
            stem = Path(str(qr)).stem
            out[stem] = str(qr_url)
    return out


def activity_live_allowlisted(key: str, final_url: str) -> bool | None:
    """Return True/False for activity keys with a special live rule; else None.

    ``3monthplan`` needs auth/login + create-your-plan in the query (stricter than
    the generic expected_redirect substring). Other override keys fall through to
    ``live_redirect_ok``'s expected_redirect path match (get-a-coach /
    join-the-community). Homepage redirects stay FAIL.
    """
    if key not in ACTIVITY_EXPECTED_REDIRECT_OVERRIDES:
        return None
    if key == "3monthplan":
        parsed = urlparse(final_url)
        path = parsed.path or ""
        query = unquote(parsed.query or "")
        # create-your-plan requires login; QR lands on auth/login with redirect back.
        return "/auth/login" in path and "create-your-plan" in query
    return None


def live_redirect_ok(entry: dict[str, Any], final_url: str | None) -> bool:
    if not final_url:
        return False
    kind = entry.get("kind")
    key = str(entry.get("key") or "")

    # Intentional alternate destinations (checked before generic expected_redirect).
    if kind == "a":
        special = activity_live_allowlisted(key, final_url)
        if special is not None:
            return special

    expected = str(entry.get("expected_redirect") or "")
    parsed = urlparse(final_url)
    path_q = parsed.path
    if parsed.query:
        path_q = f"{parsed.path}?{parsed.query}"
    # Allow expected as suffix match on path+query (hosts may vary www vs apex).
    if expected and expected in path_q:
        return True
    # Fallback: checkin / video / activity patterns.
    if kind == "c":
        code = str(entry.get("code") or "")
        return "/checkin" in parsed.path and (not code or code in (parsed.query or ""))
    if kind == "v":
        qs = parse_qs(parsed.query)
        return "/app/video" in parsed.path and key in (qs.get("v") or [])
    if kind == "a":
        return f"/activities/{key}" in parsed.path or parsed.path.rstrip("/").endswith(f"/{key}")
    return False


def check_qr(
    lang: str,
    course_type: str,
    *,
    master_path: Path | None = None,
    qr_dir: Path | None = None,
    book_path: Path | None = None,
    report_dir: Path | None = None,
    live: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """Decode QR PNGs and compare to master (+ optional book.json / live redirects)."""
    repo = root or load_repo_root()
    master_path = master_path or default_master_path(lang, course_type, repo)
    qr_dir = qr_dir or default_qr_dir(lang, course_type, repo)
    book_path = book_path or default_book_path(lang, course_type, repo)
    report_dir = report_dir or default_report_dir(lang, repo)

    failures: list[dict[str, Any]] = []
    notes: list[str] = []
    results: list[dict[str, Any]] = []

    if not master_path.is_file():
        report = {
            "kind": "qr",
            "status": "error",
            "lang": lang,
            "type": course_type,
            "generated_at": utc_now_iso(),
            "summary": {"error": "master_missing"},
            "failures": [
                {
                    "id": "master",
                    "message": f"Master list not found: {master_path}. Run: review fetch-master",
                }
            ],
            "notes": notes,
            "results": results,
        }
        write_report(report, report_dir, stem=f"qr-{course_type}")
        return report

    master = load_master(master_path)
    by_stem = master_entries_by_png_stem(master)
    book_map: dict[str, str] = {}
    if book_path.is_file():
        book_map = book_qr_urls(json.loads(book_path.read_text(encoding="utf-8")))
    else:
        notes.append(f"book.json not found at {book_path}; skipping assembler cross-check")

    if not qr_dir.is_dir():
        report = {
            "kind": "qr",
            "status": "error",
            "lang": lang,
            "type": course_type,
            "generated_at": utc_now_iso(),
            "summary": {"error": "qr_dir_missing"},
            "failures": [
                {
                    "id": "qr_dir",
                    "message": f"QR directory not found: {qr_dir}. Build the PDF first.",
                }
            ],
            "notes": notes,
            "results": results,
            "backend": backend_name(),
        }
        write_report(report, report_dir, stem=f"qr-{course_type}")
        return report

    pngs = sorted(qr_dir.glob("*.png"))
    if not pngs:
        failures.append({"id": "qr_dir", "message": f"No PNG files under {qr_dir}"})

    decoded_ok = 0
    for png in pngs:
        stem = png.stem
        entry = by_stem.get(stem)
        row: dict[str, Any] = {"file": png.name, "stem": stem}
        try:
            decoded = decode_qr_png(png)
        except QrDecodeError as exc:
            failures.append({"id": stem, "message": str(exc)})
            row["status"] = "error"
            row["error"] = str(exc)
            results.append(row)
            continue

        row["decoded"] = decoded
        if not decoded:
            failures.append({"id": stem, "message": f"No QR payload decoded from {png.name}"})
            row["status"] = "fail"
            results.append(row)
            continue

        if entry is None:
            failures.append(
                {
                    "id": stem,
                    "message": f"{png.name}: decoded OK but not in master list ({decoded!r})",
                }
            )
            row["status"] = "fail"
            row["expected"] = None
            results.append(row)
            continue

        expected = str(entry.get("qr_url") or "")
        row["expected"] = expected
        match_master = urls_equivalent(decoded, expected)
        row["match_master"] = match_master
        if not match_master:
            failures.append(
                {
                    "id": stem,
                    "message": f"{png.name}: decoded {decoded!r} != master {expected!r}",
                }
            )

        if stem in book_map:
            book_url = book_map[stem]
            row["book_qr_url"] = book_url
            match_book = urls_equivalent(decoded, book_url)
            row["match_book"] = match_book
            if not match_book:
                failures.append(
                    {
                        "id": f"{stem}:book",
                        "message": f"{png.name}: decoded {decoded!r} != book.json {book_url!r}",
                    }
                )
            if expected and not urls_equivalent(book_url, expected):
                failures.append(
                    {
                        "id": f"{stem}:book-master",
                        "message": f"{png.name}: book.json {book_url!r} != master {expected!r}",
                    }
                )

        if live:
            final = probe_final_url(decoded)
            row["live_final_url"] = final
            ok_live = live_redirect_ok(entry, final)
            row["live_ok"] = ok_live
            if not ok_live:
                failures.append(
                    {
                        "id": f"{stem}:live",
                        "message": (
                            f"{png.name}: live redirect {final!r} does not match "
                            f"expected {entry.get('expected_redirect')!r}"
                        ),
                    }
                )

        if match_master and row.get("match_book", True) and row.get("live_ok", True):
            row["status"] = "pass"
            decoded_ok += 1
        else:
            row["status"] = "fail"
        results.append(row)

    # Master entries with no PNG.
    png_stems = {p.stem for p in pngs}
    for stem, entry in by_stem.items():
        if stem not in png_stems:
            failures.append(
                {
                    "id": f"{stem}:missing",
                    "message": f"Master entry {stem} has no PNG in {qr_dir}",
                }
            )

    status = "pass" if not failures else "fail"
    report = {
        "kind": "qr",
        "status": status,
        "lang": lang,
        "type": course_type,
        "generated_at": utc_now_iso(),
        "master_path": str(master_path),
        "qr_dir": str(qr_dir),
        "book_path": str(book_path) if book_path.is_file() else None,
        "live": live,
        "backend": backend_name(),
        "summary": {
            "png_count": len(pngs),
            "master_entries": len(by_stem),
            "decoded_ok": decoded_ok,
            "failure_count": len(failures),
        },
        "failures": failures,
        "notes": notes,
        "results": results,
    }
    write_report(report, report_dir, stem=f"qr-{course_type}")
    return report


def run_qr_cli(**kwargs: Any) -> int:
    report = check_qr(**kwargs)
    return exit_code_for(report)
