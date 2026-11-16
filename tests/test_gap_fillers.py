"""Unit tests for decorative gap-filler helpers (no live API)."""

from pathlib import Path

from PIL import Image
from zume_assets.gap_fillers import (
    GapSlot,
    _page_labels,
    classify_context,
    plan_placements,
)


def test_classify_lookback_overview():
    assert (
        classify_context(labels=["LOOK BACK", "OVERVIEW"], blank=False, gap_in=5.0)
        == "lookback_overview"
    )


def test_classify_discuss_and_obey():
    assert classify_context(labels=["DISCUSS"], blank=False, gap_in=3.5) == "discuss"
    assert classify_context(labels=["OBEY"], blank=False, gap_in=6.0) == "obey"
    assert (
        classify_context(labels=["DISCUSS", "OBEY"], blank=False, gap_in=5.5) == "obey"
    )


def test_classify_checkin_short():
    assert (
        classify_context(labels=["CHECK-IN", "PRAY"], blank=False, gap_in=1.6)
        == "checkin_pray"
    )
    assert (
        classify_context(labels=["CHECK-IN", "PRAY", "OBEY"], blank=False, gap_in=1.8)
        == "checkin_pray"
    )


def test_classify_blank_even():
    assert classify_context(labels=(), blank=True, gap_in=9.0) == "blank_even"


def test_classify_empty_labels_is_read_residual():
    assert classify_context(labels=(), blank=False, gap_in=2.0) == "read_residual"


def test_page_labels_ignore_prose_obey():
    text = (
        "Jesus said - Go and MAKE DISCIPLES of all nations,\n"
        "BAPTIZING them; and TEACHING them to\n"
        "obey all I have commanded. I will be with you always.\n"
    )
    assert _page_labels(text) == ()
    assert _page_labels("OBEY\n• Practice sharing\n") == ("OBEY",)


def test_plan_placements_picks_existing_images(tmp_path: Path):
    # Tiny transparent PNGs matching pool names used by lookback_overview.
    name = "A047-jesus-teaching-disciples.png"
    img = Image.new("RGBA", (200, 300), (0, 0, 0, 0))
    img.save(tmp_path / name)

    slot = GapSlot(
        page_index=15,
        page_number=16,
        gap_in=5.0,
        context="lookback_overview",
        labels=("LOOK BACK", "OVERVIEW"),
        content_bottom_pt=200.0,
    )
    placements = plan_placements([slot], tmp_path)
    assert len(placements) == 1
    assert placements[0].image_path.name == name
    x0, y0, x1, y1 = placements[0].rect
    assert x1 > x0 and y1 > y0
    assert y1 <= 792.0 - 72.0


def test_page_override_prefers_lords_supper(tmp_path: Path, monkeypatch):
    from zume_assets import gap_fillers as gf

    monkeypatch.setitem(gf.PAGE_IMAGE_OVERRIDES, 51, "A062-last-supper.png")
    supper = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    supper.save(tmp_path / "A062-last-supper.png")
    # Pool decoy that would otherwise win for obey.
    decoy = Image.new("RGBA", (200, 300), (0, 0, 0, 0))
    decoy.save(tmp_path / "A103-jesus-pointing.png")

    slot = GapSlot(
        page_index=50,
        page_number=51,
        gap_in=8.0,
        context="obey",
        labels=("OBEY",),
        content_bottom_pt=120.0,
    )
    placements = plan_placements([slot], tmp_path)
    assert len(placements) == 1
    assert placements[0].image_path.name == "A062-last-supper.png"
