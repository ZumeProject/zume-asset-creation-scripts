---
name: vimeo-download-provenance
description: Use when downloading Zúme training MP4s, wiring Vimeo credentials, writing or checking SOURCE.json provenance, choosing Vimeo vs GCS mirrors, or debugging missing pack videos in zume-asset-creation-scripts.
---

# Vimeo download + SOURCE provenance

## Overview

Production videos come from **per-language Vimeo folders** mapped in `slide-builder/parts/vimeo-folders.json`, not GCS by default. Downloads must write `SOURCE.json` and never log secrets.

## Canonical sources (proven)

| Lang | Folder | URL |
|---|---|---|
| `en` | `21862752` | https://vimeo.com/user/75461893/folder/21862752 |
| `es` | `269525` | https://vimeo.com/user/75461893/folder/269525 |
| `pus` | `29862924` | https://vimeo.com/user/75461893/folder/29862924 |

Helpers: `slides/videos/download_lang_vimeo.py`, `slides/videos/download_en_vimeo.py`, `slides/videos/vimeo_folder.py`.

**Unmapped languages:** download scripts exit with next steps. Creating a folder and adding the map entry is a **required setup step before Keynote**, not an optional skip. Never invent a folder id.

```bash
python3 -m zume_assets prereqs --lang <lang>
```

## Download

```bash
pip install -r slide-builder/requirements.txt
# Credentials: env or repo/.env / slide-builder/.env — never commit
python3 slides/videos/download_lang_vimeo.py --lang es
python3 slides/videos/download_lang_vimeo.py --lang en
# EN-only wrapper (same folder; kept for older docs/scripts)
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Accepted env aliases: `VIMEO_ACCESS_TOKEN` / `VIMEO_PERSONAL_ACCESS_TOKEN`, `VIMEO_CLIENT_ID` / `VIMEO_CLIENT_IDENTIFIER`, `VIMEO_CLIENT_SECRET` / `VIMEO_CLIENT_SECRETS`.

Writes:

- `output/{lang}/videos/{n}.mp4` (training numbers from titles)
- `output/{lang}/videos/SOURCE.json` with `source=vimeo`, `folder_id`, timestamps

That tree is **gitignored** (`output/**/videos/`).

## Secrets

- Never print token/secret values, never paste `.env` into chat, never commit `.env`.
- Safe to confirm “credentials present” without dumping values.
- Error messages must not echo Authorization headers or token strings.

## Provenance rules

- Prefer `provenance_matches_folder()` / `SOURCE.json` before trusting a video dir.
- Do **not** silently fall back to `zume-file-mirror` / GCS for rebuilds.
- Keynote embed expects numbered MP4s available to the capture pack (`pack/videos/`).

## Common mistakes

| Mistake | Fix |
|---|---|
| Using GCS mirror as default | Use the mapped Vimeo folder for that language |
| Committing MP4s | Keep under ignored `output/**/videos/` |
| Logging `.env` contents while debugging | Check key names only |
| Pointing `--folder-id` at a non-mapped folder | Script asserts map match |
| Skipping download because “PDF worked” | Run `prereqs`; Keynote needs local MP4s |
| Inventing a folder id for an unmapped lang | Ask Chris; update `vimeo-folders.json` only with a real id |
