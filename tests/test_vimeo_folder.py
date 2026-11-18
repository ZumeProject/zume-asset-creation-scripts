"""Offline unit tests for Vimeo folder helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "slides" / "videos"))
from vimeo_folder import (  # noqa: E402
    EN_VIMEO_FOLDER_ID,
    assert_en_folder_id,
    folder_id_for_language,
    numeric_id_from_title,
    provenance_matches_folder,
    write_provenance,
)


class VimeoFolderTests(unittest.TestCase):
    def test_en_folder_id_is_21862752(self) -> None:
        folder_id, name = folder_id_for_language("en")
        self.assertEqual(folder_id, "21862752")
        self.assertEqual(assert_en_folder_id(), EN_VIMEO_FOLDER_ID)
        self.assertTrue(name)

    def test_pus_folder_id_is_29862924(self) -> None:
        folder_id, name = folder_id_for_language("pus")
        self.assertEqual(folder_id, "29862924")
        self.assertTrue(name)

    def test_numeric_id_from_title(self) -> None:
        self.assertEqual(numeric_id_from_title("(01) God Uses Ordinary People"), 1)
        self.assertEqual(numeric_id_from_title("01_God Uses Ordinary People"), 1)
        self.assertEqual(numeric_id_from_title("33. 3 Circles"), 33)
        self.assertEqual(numeric_id_from_title("70 Intro"), 70)
        self.assertIsNone(numeric_id_from_title(""))

    def test_provenance_matches_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_provenance(
                root,
                {
                    "source": "vimeo",
                    "folder_id": EN_VIMEO_FOLDER_ID,
                    "videos": {"1": {"vimeo_id": "x"}},
                },
            )
            self.assertTrue(provenance_matches_folder(root))
            self.assertFalse(provenance_matches_folder(root, folder_id="999"))


if __name__ == "__main__":
    unittest.main()
