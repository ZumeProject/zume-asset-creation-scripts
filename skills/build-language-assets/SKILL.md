---
name: build-language-assets
description: Use when building or rebuilding Zúme offline assets for a locale — Typst PDF guidebooks, Keynote decks, course types 10/20/intensive, gap fillers, or language asset pipelines in zume-asset-creation-scripts.
---

# Build language assets (PDF + Keynote)

## Overview

Production deliverables are **Typst PDF** and **Keynote** under `output/{lang}/`. PPTX is not a production target.

**PDF-only is not a full pack.** If the user asked for Keynote/videos (or “build the language”), run prerequisites first and stop on `BLOCK` — do not report silent PDF success as done.

## Prerequisites checklist (full pack)

```bash
python3 -m zume_assets prereqs --lang <lang>
```

| Check | Where | If missing |
|---|---|---|
| Vimeo folder map | `slide-builder/parts/vimeo-folders.json` | Ask Chris for folder id (user `75461893`); **do not invent**. Add map entry. Known: `en`→`21862752`, `es`→`269525`. |
| Local MP4s + `SOURCE.json` | `output/{lang}/videos/` | `python3 slides/videos/download_lang_vimeo.py --lang <lang>` (needs credentials) |
| Capture packs | Agent Store `media/{lang}-{10\|20\|intensive}-presenter-captures/` | Capture via `slides/capture/capture_presenter.py` or obtain approved pack |

Pashto (`pus`) historically had capture packs but **no Vimeo map entry** — Keynote stays blocked until a folder exists and is mapped.

## Quick path

### PDF (any OS with Typst)

```bash
pip install -e ".[dev]"
# Production packs always stamp decorative gap fillers:
python3 -m zume_assets build --lang <lang> --type <10|20|intensive> --targets pdf --gap-fillers
```

Outputs: `output/{lang}/Zume-Training-*-{lang}.pdf` plus `output/{lang}/build-{type}/`.

Diagram images (pace / Four Fields / Gen Mapping) download from presenter `images.*` during assemble. Locale scripts that omit `{{ paceN_image }}` shortcodes are merged with English shortcode slots. Missing required diagrams **hard-fail** the build.

### Keynote (macOS only)

Only after `prereqs` is clean. Follow [vimeo-download-provenance](../vimeo-download-provenance/SKILL.md) then [mac-keynote-assemble](../mac-keynote-assemble/SKILL.md).

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type <type> --lang <lang>
python3 slides/assemble-keynote/embed_videos_choose.py --type <type> --lang <lang> --promote
```

## Rules

- CLI `--targets` accepts **pdf only**; reject/restore neither `pptx` nor `keynote` as CLI targets.
- Do not write finished PDFs/Keynote into Agent Store `docs/` — see [output-paths-worktrees](../output-paths-worktrees/SKILL.md).
- English is the signed-off review locale; other langs share the same Typst path (Arabic/CJK need fonts).
- Production PDFs use `--gap-fillers` (same as EN/ES signed-off packs).

## Common mistakes

| Mistake | Fix |
|---|---|
| Building PPTX | Stop — production is PDF + Keynote only |
| Running Keynote scripts on Linux CI | Use Mac / Creator Studio |
| Skipping gap fillers on a production language pack | Pass `--gap-fillers` |
| Reporting PDF-only success when Keynote was expected | Run `prereqs`; fix BLOCK items or escalate to Chris |
| Inventing a Vimeo folder id for an unmapped lang | Wait for Chris; update `vimeo-folders.json` only with a real id |
