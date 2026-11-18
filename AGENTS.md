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
| [skills/publish-gcs-assets/SKILL.md](skills/publish-gcs-assets/SKILL.md) | Upload approved PDF/Keynote/PPTX to `zume-file-mirror` + verify downloads |

## What works

**Production deliverables** under `output/{lang}/`:

1. **Typst PDF guidebooks** — via the Python CLI
2. **Keynote decks (`.key`)** — via `slides/assemble-keynote/` on macOS (not a CLI `--targets` value)
3. **PPTX** — Keynote export during review (`File → Export To → PowerPoint`); required for publish. Do **not** restore `slides/assemble-pptx/`.

**First step of every language build** is the readiness checklist. Agents must not skip it. `zume-assets build` / `build.py` auto-run it and **abort before Typst** when the Vimeo folder map is missing.

```bash
pip install -e ".[dev]"
# Explicit checklist (also embedded in build):
python3 -m zume_assets prereqs --lang <lang>
python3 -m zume_assets prereqs --lang <lang> --pdf-only   # map BLOCK; videos/packs NOTE
python3 build.py --lang en --type 10 --targets pdf
python3 -m zume_assets build --lang en --type 20 --targets pdf
python3 -m zume_assets build --lang en --type intensive --targets pdf
# Gap fillers are ON by default (decorative bottom-gap images from images/).
# Typst-only draft (not for sign-off):
python3 -m zume_assets build --lang en --type 10 --targets pdf --no-gap-fillers
# Hard-fail on missing local videos + capture packs too:
python3 -m zume_assets build --lang en --type 10 --targets pdf --full-pack
```

Course types are `10`, `20`, and `intensive`. English is the signed-off target. The same PDF renderer also builds other locales (Arabic and Traditional Chinese have font and direction support).

