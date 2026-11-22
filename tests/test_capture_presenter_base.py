"""Presenter capture must default to production and refuse localhost QR hosts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "slides" / "capture" / "capture_presenter.py"


def _load():
    spec = importlib.util.spec_from_file_location("capture_presenter", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_prod_default_is_zume_training():
    cap = _load()
    assert cap.PROD_BASE == "https://zume.training"
    assert not cap.is_nonprod_base(cap.PROD_BASE)


@pytest.mark.parametrize(
    "base",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://myapp.local",
    ],
)
def test_nonprod_bases_detected(base):
    cap = _load()
    assert cap.is_nonprod_base(base)


def test_build_items_uses_repo_manifest_not_zume6():
    cap = _load()
    items = cap.build_items("10", "https://zume.training", "de")
    assert len(items) == 189
    assert items[0]["key"] == "s1_1_1"
    assert items[4]["key"] == "t1_a"
    assert items[5]["key"] == "t1_b"
    assert items[5]["video_id"] == "1"
    assert items[-2]["key"] == "congratulations"
    assert items[-1]["key"] == "final"
    assert "zume6" not in items[0]["url"]
    assert items[0]["url"].startswith("https://zume.training/de/presenter?")
    assert len(cap.build_items("20", "https://zume.training", "de")) == 268
    assert len(cap.build_items("intensive", "https://zume.training", "de")) == 158


def test_main_refuses_localhost_without_flag():
    cap = _load()
    with pytest.raises(SystemExit) as exc:
        cap.main(["--lang", "en", "--type", "10", "--base", "http://localhost:3000", "--limit", "1"])
    assert "Refusing non-production" in str(exc.value)
