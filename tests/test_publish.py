"""Offline unit tests for GCS publish + downloads verify."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from zume_assets.cli import main
from zume_assets.publish.names import expected_filenames, filename_for
from zume_assets.publish.pack import discover_pack, plan_uploads
from zume_assets.publish.upload import upload_pack
from zume_assets.publish.verify import verify_downloads


def _touch_pack(lang_dir: Path, lang: str, types: tuple[str, ...] = ("10", "20", "intensive")) -> None:
    lang_dir.mkdir(parents=True, exist_ok=True)
    for asset in expected_filenames(lang, types):
        (lang_dir / asset.filename).write_bytes(b"%PDF-fake" if asset.kind == "pdf" else b"key")


def test_expected_filenames_spanish():
    names = expected_filenames("es")
    assert filename_for("10", "es", ".pdf") == "Zume-Training-10-Session-es.pdf"
    assert filename_for("10", "es", ".key") == "Zume-Training-10-Session-es.key"
    assert filename_for("intensive", "es", ".pdf") == "Zume-Training-Intensive-es.pdf"
    assert {a.filename for a in names} == {
        "Zume-Training-10-Session-es.pdf",
        "Zume-Training-10-Session-es.key",
        "Zume-Training-20-Session-es.pdf",
        "Zume-Training-20-Session-es.key",
        "Zume-Training-Intensive-es.pdf",
        "Zume-Training-Intensive-es.key",
    }


def test_discover_pack_and_plan(tmp_path: Path):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es", ("10",))
    items = discover_pack("es", course_types=("10",), lang_dir=lang_dir)
    assert len(items) == 2
    assert all(not i.missing for i in items)
    assert items[0].gs_uri.startswith("gs://zume-file-mirror/es/")
    plan = plan_uploads(items)
    assert plan["present"] == 2
    assert plan["missing"] == 0


def test_discover_pack_skips_videos_by_default(tmp_path: Path):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es", ("10",))
    videos = lang_dir / "videos"
    videos.mkdir()
    (videos / "1.mp4").write_bytes(b"mp4")
    (videos / "SOURCE.json").write_text("{}", encoding="utf-8")
    items = discover_pack("es", course_types=("10",), lang_dir=lang_dir)
    assert all(i.kind != "video" for i in items)
    with_videos = discover_pack(
        "es", course_types=("10",), lang_dir=lang_dir, include_videos=True
    )
    assert any(i.kind == "video" and i.object_name == "videos/1.mp4" for i in with_videos)
    assert not any("SOURCE.json" in i.object_name for i in with_videos)


def test_upload_dry_run_default(tmp_path: Path):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es")
    result = upload_pack("es", lang_dir=lang_dir, execute=False)
    assert result["status"] == "dry-run"
    assert result["execute"] is False
    assert len(result["commands"]) == 6
    assert result["commands"][0][0] == "gcloud"
    assert "storage" in result["commands"][0]
    assert result["uploaded"] == []


def test_upload_execute_uses_cp_fn(tmp_path: Path):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es", ("10",))
    copied: list[tuple[str, str]] = []

    def fake_cp(local: Path, gs_uri: str) -> None:
        copied.append((str(local), gs_uri))

    result = upload_pack(
        "es",
        course_types=("10",),
        lang_dir=lang_dir,
        execute=True,
        cp_fn=fake_cp,
    )
    assert result["status"] == "uploaded"
    assert len(copied) == 2
    assert all(u.startswith("gs://zume-file-mirror/es/") for _, u in copied)


def test_upload_execute_refuses_missing(tmp_path: Path):
    lang_dir = tmp_path / "es"
    lang_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="missing required local assets"):
        upload_pack("es", course_types=("10",), lang_dir=lang_dir, execute=True)


def test_verify_downloads_pass():
    row = {
        "keynote_10_session": "Zume-Training-10-Session-es.key",
        "keynote_20_session": "Zume-Training-20-Session-es.key",
        "keynote_intensive": "Zume-Training-Intensive-es.key",
        "powerpoint_10_session": "legacy.pptx",
        "guidebook_10_session": "Zume-Training-10-Session-es.pdf",
        "guidebook_20_session": "Zume-Training-20-Session-es.pdf",
        "guidebook_intensive": "Zume-Training-Intensive-es.pdf",
        "download_id": "abc",
        "language_id": "es",
    }
    report = verify_downloads("es", fetch=lambda _lang: row)
    assert report["status"] == "pass"
    assert report["download_id"] == "abc"
    assert any("PPTX" in n for n in report["notes"])


def test_verify_downloads_fail_mismatch():
    row = {
        "guidebook_10_session": "old-name.pdf",
        "guidebook_20_session": "Zume-Training-20-Session-es.pdf",
        "guidebook_intensive": "Zume-Training-Intensive-es.pdf",
        "keynote_10_session": "Zume-Training-10-Session-es.key",
        "keynote_20_session": None,
        "keynote_intensive": "Zume-Training-Intensive-es.key",
        "download_id": "x",
        "language_id": "es",
    }
    report = verify_downloads("es", fetch=lambda _lang: row)
    assert report["status"] == "fail"
    fields = {f["field"] for f in report["failures"]}
    assert "guidebook_10_session" in fields
    assert "keynote_20_session" in fields


def test_publish_cli_dry_run(tmp_path: Path, capsys, monkeypatch):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es", ("10",))
    code = main(
        [
            "publish",
            "upload",
            "--lang",
            "es",
            "--types",
            "10",
            "--dir",
            str(lang_dir),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "gs://zume-file-mirror/es/Zume-Training-10-Session-es.pdf" in out


def test_publish_cli_verify(capsys, monkeypatch):
    row = {
        "guidebook_10_session": "Zume-Training-10-Session-es.pdf",
        "keynote_10_session": "Zume-Training-10-Session-es.key",
        "download_id": "d1",
        "language_id": "es",
    }

    def fake_fetch(lang: str):
        assert lang == "es"
        return row

    monkeypatch.setattr(
        "zume_assets.publish.verify.fetch_downloads",
        fake_fetch,
    )
    # verify_downloads is imported inside _cmd_publish; patch the module used at call time
    import zume_assets.publish.verify as verify_mod

    monkeypatch.setattr(verify_mod, "fetch_downloads", fake_fetch)

    code = main(["publish", "verify-downloads", "--lang", "es", "--types", "10"])
    assert code == 0
    out = capsys.readouterr().out
    assert "verify-downloads pass" in out


def test_publish_help(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["publish", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "upload" in out
    assert "verify-downloads" in out


def test_publish_cli_json_plan(tmp_path: Path, capsys):
    lang_dir = tmp_path / "es"
    _touch_pack(lang_dir, "es", ("10",))
    code = main(
        [
            "publish",
            "upload",
            "--lang",
            "es",
            "--types",
            "10",
            "--dir",
            str(lang_dir),
            "--json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "dry-run"
    assert data["plan"]["present"] == 2
