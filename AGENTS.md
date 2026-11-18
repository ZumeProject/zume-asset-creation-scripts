# Agent notes

This repo builds offline Zúme training assets from the live zume6 APIs. Read this before changing the pipeline.

## Agent skills (read these)

In-repo skills under [`skills/`](skills/). Cursor ignores `.cursor/`, so skills are committed here and linked explicitly:

| Skill | When |
|---|---|
| [skills/build-language-assets/SKILL.md](skills/build-language-assets/SKILL.md) | Building a locale’s Typst PDF and/or Keynote deck |
| [skills/vimeo-download-provenance/SKILL.md](skills/vimeo-download-provenance/SKILL.md) | Downloading training MP4s from Vimeo, `SOURCE.json`, credentials |
| [skills/mac-keynote-assemble/SKILL.md](skills/mac-keynote-assemble/SKILL.md) | macOS Keynote assemble, embed, play chrome, health recovery |
| [skills/output-paths-worktrees/SKILL.md](skills/output-paths-worktrees/SKILL.md) | `output/{lang}/`, gitignore, worktrees, Agent Store boundaries |
| [skills/pipeline-review/SKILL.md](skills/pipeline-review/SKILL.md) | Independent QR decode + Keynote video mapping vs online master |

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
# optional decorative bottom-gap images after Typst:
python3 -m zume_assets build --lang en --type 10 --targets pdf --gap-fillers
```

Course types are `10`, `20`, and `intensive`. English is the signed-off target. The same PDF renderer also builds other locales (Arabic and Traditional Chinese have font and direction support).

Requires Python 3.10+ and the [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (0.13.x). A Latin sans font Typst can see (Liberation Sans, DejaVu Sans, or Noto Sans) is required. Arabic and CJK builds also need a matching fallback font.

Content comes from `https://api.zume.training/api/v1`. QR payloads use `https://zume.training/app/qr/?l={locale}&{c|v|a}={id}`.

### Videos (EN proven path)

Canonical EN Vimeo folder: `https://vimeo.com/user/75461893/folder/21862752` (also `en` in `slide-builder/parts/vimeo-folders.json`).

```bash
pip install -r slide-builder/requirements.txt
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Writes numbered MP4s plus `SOURCE.json` provenance. Keynote assemble reads pack videos (typically synced from that download). Do **not** default to GCS / `zume-file-mirror`. Never log or commit Vimeo tokens from `.env`.

### Keynote (macOS / Creator Studio)

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```

See `slides/assemble-keynote/README.md` and the mac-keynote-assemble skill. Do not run Keynote assembly on Linux CI.

### Pipeline review (QR + video)

After a language build, refresh the on-demand master list and run independent checks (report only; non-zero exit on mismatch). CI stays offline by default — live fetch is opt-in.

```bash
pip install -e ".[dev]"   # includes zxing-cpp for QR decode
python3 -m zume_assets review fetch-master --lang en --type 10
python3 -m zume_assets review qr --lang en --type 10
python3 -m zume_assets review videos --lang en --type 10
python3 -m zume_assets review all --lang es --type 10 --fetch
```

Master cache: `manifest/review/{lang}-{type}.json`. Reports: `output/{lang}/review/`. See the pipeline-review skill. With `--live`, activity `3monthplan` → `auth/login` (create-your-plan) is an allowed destination; do not treat homepage redirects for `getacoach` / `join_the_community` / `next_steps` as OK without evidence.

## Workspace paths

Keep all work inside the active repo checkout. Do not create sibling folders under `~/Documents/ZUME/` (or elsewhere) for outputs, capture packs, worktrees, or scratch.

Canonical deliverable path:

`<repo>/output/{lang}/`

Language subdirs are fine (`output/en/…`). Comparison downloads go in `<repo>/reference/`.

**Gitignore policy:** `output/**/videos/`, `output/**/*.mp4`, and `output/**/build-*/` are ignored (download caches + Typst intermediates). Finished PDFs and Keynote under `output/{lang}/` are *not* blanket-ignored so they *may* be tracked if Chris asks — leave large binaries local unless explicitly told to commit. Never commit videos. See the output-paths-worktrees skill.

If a git worktree is needed, create it only as `<repo>/.worktrees/<name>` (gitignored). Never use `../<repo>-wt-*` or any other path next to the checkout.

Do **not** write finished PDFs or Keynote files into Agent Store `docs/` (or any other store path). Store may keep `internal/` notes and short `FULL-PATH` / `OUTPUT-PATH.txt` pointers that point at the local `output/` tree.

## Do not

- Do not publish to GCS or change downloads rows. `publish/` is a placeholder and stays unused until English PDFs are signed off.
- Do not copy or save final deliverables into Agent Store `docs/` (use repo `output/` only).
- Do not create output, worktree, or capture-pack directories outside the active repo root.
- Do not build, require, or advertise PowerPoint / PPTX in production. The CLI must keep rejecting `pptx`. Do not restore `slides/assemble-pptx/`.
- Do not treat `keynote` as a CLI `--targets` value; Keynote is assembled only via `slides/assemble-keynote/` on macOS. The CLI rejects `keynote` the same way it rejects other non-PDF targets.
- Do not bring back a Playwright or Chromium PDF printer. The old zume5 `/book/generator` path was removed. (`slides/capture/` Playwright is for presenter PNGs only.)
- Do not page-stamp PDFs with PyPDF or ReportLab for guidebook layout. Typst owns layout; `gap-fillers` may stamp decorative images after compile.
- Keynote assembly is macOS-only. Do not try to run it on Linux CI.
- Do not print, paste, or commit secrets from `.env` / Vimeo credentials.

## Layout

```
manifest/                 course structure
manifest/review/          on-demand review master lists ({lang}-{type}.json)
pdf/templates/            Typst book template
pdf/assets/               cover and logo
zume_assets/              assembler, QR, Typst compile, CLI, gap fillers
zume_assets/review/       pipeline review (master, QR decode, video check)
tests/                    offline unit tests (no live API)
skills/                   in-repo agent skills (linked above)
slide-builder/            legacy multi-lang packer + shared vimeo-folders.json / requirements
slides/capture/           presenter PNG capture packs
slides/videos/            EN Vimeo download + provenance (production video path)
slides/assemble-keynote/  macOS Keynote deck assembly
publish/                  future GCS upload (unused)
```

`slides/videos/` is the production EN video download path. `slide-builder/` remains for its folder map, PyVimeo requirements, and legacy interactive packer until a follow-up relocates those pieces. Its Python deps stay in `slide-builder/requirements.txt` and are not part of the guidebook package.

## Checks

```bash
ruff check .
pytest
```

CI runs those without the live API. A separate workflow job builds the English 10-session PDF against `api.zume.training`.
