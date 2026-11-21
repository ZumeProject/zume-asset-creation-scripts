"""Offline QR decode review tests using generated PNGs + fixture master."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from zume_assets.qr import make_qr_png
from zume_assets.review.decode import backend_name
from zume_assets.review.qr_check import (
    activity_live_allowlisted,
    check_qr,
    is_locale_homepage,
    live_redirect_failure_message,
    live_redirect_ok,
    urls_equivalent,
)

FIXTURES = Path(__file__).parent / "fixtures" / "review"


@pytest.fixture
def qr_workspace(tmp_path: Path) -> Path:
    master = FIXTURES / "master-en-10.json"
    data = json.loads(master.read_text(encoding="utf-8"))
    qr_dir = tmp_path / "qr"
    qr_dir.mkdir()
    # Only emit a subset so tests stay small; include matching + one intentional mismatch later.
    for entry in data["checkins"] + data["videos"][:1] + [
        a for a in data["activities"] if a["key"] == "soaps"
    ]:
        make_qr_png(entry["qr_url"], qr_dir / f"{entry['png_stem']}.png")
    book_src = FIXTURES / "book.json"
    book_dst = tmp_path / "book.json"
    shutil.copy(book_src, book_dst)
    shutil.copy(master, tmp_path / "master.json")
    return tmp_path


@pytest.mark.skipif(backend_name() == "none", reason="zxing-cpp/pyzbar not installed")
def test_qr_check_pass(qr_workspace: Path):
    # Master fixture has extra entries (video-2, join_the_community) without PNGs —
    # trim master to only stems we generated so the check can pass cleanly.
    master = json.loads((qr_workspace / "master.json").read_text(encoding="utf-8"))
    keep = {"checkin-5678", "video-1", "activity-soaps"}
    master["checkins"] = [c for c in master["checkins"] if c["png_stem"] in keep]
    master["videos"] = [v for v in master["videos"] if v["png_stem"] in keep]
    master["activities"] = [a for a in master["activities"] if a["png_stem"] in keep]
    (qr_workspace / "master.json").write_text(json.dumps(master), encoding="utf-8")

    report = check_qr(
        "en",
        "10",
        master_path=qr_workspace / "master.json",
        qr_dir=qr_workspace / "qr",
        book_path=qr_workspace / "book.json",
        report_dir=qr_workspace / "review",
        live=False,
    )
    assert report["status"] == "pass"
    assert report["summary"]["failure_count"] == 0
    assert (qr_workspace / "review" / "qr-10.json").is_file()
    assert (qr_workspace / "review" / "qr-10.md").is_file()


@pytest.mark.skipif(backend_name() == "none", reason="zxing-cpp/pyzbar not installed")
def test_qr_check_mismatch(qr_workspace: Path):
    # Overwrite one PNG with the wrong payload.
    make_qr_png(
        "https://zume.training/app/qr/?l=es&v=1",
        qr_workspace / "qr" / "video-1.png",
    )
    master = json.loads((qr_workspace / "master.json").read_text(encoding="utf-8"))
    keep = {"checkin-5678", "video-1", "activity-soaps"}
    master["checkins"] = [c for c in master["checkins"] if c["png_stem"] in keep]
    master["videos"] = [v for v in master["videos"] if v["png_stem"] in keep]
    master["activities"] = [a for a in master["activities"] if a["png_stem"] in keep]
    (qr_workspace / "master.json").write_text(json.dumps(master), encoding="utf-8")

    report = check_qr(
        "en",
        "10",
        master_path=qr_workspace / "master.json",
        qr_dir=qr_workspace / "qr",
        book_path=qr_workspace / "book.json",
        report_dir=qr_workspace / "review",
        live=False,
    )
    assert report["status"] == "fail"
    assert any("video-1" in f.get("id", "") for f in report["failures"])


def test_urls_equivalent_order_insensitive():
    a = "https://zume.training/app/qr/?l=en&v=1"
    b = "https://zume.training/app/qr/?v=1&l=en"
    assert urls_equivalent(a, b)


def test_live_redirect_ok_3monthplan_auth_login():
    """create-your-plan requires login; auth/login redirect is expected design."""
    entry = {
        "kind": "a",
        "key": "3monthplan",
        "expected_redirect": "/auth/login",
    }
    final = (
        "https://zume.training/es/auth/login?"
        "redirect=%2Fes%2Fdashboard%2Ftraining%2Fcreate-your-plan"
    )
    assert live_redirect_ok(entry, final) is True
    assert activity_live_allowlisted("3monthplan", final) is True


def test_live_redirect_ok_3monthplan_rejects_bare_login_or_homepage():
    entry = {
        "kind": "a",
        "key": "3monthplan",
        "expected_redirect": "/auth/login",
    }
    # Must include create-your-plan in the redirect query — bare login is not enough.
    assert live_redirect_ok(entry, "https://zume.training/en/auth/login") is False
    assert live_redirect_ok(entry, "https://zume.training/es") is False


def test_live_redirect_ok_marketing_activity_pages():
    """Prod QR finals for coaching/community land on locale marketing pages."""
    cases = (
        ("getacoach", "/get-a-coach", "https://zume.training/get-a-coach"),
        ("getacoach", "/get-a-coach", "https://zume.training/es/get-a-coach"),
        ("getacoach", "/get-a-coach", "https://zume.training/pus/get-a-coach"),
        (
            "join_the_community",
            "/join-the-community",
            "https://zume.training/es/join-the-community",
        ),
        (
            "next_steps",
            "/join-the-community",
            "https://zume.training/es/join-the-community",
        ),
    )
    for key, expected, final in cases:
        entry = {"kind": "a", "key": key, "expected_redirect": expected}
        assert live_redirect_ok(entry, final) is True
        # Fall through to expected_redirect path match (not 3monthplan-strict).
        assert activity_live_allowlisted(key, final) is None


def test_live_redirect_ok_homepage_activities_still_fail():
    """Homepage redirects stay FAIL except getacoach on NO_COACH_LOCALES."""
    cases = (
        ("getacoach", "/get-a-coach"),
        ("join_the_community", "/join-the-community"),
        ("next_steps", "/join-the-community"),
    )
    for key, expected in cases:
        entry = {"kind": "a", "key": key, "expected_redirect": expected}
        # Spanish has coaches — homepage is still FAIL for getacoach.
        assert live_redirect_ok(entry, "https://zume.training/es", locale="es") is False
        assert activity_live_allowlisted(key, "https://zume.training/es", locale="es") is None
        if key != "getacoach":
            assert live_redirect_ok(entry, "https://zume.training/pus", locale="pus") is False


def test_getacoach_no_coach_locale_homepage_is_ok():
    """zume6 NO_COACH_LOCALES (e.g. pus) intentionally 307 → /{lang}."""
    entry = {
        "kind": "a",
        "key": "getacoach",
        "expected_redirect": "/get-a-coach",
    }
    final = "https://zume.training/pus"
    assert live_redirect_ok(entry, final, locale="pus") is True
    assert activity_live_allowlisted("getacoach", final, locale="pus") is True
    # Still FAIL when locale is offered coaches but page collapsed.
    assert live_redirect_ok(entry, "https://zume.training/es", locale="es") is False


def test_getacoach_homepage_failure_message_is_explicit():
    """Unexpected homepage for a coach-offered locale → explicit FAIL message."""
    entry = {
        "kind": "a",
        "key": "getacoach",
        "expected_redirect": "/get-a-coach",
        "png_stem": "activity-getacoach",
    }
    final = "https://zume.training/es"
    assert is_locale_homepage(final, "es") is True
    assert live_redirect_ok(entry, final, locale="es") is False
    msg = live_redirect_failure_message(
        entry, final, label="activity-getacoach.png", locale="es"
    )
    assert "locale homepage" in msg
    assert "marketing page missing" in msg
    assert "getacoach" in msg
    assert "not a bad QR PNG" in msg


def test_live_redirect_ok_normal_activity_path():
    entry = {
        "kind": "a",
        "key": "soaps",
        "expected_redirect": "/activities/soaps",
    }
    assert live_redirect_ok(entry, "https://zume.training/en/activities/soaps") is True
