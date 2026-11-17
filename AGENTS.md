# Agent notes

This repo builds offline Zúme training assets from the live zume6 APIs. Read this before changing the pipeline.

## What works

**Production deliverables** under `output/{lang}/`:

1. **Typst PDF guidebooks** — via the Python CLI
2. **Keynote decks (`.key`)** — via `slides/assemble-keynote/` on macOS (not a CLI `--targets` value)

PowerPoint / PPTX is **not** a production target. The old `slides/assemble-pptx/` tree was removed.

```bash
pip install -e ".[dev]"
python3 build.py --lang en --type 10 --targets pdf
python3 -m zume_assets build --lang en --type 20 --targets pdf
python3 -m zume_assets build --lang en --type intensive --targets pdf
```

Course types are `10`, `20`, and `intensive`. English is the signed-off target. The same PDF renderer also builds other locales (Arabic and Traditional Chinese have font and direction support).

Requires Python 3.10+ and the [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (0.13.x). A Latin sans font Typst can see (Liberation Sans, DejaVu Sans, or Noto Sans) is required. Arabic and CJK builds also need a matching fallback font.

Content comes from `https://api.zume.training/api/v1`. QR payloads use `https://zume.training/app/qr/?l={locale}&{c|v|a}={id}`.

Keynote (macOS / Creator Studio):

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```

See `slides/assemble-keynote/README.md`. Do not try to run Keynote assembly on Linux CI.

## Workspace paths

Keep all work inside the active repo checkout. Do not create sibling folders under `~/Documents/ZUME/` (or elsewhere) for outputs, capture packs, worktrees, or scratch.

Canonical deliverable path:

`<repo>/output/{lang}/`

Language subdirs are fine (`output/en/…`). Comparison downloads go in `<repo>/reference/`. Both are gitignored. Do not commit PDFs or Keynote packages.

If a git worktree is needed, create it only as `<repo>/.worktrees/<name>` (gitignored). Never use `../<repo>-wt-*` or any other path next to the checkout.

Do **not** write finished PDFs or Keynote files into Agent Store `docs/` (or any other store path). Store may keep `internal/` notes and short `FULL-PATH` / `OUTPUT-PATH.txt` pointers that point at the local `output/` tree.

## Do not

- Do not publish to GCS or change downloads rows. `publish/` is a placeholder and stays unused until English PDFs are signed off.
- Do not copy or save final deliverables into Agent Store `docs/` (use repo `output/` only).
- Do not create output, worktree, or capture-pack directories outside the active repo root.
- Do not build, require, or advertise PowerPoint / PPTX in production. The CLI must keep rejecting `pptx`. Do not restore `slides/assemble-pptx/`.
- Do not treat `keynote` as a CLI `--targets` value; Keynote is assembled only via `slides/assemble-keynote/` on macOS. The CLI rejects `keynote` the same way it rejects other non-PDF targets.
- Do not bring back a Playwright or Chromium PDF printer. The old zume5 `/book/generator` path was removed.
- Do not page-stamp PDFs with PyPDF or ReportLab. Typst owns guidebook layout.
- Keynote assembly is macOS-only. Do not try to run it on Linux CI.

## Layout

```
manifest/               course structure
pdf/templates/          Typst book template
pdf/assets/             cover and logo
zume_assets/            assembler, QR, Typst compile, CLI
tests/                  offline unit tests (no live API)
slide-builder/          current video download + slide screenshot packer
slides/capture/         presenter PNG capture packs
slides/videos/          EN Vimeo download helpers
slides/assemble-keynote/  macOS Keynote deck assembly
publish/                future GCS upload
```

`slide-builder/` is still the only way to download videos and screenshot slides for the legacy packer. Leave it until `slides/` fully replaces it. Its Python dependencies stay in `slide-builder/requirements.txt` and are not part of the guidebook package.

## Checks

```bash
ruff check .
pytest
```

CI runs those without the live API. A separate workflow job builds the English 10-session PDF against `api.zume.training`.
