"""Offline checks for language pack prerequisite checklist."""

from zume_assets.lang_prereqs import (
    check_language_pack_prereqs,
    folder_id_for_language,
    format_prereq_report,
)


def test_known_folder_ids():
    en = folder_id_for_language("en")
    assert en is not None and en[0] == "21862752"
    es = folder_id_for_language("es")
    assert es is not None and es[0] == "269525"
    assert folder_id_for_language("pus") is None


def test_pus_prereqs_block_without_vimeo_map(tmp_path):
    # Empty store so capture packs are also missing; focus on map block.
    store = tmp_path / "store"
    store.mkdir()
    issues = check_language_pack_prereqs(
        "pus",
        course_types=("10",),
        store=store,
        require_videos=True,
        require_capture_packs=True,
    )
    ids = {i.id for i in issues}
    assert "vimeo_folder_map" in ids
    assert any(i.id.startswith("capture_pack_") for i in issues)
    report = format_prereq_report("pus", issues)
    assert "BLOCK" in report
    assert "21862752" in report
    assert "269525" in report


def test_pdf_only_skips_video_and_pack_checks():
    issues = check_language_pack_prereqs(
        "pus",
        require_videos=False,
        require_capture_packs=False,
    )
    assert issues == []
