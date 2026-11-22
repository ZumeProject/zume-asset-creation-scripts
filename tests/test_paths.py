"""Working files live under build/; finished uploads stay under output/."""

from pathlib import Path

from zume_assets.paths import (
    book_path,
    capture_pack_dir,
    ensure_capture_videos_link,
    finished_dir,
    legacy_project_dir,
    qr_dir,
    reference_dir,
    report_dir,
    source_json,
    typst_build_dir,
    videos_dir,
)
from zume_assets.review.paths import build_dir


def test_finished_pdf_stays_under_output(tmp_path: Path):
    from zume_assets.cli import default_pdf_path

    pdf = default_pdf_path("en", "10", tmp_path)
    assert pdf == tmp_path / "output" / "en" / "Zume-Training-10-Session-en.pdf"
    assert finished_dir("en", tmp_path) == tmp_path / "output" / "en"


def test_working_tree_layout(tmp_path: Path):
    assert videos_dir("es", tmp_path) == tmp_path / "build" / "es" / "videos"
    assert source_json("es", tmp_path) == tmp_path / "build" / "es" / "videos" / "SOURCE.json"
    assert typst_build_dir("es", "20", tmp_path) == tmp_path / "build" / "es" / "20"
    assert build_dir("es", "20", tmp_path) == tmp_path / "build" / "es" / "20"
    assert qr_dir("es", "20", tmp_path) == tmp_path / "build" / "es" / "20" / "qr"
    assert book_path("es", "20", tmp_path) == tmp_path / "build" / "es" / "20" / "book.json"
    assert report_dir("es", tmp_path) == tmp_path / "build" / "es" / "review"
    assert capture_pack_dir("es", "intensive", tmp_path) == (
        tmp_path / "build" / "es" / "captures" / "intensive"
    )
    assert reference_dir(tmp_path) == tmp_path / "build" / "reference"
    assert legacy_project_dir("es", tmp_path) == tmp_path / "build" / "legacy" / "es"


def test_capture_videos_are_a_relative_link(tmp_path: Path):
    pack = capture_pack_dir("en", "10", tmp_path)
    link = ensure_capture_videos_link(pack, videos_dir("en", tmp_path))
    assert link.is_symlink()
    assert link.readlink() == Path("../../videos")
    assert link.resolve() == videos_dir("en", tmp_path).resolve()
    (videos_dir("en", tmp_path) / "1.mp4").write_bytes(b"mp4")
    assert (link / "1.mp4").is_file()


def test_gitignore_covers_build_and_output():
    text = Path(__file__).resolve().parents[1].joinpath(".gitignore").read_text(encoding="utf-8")
    assert "\noutput/\n" in text or text.startswith("output/\n") or "\noutput/\n" in f"\n{text}"
    assert "\nbuild/\n" in f"\n{text}"
    assert "\nreference/\n" in f"\n{text}"