Requires Python 3.10+ and the [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (0.13.x). A Latin sans font Typst can see (Liberation Sans, DejaVu Sans, or Noto Sans) is required. Arabic and CJK builds also need a matching fallback font.

Content comes from `https://api.zume.training/api/v1`. QR payloads use `https://zume.training/app/qr/?l={locale}&{c|v|a}={id}`.

**PDF diagram images** (pace timelines, Four Fields, Generational Mapping) come from presenter `images.*` URLs plus script `{{ paceN_image }}` shortcodes. Locale scripts that omit shortcodes are merged with English shortcode slots at assemble time. Missing required diagram assets hard-fail the build — do not ship blank slots. Decorative bottom-gap fillers from `images/` are **on by default** for `build` (requires `pymupdf` / `pip install -e ".[dev]"`). Use `--no-gap-fillers` only for intentional Typst-only drafts — do not report those as signed-off language packs.

### Full pack prerequisites (before PDF / Keynote / videos)

Readiness runs at the **start** of the process so a missing Vimeo folder is corrected before Typst or Keynote work. Do not invent Vimeo folder ids.

| Mode | Vimeo map | Local MP4s | Capture packs |
|---|---|---|---|
| Default `build` / `prereqs --pdf-only` | **BLOCK** (abort) | NOTE warning | NOTE warning |
| `build --full-pack` / `prereqs` / Keynote assemble | **BLOCK** | **BLOCK** | **BLOCK** |

```bash
python3 -m zume_assets prereqs --lang <lang>
```

Checks:

1. **Vimeo folder map** — `slide-builder/parts/vimeo-folders.json` must list `language_code` → `folder_id`
2. **Local MP4s** — `output/{lang}/videos/` + `SOURCE.json` from the download script
3. **Presenter capture packs** — Agent Store `media/{lang}-{10|20|intensive}-presenter-captures/` (`manifest.json` + PNGs)

Proven production folder ids (do not guess others):

| Lang | Folder | URL |
|---|---|---|
| `en` | `21862752` | https://vimeo.com/user/75461893/folder/21862752 |
| `es` | `269525` | https://vimeo.com/user/75461893/folder/269525 |
| `pus` | `29862924` | https://vimeo.com/user/75461893/folder/29862924 |

If a language is **not** in the map, stop and ask Chris for the folder URL/id, add the map entry, then continue. Missing map/pack/folder is a required setup step, not an optional skip.

### Videos (production path)

```bash
pip install -r slide-builder/requirements.txt
# Any mapped language (writes output/{lang}/videos + SOURCE.json; gitignored)
python3 slides/videos/download_lang_vimeo.py --lang es
python3 slides/videos/download_lang_vimeo.py --lang en
# EN-only wrapper (same folder; kept for older docs/scripts)
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Writes numbered MP4s plus `SOURCE.json` provenance. Keynote assemble reads pack videos (typically synced from that download). Do **not** default to GCS / `zume-file-mirror`. Never log or commit Vimeo tokens from `.env`. Unmapped languages exit with explicit next steps (see `prereqs`).

### Keynote (macOS / Creator Studio)

```bash
python3 -m zume_assets prereqs --lang en   # must be clean; assemble also re-checks
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```

See `slides/assemble-keynote/README.md` and the mac-keynote-assemble skill. Do not run Keynote assembly on Linux CI. Missing map/videos/capture packs abort assemble (no silent success).

### Pipeline review (QR + video)

After a language build, refresh the on-demand master list and run independent checks (report only; non-zero exit on mismatch). CI stays offline by default — live fetch is opt-in.

```bash
pip install -e ".[dev]"   # includes zxing-cpp for QR decode
python3 -m zume_assets review fetch-master --lang en --type 10
python3 -m zume_assets review qr --lang en --type 10
python3 -m zume_assets review videos --lang en --type 10
python3 -m zume_assets review all --lang es --type 10 --fetch
```

Master cache: `manifest/review/{lang}-{type}.json`. Reports: `output/{lang}/review/`. See the pipeline-review skill. With `--live`, allowlisted activity redirects include `3monthplan` → `auth/login` and marketing pages for `getacoach` / `join_the_community` / `next_steps` (locale-prefixed paths OK). A `getacoach` live FAIL that lands on `/{lang}` homepage means the locale marketing page is missing — not a bad QR PNG; do not treat homepage as allowlisted. Video review gates on `vimeo_id` (title string mismatches are notes only). Pack training id `20` / `t20_b` may alias online `19` when SOURCE records that alias — treat as PASS. `review videos` / `review all` prefer Agent Store `media/{lang}-{type}-presenter-captures/` when present (no manual `--pack` needed); SOURCE-only mode still FAILs on missing master ids but treats Vimeo-folder extras as notes.

### Publish (GCS + downloads verify)

After human sign-off for a language pack, upload PDF + Keynote + PPTX from `output/{lang}/` to `gs://zume-file-mirror/{lang}/` via `gcloud storage cp`, then verify `GET /api/v1/downloads/{lang}` (`guidebook_*`, `keynote_*`, `powerpoint_*`). Dry-run by default; require `--execute` for real upload. Once `--execute` is authorized, **always overwrite** same-named objects (no second prompt). Do not upload `videos/` unless `--include-videos`. Needs `gcloud` + ADC on the machine (typically macOS Creator Studio). Missing PPTX after review: export from Keynote UI (computer use). See the publish-gcs-assets skill.

```bash
python3 -m zume_assets publish upload --lang es
python3 -m zume_assets publish upload --lang es --execute
python3 -m zume_assets publish verify-downloads --lang es
```

## Workspace paths

Keep all work inside the active repo checkout. Do not create sibling folders under `~/Documents/ZUME/` (or elsewhere) for outputs, capture packs, worktrees, or scratch.

Canonical deliverable path:

`<repo>/output/{lang}/`

Language subdirs are fine (`output/en/…`). Comparison downloads go in `<repo>/reference/`.

**Gitignore policy:** `output/**/videos/`, `output/**/*.mp4`, and `output/**/build-*/` are ignored (download caches + Typst intermediates). Finished PDFs and Keynote under `output/{lang}/` are *not* blanket-ignored so they *may* be tracked if Chris asks — leave large binaries local unless explicitly told to commit. Never commit videos. See the output-paths-worktrees skill.

If a git worktree is needed, create it only as `<repo>/.worktrees/<name>` (gitignored). Never use `../<repo>-wt-*` or any other path next to the checkout.

Do **not** write finished PDFs or Keynote files into Agent Store `docs/` (or any other store path). Store may keep `internal/` notes and short `FULL-PATH` / `OUTPUT-PATH.txt` pointers that point at the local `output/` tree.

## Do not

- Do not upload to GCS without human sign-off for that language. Prefer dry-run; only pass `--execute` after approval. After `--execute`, overwrite same-named GCS objects without asking again. Do not update zume6 downloads rows from this CLI (verify only). Do not upload `videos/` unless explicitly opted in. Never print GCS/ADC credentials.
- Do not copy or save final deliverables into Agent Store `docs/` (use repo `output/` only).
- Do not create output, worktree, or capture-pack directories outside the active repo root.
- Do not restore `slides/assemble-pptx/`. Build CLI must keep rejecting `--targets pptx`; publish PPTX comes from Keynote export only.
- Do not treat `keynote` as a CLI `--targets` value; Keynote is assembled only via `slides/assemble-keynote/` on macOS. The CLI rejects `keynote` the same way it rejects other non-PDF targets.
- Do not bring back a Playwright or Chromium PDF printer. The old zume5 `/book/generator` path was removed. (`slides/capture/` Playwright is for presenter PNGs only.)
- Do not page-stamp PDFs with PyPDF or ReportLab for guidebook layout. Typst owns layout; gap fillers stamp decorative images after compile by default (`--no-gap-fillers` to skip).
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
zume_assets/publish/      GCS upload (gcloud) + downloads verify
tests/                    offline unit tests (no live API)
skills/                   in-repo agent skills (linked above)
slide-builder/            legacy multi-lang packer + shared vimeo-folders.json / requirements
slides/capture/           presenter PNG capture packs
slides/videos/            EN Vimeo download + provenance (production video path)
slides/assemble-keynote/  macOS Keynote deck assembly
publish/                  GCS publish notes (CLI lives in zume_assets/publish/)
```

`slides/videos/` is the production EN video download path. `slide-builder/` remains for its folder map, PyVimeo requirements, and legacy interactive packer until a follow-up relocates those pieces. Its Python deps stay in `slide-builder/requirements.txt` and are not part of the guidebook package.

## Checks

```bash
ruff check .
pytest
```

CI runs those without the live API. A separate workflow job builds the English 10-session PDF against `api.zume.training`.
