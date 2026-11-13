# Agent notes

This repo builds offline Zúme training assets from the live zume6 APIs. Read this before changing the pipeline.

## What works

PDF guidebooks only. The CLI rejects every other target.

```bash
pip install -e ".[dev]"
python3 build.py --lang en --type 10 --targets pdf
python3 -m zume_assets build --lang en --type 20 --targets pdf
python3 -m zume_assets build --lang en --type intensive --targets pdf
```

Course types are `10`, `20`, and `intensive`. English is the signed-off target. The same renderer also builds other locales (Arabic and Traditional Chinese have font and direction support).

Requires Python 3.10+ and the [Typst](https://github.com/typst/typst/releases) CLI on `PATH` (0.13.x). A Latin sans font Typst can see (Liberation Sans, DejaVu Sans, or Noto Sans) is required. Arabic and CJK builds also need a matching fallback font.

Content comes from `https://api.zume.training/api/v1`. QR payloads use `https://zume.training/app/qr/?l={locale}&{c|v|a}={id}`.

Generated files land in `output/` and comparison downloads in `reference/`. Both are gitignored. Do not commit PDFs.

## Do not

- Do not publish to GCS or change downloads rows. `publish/` is a placeholder and stays unused until English PDFs are signed off.
- Do not add PowerPoint or Keynote targets. `slides/capture`, `slides/assemble-pptx`, and `slides/assemble-keynote` are placeholders. The CLI must keep rejecting `pptx` and `keynote`.
- Do not bring back a Playwright or Chromium PDF printer. The old zume5 `/book/generator` path was removed.
- Do not page-stamp PDFs with PyPDF or ReportLab. Typst owns guidebook layout.
- Keynote assembly is macOS-only. Do not try to run it on Linux CI.

## Layout

```
manifest/          course structure
pdf/templates/     Typst book template
pdf/assets/        cover and logo
zume_assets/       assembler, QR, Typst compile, CLI
tests/             offline unit tests (no live API)
slide-builder/     current video download + slide screenshot packer
slides/            future deck capture and assembly
publish/           future GCS upload
```

`slide-builder/` is still the only way to download videos and screenshot slides. Leave it until `slides/` replaces it. Its Python dependencies stay in `slide-builder/requirements.txt` and are not part of the guidebook package.

## Checks

```bash
ruff check .
pytest
```

CI runs those without the live API. A separate workflow job builds the English 10-session PDF against `api.zume.training`.
