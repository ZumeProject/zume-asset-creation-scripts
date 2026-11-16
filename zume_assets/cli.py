"""CLI for Zume asset builds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .api import load_repo_root
from .book_assembler import OUTPUT_NAMES, assemble_book
from .gap_fillers import (
    apply_gap_fillers,
    default_images_dir,
    placements_report,
)
from .typst_render import compile_pdf, prepare_build_dir


def default_output_root(root: Path | None = None) -> Path:
    """Canonical finished-asset root: <repo>/output (never Agent Store docs/)."""
    return (root or load_repo_root()) / "output"


def default_pdf_path(lang: str, course_type: str, root: Path | None = None) -> Path:
    repo = root or load_repo_root()
    out_name = OUTPUT_NAMES[course_type].format(lang=lang)
    return default_output_root(repo) / lang / out_name


def build_pdf(lang: str, course_type: str, output: Path | None = None) -> Path:
    root = load_repo_root()
    build_dir = default_output_root(root) / lang / f"build-{course_type}"
    book = assemble_book(lang=lang, course_type=course_type, build_dir=build_dir)
    prepare_build_dir(build_dir, book)

    output_pdf = output or default_pdf_path(lang, course_type, root)
    compile_pdf(build_dir, output_pdf)
    return output_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zume-assets",
        description="Build Zume offline training assets from live zume6 APIs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build one or more asset targets")
    build.add_argument("--lang", default="en", help="Locale code (default: en)")
    build.add_argument(
        "--type",
        dest="course_type",
        default="10",
        choices=["10", "20", "intensive"],
        help="Course format: 10, 20, or intensive",
    )
    build.add_argument(
        "--targets",
        default="pdf",
        help="Comma-separated targets (only pdf is implemented)",
    )
    build.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional PDF output path override",
    )
    build.add_argument(
        "--gap-fillers",
        action="store_true",
        help="Stamp decorative bottom-gap images from images/ after Typst compile",
    )
    build.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="PNG library for --gap-fillers (default: <repo>/images)",
    )

    gap = sub.add_parser(
        "gap-fill",
        help="Stamp decorative bottom-gap fillers into an existing guidebook PDF",
    )
    gap.add_argument("--pdf", type=Path, required=True, help="Input Typst PDF")
    gap.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output PDF path (may equal --pdf to overwrite)",
    )
    gap.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="PNG library (default: <repo>/images)",
    )
    gap.add_argument(
        "--min-gap-in",
        type=float,
        default=1.35,
        help="Minimum leftover inches to fill (default: 1.35)",
    )
    gap.add_argument(
        "--include-blank-even",
        action="store_true",
        help="Also decorate blank even verso pages (off by default)",
    )

    args = parser.parse_args(argv)

    if args.command == "build":
        targets = [t.strip() for t in args.targets.split(",") if t.strip()]
        unsupported = [t for t in targets if t != "pdf"]
        if unsupported:
            print(
                f"Unsupported targets in this phase: {', '.join(unsupported)} "
                "(only pdf is implemented).",
                file=sys.stderr,
            )
            return 2
        try:
            pdf_path = build_pdf(args.lang, args.course_type, args.output)
            if args.gap_fillers:
                root = load_repo_root()
                images_dir = args.images_dir or default_images_dir(root)
                placements = apply_gap_fillers(pdf_path, pdf_path, images_dir)
                print(placements_report(placements), end="")
        except Exception as exc:
            print(f"Build failed: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {pdf_path}")
        return 0

    if args.command == "gap-fill":
        root = load_repo_root()
        images_dir = args.images_dir or default_images_dir(root)
        try:
            placements = apply_gap_fillers(
                args.pdf,
                args.output,
                images_dir,
                min_gap_in=args.min_gap_in,
                include_blank_even=args.include_blank_even,
            )
        except Exception as exc:
            print(f"Gap fill failed: {exc}", file=sys.stderr)
            return 1
        print(placements_report(placements), end="")
        print(f"Wrote {args.output}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
