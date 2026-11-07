"""CLI for Zume asset builds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .api import load_repo_root
from .book_assembler import OUTPUT_NAMES, assemble_book
from .typst_render import compile_pdf, prepare_build_dir


def build_pdf(lang: str, course_type: str, output: Path | None = None) -> Path:
    root = load_repo_root()
    build_dir = root / "output" / lang / f"build-{course_type}"
    book = assemble_book(lang=lang, course_type=course_type, build_dir=build_dir)
    prepare_build_dir(build_dir, book)

    out_name = OUTPUT_NAMES[course_type].format(lang=lang)
    output_pdf = output or (root / "output" / lang / out_name)
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
        help="Comma-separated targets (Phase 1 supports: pdf)",
    )
    build.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional PDF output path override",
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
        except Exception as exc:
            print(f"Build failed: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote {pdf_path}")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
