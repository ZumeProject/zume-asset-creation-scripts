"""CLI wiring for review subcommands (offline)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from zume_assets.cli import main
from zume_assets.qr import make_qr_png
from zume_assets.review.decode import backend_name

FIXTURES = Path(__file__).parent / "fixtures" / "review"


def test_review_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["review", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "fetch-master" in out
    assert "qr" in out
    assert "videos" in out
    assert "all" in out


def test_review_videos_cli(tmp_path: Path, capsys):
    master = tmp_path / "master.json"
    shutil.copy(FIXTURES / "master-en-10.json", master)
    source = tmp_path / "SOURCE.json"
    shutil.copy(FIXTURES / "SOURCE.json", source)
    report_dir = tmp_path / "review"

    code = main(
        [
            "review",
            "videos",
            "--lang",
            "en",
            "--type",
            "10",
            "--master",
            str(master),
            "--source",
            str(source),
            "--pack",
            str(tmp_path / "no-pack"),
            "--report-dir",
            str(report_dir),
        ]
    )
    assert code == 0
    assert (report_dir / "videos-10.json").is_file()
    data = json.loads((report_dir / "videos-10.json").read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    out = capsys.readouterr().out
    assert "Video review pass" in out


def test_review_qr_cli_requires_backend(tmp_path: Path):
    if backend_name() == "none":
        return
    master_data = json.loads((FIXTURES / "master-en-10.json").read_text(encoding="utf-8"))
    master_data["checkins"] = master_data["checkins"][:1]
    master_data["videos"] = []
    master_data["activities"] = []
    master = tmp_path / "master.json"
    master.write_text(json.dumps(master_data), encoding="utf-8")
    qr_dir = tmp_path / "qr"
    qr_dir.mkdir()
    make_qr_png(master_data["checkins"][0]["qr_url"], qr_dir / "checkin-5678.png")
    report_dir = tmp_path / "review"
    code = main(
        [
            "review",
            "qr",
            "--lang",
            "en",
            "--type",
            "10",
            "--master",
            str(master),
            "--qr-dir",
            str(qr_dir),
            "--book",
            str(FIXTURES / "book.json"),
            "--report-dir",
            str(report_dir),
        ]
    )
    assert code == 0
