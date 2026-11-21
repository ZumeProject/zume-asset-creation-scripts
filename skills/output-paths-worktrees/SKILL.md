---
name: output-paths-worktrees
description: Use when choosing where to write Zúme PDFs, Keynote, videos, or scratch trees — build/ working files, output/{lang}/ uploads, gitignore, git worktrees, or folder layout rules in zume-asset-creation-scripts.
---

# Output paths, gitignore, worktrees

## Overview

Finished uploads and working files both stay inside the **active repo checkout**. Agent Store holds notes/pointers, not deliverable binaries or capture packs.

After a language upload is verified, delete that language’s `build/{lang}/` and `output/{lang}/`.

## Canonical paths

| Kind | Path |
|---|---|
| Finished uploads (PDF, `.key`, PPTX) | `<repo>/output/{lang}/` — nine names only |
| Typst intermediates | `<repo>/build/{lang}/{type}/` (`book.json`, `qr/`, `cache/`, diagram `images/`) |
| Video downloads | `<repo>/build/{lang}/videos/` (+ `SOURCE.json`) |
| Review reports | `<repo>/build/{lang}/review/` |
| Capture packs | `<repo>/build/{lang}/captures/{type}/` (`videos` → `../../videos`) |
| Comparison downloads | `<repo>/build/reference/` |
| Legacy slide-builder packer | `<repo>/build/legacy/{lang}/` |
| Git worktrees | `<repo>/.worktrees/<name>` for code only |
| Agent Store | `internal/` notes, short `FULL-PATH` / `OUTPUT-PATH.txt` pointers |

Do **not** create sibling folders under `~/Documents/ZUME/` for outputs, packs, or worktrees.

Gap-filler art stays in tracked `images/`. Do not move it into `build/`.

## Gitignore

Ignored (never commit):

- `output/` — finished PDF, Keynote, and PPTX
- `build/` — working tree above, and Python packaging output
- `slide-builder/**/videos/`, legacy slide-builder language output dirs
- `.env`, `.worktrees/`
- `reference/` — leftover ignore for the old comparison folder; new comparisons go in `build/reference/`

Do not commit MP4s, PDFs, Keynote, or PPTX. `images/` and `manifest/review/` stay in git.

`python -m build` also writes `build/`. Do not run it while a language pack is there.

## Agent Store boundary

- Never copy final PDF/Keynote into Agent Store `docs/`.
- Capture packs live under repo `build/{lang}/captures/`, not store `media/`.
- Assembled decks still go to repo `output/{lang}/` on `--promote`.

## Common mistakes

| Mistake | Fix |
|---|---|
| `../zume-asset-creation-scripts-wt-*` worktrees | Use `<repo>/.worktrees/<name>` for code; build assets on the main checkout |
| Building inside a worktree | That checkout grows its own `build/` and `output/` |
| Committing MP4s or guidebooks | Keep them under ignored `build/` and `output/` |
| Saving deliverables to store `docs/` | Write `output/{lang}/` + optional pointer file |
| Copying MP4s into each capture pack | Link `captures/{type}/videos` at `build/{lang}/videos` |
| Putting videos or review reports in `output/` | `output/{lang}/` is the nine upload files |
