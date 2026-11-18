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
| Local MP4s + `SOURCE.json` | `output/{lang}/videos/` | `python3 slides/videos/download_lang_vimeo.py --lang <lang>` (needs credentials) |
| Capture packs | Agent Store `media/{lang}-{10\|20\|intensive}-presenter-captures/` | Capture via `slides/capture/capture_presenter.py` or obtain approved pack |

Gate behavior:

- Default PDF `build` → missing **map** aborts; missing videos/packs print `[NOTE]` and continue (not a finished Keynote pack).
- `build --full-pack` or Keynote assemble → every gap is `[BLOCK]`.

## Quick path

### PDF (any OS with Typst)

```bash
pip install -e ".[dev]"
python3 -m zume_assets prereqs --lang <lang> --pdf-only
# Production packs always stamp decorative gap fillers:
python3 -m zume_assets build --lang <lang> --type <10|20|intensive> --targets pdf --gap-fillers
```

Outputs: `output/{lang}/Zume-Training-*-{lang}.pdf` plus `output/{lang}/build-{type}/`.

Diagram images (pace / Four Fields / Gen Mapping) download from presenter `images.*` during assemble. Locale scripts that omit `{{ paceN_image }}` shortcodes are merged with English shortcode slots. Missing required diagrams **hard-fail** the build.

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
- Production PDFs use `--gap-fillers` (same as EN/ES signed-off packs).
- Agents must not skip `prereqs` / the build gate.

## Common mistakes

| Mistake | Fix |
|---|---|
| Building PPTX | Stop — production is PDF + Keynote only |
| Running Keynote scripts on Linux CI | Use Mac / Creator Studio |
| Skipping gap fillers on a production language pack | Pass `--gap-fillers` |
| Skipping readiness / inventing a Vimeo folder id | Run `prereqs`; ask Chris for a real folder id |
| Reporting PDF-only success when Keynote was expected | Use `--full-pack` or fix NOTE items before Keynote |
