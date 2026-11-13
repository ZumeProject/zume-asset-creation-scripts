from zume_assets.html_text import (
    fix_zume_brand_spacing,
    html_to_text,
    paragraphs,
    strip_markdown,
    unescape_markdown,
)


def test_fix_zume_brand_spacing():
    assert fix_zume_brand_spacing("**Z ÚME COACHING TIP**") == "**ZÚME COACHING TIP**"
    assert fix_zume_brand_spacing("Zúme coaches") == "Zúme coaches"
    assert fix_zume_brand_spacing("Z\u00A0úme") == "Zúme"
    assert paragraphs("**Z ÚME COACHING TIP**\n\nNext.") == [
        "ZÚME COACHING TIP",
        "Next.",
    ]


def test_html_to_text_skips_scripts_and_marks_list_items():
    html = "<p>Hello</p><script>secret()</script><ul><li>One</li><li>Two</li></ul>"
    text = html_to_text(html)
    assert "secret" not in text
    assert "Hello" in text
    assert "• One" in text
    assert "• Two" in text


def test_html_to_text_empty():
    assert html_to_text(None) == ""
    assert html_to_text("") == ""


def test_unescape_markdown_hyphens_and_line_breaks():
    assert unescape_markdown(r"a \- b") == "a - b"
    assert unescape_markdown("line\\\nnext") == "line next"


def test_strip_markdown_emphasis_and_headings():
    assert strip_markdown("**Bold** and *plain*") == "Bold and plain"
    assert strip_markdown("# Title") == "Title"
    assert strip_markdown(r"\-\- still") == "-- still"


def test_paragraphs_split_and_flatten():
    assert paragraphs("First\\-line.\n\n**Second**\nstill second.") == [
        "First-line.",
        "Second still second.",
    ]
    assert paragraphs(None) == []
