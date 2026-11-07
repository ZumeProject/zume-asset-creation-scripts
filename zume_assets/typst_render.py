"""Compile book.json + Typst template into a PDF."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .api import load_repo_root


def find_typst() -> str:
    path = shutil.which("typst")
    if not path:
        raise RuntimeError(
            "typst binary not found on PATH. Install from https://github.com/typst/typst/releases"
        )
    return path


def preferred_font() -> str:
    """Pick a widely available sans font on Linux."""
    candidates = [
        "Liberation Sans",
        "DejaVu Sans",
        "Noto Sans",
        "FreeSans",
        "Arial",
    ]
    try:
        out = subprocess.check_output([find_typst(), "fonts"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return candidates[0]
    available = set(line.strip() for line in out.splitlines() if line.strip())
    for name in candidates:
        if name in available:
            return name
    return candidates[0]


def prepare_build_dir(build_dir: Path, book: dict) -> Path:
    """Copy template beside book.json and rewrite font if needed."""
    root = load_repo_root()
    template_src = root / "pdf" / "templates" / "book.typ"
    build_dir.mkdir(parents=True, exist_ok=True)
    typ_path = build_dir / "book.typ"
    text = template_src.read_text(encoding="utf-8")
    font = preferred_font()
    text = text.replace('font: "Liberation Sans"', f'font: "{font}"')
    typ_path.write_text(text, encoding="utf-8")
    return typ_path


def compile_pdf(build_dir: Path, output_pdf: Path) -> Path:
    typst = find_typst()
    typ_path = build_dir / "book.typ"
    if not typ_path.exists():
        raise FileNotFoundError(f"Missing Typst entrypoint: {typ_path}")
    if not (build_dir / "book.json").exists():
        raise FileNotFoundError(f"Missing book.json in {build_dir}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        typst,
        "compile",
        "--root",
        str(build_dir),
        str(typ_path),
        str(output_pdf),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "typst compile failed:\n"
            + (proc.stderr or proc.stdout or "(no output)")
        )
    return output_pdf
