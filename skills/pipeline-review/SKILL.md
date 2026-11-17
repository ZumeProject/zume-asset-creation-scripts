---
name: pipeline-review
description: Use when verifying Zúme guidebook QR codes or Keynote video mapping against the live online master list — review fetch-master, review qr, review videos, review all in zume-asset-creation-scripts.
---

# Pipeline review (QR + video)

## Overview

Script-first confirmation that PDF QR PNGs encode the correct locale/destination and that Keynote pack videos match online `vimeoId` + title metadata. Agents run the CLI and surface reports; do not eyeball QR matrices unless decode fails.

## Install

```bash
pip install -e ".[dev]"          # includes zxing-cpp for QR decode
# or: pip install -e ".[review]"
```

## Commands

```bash
# Refresh master cache (network) → manifest/review/{lang}-{type}.json
python3 -m zume_assets review fetch-master --lang en --type 10
python3 -m zume_assets review fetch-master --lang es --type 10 --follow-redirects

# Decode output/{lang}/build-{type}/qr/*.png vs master (+ optional book.json / --live)
python3 -m zume_assets review qr --lang en --type 10
python3 -m zume_assets review qr --lang es --type 10 --live

# SOURCE.json + pack video-replace-list vs master videos
python3 -m zume_assets review videos --lang en --type 10
python3 -m zume_assets review videos --lang en --type 10 --pack /path/to/pack

# QR + videos (optionally refresh master first)
python3 -m zume_assets review all --lang en --type 10 --fetch
```

Reports land in `output/{lang}/review/` (`qr-{type}.json|.md`, `videos-{type}.json|.md`, `all-{type}.json|.md`). Exit non-zero on mismatch; report only (no auto-fix).

## Rules

- CI stays **offline** by default — do not require live fetch in GitHub Actions.
- Prefer independent PNG decode over trusting `book.json` alone.
- Video theme = automated id + locale metadata match (no AI frame review).
- Never print or commit Vimeo / `.env` secrets.

## Common mistakes

| Mistake | Fix |
|---|---|
| Running `review qr` before a PDF build | Build PDF so `output/{lang}/build-{type}/qr/` exists |
| Missing master JSON | `review fetch-master --lang … --type …` |
| Expecting CI to hit the live API | Use fixtures / committed `manifest/review/` caches |
| Unpacking `.key` for video ids in v1 | Use pack `video-replace-list.json` / `SOURCE.json` |
