"""Offline checks for language pack prerequisite checklist."""

from zume_assets.lang_prereqs import (
    blocking_issues,
    check_build_readiness,
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


def test_legacy_pdf_only_flags_skip_videos_and_packs():
    issues = check_language_pack_prereqs(
        "pus",
        require_videos=False,
        require_capture_packs=False,
        require_vimeo_map=True,
    )
    # Map exists for pus; nothing else required.
    assert issues == []


def test_build_readiness_pdf_blocks_on_missing_map(tmp_path):
    folders = tmp_path / "slide-builder" / "parts"
    folders.mkdir(parents=True)
    (folders / "vimeo-folders.json").write_text(
        '{"languages": []}\n',
        encoding="utf-8",
    )
    store = tmp_path / "store"
    store.mkdir()
    issues = check_build_readiness(
        "xx",
        mode="pdf",
        course_type="10",
        root=tmp_path,
        store=store,
    )
    assert [i.id for i in blocking_issues(issues)] == ["vimeo_folder_map"]
    report = format_prereq_report("xx", issues, aborted=True, mode="pdf")
    assert "Build aborted" in report
    assert "Do not invent" in report


def test_build_readiness_pdf_notes_missing_videos(tmp_path):
    folders = tmp_path / "slide-builder" / "parts"
    folders.mkdir(parents=True)
    (folders / "vimeo-folders.json").write_text(
        '{"languages": [{"name": "test", "folder_id": "999", "language_code": "zz"}]}\n',
        encoding="utf-8",
    )
    store = tmp_path / "store"
    store.mkdir()
    issues = check_build_readiness(
        "zz",
        mode="pdf",
        course_type="10",
        root=tmp_path,
        store=store,
    )
    assert blocking_issues(issues) == []
    ids = {i.id: i.blocking for i in issues}
    assert ids.get("local_videos") is False
    assert ids.get("capture_pack_10") is False


def test_build_readiness_full_blocks_videos_and_packs(tmp_path):
    folders = tmp_path / "slide-builder" / "parts"
    folders.mkdir(parents=True)
    (folders / "vimeo-folders.json").write_text(
        '{"languages": [{"name": "test", "folder_id": "999", "language_code": "zz"}]}\n',
        encoding="utf-8",
    )
    store = tmp_path / "store"
    store.mkdir()
    issues = check_build_readiness(
        "zz",
        mode="full",
        course_type="10",
        root=tmp_path,
        store=store,
    )
    blocked = {i.id for i in blocking_issues(issues)}
    assert "local_videos" in blocked
    assert "capture_pack_10" in blocked
