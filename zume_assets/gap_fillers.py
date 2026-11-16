"""Decorative bottom-gap fillers for Typst guidebook PDFs.

After Typst layout, measure leftover space above the footer and stamp
transparent PNGs from the repo ``images/`` library into those gaps.
This does not reflow content or change page breaks.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - optional until gap-fill runs
    fitz = None  # type: ignore[assignment]

PAGE_HEIGHT_PT = 792.0  # US Letter
FOOTER_MARGIN_PT = 72.0  # matches book.typ bottom margin
DEFAULT_MIN_GAP_IN = 1.35
DEFAULT_PAD_IN = 0.22
DEFAULT_MAX_WIDTH_IN = 6.4

# Context → preferred image filenames (repo images/). Order = preference.
# Pools are curated for tone; aspect fit is still enforced at placement time.
CONTEXT_POOLS: dict[str, list[str]] = {
    "lookback_overview": [
        "A047-jesus-teaching-disciples.png",
        "A075-jesus-teaching-seated-group.png",
        "A003-jesus-beside-disciple.png",
        "A001-jesus-holding-scroll.png",
        "A015-fruit-tree.png",
        "A042-garden-with-tree-and-people.png",
        "A028-open-bible.png",
        "A018-bible-reader.png",
        "A014-jesus-speaking.png",
        "A006-king-on-throne.png",
        "A097-watering-fruitful-plant.png",
    ],
    "discuss": [
        "A008-people-around-a-table.png",
        "A053-small-group-at-table.png",
        "A052-two-people-at-table.png",
        "A023-sharing-with-a-friend.png",
        "A041-sharing-pair-closeup.png",
        "A032-circle-of-people.png",
        "A037-questioning-person.png",
        "A051-thinking-person-closeup.png",
        "A111-listening-with-care.png",
        "A029-hearing-and-sharing-pair.png",
        "A078-small-group-in-circle.png",
        "A110-four-person-mentoring-group.png",
        "A074-person-of-peace-conversation.png",
    ],
    "obey": [
        "A103-jesus-pointing.png",
        "A105-walking-person.png",
        "A002-walking-disciple-pair.png",
        "A057-three-walking-disciples.png",
        "A071-jesus-sending-disciples.png",
        "A087-leader-holding-gear.png",
        "A091-checklist-clipboard.png",
        "A072-welcoming-person.png",
        "A050-standing-speaker.png",
        "A060-looking-into-distance.png",
        "A083-cyclist-modeling.png",
        "A084-helping-someone-ride-bicycle.png",
    ],
    "pray": [
        "A030-kneeling-prayer.png",
        "A034-praying-hands.png",
        "A020-praying-at-desk.png",
        "A080-pair-praying.png",
        "A035-hand-reaching-from-cloud.png",
        "A011-breathing-person.png",
        "A038-prayer-cycle-diagram.png",
    ],
    "checkin_pray": [
        "A064-neighborhood-street.png",
        "A071-jesus-sending-disciples.png",
        "A095-person-sowing-seed.png",
        "A055-two-seedlings.png",
        "A022-breath-symbol.png",
        "A061-fruit-bushes.png",
        "A036-cyan-heart.png",
        "A021-helping-hand-and-heart.png",
        "A070-religious-buildings.png",
    ],
    "activity": [
        "A039-person-holding-long-list.png",
        "A025-three-women-accountability-group.png",
        "A026-three-men-accountability-group.png",
        "A078-small-group-in-circle.png",
        "A110-four-person-mentoring-group.png",
        "A077-three-thirds-circle.png",
        "A082-group-with-new-leader.png",
        "A093-multiplying-small-groups.png",
    ],
    "read_residual": [
        "A019-bible-study-and-notes.png",
        "A018-bible-reader.png",
        "A028-open-bible.png",
        "A047-jesus-teaching-disciples.png",
        "A014-jesus-speaking.png",
        "A059-light-bulb-idea.png",
        "A016-person-on-rock-above-waves.png",
        "A058-bridge-across-chasm.png",
        "A113-three-circles-gospel-diagram.png",
        "A056-duck-with-four-ducklings.png",
        "A045-tomb-with-stone.png",
        "A046b-jesus-at-resurrection-tomb.png",
        "A049-baptism-immersion.png",
        "A048-baptism-standing-pair.png",
    ],
    "finale": [
        "A081-four-celebrating-people.png",
        "A054-celebrating-pair.png",
        "A100-people-around-globe.png",
        "A090-people-connected-to-globe.png",
    ],
    "blank_even": [
        "A100-people-around-globe.png",
        "A005-jesus-and-globe.png",
        "A017-jesus-and-disciple-holding-globe.png",
        "A012-shepherd-with-sheep.png",
    ],
}


@dataclass(frozen=True)
class GapSlot:
    page_index: int  # 0-based
    page_number: int  # 1-based
    gap_in: float
    context: str
    labels: tuple[str, ...]
    content_bottom_pt: float | None


@dataclass(frozen=True)
class FillerPlacement:
    slot: GapSlot
    image_path: Path
    rect: tuple[float, float, float, float]  # x0,y0,x1,y1 in PDF points


def _require_fitz() -> None:
    if fitz is None:
        raise RuntimeError(
            "pymupdf is required for gap fillers. Install with: pip install pymupdf"
        )


def default_images_dir(repo_root: Path) -> Path:
    return repo_root / "images"


_SECTION_LABELS = (
    "CHECK-IN",
    "PRAY",
    "LOOK BACK",
    "OVERVIEW",
    "READ",
    "WATCH",
    "DISCUSS",
    "OBEY",
    "ACTIVITY",
    "BREAK",
    "CONGRATULATIONS",
)


def _page_labels(text: str) -> tuple[str, ...]:
    """Return section labels that appear as their own line (not body prose)."""
    found: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().upper()
        if not line:
            continue
        # Exact header lines only — never match "obey all I have commanded…".
        if line in _SECTION_LABELS and line not in found:
            found.append(line)
    return tuple(found)


def classify_context(*, labels: Iterable[str], blank: bool, gap_in: float) -> str:
    labs = set(labels)
    if blank:
        return "blank_even"
    if "CONGRATULATIONS" in labs:
        return "finale"
    # Session openers first so short CHECK-IN/PRAY leftovers are not mis-tagged OBEY.
    if "CHECK-IN" in labs and gap_in <= 2.2:
        return "checkin_pray"
    if labs and labs <= {"CHECK-IN", "PRAY"} and gap_in <= 2.2:
        return "checkin_pray"
    if "LOOK BACK" in labs or "OVERVIEW" in labs:
        return "lookback_overview"
    if "OBEY" in labs and "DISCUSS" in labs:
        return "obey" if gap_in >= 4.0 else "discuss"
    if "OBEY" in labs and "DISCUSS" not in labs and "ACTIVITY" not in labs:
        return "obey"
    if "DISCUSS" in labs and "OBEY" not in labs:
        return "discuss"
    if "ACTIVITY" in labs and gap_in >= 2.5:
        return "activity"
    if "PRAY" in labs and "ACTIVITY" in labs and gap_in >= 4.0:
        return "pray"
    if "PRAY" in labs and not labs & {"READ", "DISCUSS", "OBEY", "LOOK BACK", "OVERVIEW", "WATCH"}:
        if gap_in >= 4.0:
            return "pray"
    return "read_residual"


def measure_content_bottom_pt(page) -> float | None:
    """Lowest content ink, ignoring the footer band and the tall blue rail stroke."""
    bottoms: list[float] = []
    usable_cutoff = PAGE_HEIGHT_PT - FOOTER_MARGIN_PT + 6

    d = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if not (span.get("text") or "").strip():
                    continue
                y1 = span["bbox"][3]
                if y1 <= usable_cutoff:
                    bottoms.append(y1)

    for info in page.get_image_info():
        bbox = info.get("bbox")
        if not bbox:
            continue
        if bbox[3] <= usable_cutoff:
            bottoms.append(bbox[3])

    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        width = rect.x1 - rect.x0
        height = rect.y1 - rect.y0
        if height > 50 and width < 5:
            continue  # vertical blue bar
        if rect.y1 > usable_cutoff:
            continue
        if width > 100 or (height < 20 and width > 40):
            bottoms.append(rect.y1)

    return max(bottoms) if bottoms else None


def find_gap_slots(
    pdf_path: Path,
    *,
    min_gap_in: float = DEFAULT_MIN_GAP_IN,
    include_blank_even: bool = False,
    skip_cover: bool = True,
) -> list[GapSlot]:
    _require_fitz()
    doc = fitz.open(pdf_path)
    slots: list[GapSlot] = []
    try:
        for index, page in enumerate(doc):
            page_number = index + 1
            if skip_cover and page_number <= 2:
                continue
            text = page.get_text("text")
            labels = _page_labels(text)
            bottom = measure_content_bottom_pt(page)
            usable = PAGE_HEIGHT_PT - FOOTER_MARGIN_PT
            blank = bottom is None or (
                not any(line.strip() and not line.strip().isdigit() for line in text.splitlines())
                and (bottom is None or bottom < 120)
            )
            # Blank even verso: only page number near footer
            stripped_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            only_pagenum = len(stripped_lines) == 1 and stripped_lines[0].isdigit()
            if only_pagenum:
                blank = True
                gap_in = usable / 72.0
                bottom = None
            elif bottom is None:
                blank = True
                gap_in = usable / 72.0
            else:
                gap_in = (usable - bottom) / 72.0

            if blank and not include_blank_even:
                continue
            if gap_in < min_gap_in and not blank:
                continue

            context = classify_context(labels=labels, blank=blank, gap_in=gap_in)
            if context == "blank_even" and not include_blank_even:
                continue
            slots.append(
                GapSlot(
                    page_index=index,
                    page_number=page_number,
                    gap_in=gap_in,
                    context=context,
                    labels=labels,
                    content_bottom_pt=bottom,
                )
            )
    finally:
        doc.close()
    return slots


def _aspect(path: Path) -> float:
    with Image.open(path) as im:
        w, h = im.size
    return w / max(h, 1)


def _pick_image(
    slot: GapSlot,
    images_dir: Path,
    use_counts: dict[str, int],
) -> Path | None:
    pool = CONTEXT_POOLS.get(slot.context, CONTEXT_POOLS["read_residual"])
    # Prefer least-used images; allow reuse only after the pool is exhausted.
    candidates = [name for name in pool if (images_dir / name).exists()]
    if not candidates:
        return None

    prefer_landscape = slot.gap_in < 2.6
    prefer_portrait = slot.gap_in >= 4.0

    def score(name: str) -> tuple[int, int, float]:
        path = images_dir / name
        ratio = _aspect(path)
        uses = use_counts.get(name, 0)
        shape = 0
        if prefer_landscape and ratio >= 1.2:
            shape = 2
        elif prefer_portrait and ratio <= 0.95:
            shape = 2
        elif 0.85 <= ratio <= 1.25:
            shape = 1
        # Lower use count first (negate), then shape fit.
        return (-uses, shape, -abs(ratio - (1.6 if prefer_landscape else 0.75)))

    ranked = sorted(candidates, key=score, reverse=True)
    return images_dir / ranked[0]


def plan_placements(
    slots: list[GapSlot],
    images_dir: Path,
    *,
    pad_in: float = DEFAULT_PAD_IN,
    max_width_in: float = DEFAULT_MAX_WIDTH_IN,
    page_width_pt: float = 612.0,
) -> list[FillerPlacement]:
    use_counts: dict[str, int] = {}
    placements: list[FillerPlacement] = []
    pad = pad_in * 72.0
    max_w = max_width_in * 72.0
    footer_top = PAGE_HEIGHT_PT - FOOTER_MARGIN_PT

    for slot in slots:
        image_path = _pick_image(slot, images_dir, use_counts)
        if image_path is None:
            continue
        use_counts[image_path.name] = use_counts.get(image_path.name, 0) + 1

        content_bottom = slot.content_bottom_pt
        if content_bottom is None:
            # Full blank verso: keep generous margins; do not crowd session rhythm.
            top = 0.9 * 72.0
            bottom = footer_top - pad
        else:
            top = content_bottom + pad
            bottom = footer_top - pad
        avail_h = bottom - top
        if avail_h < 0.7 * 72.0:
            continue

        ratio = _aspect(image_path)
        # Fit inside available box, capped width, centered horizontally.
        width = min(max_w, page_width_pt - 2 * (0.55 * 72.0))
        height = width / ratio
        if height > avail_h:
            height = avail_h
            width = height * ratio
        # For very tall gaps with landscape art, don't stretch — leave quiet space.
        if height < 0.55 * 72.0:
            continue

        x0 = (page_width_pt - width) / 2.0
        # Center in the leftover band (B-filler preview method).
        y0 = top + max(0.0, (avail_h - height) / 2.0)
        if y0 + height > bottom:
            y0 = bottom - height
        placements.append(
            FillerPlacement(
                slot=slot,
                image_path=image_path,
                rect=(x0, y0, x0 + width, y0 + height),
            )
        )
    return placements


def apply_gap_fillers(
    input_pdf: Path,
    output_pdf: Path,
    images_dir: Path,
    *,
    min_gap_in: float = DEFAULT_MIN_GAP_IN,
    include_blank_even: bool = False,
    pad_in: float = DEFAULT_PAD_IN,
) -> list[FillerPlacement]:
    """Stamp decorative fillers into a copy of ``input_pdf``; return placements."""
    _require_fitz()
    slots = find_gap_slots(
        input_pdf,
        min_gap_in=min_gap_in,
        include_blank_even=include_blank_even,
    )
    placements = plan_placements(slots, images_dir, pad_in=pad_in)
    doc = fitz.open(input_pdf)
    try:
        for place in placements:
            page = doc[place.slot.page_index]
            page.insert_image(
                fitz.Rect(*place.rect),
                filename=str(place.image_path),
                keep_proportion=True,
                overlay=True,
            )
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf, deflate=True, garbage=3)
    finally:
        doc.close()
    return placements


def placements_report(placements: list[FillerPlacement]) -> str:
    lines = [
        f"Placed {len(placements)} decorative gap fillers:",
        "",
        "| Page | Gap | Context | Image |",
        "|---:|---:|---|---|",
    ]
    for p in placements:
        lines.append(
            f"| {p.slot.page_number} | {p.slot.gap_in:.2f}in | `{p.slot.context}` | `{p.image_path.name}` |"
        )
    return "\n".join(lines) + "\n"
