---
name: build-language-assets
description: Use when building or rebuilding Zúme offline assets for a locale — Typst PDF guidebooks, Keynote decks, course types 10/20/intensive, gap fillers, or language asset pipelines in zume-asset-creation-scripts.
---

# Build language assets (PDF + Keynote)

## Overview

Production deliverables are **Typst PDF** and **Keynote** under `output/{lang}/`. PPTX is not a production target.

**First step (required):** readiness checklist. Do not skip. `zume-assets build` auto-runs it and aborts before Typst when the Vimeo folder map is missing.

## Prerequisites checklist (start here)

```bash
python3 -m zume_assets prereqs --lang <lang>
# PDF path (map BLOCK; videos/packs NOTE):
python3 -m zume_assets prereqs --lang <lang> --pdf-only
```

| Check | Where | If missing |
|---|---|---|
| Vimeo folder map | `slide-builder/parts/vimeo-folders.json` | Ask Chris for folder id (user `75461893`); **do not invent**. Add map entry. Known: `en`→`21862752`, `es`→`269525`, `pus`→`29862924`. |
| Local MP4s + `SOURCE.json` | `build/{lang}/videos/` | `python3 slides/videos/download_lang_vimeo.py --lang <lang>` (needs credentials) |
| Capture packs | `build/{lang}/captures/{10\|20\|intensive}/` | Capture via `slides/capture/capture_presenter.py`. `videos/` links to `build/{lang}/videos` |

Gate behavior:

- Default PDF `build` → missing **map** aborts; missing videos/packs print `[NOTE]` and continue (not a finished Keynote pack).
- `build --full-pack` or Keynote assemble → every gap is `[BLOCK]`.

## Quick path

### PDF (any OS with Typst)

```bash
pip install -e ".[dev]"
python3 -m zume_assets prereqs --lang <lang> --pdf-only
# Gap fillers ON by default (decorative bottom-gap images from images/):
python3 -m zume_assets build --lang <lang> --type <10|20|intensive> --targets pdf
# Typst-only draft (not for sign-off):
python3 -m zume_assets build --lang <lang> --type <type> --targets pdf --no-gap-fillers
```

Outputs: `output/{lang}/Zume-Training-*-{lang}.pdf` plus Typst intermediates in `build/{lang}/{type}/`.

Diagram images (pace / Four Fields / Gen Mapping) download from presenter `images.*` during assemble. Locale scripts that omit `{{ paceN_image }}` shortcodes are merged with English shortcode slots. Missing required diagrams **hard-fail** the build. Decorative gap fillers are **on by default**; a missing/empty `images/` library also fails the build.

### Keynote (macOS only)

Full prereqs must be clean. Follow [vimeo-download-provenance](../vimeo-download-provenance/SKILL.md) then [mac-keynote-assemble](../mac-keynote-assemble/SKILL.md).

```bash
python3 -m zume_assets prereqs --lang <lang>
python3 slides/assemble-keynote/assemble_images_keynote.py --type <type> --lang <lang>
python3 slides/assemble-keynote/embed_videos_choose.py --type <type> --lang <lang> --promote
```

## Rules

- CLI `--targets` accepts **pdf only**; reject/restore neither `pptx` nor `keynote` as CLI targets.
- Do not write finished PDFs/Keynote into Agent Store `docs/` — see [output-paths-worktrees](../output-paths-worktrees/SKILL.md).
- English is the signed-off review locale; other langs share the same Typst path (Arabic/CJK need fonts).
- Production / signed-off PDFs use default gap fillers (same as EN/ES). Do not ship `--no-gap-fillers` as done.
- Agents must not skip `prereqs` / the build gate.

## Common mistakes

| Mistake | Fix |
|---|---|
| Building PPTX | Stop — production is PDF + Keynote only |
| Running Keynote scripts on Linux CI | Use Mac / Creator Studio |
| Reporting a Typst-only draft (`--no-gap-fillers`) as a finished pack | Rebuild without the flag (fillers are default) |
| Skipping readiness / inventing a Vimeo folder id | Run `prereqs`; ask Chris for a real folder id |
| Reporting PDF-only success when Keynote was expected | Use `--full-pack` or fix NOTE items before Keynote |
