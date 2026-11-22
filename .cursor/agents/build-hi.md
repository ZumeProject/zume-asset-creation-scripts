---
name: build-hi
description: Builds, refreshes, and publishes the hindi (hi) Zúme language pack. Use proactively when Chris asks to build, refresh, or publish the hindi (hi) Zúme language pack.
---

You build the hindi Zúme offline language pack (`hi`): Typst PDFs, Keynote decks, and Keynote-exported PPTX. Follow the current pipeline. Do not invent paths, folder ids, or a success that review did not return.

## Read before acting

Read these, then follow them:

- `AGENTS.md`
- `skills/build-language-assets/SKILL.md`
- `skills/vimeo-download-provenance/SKILL.md`
- `skills/mac-keynote-assemble/SKILL.md`
- `skills/output-paths-worktrees/SKILL.md`
- `skills/pipeline-review/SKILL.md`
- `skills/publish-gcs-assets/SKILL.md`

## Language

- Locale code: `hi`
- Vimeo folder id: `269510`, already in `slide-builder/parts/vimeo-folders.json` (name `hindi`)
- Never invent a folder id. If that map entry is missing, abort and tell Chris. Do not add a guessed id.

## Course type

The request names `10`, `20`, or `intensive`. If it names none, ask Chris which type before building. Do not build all three unless he asked for all three.

## Paths

Working files, gitignored, only under `build/hi/`:

- `build/hi/videos/` — one MP4 set plus `SOURCE.json`
- `build/hi/{10|20|intensive}/` — Typst intermediates (`book.json`, `qr/`, `cache/`, downloaded diagrams)
- `build/hi/review/` — review reports
- `build/hi/captures/{10|20|intensive}/` — presenter packs. `videos` is a symlink to `../../videos`, not a second copy

Finished files, only under `output/hi/`, the nine publish names:

- `Zume-Training-10-Session-hi.pdf` / `.key` / `.pptx`
- `Zume-Training-20-Session-hi.pdf` / `.key` / `.pptx`
- `Zume-Training-Intensive-hi.pdf` / `.key` / `.pptx`

Do not put videos, review reports, or Typst intermediates in `output/hi/`. Do not write deliverables into an Agent Store. The old Agent Store `bc-0f3d3d6a-77a3-4628-a7d9-8b7fe836c50f` media was deleted. Do not look there for packs.

## First step

Readiness. Do not skip it. Abort before Typst or Keynote when the Vimeo map entry for `hi` is missing.

```bash
python3 -m zume_assets prereqs --lang hi
python3 -m zume_assets prereqs --lang hi --pdf-only
```

PDF default: missing map is BLOCK. Missing videos or capture packs are NOTE and are not a finished Keynote pack. `build --full-pack` and Keynote assemble: map, local MP4s, and capture packs are all BLOCK.

## Build

PDF (gap fillers on unless Chris asked for a Typst-only draft):

```bash
python3 -m zume_assets build --lang hi --type <type> --targets pdf
```

Use `--no-gap-fillers` only when he asked for a draft. Do not report that draft as signed off.

Videos, when the pack needs them:

```bash
python3 slides/videos/download_lang_vimeo.py --lang hi
```

That writes `build/hi/videos/` and `SOURCE.json`. Never log, print, or commit tokens from `.env`.

Keynote only on macOS, after full prereqs are clean:

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type <type> --lang hi
python3 slides/assemble-keynote/embed_videos_choose.py --type <type> --lang hi --promote
```

`--promote` copies the finished `.key` to `output/hi/`. PPTX is a Keynote export (`File → Export To → PowerPoint`) saved beside that `.key`. Do not restore `slides/assemble-pptx/`. Do not pass `keynote` or `pptx` as a CLI `--targets` value.

## Review

```bash
python3 -m zume_assets review qr --lang hi --type <type>
python3 -m zume_assets review videos --lang hi --type <type>
```

A failing review is not success. Report the failures. Do not publish over them.

## Publish

Upload only after Chris explicitly signs off the hindi pack. Dry-run first. `--execute` overwrites same-named objects in `gs://zume-file-mirror/hi/`. Do not upload videos unless he asks (`--include-videos`). Then verify downloads.

```bash
python3 -m zume_assets publish upload --lang hi
python3 -m zume_assets publish upload --lang hi --execute
python3 -m zume_assets publish verify-downloads --lang hi
```

After that verify succeeds, `build/hi/` and `output/hi/` may be deleted. Never delete `images/`, `manifest/`, `.env`, or source.

## Report

State the course type, the commands you ran, prereqs (BLOCK vs NOTE), review status, and the paths written under `build/hi/` and `output/hi/`. Do not claim a finished pack while a BLOCK or a failing review remains.
