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
    pus = folder_id_for_language("pus")
    assert pus is not None and pus[0] == "29862924"


def test_pus_prereqs_blocks_on_videos_not_map(tmp_path):
    # Capture packs absent in empty store; map is present so BLOCK is local_videos.
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
    assert "vimeo_folder_map" not in ids
    assert "local_videos" in ids
    assert any(i.id.startswith("capture_pack_") for i in issues)
    report = format_prereq_report("pus", issues)
    assert "BLOCK" in report
    assert "29862924" in report


def test_pdf_only_skips_video_and_pack_checks():
    issues = check_language_pack_prereqs(
        "pus",
        require_videos=False,
        require_capture_packs=False,
    )
    assert issues == []
