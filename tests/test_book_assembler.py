import json

from zume_assets.book_assembler import (
    _typst_lang_region,
    assemble_book,
    format_duration,
    load_course_manifest,
    overview_block,
)


def test_format_duration_omits_zero():
    assert format_duration(5) == "5 min"
    assert format_duration(0) is None
    assert format_duration(None) is None


def test_typst_lang_region():
    assert _typst_lang_region("en") == ("en", None)
    assert _typst_lang_region("zhtw") == ("zh", "TW")
    assert _typst_lang_region("ar") == ("ar", None)


def test_unknown_course_manifest():
    try:
        load_course_manifest("nope")
    except NotImplementedError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected NotImplementedError")


def test_overview_block_tool_practice_session():
    session = {"conceptKeys": [], "toolKeys": [4]}
    presenter = {"concepts": {"4": "List of 100"}}
    ui = {
        "label.overview": "OVERVIEW",
        "instruction.tool_session_intro": "Practice this tool.",
    }
    block = overview_block(session, presenter, ui, 15)
    assert block["concepts"] == ["List of 100"]
    assert block["concepts_intro"] == "Practice this tool."
    assert block["tools"] == []
    assert block["duration"] == "15 min"


def _stub_fetches(monkeypatch, locale: str):
    def presenter(lang, fallback="en"):
        return {
            "locale": locale,
            "ui": {
                "label.watch": "READ",
                "label.checkin": "CHECK-IN",
                "s1.session.1.title": "Session One",
            },
            "videos": {"1": {"title": r"God's Story \- hyphen"}},
            "concepts": {},
        }

    monkeypatch.setattr("zume_assets.book_assembler.fetch_presenter_content", presenter)
    monkeypatch.setattr(
        "zume_assets.book_assembler.fetch_script_by_video",
        lambda video_key, language_id="en": {"content": r"Line \- one.\n\n**Bold** line."},
    )
    monkeypatch.setattr(
        "zume_assets.book_assembler.fetch_activity",
        lambda activity_key, language_id="en", render_shortcodes=True: {
            "title": "Do this",
            "content": "<p>Body</p><script>skip()</script>",
        },
    )


def test_assemble_book_offline(tmp_path, monkeypatch):
    _stub_fetches(monkeypatch, "en")
    book = assemble_book(lang="en", course_type="10", build_dir=tmp_path, cache_api=True)

    manifest = load_course_manifest("10")
    assert book["meta"]["session_count"] == len(manifest) == 10
    assert book["typst_lang"] == "en"
    assert book["typst_region"] is None
    assert book["direction"] == "ltr"
    assert book["output_name"] == "Zume-Training-10-Session-en.pdf"
    assert book["sessions"][0]["title"] == "Session One"
    assert (tmp_path / "book.json").exists()

    checkins = [b for b in book["sessions"][0]["blocks"] if b["kind"] == "checkin"]
    assert checkins[0]["qr_url"] == "https://zume.training/app/qr/?l=en&c=5678"
    assert (tmp_path / checkins[0]["qr"]).exists()

    reads = [b for s in book["sessions"] for b in s["blocks"] if b["kind"] == "read"]
    assert any("Bold" in " ".join(b["paragraphs"]) for b in reads)
    dumped = json.dumps(book)
    assert r"\-" not in dumped
    assert "skip()" not in dumped


def test_assemble_book_arabic_is_rtl(tmp_path, monkeypatch):
    _stub_fetches(monkeypatch, "ar")
    book = assemble_book(lang="ar", course_type="intensive", build_dir=tmp_path, cache_api=False)
    assert book["direction"] == "rtl"
    assert book["typst_lang"] == "ar"
    assert book["output_name"] == "Zume-Training-Intensive-ar.pdf"
    assert book["meta"]["session_count"] == len(load_course_manifest("intensive"))
