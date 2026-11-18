"""Offline Keynote/SOURCE video mapping review tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from zume_assets.review.video_check import (
    OFFICIAL_VIDEO_ALIASES,
    check_videos,
    source_alias_target,
    training_id_from_slide_key,
)

FIXTURES = Path(__file__).parent / "fixtures" / "review"


def test_training_id_from_slide_key():
    assert training_id_from_slide_key("t3_b") == "3"
    assert training_id_from_slide_key("t10_e") == "10"
    assert training_id_from_slide_key("t10_g") == "33"
    assert training_id_from_slide_key("t20_b") == "20"
    assert training_id_from_slide_key("overview") is None


def test_official_video_aliases_map():
    assert OFFICIAL_VIDEO_ALIASES["20"] == "19"


def test_source_alias_target_from_provenance_aliases():
    source_videos = {
        "19": {"vimeo_id": "287853699", "title": "Faithfulness", "status": "cached"},
        "20": {
            "vimeo_id": "287853699",
            "title": "Faithfulness",
            "status": "aliased",
        },
    }
    aliases = {"20": {"from": "19", "reason": "t20_b / Faithfulness slot"}}
    assert source_alias_target("20", source_videos, aliases) == "19"
    assert source_alias_target("19", source_videos, aliases) is None


def test_source_alias_target_status_aliased_without_from():
    source_videos = {
        "19": {"vimeo_id": "287853699", "status": "cached"},
        "20": {"vimeo_id": "287853699", "status": "aliased"},
    }
    assert source_alias_target("20", source_videos, {}) == "19"


def test_source_alias_target_rejects_unrecorded():
    source_videos = {"20": {"vimeo_id": "287853699", "status": "cached"}}
    assert source_alias_target("20", source_videos, {}) is None


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


def test_video_check_title_mismatch_is_note_not_fail(tmp_path: Path):
    """SOURCE Vimeo filenames vs API display titles must not FAIL when vimeo_id matches."""
    master = tmp_path / "master.json"
    shutil.copy(FIXTURES / "master-en-10.json", master)
    source_data = json.loads((FIXTURES / "SOURCE.json").read_text(encoding="utf-8"))
    source_data["videos"]["1"]["title"] = "01_en_god_uses_ordinary_people"
    source_data["videos"]["2"]["title"] = "02_en_simple_definition"
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
    assert report["status"] == "pass", report["failures"]
    assert not any("title" in f.get("id", "") for f in report["failures"])
    assert any("title differs" in n for n in report["notes"])
    mismatched = [r for r in report["results"] if r.get("title_note") == "mismatch"]
    assert len(mismatched) == 2


def test_video_check_id_20_alias_of_19_passes(tmp_path: Path):
    """Pack t20_b / id 20 is OK when SOURCE aliases 20→19 and vimeo matches online 19."""
    master_data = {
        "lang": "en",
        "type": "10",
        "videos": [
            {
                "key": "19",
                "kind": "v",
                "title": "Faithfulness",
                "vimeoId": "287853699",
            }
        ],
    }
    master = tmp_path / "master.json"
    master.write_text(json.dumps(master_data), encoding="utf-8")

    source_data = {
        "source": "vimeo",
        "aliases": {
            "20": {
                "from": "19",
                "reason": "t20_b / Faithfulness slot; folder has 19 only",
            }
        },
        "videos": {
            "19": {
                "vimeo_id": "287853699",
                "title": "(19) Faithfulness",
                "status": "cached",
            },
            "20": {
                "vimeo_id": "287853699",
                "title": "(19) Faithfulness",
                "status": "aliased",
            },
        },
    }
    source = tmp_path / "SOURCE.json"
    source.write_text(json.dumps(source_data), encoding="utf-8")

    pack = tmp_path / "pack"
    (pack / "work").mkdir(parents=True)
    (pack / "videos").mkdir()
    mp4 = pack / "videos" / "20.mp4"
    mp4.write_bytes(b"\x00" * 16)
    replace = [
        {
            "index": 42,
            "key": "t20_b",
            "path": str(mp4),
            "video_id": "20",
        }
    ]
    (pack / "work" / "video-replace-list.json").write_text(
        json.dumps(replace), encoding="utf-8"
    )

    report = check_videos(
        "en",
        "10",
        master_path=master,
        source_path=source,
        pack=pack,
        report_dir_path=tmp_path / "review",
    )
    assert report["status"] == "pass", report["failures"]
    row = next(r for r in report["results"] if r["training_id"] == "20")
    assert row["status"] == "pass"
    assert row["alias_of"] == "19"
    assert row["compared_to_training_id"] == "19"
    assert row["online_vimeoId"] == "287853699"
    assert any("official alias of 19" in n for n in report["notes"])


def test_video_check_id_20_without_alias_still_fails(tmp_path: Path):
    master_data = {
        "lang": "en",
        "type": "10",
        "videos": [
            {
                "key": "19",
                "kind": "v",
                "title": "Faithfulness",
                "vimeoId": "287853699",
            }
        ],
    }
    master = tmp_path / "master.json"
    master.write_text(json.dumps(master_data), encoding="utf-8")

    source_data = {
        "videos": {
            "20": {
                "vimeo_id": "287853699",
                "title": "Something",
                "status": "cached",
            }
        }
    }
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
    assert any(f.get("id") == "20" for f in report["failures"])
