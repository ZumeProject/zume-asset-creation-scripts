"""CLI for Zume asset builds, pipeline review, and GCS publish."""

from __future__ import annotations

import argparse
import json
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


def _add_lang_type(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lang", default="en", help="Locale code (default: en)")
    parser.add_argument(
        "--type",
        dest="course_type",
        default="10",
        choices=["10", "20", "intensive"],
        help="Course format: 10, 20, or intensive",
    )


def _cmd_review(argv: list[str] | None) -> int:
    from .review.master import fetch_master
    from .review.paths import report_dir
    from .review.qr_check import check_qr
    from .review.report import exit_code_for, utc_now_iso, write_report
    from .review.video_check import check_videos

    parser = argparse.ArgumentParser(
        prog="zume-assets review",
        description="Pipeline review: master list, QR decode, Keynote video mapping.",
    )
    sub = parser.add_subparsers(dest="review_command", required=True)

    fetch_p = sub.add_parser(
        "fetch-master",
        help="Fetch on-demand master list from api.zume.training into manifest/review/",
    )
    _add_lang_type(fetch_p)
    fetch_p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override master JSON path (default: manifest/review/{lang}-{type}.json)",
    )
    fetch_p.add_argument(
        "--follow-redirects",
        action="store_true",
        help="Probe live QR redirect destinations (network)",
    )

    qr_p = sub.add_parser(
        "qr",
        help="Decode build QR PNGs and compare to master (+ optional --live redirects)",
    )
    _add_lang_type(qr_p)
    qr_p.add_argument("--master", type=Path, default=None, help="Master JSON path")
    qr_p.add_argument("--qr-dir", type=Path, default=None, help="Directory of QR PNGs")
    qr_p.add_argument("--book", type=Path, default=None, help="book.json for assembler cross-check")
    qr_p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Report output dir (default: output/{lang}/review)",
    )
    qr_p.add_argument(
        "--live",
        action="store_true",
        help="Follow decoded QR URLs and check destinations (network)",
    )

    vid_p = sub.add_parser(
        "videos",
        help="Compare pack/SOURCE video ids+titles to master online metadata",
    )
    _add_lang_type(vid_p)
    vid_p.add_argument("--master", type=Path, default=None, help="Master JSON path")
    vid_p.add_argument(
        "--source",
        type=Path,
        default=None,
        help="SOURCE.json path (default: output/{lang}/videos/SOURCE.json)",
    )
    vid_p.add_argument(
        "--pack",
        type=Path,
        default=None,
        help="Keynote capture pack dir (manifest.json / work/video-replace-list.json)",
    )
    vid_p.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Report output dir (default: output/{lang}/review)",
    )

    all_p = sub.add_parser(
        "all",
        help="Run QR + video checks (optionally fetch master first)",
    )
    _add_lang_type(all_p)
    all_p.add_argument(
        "--fetch",
        action="store_true",
        help="Refresh master from live API before checks (network)",
    )
    all_p.add_argument(
        "--follow-redirects",
        action="store_true",
        help="With --fetch, also probe redirect destinations",
    )
    all_p.add_argument("--master", type=Path, default=None, help="Master JSON path")
    all_p.add_argument("--qr-dir", type=Path, default=None)
    all_p.add_argument("--book", type=Path, default=None)
    all_p.add_argument("--source", type=Path, default=None)
    all_p.add_argument("--pack", type=Path, default=None)
    all_p.add_argument("--report-dir", type=Path, default=None)
    all_p.add_argument("--live", action="store_true", help="Live QR redirect checks")

    args = parser.parse_args(argv)

    if args.review_command == "fetch-master":
        try:
            data, path = fetch_master(
                args.lang,
                args.course_type,
                output=args.output,
                follow_redirects=args.follow_redirects,
            )
        except Exception as exc:
            print(f"fetch-master failed: {exc}", file=sys.stderr)
            return 1
        counts = data.get("counts") or {}
        print(
            f"Wrote {path} "
            f"(checkins={counts.get('checkins')} videos={counts.get('videos')} "
            f"activities={counts.get('activities')})"
        )
        return 0

    if args.review_command == "qr":
        report = check_qr(
            args.lang,
            args.course_type,
            master_path=args.master,
            qr_dir=args.qr_dir,
            book_path=args.book,
            report_dir=args.report_dir,
            live=args.live,
        )
        out = args.report_dir or report_dir(args.lang)
        print(f"QR review {report.get('status')}: {out / f'qr-{args.course_type}.json'}")
        return exit_code_for(report)

    if args.review_command == "videos":
        report = check_videos(
            args.lang,
            args.course_type,
            master_path=args.master,
            source_path=args.source,
            pack=args.pack,
            report_dir_path=args.report_dir,
        )
        out = args.report_dir or report_dir(args.lang)
        print(f"Video review {report.get('status')}: {out / f'videos-{args.course_type}.json'}")
        return exit_code_for(report)

    if args.review_command == "all":
        if args.fetch:
            try:
                _data, path = fetch_master(
                    args.lang,
                    args.course_type,
                    output=args.master,
                    follow_redirects=args.follow_redirects,
                )
                print(f"Wrote master {path}")
            except Exception as exc:
                print(f"fetch-master failed: {exc}", file=sys.stderr)
                return 1
        qr_report = check_qr(
            args.lang,
            args.course_type,
            master_path=args.master,
            qr_dir=args.qr_dir,
            book_path=args.book,
            report_dir=args.report_dir,
            live=args.live,
        )
        vid_report = check_videos(
            args.lang,
            args.course_type,
            master_path=args.master,
            source_path=args.source,
            pack=args.pack,
            report_dir_path=args.report_dir,
        )
        out = args.report_dir or report_dir(args.lang)
        combined_status = (
            "pass"
            if qr_report.get("status") == "pass" and vid_report.get("status") == "pass"
            else "fail"
        )
        if qr_report.get("status") == "error" or vid_report.get("status") == "error":
            combined_status = "error"
        combined = {
            "kind": "all",
            "status": combined_status,
            "lang": args.lang,
            "type": args.course_type,
            "generated_at": utc_now_iso(),
            "summary": {
                "qr_status": qr_report.get("status"),
                "videos_status": vid_report.get("status"),
            },
            "failures": list(qr_report.get("failures") or [])
            + list(vid_report.get("failures") or []),
            "notes": [
                f"qr report: {out / f'qr-{args.course_type}.json'}",
                f"videos report: {out / f'videos-{args.course_type}.json'}",
            ],
        }
        write_report(combined, out, stem=f"all-{args.course_type}")
        print(f"Review all {combined_status}: {out / f'all-{args.course_type}.json'}")
        return exit_code_for(combined)

    parser.print_help()
    return 2


