---
name: output-paths-worktrees
description: Use when choosing where to write Zúme PDFs, Keynote, videos, or scratch trees — output/{lang}/, gitignore, git worktrees, Agent Store docs vs repo, or folder layout rules in zume-asset-creation-scripts.
---

# Output paths, gitignore, worktrees

## Overview

All finished assets stay inside the **active repo checkout**. Agent Store holds notes/pointers, not deliverable binaries.

## Canonical paths

| Kind | Path |
|---|---|
| Deliverables | `<repo>/output/{lang}/` (PDF, `.key`) |
| Typst intermediates | `<repo>/output/{lang}/build-{type}/` |
| Video downloads | `<repo>/output/{lang}/videos/` (+ `SOURCE.json`) |
| Comparison downloads | `<repo>/reference/` |
| Git worktrees | `<repo>/.worktrees/<name>` only |
| Agent Store | `internal/` notes, short `FULL-PATH` / `OUTPUT-PATH.txt` pointers |

Do **not** create sibling folders under `~/Documents/ZUME/` for outputs, packs, or worktrees.

## Gitignore

Ignored (never commit):

- `output/**/videos/`, `output/**/*.mp4`, `output/**/build-*/`
- `slide-builder/**/videos/`, legacy slide-builder language output dirs
- `.env`, `.worktrees/`, comparison binaries under `reference/`

Finished PDFs/Keynote under `output/{lang}/` are **not** blanket-ignored — commit only if Chris explicitly asks; prefer leaving large binaries local.

## Agent Store boundary

- Never copy final PDF/Keynote into Agent Store `docs/`.
- Capture packs may live under store `media/`; assembled decks still go to repo `output/`.

## Common mistakes

| Mistake | Fix |
|---|---|
| `../zume-asset-creation-scripts-wt-*` worktrees | Use `<repo>/.worktrees/<name>` |
| Committing MP4s | Keep under ignored `videos/` |
| Saving deliverables to store `docs/` | Write `output/{lang}/` + optional pointer file |
| Ignoring all of `output/` forever when Chris wants a tracked PDF | Policy allows tracking PDFs/Keynote; still ignore videos/`build-*` |
