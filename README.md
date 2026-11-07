# Zume asset creation scripts

Pipeline for regenerating offline Zúme training assets (PDF guidebooks, and later PowerPoint / Keynote) from live [zume6](https://zume.training) APIs.

Legacy packages (`pdf-creator/`, `slide-builder/`, `pdf-numbering/`) remain for reference. New work lives under `manifest/`, `pdf/`, and `zume_assets/`.

## Phase 1 — English 10-session PDF (Typst)

Programmatic guidebook generation (not Chromium print):

1. Fetch live presenter / scripts / activities APIs
2. Assemble a normalized book JSON from the 10-session course manifest
3. Emit QR images + compile a Typst template → PDF

### Prerequisites

- Python 3.10+
- [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (tested with 0.13.x)
- A Latin sans font Typst can see (Liberation Sans / DejaVu Sans / Noto Sans)

```bash
pip install -r requirements.txt
typst --version
```

### Build the English 10-session guidebook

From the repo root:

```bash
python3 build.py --lang en --type 10 --targets pdf
# equivalent:
python3 -m zume_assets build --lang en --type 10 --targets pdf
```

Output:

- `output/en/Zume-Training-10-Session-en.pdf` — reviewable guidebook
- `output/en/build-10/book.json` — assembled content
- `output/en/build-10/qr/` — QR PNGs
- `output/en/build-10/cache/` — cached API payloads

Reference PDF (downloaded for comparison only; never uploaded over GCS):

- `reference/en/Zume-Training-10-Session-en.pdf`

### Layout

```
manifest/           # course structure + concept slug map
pdf/templates/      # Typst book template
zume_assets/        # assembler, QR, Typst compile, CLI
output/             # generated artifacts (gitignored)
reference/          # downloaded current GCS assets for diffing (gitignored binaries OK)
pdf-creator/        # legacy Playwright PDF (zume5 /book/generator — dead)
slide-builder/      # legacy screenshot + Vimeo packs
pdf-numbering/      # legacy page-number stamper
```

### Notes

- Do **not** publish to GCS from this pipeline until English PDFs are signed off.
- PPTX / Keynote targets are not implemented yet.
- HTML workbook at `https://zume.training/workbook/10` remains the interactive preview; this PDF is a parallel renderer over the same APIs.
