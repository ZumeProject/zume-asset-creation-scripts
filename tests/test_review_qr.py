"""Offline QR decode review tests using generated PNGs + fixture master."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from zume_assets.qr import make_qr_png
from zume_assets.review.decode import backend_name
from zume_assets.review.qr_check import check_qr, urls_equivalent

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
