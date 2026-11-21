"""Verify zume.training downloads listing for a language pack."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..api import API_BASE, _get_json
from .names import expected_filenames

FetchFn = Callable[[str], dict[str, Any]]


def fetch_downloads(language_id: str) -> dict[str, Any]:
    """GET /api/v1/downloads/{language_id} (Resources / Translations downloads)."""
    return _get_json(f"{API_BASE}/downloads/{language_id}")


def verify_downloads(
    lang: str,
    *,
    course_types: tuple[str, ...] | list[str] | None = None,
    fetch: FetchFn | None = None,
) -> dict[str, Any]:
    """
    Assert downloads row filenames match expected PDF + Keynote + PPTX names.

    Checks guidebook_*, keynote_*, and powerpoint_* fields.
    Returns a report dict; status is pass | fail | error.
    """
    fetch_fn = fetch or fetch_downloads
    expected = expected_filenames(lang, course_types)
    fields = {a.downloads_field for a in expected}

    try:
        row = fetch_fn(lang)
    except Exception as exc:
        return {
            "kind": "verify-downloads",
            "status": "error",
            "lang": lang,
            "api": f"{API_BASE}/downloads/{lang}",
            "failures": [{"field": None, "expected": None, "actual": None, "detail": str(exc)}],
            "row": None,
            "checks": [],
            "notes": [],
        }

    if not isinstance(row, dict):
        return {
            "kind": "verify-downloads",
            "status": "error",
            "lang": lang,
            "api": f"{API_BASE}/downloads/{lang}",
            "failures": [
                {
                    "field": None,
                    "expected": None,
                    "actual": type(row).__name__,
                    "detail": "Downloads response was not a JSON object",
                }
            ],
            "row": row,
            "checks": [],
            "notes": [],
        }

    checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for asset in expected:
        actual = row.get(asset.downloads_field)
        ok = actual == asset.filename
        if not ok:
            detail = (
                "downloads field is null / missing"
                if actual is None
                else "filename mismatch"
            )
            failures.append(
                {
                    "field": asset.downloads_field,
                    "expected": asset.filename,
                    "actual": actual,
                    "detail": detail,
                }
            )
        checks.append(
            {
                "field": asset.downloads_field,
                "course_type": asset.course_type,
                "kind": asset.kind,
                "expected": asset.filename,
                "actual": actual,
                "ok": ok,
            }
        )

    status = "pass" if not failures else "fail"
    keep_keys = fields | {"download_id", "language_id", "online_store"}
    return {
        "kind": "verify-downloads",
        "status": status,
        "lang": lang,
        "api": f"{API_BASE}/downloads/{lang}",
        "download_id": row.get("download_id"),
        "language_id": row.get("language_id", lang),
        "fields_checked": sorted(fields),
        "checks": checks,
        "failures": failures,
        "notes": [],
        "row": {k: row.get(k) for k in sorted(row.keys()) if k in keep_keys},
    }
