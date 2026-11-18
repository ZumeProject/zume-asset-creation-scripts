---
name: publish-gcs-assets
description: Use when the user says a language pack is ready to upload to Google / GCS / zume-file-mirror — dry-run then execute upload of PDF + Keynote, then verify-downloads on zume.training.
---

# Publish approved language assets to GCS

## Overview

After human review + generation, upload finished **PDF + Keynote** under `output/{lang}/` to `gs://zume-file-mirror/{lang}/`, then verify the language’s Downloads listing via `GET https://api.zume.training/api/v1/downloads/{lang}`.

Trigger phrases: “{lang} assets are ready, upload to Google”, “publish Spanish to GCS”, “upload es to zume-file-mirror”.

## Prerequisites (Mac / Creator Studio)

1. Google Cloud SDK `gcloud` on `PATH`
2. Authenticated Application Default Credentials, e.g.:
   - `gcloud auth application-default login`, or
   - `gcloud auth login` with an account that can write the bucket
3. Local pack present under `<repo>/output/{lang}/` (not Agent Store `docs/`)

Never print, paste, or commit credentials / ADC tokens.

## Agent workflow

Always dry-run first, then execute, then verify:

```bash
pip install -e ".[dev]"

# 1) Dry-run (default) — lists local → gs:// paths; no network write
python3 -m zume_assets publish upload --lang es
python3 -m zume_assets publish upload --lang es --types 10,20,intensive --json

# 2) Real upload
python3 -m zume_assets publish upload --lang es --execute

# 3) Verify Downloads row filenames
python3 -m zume_assets publish verify-downloads --lang es
```

Spanish example expected objects:

- `gs://zume-file-mirror/es/Zume-Training-10-Session-es.pdf` / `.key`
- `gs://zume-file-mirror/es/Zume-Training-20-Session-es.pdf` / `.key`
- `gs://zume-file-mirror/es/Zume-Training-Intensive-es.pdf` / `.key`

Public URL shape: `https://storage.googleapis.com/zume-file-mirror/{lang}/{filename}`.

## Rules

- Production upload = **PDF + Keynote only**. Do not upload PPTX.
- Do **not** upload `output/{lang}/videos/` unless the user explicitly asks; then pass `--include-videos`.
- Dry-run by default; require `--execute` for real `gcloud storage cp`.
- `verify-downloads` asserts guidebook_* and keynote_* fields match the stable `Zume-Training-…` names. It does **not** update downloads rows — if the API still lists old names, report the mismatch (admin/API update is a separate step).
- Keep deliverables under repo `output/{lang}/` only.

## Common mistakes

| Mistake | Fix |
|---|---|
| Upload without dry-run | Run without `--execute` first; show Chris the plan |
| Uploading videos by default | Omit `--include-videos` unless asked |
| Treating PPTX as required | Ignore powerpoint_* fields; pipeline does not publish PPTX |
| Writing into Agent Store `docs/` | Upload from checkout `output/{lang}/` only |
| Missing `gcloud` | Install Cloud SDK + auth before `--execute` |
