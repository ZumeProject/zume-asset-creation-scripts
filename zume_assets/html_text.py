"""Convert activity HTML bodies into Typst-friendly plain text."""

from __future__ import annotations

import re
from html.parser import HTMLParser

# Live scripts sometimes ship "Z ÚME" (space before accented Ú) instead of "ZÚME".
_ZUME_BRAND_GAP = re.compile(r"Z[\s\u00A0\u2000-\u200B\u202F]+([Úú])")


def fix_zume_brand_spacing(text: str) -> str:
    """Collapse a spurious gap between Z and ú/Ú in the Zúme brand."""
    if not text or "Z" not in text:
        return text
    return _ZUME_BRAND_GAP.sub(r"Z\1", text)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip = True
            return
        if tag in {"br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("• ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = False
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = data.strip()
        if text:
            self.parts.append(text + " ")


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# Markdown allows backslash-escaping these ASCII punctuation chars.
# Scripts use e.g. `\-` / `\--` so hyphens aren't treated as list markers;
# once we flatten to plain text for Typst, those backslashes must not remain.
_MD_ESCAPABLE = r"""\\`*_{}[\]()#+.!|-"""


def unescape_markdown(text: str) -> str:
    """Remove Markdown backslash escapes so Typst never shows literal \\- etc."""
    # Soft/hard line break: trailing backslash before newline → space
    text = re.sub(r"\\\s*\n", " ", text)
    # \X → X for Markdown-escapable punctuation (and \\ → \)
    text = re.sub(rf"\\([{_MD_ESCAPABLE}])", r"\1", text)
    return fix_zume_brand_spacing(text)


def strip_markdown(text: str) -> str:
    """Scripts sometimes ship light Markdown; Typst should see plain text."""
    text = unescape_markdown(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    # Escapes may have protected markers inside emphasis; unescape again after strip.
    text = unescape_markdown(text)
    return fix_zume_brand_spacing(text)


def paragraphs(text: str | None) -> list[str]:
    if not text:
        return []
    text = strip_markdown(text)
    chunks = re.split(r"\n\s*\n", text.strip())
    out: list[str] = []
    for chunk in chunks:
        line = re.sub(r"\s*\n\s*", " ", chunk).strip()
        if line:
            out.append(fix_zume_brand_spacing(line))
    return out
