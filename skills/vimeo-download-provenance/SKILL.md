---
name: vimeo-download-provenance
description: Use when downloading Zúme training MP4s, wiring Vimeo credentials, writing or checking SOURCE.json provenance, choosing Vimeo vs GCS mirrors, or debugging missing pack videos in zume-asset-creation-scripts.
---

# Vimeo download + SOURCE provenance

## Overview

EN production videos come from **Vimeo folder `21862752`**, not GCS by default. Downloads must write `SOURCE.json` and never log secrets.

## Canonical source

- URL: `https://vimeo.com/user/75461893/folder/21862752`
- Also `language_code=en` in `slide-builder/parts/vimeo-folders.json`
- Helpers: `slides/videos/download_en_vimeo.py`, `slides/videos/vimeo_folder.py`

## Download

```bash
pip install -r slide-builder/requirements.txt
# Credentials: env or repo/.env / slide-builder/.env — never commit
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Accepted env aliases: `VIMEO_ACCESS_TOKEN` / `VIMEO_PERSONAL_ACCESS_TOKEN`, `VIMEO_CLIENT_ID` / `VIMEO_CLIENT_IDENTIFIER`, `VIMEO_CLIENT_SECRET` / `VIMEO_CLIENT_SECRETS`.

Writes:

- `output/en/videos/{n}.mp4` (training numbers from titles)
- `output/en/videos/SOURCE.json` with `source=vimeo`, `folder_id`, timestamps

That tree is **gitignored** (`output/**/videos/`).

## Secrets

- Never print token/secret values, never paste `.env` into chat, never commit `.env`.
- Safe to confirm “credentials present” without dumping values.
- Error messages must not echo Authorization headers or token strings.

## Provenance rules

- Prefer `provenance_matches_folder()` / `SOURCE.json` before trusting a video dir.
- Do **not** silently fall back to `zume-file-mirror` / GCS for EN rebuilds.
- Keynote embed expects numbered MP4s available to the capture pack (`pack/videos/`).

## Common mistakes

| Mistake | Fix |
|---|---|
| Using GCS mirror as default | Use Vimeo folder 21862752 |
| Committing MP4s | Keep under ignored `output/**/videos/` |
| Logging `.env` contents while debugging | Check key names only |
| Pointing `--folder-id` at a non-EN folder for `download_en_vimeo.py` | Script asserts EN folder id |
