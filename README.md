# Zume asset creation scripts

Pipeline for regenerating offline Zúme training assets from live [zume6](https://zume.training) APIs. PDF guidebooks are implemented. PowerPoint and Keynote are not.

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

Output for the 10-session English book:

- `output/en/Zume-Training-10-Session-en.pdf` — reviewable guidebook
- `output/en/build-10/book.json` — assembled content
- `output/en/build-10/qr/` — QR PNGs
- `output/en/build-10/cache/` — cached API payloads

20-session and intensive files follow the same pattern (`Zume-Training-20-Session-en.pdf`, `Zume-Training-Intensive-en.pdf`).

Reference PDFs (downloaded for comparison only; never uploaded over GCS) belong under `reference/`.

### Checks

```bash
ruff check .
pytest
```

Tests stub the API. They do not call `api.zume.training`.

### Layout

```
manifest/           # course structure + concept slug map
pdf/templates/      # Typst book template
pdf/assets/         # cover and logo
zume_assets/        # assembler, QR, Typst compile, CLI
tests/              # offline unit tests
slide-builder/      # current video download + slide screenshot packer
slides/             # future deck capture and pptx/keynote assembly
publish/            # future GCS upload
```

### Notes

- Do **not** publish to GCS from this pipeline until English PDFs are signed off.
- PPTX and Keynote targets are not implemented. The CLI rejects them.
- `slide-builder/` is still the only video and slide-screenshot path. Install it separately with `pip install -r slide-builder/requirements.txt`.
- HTML workbook at `https://zume.training/workbook/10` remains the interactive preview; this PDF is a parallel renderer over the same APIs.
