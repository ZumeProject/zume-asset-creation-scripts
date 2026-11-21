"""Offline master-list builder tests (no live API)."""

from __future__ import annotations

from pathlib import Path

from zume_assets.review.master import (
    build_master,
    collect_keys_from_manifest,
    expected_redirect_path,
)

FIXTURES = Path(__file__).parent / "fixtures" / "review"


def test_collect_keys_from_minimal_manifest():
    sessions = [
        {
            "session": 1,
            "checkinCode": "5678",
            "slides": [
                {"type": "video", "videoKey": "1"},
                {"type": "activity", "activityKey": "soaps"},
            ],
        }
    ]
    checkins, videos, activities = collect_keys_from_manifest(sessions)
    assert checkins == [{"session": 1, "code": "5678"}]
    assert videos == {"1"}
    assert "soaps" in activities
    assert "join_the_community" in activities


def test_expected_redirect_patterns():
    assert expected_redirect_path("c", "5678", "en") == "/checkin?code=5678"
    assert expected_redirect_path("v", "1", "es") == "/app/video?v=1&l=es"
    assert expected_redirect_path("a", "soaps", "en") == "/activities/soaps"
    # 3monthplan intentionally lands on auth/login (create-your-plan requires login).
    assert expected_redirect_path("a", "3monthplan", "en") == "/auth/login"
    # Coaching/community QR land on marketing pages, not /activities/{key}.
    assert expected_redirect_path("a", "getacoach", "en") == "/get-a-coach"
    assert expected_redirect_path("a", "join_the_community", "es") == "/join-the-community"
    assert expected_redirect_path("a", "next_steps", "es") == "/join-the-community"


def test_build_master_offline_from_presenter_stub(tmp_path: Path):
    sessions = [
        {
            "session": 1,
            "checkinCode": "5678",
            "slides": [
                {"type": "watch", "videoKey": "1"},
                {"type": "video", "videoKey": "1"},
                {"type": "activity", "activityKey": "soaps"},
            ],
        }
    ]
    presenter = {
        "locale": "en",
        "videos": {
            "1": {"title": "God Uses Ordinary People", "vimeoId": "247062938"},
        },
        "activities": {"soaps": {"title": "SOAPS"}},
    }
    master = build_master(
        "en",
        "10",
        presenter=presenter,
        sessions=sessions,
        follow_redirects=False,
    )
    assert master["counts"]["checkins"] == 1
    assert master["counts"]["videos"] == 1
    assert master["videos"][0]["qr_url"] == "https://zume.training/app/qr/?l=en&v=1"
    assert master["videos"][0]["vimeoId"] == "247062938"
    assert master["checkins"][0]["png_stem"] == "checkin-5678"
    assert any(a["key"] == "join_the_community" for a in master["activities"])


def test_build_master_3monthplan_expected_redirect_override():
    sessions = [
        {
            "session": 1,
            "checkinCode": "5678",
            "slides": [{"type": "activity", "activityKey": "3monthplan"}],
        }
    ]
    presenter = {
        "locale": "en",
        "videos": {},
        "activities": {"3monthplan": {"title": "Three Month Plan"}},
    }
    master = build_master(
        "en",
        "10",
        presenter=presenter,
        sessions=sessions,
        follow_redirects=False,
    )
    plan = next(a for a in master["activities"] if a["key"] == "3monthplan")
    assert plan["expected_redirect"] == "/auth/login"
