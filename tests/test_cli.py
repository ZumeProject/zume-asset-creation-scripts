from zume_assets.api import load_repo_root
from zume_assets.cli import default_output_root, default_pdf_path, main
from zume_assets.lang_prereqs import PrereqIssue


def test_rejects_non_pdf_targets(capsys):
    code = main(["build", "--targets", "pptx,keynote"])
    assert code == 2
    err = capsys.readouterr().err
    assert "pptx" in err
    assert "keynote" in err
    assert "only pdf is supported" in err
    assert "not a production target" in err


def test_default_pdf_path_under_repo_output():
    root = load_repo_root()
    assert default_output_root(root) == root / "output"
    pdf = default_pdf_path("en", "10", root)
    assert pdf == root / "output" / "en" / "Zume-Training-10-Session-en.pdf"
    assert "AgentStores" not in str(pdf)
    assert "/cursor/stores" not in str(pdf)


def test_build_aborts_when_vimeo_map_missing(monkeypatch, tmp_path, capsys):
    folders = tmp_path / "slide-builder" / "parts"
    folders.mkdir(parents=True)
    (folders / "vimeo-folders.json").write_text('{"languages": []}\n', encoding="utf-8")

    monkeypatch.setattr("zume_assets.lang_prereqs.load_repo_root", lambda: tmp_path)

    called = {"build": False}

    def boom(*_args, **_kwargs):
        called["build"] = True
        raise AssertionError("build_pdf must not run when map is missing")

    monkeypatch.setattr("zume_assets.cli.build_pdf", boom)

    code = main(["build", "--lang", "xx", "--type", "10", "--targets", "pdf"])
    assert code == 1
    assert called["build"] is False
    err = capsys.readouterr().err
    assert "vimeo_folder_map" in err
    assert "Build aborted" in err
    assert "slide-builder/parts/vimeo-folders.json" in err


def test_build_full_pack_aborts_on_local_videos(monkeypatch, capsys):
    monkeypatch.setattr(
        "zume_assets.lang_prereqs.check_build_readiness",
        lambda *_a, **_k: [
            PrereqIssue(
                id="local_videos",
                blocking=True,
                message="No local Vimeo download",
                next_steps=["download"],
            )
        ],
    )
    called = {"build": False}
    monkeypatch.setattr(
        "zume_assets.cli.build_pdf",
        lambda *_a, **_k: called.__setitem__("build", True),
    )
    code = main(
        ["build", "--lang", "en", "--type", "10", "--targets", "pdf", "--full-pack"]
    )
    assert code == 1
    assert called["build"] is False
    assert "local_videos" in capsys.readouterr().err


def test_build_applies_gap_fillers_by_default(monkeypatch, tmp_path, capsys):
    pdf = tmp_path / "out.pdf"
    pdf.write_bytes(b"%PDF")
    images = tmp_path / "images"
    images.mkdir()
    (images / "A001.png").write_bytes(b"PNG")

    monkeypatch.setattr("zume_assets.lang_prereqs.check_build_readiness", lambda *_a, **_k: [])
    monkeypatch.setattr("zume_assets.cli.build_pdf", lambda *_a, **_k: pdf)
    monkeypatch.setattr("zume_assets.cli.load_repo_root", lambda: tmp_path)
    monkeypatch.setattr("zume_assets.cli.default_images_dir", lambda _root: images)

    called = {"gap": False}

    def fake_apply(input_pdf, output_pdf, images_dir, **_kwargs):
        called["gap"] = True
        assert images_dir == images
        assert input_pdf == pdf
        return []

    monkeypatch.setattr("zume_assets.cli.apply_gap_fillers", fake_apply)
    monkeypatch.setattr("zume_assets.cli.placements_report", lambda _p: "Placed 0\n")

    code = main(["build", "--lang", "en", "--type", "10", "--targets", "pdf"])
    assert code == 0
    assert called["gap"] is True
    out = capsys.readouterr()
    assert "Wrote" in out.out
    assert "--no-gap-fillers" not in out.err


def test_build_no_gap_fillers_warns_and_skips(monkeypatch, tmp_path, capsys):
    pdf = tmp_path / "out.pdf"
    pdf.write_bytes(b"%PDF")

    monkeypatch.setattr("zume_assets.lang_prereqs.check_build_readiness", lambda *_a, **_k: [])
    monkeypatch.setattr("zume_assets.cli.build_pdf", lambda *_a, **_k: pdf)

    def boom(*_a, **_k):
        raise AssertionError("apply_gap_fillers must not run with --no-gap-fillers")

    monkeypatch.setattr("zume_assets.cli.apply_gap_fillers", boom)

    code = main(
        ["build", "--lang", "en", "--type", "10", "--targets", "pdf", "--no-gap-fillers"]
    )
    assert code == 0
    err = capsys.readouterr().err
    assert "WARNING" in err
    assert "--no-gap-fillers" in err


def test_build_gap_fillers_fail_when_images_missing(monkeypatch, tmp_path, capsys):
    pdf = tmp_path / "out.pdf"
    pdf.write_bytes(b"%PDF")
    empty = tmp_path / "empty-images"
    empty.mkdir()

    monkeypatch.setattr("zume_assets.lang_prereqs.check_build_readiness", lambda *_a, **_k: [])
    monkeypatch.setattr("zume_assets.cli.build_pdf", lambda *_a, **_k: pdf)
    monkeypatch.setattr("zume_assets.cli.load_repo_root", lambda: tmp_path)
    monkeypatch.setattr("zume_assets.cli.default_images_dir", lambda _root: empty)

    code = main(["build", "--lang", "en", "--type", "10", "--targets", "pdf"])
    assert code == 1
    err = capsys.readouterr().err
    assert "Gap fillers enabled" in err
    assert "empty" in err.lower() or "missing" in err.lower()
