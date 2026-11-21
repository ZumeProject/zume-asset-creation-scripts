"""Stable production filenames for PDF, Keynote, and Keynote-exported PPTX."""

from __future__ import annotations

from dataclasses import dataclass

COURSE_TYPES = ("10", "20", "intensive")

REQUIRED_KINDS = frozenset({"pdf", "keynote", "pptx"})

# Stem shared by PDF / Keynote / PPTX deliverables under output/{lang}/.
STEMS: dict[str, str] = {
    "10": "Zume-Training-10-Session-{lang}",
    "20": "Zume-Training-20-Session-{lang}",
    "intensive": "Zume-Training-Intensive-{lang}",
}

# Kind → file extension
KIND_EXT: dict[str, str] = {
    "pdf": ".pdf",
    "keynote": ".key",
    "pptx": ".pptx",
}

# downloads API field → (course_type, extension)
EXPECTED_DOWNLOAD_FIELDS: dict[str, tuple[str, str]] = {
    "guidebook_10_session": ("10", ".pdf"),
    "guidebook_20_session": ("20", ".pdf"),
    "guidebook_intensive": ("intensive", ".pdf"),
    "keynote_10_session": ("10", ".key"),
    "keynote_20_session": ("20", ".key"),
    "keynote_intensive": ("intensive", ".key"),
    "powerpoint_10_session": ("10", ".pptx"),
    "powerpoint_20_session": ("20", ".pptx"),
    "powerpoint_intensive": ("intensive", ".pptx"),
}


@dataclass(frozen=True)
class AssetName:
    course_type: str
    kind: str  # "pdf" | "keynote" | "pptx"
    filename: str
    downloads_field: str

    @property
    def extension(self) -> str:
        return KIND_EXT[self.kind]


def stem_for(course_type: str, lang: str) -> str:
    if course_type not in STEMS:
        raise ValueError(f"Unknown course type: {course_type!r}")
    return STEMS[course_type].format(lang=lang)


def filename_for(course_type: str, lang: str, ext: str) -> str:
    if not ext.startswith("."):
        ext = f".{ext}"
    return f"{stem_for(course_type, lang)}{ext}"


def expected_filenames(
    lang: str,
    course_types: tuple[str, ...] | list[str] | None = None,
) -> list[AssetName]:
    """Return expected PDF + Keynote + PPTX names for the given types (default all)."""
    types = tuple(course_types) if course_types else COURSE_TYPES
    unknown = [t for t in types if t not in STEMS]
    if unknown:
        raise ValueError(f"Unknown course type(s): {', '.join(unknown)}")

    out: list[AssetName] = []
    field_by_type_ext = {
        (ctype, ext): field for field, (ctype, ext) in EXPECTED_DOWNLOAD_FIELDS.items()
    }
    for ctype in types:
        for kind, ext in (("pdf", ".pdf"), ("keynote", ".key"), ("pptx", ".pptx")):
            field = field_by_type_ext[(ctype, ext)]
            out.append(
                AssetName(
                    course_type=ctype,
                    kind=kind,
                    filename=filename_for(ctype, lang, ext),
                    downloads_field=field,
                )
            )
    return out
