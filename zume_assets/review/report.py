"""Shared review report helpers (JSON + markdown, exit status)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_report(
    report: dict[str, Any],
    report_dir: Path,
    *,
    stem: str,
) -> tuple[Path, Path]:
    """Write report.json and report.md; return (json_path, md_path)."""
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: dict[str, Any]) -> str:
    status = str(report.get("status") or "unknown").upper()
    kind = str(report.get("kind") or "review")
    lang = report.get("lang", "?")
    course_type = report.get("type", "?")
    lines = [
        f"# Review: {kind}",
        "",
        f"- **Status:** {status}",
        f"- **Locale:** `{lang}`",
        f"- **Course type:** `{course_type}`",
        f"- **Generated:** {report.get('generated_at', '')}",
        "",
    ]
    summary = report.get("summary") or {}
    if summary:
        lines.append("## Summary")
        lines.append("")
        for key, value in summary.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    failures = report.get("failures") or []
    if failures:
        lines.append("## Failures")
        lines.append("")
        for item in failures:
            if isinstance(item, dict):
                msg = item.get("message") or item.get("id") or json.dumps(item, ensure_ascii=False)
                lines.append(f"- {msg}")
            else:
                lines.append(f"- {item}")
        lines.append("")
    else:
        lines.append("## Failures")
        lines.append("")
        lines.append("_None._")
        lines.append("")

    notes = report.get("notes") or []
    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines) + "\n"


def exit_code_for(report: dict[str, Any]) -> int:
    """Non-zero when status is not pass (mismatches / decode errors)."""
    status = str(report.get("status") or "").lower()
    if status == "pass":
        return 0
    if status == "error":
        return 2
    return 1
