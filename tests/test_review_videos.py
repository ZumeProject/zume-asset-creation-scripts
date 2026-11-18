"""Offline Keynote/SOURCE video mapping review tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from zume_assets.review.video_check import check_videos, training_id_from_slide_key

FIXTURES = Path(__file__).parent / "fixtures" / "review"


def test_training_id_from_slide_key():
    assert training_id_from_slide_key("t3_b") == "3"
    assert training_id_from_slide_key("t10_e") == "10"
    assert training_id_from_slide_key("t10_g") == "33"
    assert training_id_from_slide_key("overview") is None


def test_video_check_pass(tmp_path: Path):
    master = tmp_path / "master.json"
    shutil.copy(FIXTURES / "master-en-10.json", master)
    source = tmp_path / "SOURCE.json"
    shutil.copy(FIXTURES / "SOURCE.json", source)

    pack = tmp_path / "pack"
    (pack / "work").mkdir(parents=True)
    (pack / "videos").mkdir()
    shutil.copy(FIXTURES / "video-replace-list.json", pack / "work" / "video-replace-list.json")
    # Touch MP4 placeholders referenced by the replace list.
    replace = json.loads((pack / "work" / "video-replace-list.json").read_text(encoding="utf-8"))
    for item in replace:
        mp4 = pack / "videos" / f"{item['video_id']}.mp4"
        mp4.write_bytes(b"\x00" * 16)
        item["path"] = str(mp4)
    (pack / "work" / "video-replace-list.json").write_text(json.dumps(replace), encoding="utf-8")

    report = check_videos(
        "en",
        "10",
        master_path=master,
        source_path=source,
        pack=pack,
        report_dir_path=tmp_path / "review",
    )
    assert report["status"] == "pass", report["failures"]
    assert report["summary"]["checked"] == 2


def test_video_check_vimeo_mismatch(tmp_path: Path):
    master = tmp_path / "master.json"
    shutil.copy(FIXTURES / "master-en-10.json", master)
    source_data = json.loads((FIXTURES / "SOURCE.json").read_text(encoding="utf-8"))
    source_data["videos"]["1"]["vimeo_id"] = "999999999"
    source = tmp_path / "SOURCE.json"
    source.write_text(json.dumps(source_data), encoding="utf-8")

    report = check_videos(
        "en",
        "10",
        master_path=master,
        source_path=source,
        pack=tmp_path / "missing-pack",
        report_dir_path=tmp_path / "review",
    )
    assert report["status"] == "fail"
    assert any("vimeo" in f.get("id", "") for f in report["failures"])