def _parse_course_types(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return ("10", "20", "intensive")
    types = tuple(t.strip() for t in raw.split(",") if t.strip())
    allowed = {"10", "20", "intensive"}
    bad = [t for t in types if t not in allowed]
    if bad:
        raise ValueError(f"Unknown course type(s): {', '.join(bad)}")
    return types


def _cmd_publish(argv: list[str] | None) -> int:
    from .publish.upload import upload_pack
    from .publish.verify import verify_downloads

    parser = argparse.ArgumentParser(
        prog="zume-assets publish",
        description=(
            "Upload approved PDF + Keynote + PPTX packs to gs://zume-file-mirror/{lang}/ "
            "(overwrites same-named objects on --execute) and verify downloads on "
            "api.zume.training."
        ),
    )
    sub = parser.add_subparsers(dest="publish_command", required=True)

    up = sub.add_parser(
        "upload",
        help="Upload local output/{lang}/ PDF + Keynote + PPTX (dry-run by default)",
    )
    up.add_argument("--lang", required=True, help="Locale code (e.g. es)")
    up.add_argument(
        "--types",
        default="10,20,intensive",
        help="Comma-separated course types (default: 10,20,intensive)",
    )
    up.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Override output/{lang} directory",
    )
    up.add_argument(
        "--execute",
        action="store_true",
        help="Actually run gcloud storage cp (default is dry-run)",
    )
    up.add_argument(
        "--include-videos",
        action="store_true",
        help="Also upload output/{lang}/videos/* (off by default; gitignored)",
    )
    up.add_argument(
        "--allow-missing",
        action="store_true",
        help="Dry-run even when some PDF/Keynote/PPTX files are missing",
    )
    up.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON plan/result",
    )

    ver = sub.add_parser(
        "verify-downloads",
        help=(
            "Assert downloads/{lang} lists expected PDF/Keynote/PPTX names "
            "(guidebook_*/keynote_*/powerpoint_*)"
        ),
    )
    ver.add_argument("--lang", required=True, help="Locale code (e.g. es)")
    ver.add_argument(
        "--types",
        default="10,20,intensive",
        help="Comma-separated course types (default: 10,20,intensive)",
    )
    ver.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )

    args = parser.parse_args(argv)

    try:
        course_types = _parse_course_types(args.types)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.publish_command == "upload":
        try:
            result = upload_pack(
                args.lang,
                course_types=course_types,
                lang_dir=args.dir,
                include_videos=args.include_videos,
                execute=args.execute,
                require_all=not args.allow_missing,
            )
        except Exception as exc:
            print(f"publish upload failed: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            mode = "EXECUTE" if args.execute else "DRY-RUN"
            print(f"publish upload [{mode}] lang={args.lang} status={result['status']}")
            for entry in result.get("plan", {}).get("files") or []:
                flag = "MISSING" if entry.get("missing") else "ok"
                size = entry.get("bytes")
                size_s = f" ({size} bytes)" if size is not None else ""
                print(f"  [{flag}] {entry['local']} -> {entry['gs_uri']}{size_s}")
            if not args.execute:
                print("Re-run with --execute to upload (requires gcloud auth).")
            else:
                print(f"Uploaded {len(result.get('uploaded') or [])} object(s).")
        if result.get("status") == "incomplete":
            return 1
        return 0

    if args.publish_command == "verify-downloads":
        report = verify_downloads(args.lang, course_types=course_types)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            print(
                f"verify-downloads {report.get('status')}: "
                f"{report.get('api')} (download_id={report.get('download_id')})"
            )
            for check in report.get("checks") or []:
                mark = "ok" if check.get("ok") else "FAIL"
                print(
                    f"  [{mark}] {check['field']}: "
                    f"expected={check['expected']!r} actual={check['actual']!r}"
                )
            for note in report.get("notes") or []:
                print(f"  note: {note}")
            for fail in report.get("failures") or []:
                if fail.get("field") is None:
                    print(f"  error: {fail.get('detail')}")
        if report.get("status") == "pass":
            return 0
        return 1

    parser.print_help()
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zume-assets",
        description="Build Zume offline training assets from live zume6 APIs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build one or more asset targets")
    _add_lang_type(build)
    build.add_argument(
        "--targets",
        default="pdf",
        help="Comma-separated targets (only pdf; Keynote uses slides/assemble-keynote)",
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
    gap.add_argument(
        "--type",
        dest="course_type",
        default=None,
        choices=["10", "20", "intensive"],
        help="Course format for page-image overrides (e.g. EN10 Lord's Supper on p51)",
    )

    sub.add_parser(
        "review",
        help="Pipeline review (fetch-master / qr / videos / all); see: zume-assets review -h",
        add_help=False,
    )
    sub.add_parser(
        "publish",
        help="GCS upload + downloads verify; see: zume-assets publish -h",
        add_help=False,
    )

    # Peek at argv so nested commands use their own subparsers.
    raw = list(argv) if argv is not None else sys.argv[1:]
    if raw and raw[0] == "review":
        return _cmd_review(raw[1:])
    if raw and raw[0] == "publish":
        return _cmd_publish(raw[1:])

    args = parser.parse_args(argv)

    if args.command == "build":
        targets = [t.strip() for t in args.targets.split(",") if t.strip()]
        unsupported = [t for t in targets if t != "pdf"]
        if unsupported:
            print(
                f"Unsupported targets: {', '.join(unsupported)} "
                "(only pdf is supported by this CLI; Keynote uses "
                "slides/assemble-keynote; pptx is not a production target).",
                file=sys.stderr,
            )
            return 2
        try:
            pdf_path = build_pdf(args.lang, args.course_type, args.output)
            if args.gap_fillers:
                root = load_repo_root()
                images_dir = args.images_dir or default_images_dir(root)
                placements = apply_gap_fillers(
                    pdf_path,
                    pdf_path,
                    images_dir,
                    course_type=args.course_type,
                )
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
                course_type=args.course_type,
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
