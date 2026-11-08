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


# Latin body first; script fallbacks cover Arabic / CJK when Liberation lacks glyphs.
_LATIN_SANS = (
    "Liberation Sans",
    "DejaVu Sans",
    "Noto Sans",
    "FreeSans",
    "Arial",
)
_SCRIPT_FALLBACKS = (
    "Noto Sans Arabic",
    "Noto Naskh Arabic",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK TC",
    "Noto Sans CJK SC",
)


def preferred_font_stack() -> list[str]:
    """Ordered Typst font stack: Latin sans + available script fallbacks."""
    try:
        out = subprocess.check_output([find_typst(), "fonts"], text=True, stderr=subprocess.DEVNULL)
        available = set(line.strip() for line in out.splitlines() if line.strip())
    except Exception:
        available = set()

    stack: list[str] = []
    for name in _LATIN_SANS:
        if not available or name in available:
            stack.append(name)
            break
    if not stack:
        stack.append(_LATIN_SANS[0])
    for name in _SCRIPT_FALLBACKS:
        if not available or name in available:
            if name not in stack:
                stack.append(name)
    return stack


def preferred_font() -> str:
    """Primary Latin sans (kept for callers that want a single name)."""
    return preferred_font_stack()[0]


def prepare_build_dir(build_dir: Path, book: dict) -> Path:
    """Copy template + static assets beside book.json and rewrite font if needed."""
    root = load_repo_root()
    template_src = root / "pdf" / "templates" / "book.typ"
    assets_dir = root / "pdf" / "assets"
    build_dir.mkdir(parents=True, exist_ok=True)
    typ_path = build_dir / "book.typ"
    text = template_src.read_text(encoding="utf-8")
    stack = preferred_font_stack()
    font_expr = "(" + ", ".join(f'"{name}"' for name in stack) + ")"
    text = text.replace('font: ("Liberation Sans",)', f"font: {font_expr}")
    typ_path.write_text(text, encoding="utf-8")

    for name in ("cover-10.png", "zume-logo.png"):
        src = assets_dir / name
        if src.exists():
            shutil.copy2(src, build_dir / name)
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
