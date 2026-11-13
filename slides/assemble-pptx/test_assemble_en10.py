#!/usr/bin/env python3
"""Unit tests for EN 10 PPTX assembler against store manifest.json."""
from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from assemble_en10 import (
    PNG_PX,
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    build_pptx,
    count_present_pngs,
    make_placeholder_png,
    normalize_manifest,
    pack_ready,
    resolve_slide_image,
    slide_png_path,
)

STORE_PACK = Path(
    "/cursor/stores/bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f/media/en-10-presenter-captures"
)
STORE_MANIFEST = STORE_PACK / "manifest.json"


def _unique_mp4(path: Path, tag: str, size: int = 120_000) -> Path:
    payload = b"ftyp" + tag.encode("utf-8")[:12].ljust(12, b"_")
    path.write_bytes(payload + b"\x00" * max(0, size - len(payload)))
    return path


class ManifestContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not STORE_MANIFEST.exists():
            raise unittest.SkipTest(f"store manifest missing: {STORE_MANIFEST}")
        cls.raw = json.loads(STORE_MANIFEST.read_text(encoding="utf-8"))
        cls.manifest = normalize_manifest(cls.raw)

    def test_slide_count_near_reference(self) -> None:
        slides = self.manifest["slides"]
        self.assertGreaterEqual(len(slides), 188)
        self.assertLessEqual(len(slides), 189)
        self.assertEqual(self.manifest["slide_count"], len(slides))

    def test_video_slots_near_reference(self) -> None:
        slots = self.manifest["video_slots"]
        # Reference PPSX has 28; normalize also embeds t10_e/t10_g thoughts
        self.assertGreaterEqual(len(slots), 27)
        self.assertLessEqual(len(slots), 29)
        keys = [s["key"] for s in slots]
        self.assertEqual(keys[0], "t1_b")
        self.assertEqual(keys[-1], "t30_b")
        ids = [str(s["video_id"]) for s in slots]
        self.assertEqual(len(ids), len(set(ids)))

    def test_viewport_or_default_matches_reference_png(self) -> None:
        px = self.manifest.get("expected_png_px") or list(PNG_PX)
        self.assertEqual(tuple(px), (3692, 2068))
        self.assertEqual(PNG_PX, (3692, 2068))

    def test_ordered_indexes_and_final_slides(self) -> None:
        slides = self.manifest["slides"]
        self.assertEqual(slides[0]["key"], "s1_1_1")
        self.assertEqual(slides[0]["index"], 1)
        self.assertEqual(slides[-1]["key"], "final")
        finals = [s for s in slides if s["key"] == "final"]
        self.assertEqual(len(finals), 10)
        congrats = [s for s in slides if s["key"] == "congratulations"]
        self.assertEqual(len(congrats), 1)

    def test_png_path_resolves_under_pngs(self) -> None:
        slide = self.manifest["slides"][0]
        path = slide_png_path(STORE_PACK, slide)
        self.assertEqual(path.parent.name, "pngs")
        self.assertTrue(str(path).endswith(".png"))


class AssemblerUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not STORE_MANIFEST.exists():
            raise unittest.SkipTest(f"store manifest missing: {STORE_MANIFEST}")
        cls.raw = json.loads(STORE_MANIFEST.read_text(encoding="utf-8"))
        cls.manifest = normalize_manifest(cls.raw)

    def test_placeholder_png_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "ph.png"
            make_placeholder_png(dest, index=1, key="s1_1_1", session=1)
            from PIL import Image

            with Image.open(dest) as im:
                self.assertEqual(im.size, (3692, 2068))

    def test_resolve_uses_placeholder_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            pack = Path(td)
            slide = {
                "index": 1,
                "session": 1,
                "key": "s1_1_1",
                "png": "001_s1_1_1.png",
            }
            path, is_ph = resolve_slide_image(pack, slide, allow_placeholders=True)
            self.assertTrue(is_ph)
            self.assertTrue(path.exists())
            with self.assertRaises(FileNotFoundError):
                resolve_slide_image(pack, slide, allow_placeholders=False)

    def test_build_pptx_with_all_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pack = root / "pack"
            pack.mkdir()
            (pack / "manifest.json").write_text(json.dumps(self.raw), encoding="utf-8")
            (pack / "pngs").mkdir()
            videos: dict[str, Path] = {}
            vdir = root / "videos"
            vdir.mkdir()
            for slot in self.manifest["video_slots"]:
                vid = str(slot["video_id"])
                videos[vid] = _unique_mp4(vdir / f"{vid}.mp4", tag=vid)

            out = root / "out.pptx"
            stats = build_pptx(
                self.manifest,
                pack,
                videos,
                out,
                allow_placeholders=True,
                skip_missing_videos=False,
            )
            self.assertTrue(out.exists())
            self.assertEqual(stats["slide_count"], 189)
            self.assertEqual(stats["placeholders"], 189)
            self.assertEqual(stats["video_embedded"], len(self.manifest["video_slots"]))
            self.assertEqual(stats["slide_width_emu"], int(SLIDE_WIDTH))
            self.assertEqual(stats["slide_height_emu"], int(SLIDE_HEIGHT))

            with zipfile.ZipFile(out) as z:
                slide_files = [
                    n
                    for n in z.namelist()
                    if n.startswith("ppt/slides/slide") and n.endswith(".xml")
                ]
                self.assertEqual(len(slide_files), 189)
                pres = z.read("ppt/presentation.xml").decode("utf-8")
                self.assertIn(f'cx="{int(SLIDE_WIDTH)}"', pres)
                self.assertIn(f'cy="{int(SLIDE_HEIGHT)}"', pres)
                media = [n for n in z.namelist() if n.startswith("ppt/media/")]
                mp4s = [n for n in media if n.endswith(".mp4")]
                self.assertEqual(len(mp4s), len(self.manifest["video_slots"]))
                video_slides = 0
                for n in z.namelist():
                    if n.startswith("ppt/slides/_rels/") and n.endswith(".rels"):
                        if "relationships/video" in z.read(n).decode("utf-8", "ignore"):
                            video_slides += 1
                self.assertEqual(video_slides, len(self.manifest["video_slots"]))

    def test_pack_ready_counts_existing_store_pngs(self) -> None:
        present, total, missing = count_present_pngs(self.manifest, STORE_PACK)
        self.assertEqual(total, 189)
        self.assertEqual(present + len(missing), 189)
        ready, _ = pack_ready(self.manifest, STORE_PACK)
        self.assertEqual(ready, present >= total)


if __name__ == "__main__":
    unittest.main()
