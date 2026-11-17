---
name: build-language-assets
description: Use when building or rebuilding Zúme offline assets for a locale — Typst PDF guidebooks, Keynote decks, course types 10/20/intensive, gap fillers, or language asset pipelines in zume-asset-creation-scripts.
---

# Build language assets (PDF + Keynote)

## Overview

Production deliverables are **Typst PDF** and **Keynote** under `output/{lang}/`. PPTX is not a production target.

## Quick path

### PDF (any OS with Typst)

```bash
pip install -e ".[dev]"
python3 -m zume_assets build --lang <lang> --type <10|20|intensive> --targets pdf
# EN decorative bottom gaps:
python3 -m zume_assets build --lang en --type 10 --targets pdf --gap-fillers
```

Outputs: `output/{lang}/Zume-Training-*-{lang}.pdf` plus `output/{lang}/build-{type}/`.

### Keynote (macOS only)

Needs a presenter capture pack + local MP4s. Follow [mac-keynote-assemble](../mac-keynote-assemble/SKILL.md) after [vimeo-download-provenance](../vimeo-download-provenance/SKILL.md) for EN videos.

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type <type> --lang <lang>
python3 slides/assemble-keynote/embed_videos_choose.py --type <type> --lang <lang> --promote
```

## Rules

- CLI `--targets` accepts **pdf only**; reject/restore neither `pptx` nor `keynote` as CLI targets.
- Do not write finished PDFs/Keynote into Agent Store `docs/` — see [output-paths-worktrees](../output-paths-worktrees/SKILL.md).
- English is the signed-off review locale; other langs share the same Typst path (Arabic/CJK need fonts).

## Common mistakes

| Mistake | Fix |
|---|---|
| Building PPTX | Stop — production is PDF + Keynote only |
| Running Keynote scripts on Linux CI | Use Mac / Creator Studio |
| Skipping gap fillers when Chris asked for EN decorative fills | Pass `--gap-fillers` or `gap-fill` subcommand |
