# Zume asset creation scripts

Pipeline for regenerating offline Zúme training assets from live [zume6](https://zume.training) APIs.

**Production deliverables** (under `output/{lang}/`):

- Typst **PDF** guidebooks (this CLI)
- **Keynote** decks via `slides/assemble-keynote/` (macOS)
- **PPTX** via Keynote export during review (required for publish; do not restore `slides/assemble-pptx/`)

See [AGENTS.md](AGENTS.md) for agent rules and [skills/](skills/) for step-by-step agent skills.

## PDF guidebooks (Typst)

1. Fetch live presenter, scripts, and activities APIs
2. Assemble a normalized book JSON from the course manifest (`10`, `20`, or `intensive`)
3. Emit QR images and compile a Typst template to PDF
4. Stamp decorative bottom-gap images from `images/` (on by default; `--no-gap-fillers` to skip)

English is the review target. The same command builds other locales. Arabic and Traditional Chinese include font and direction handling.

### Prerequisites

- Python 3.10+
- [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (tested with 0.13.x)
- A Latin sans font Typst can see (Liberation Sans / DejaVu Sans / Noto Sans)

```bash
pip install -e ".[dev]"
typst --version
```

### Build a guidebook

From the repo root:

```bash
python3 build.py --lang en --type 10 --targets pdf
python3 build.py --lang en --type 20 --targets pdf
python3 build.py --lang en --type intensive --targets pdf
# equivalent (gap fillers on by default):
python3 -m zume_assets build --lang en --type 10 --targets pdf
# Typst-only draft without decorative fillers:
python3 -m zume_assets build --lang en --type 10 --targets pdf --no-gap-fillers
```

Finished PDF, Keynote, and PPTX land under `output/{lang}/`. Working files
(Typst intermediates, videos, review reports, capture packs) land under
gitignored `build/{lang}/`. See [AGENTS.md](AGENTS.md).
Do not copy final PDFs or Keynote into Agent Store `docs/`.

Output for the 10-session English book:

- `output/en/Zume-Training-10-Session-en.pdf` — reviewable guidebook
- `build/en/10/book.json` — assembled content
- `build/en/10/qr/` — QR PNGs
- `build/en/10/cache/` — cached API payloads

20-session and intensive files follow the same pattern (`Zume-Training-20-Session-en.pdf`, `Zume-Training-Intensive-en.pdf`).

Reference PDFs (downloaded for comparison only; never uploaded over GCS) belong under `build/reference/`.

## Videos (Vimeo → local MP4s)

EN proven source: [Vimeo folder 21862752](https://vimeo.com/user/75461893/folder/21862752).

```bash
pip install -r slide-builder/requirements.txt
python3 slides/videos/download_en_vimeo.py --out build/en/videos
```

Writes numbered `build/en/videos/{id}.mp4` plus `SOURCE.json`. Credentials come from env or repo `.env` (never commit or log tokens). See [slides/videos/README.md](slides/videos/README.md).

## Keynote decks (macOS)

Presenter PNG capture + local MP4s → `.key` under `output/{lang}/`. See
[slides/assemble-keynote/README.md](slides/assemble-keynote/README.md).

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```

Keynote is not a `zume_assets build --targets` value; the CLI rejects non-PDF targets
(including `pptx` and `keynote`).

### Checks

```bash
ruff check .
pytest
```

Tests stub the API. They do not call `api.zume.training`.

### Layout

```
manifest/                 # course structure + concept slug map
pdf/templates/            # Typst book template
pdf/assets/               # cover and logo
zume_assets/              # assembler, QR, Typst compile, CLI
tests/                    # offline unit tests
skills/                   # in-repo agent skills
slide-builder/            # legacy packer + vimeo-folders.json + PyVimeo deps
slides/capture/           # presenter PNG capture
slides/videos/            # EN Vimeo download helpers (production video path)
slides/assemble-keynote/  # macOS Keynote assembly
publish/                  # GCS publish notes (CLI: zume_assets publish)
```

## Publish (GCS)

After a language pack is approved, upload PDF + Keynote + PPTX to `gs://zume-file-mirror/{lang}/` and verify Downloads:

```bash
python3 -m zume_assets publish upload --lang es
python3 -m zume_assets publish upload --lang es --execute
python3 -m zume_assets publish verify-downloads --lang es
```

Requires `gcloud` + auth on the machine. Dry-run by default; `--execute` overwrites same-named GCS objects. See [publish/README.md](publish/README.md) and [skills/publish-gcs-assets/SKILL.md](skills/publish-gcs-assets/SKILL.md).

### Notes

- Only publish after human sign-off for that language; use `--execute` only after a dry-run looks right. Overwrite is then the default (no second prompt).
- Build CLI only builds PDF. Keynote uses `slides/assemble-keynote/` on macOS; PPTX for publish is Keynote export (do not restore `slides/assemble-pptx/`).
- Video downloads: use `slides/videos/` (production). `slide-builder/` still holds `vimeo-folders.json` and shared requirements until a follow-up relocates them.
- HTML workbook at `https://zume.training/workbook/10` remains the interactive preview; this PDF is a parallel renderer over the same APIs.
