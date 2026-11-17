# Zume asset creation scripts

Pipeline for regenerating offline Zúme training assets from live [zume6](https://zume.training) APIs.

**Production deliverables** (under `output/{lang}/`):

- Typst **PDF** guidebooks (this CLI)
- **Keynote** decks via `slides/assemble-keynote/` (macOS)

PowerPoint / PPTX is not a production target.

See [AGENTS.md](AGENTS.md) for the rules agents should follow in this repo.

## PDF guidebooks (Typst)

1. Fetch live presenter, scripts, and activities APIs
2. Assemble a normalized book JSON from the course manifest (`10`, `20`, or `intensive`)
3. Emit QR images and compile a Typst template to PDF

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
# equivalent:
python3 -m zume_assets build --lang en --type 10 --targets pdf
```

All finished assets land under the repo `output/` tree (for example
`<repo>/output/en/`). See [AGENTS.md](AGENTS.md) for workspace path rules.
Do not copy final PDFs or Keynote into Agent Store `docs/`.

Output for the 10-session English book:

- `output/en/Zume-Training-10-Session-en.pdf` — reviewable guidebook
- `output/en/build-10/book.json` — assembled content
- `output/en/build-10/qr/` — QR PNGs
- `output/en/build-10/cache/` — cached API payloads

20-session and intensive files follow the same pattern (`Zume-Training-20-Session-en.pdf`, `Zume-Training-Intensive-en.pdf`).

Reference PDFs (downloaded for comparison only; never uploaded over GCS) belong under `reference/`.

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
slide-builder/            # current video download + slide screenshot packer
slides/capture/           # presenter PNG capture
slides/videos/            # EN Vimeo download helpers
slides/assemble-keynote/  # macOS Keynote assembly
publish/                  # future GCS upload
```

### Notes

- Do **not** publish to GCS from this pipeline until English PDFs are signed off.
- Production outputs are PDF + Keynote only. PPTX tooling was removed; do not restore it for production.
- The CLI only builds PDF. Keynote uses `slides/assemble-keynote/` on macOS.
- `slide-builder/` is still the only video and slide-screenshot path. Install it separately with `pip install -r slide-builder/requirements.txt`.
- HTML workbook at `https://zume.training/workbook/10` remains the interactive preview; this PDF is a parallel renderer over the same APIs.
