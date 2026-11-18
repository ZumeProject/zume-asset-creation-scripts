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
- Video theme = automated **Vimeo id** match vs master (no AI frame review). Title strings are notes only.
- Never print or commit Vimeo / `.env` secrets.

## Live redirect allowlist

With `--live`, most activity QRs must land on `/activities/{key}`. Intentional exceptions (see `ACTIVITY_EXPECTED_REDIRECT_OVERRIDES` in `master.py`):

| Activity | Live final (expected) | Why |
|---|---|---|
| `3monthplan` | `…/{locale}/auth/login?redirect=…/create-your-plan` | create-your-plan requires login |
| `getacoach` | `…/{locale}/get-a-coach` | marketing page |
| `join_the_community` | `…/{locale}/join-the-community` | marketing page |
| `next_steps` | `…/{locale}/join-the-community` | same destination as join |

## Video review allowlist / noise

| Case | Review outcome | Why |
|---|---|---|
| Pack id **20** / `t20_b` when SOURCE aliases **20→19** and SOURCE `vimeo_id` matches online **19** | **PASS** | Course reformat: no distinct Vimeo for 20; download copies 19→20 |
| SOURCE title (Vimeo filename) ≠ API display title | **note only** (not FAIL) | Same `vimeo_id` proves the embed; string formats differ by design |

Official map: `OFFICIAL_VIDEO_ALIASES` in `zume_assets/review/video_check.py` (`20` → `19`). Require SOURCE evidence (`aliases["20"].from == "19"` and/or `videos["20"].status == "aliased"`).

## Common mistakes

| Mistake | Fix |
|---|---|
| Running `review qr` before a PDF build | Build PDF so `output/{lang}/build-{type}/qr/` exists |
| Missing master JSON | `review fetch-master --lang … --type …` |
| Expecting CI to hit the live API | Use fixtures / committed `manifest/review/` caches |
| Unpacking `.key` for video ids in v1 | Use pack `video-replace-list.json` / `SOURCE.json` |
| Marking `3monthplan` → auth/login as FAIL | Allowed by design (login gate for create-your-plan) |
| Failing video review on title string noise | Ignore titles; gate on `vimeo_id` only |
| Failing pack `t20_b` / id 20 when SOURCE aliases 19 | Official allowlist — must PASS |
