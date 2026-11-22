---
name: publish-gcs-assets
description: Use when the user says a language pack is ready to upload to Google / GCS / zume-file-mirror — dry-run then execute upload of PDF + Keynote + PPTX, then verify-downloads on zume.training.
---

# Publish approved language assets to GCS

## Overview

After human review + generation, upload finished **PDF + Keynote + PPTX** under `output/{lang}/` to `gs://zume-file-mirror/{lang}/`, then verify the language’s Downloads listing via `GET https://api.zume.training/api/v1/downloads/{lang}`.

Trigger phrases: “{lang} assets are ready, upload to Google”, “publish Spanish to GCS”, “upload es to zume-file-mirror”.

## Prerequisites (Mac / Creator Studio)

1. Google Cloud SDK `gcloud` on `PATH`
2. Authenticated Application Default Credentials, e.g.:
   - `gcloud auth application-default login`, or
   - `gcloud auth login` with an account that can write the bucket
3. Local pack present under `<repo>/output/{lang}/` (not Agent Store `docs/`)

Never print, paste, or commit credentials / ADC tokens.

## Pack contents

For each of `10` / `20` / `intensive`, expect three siblings (same stem):

- `Zume-Training-…-{lang}.pdf`
- `Zume-Training-…-{lang}.key`
- `Zume-Training-…-{lang}.pptx`

**PPTX source:** Keynote export during human review (`File → Export To → PowerPoint`), not the removed `slides/assemble-pptx/` builder. Do not restore that tree.

If PPTX is missing after review, the agent may open Keynote on the Mac and export via UI (computer use), saving next to the `.key` under `output/{lang}/`.

## Agent workflow

Always dry-run first, then execute, then verify:

```bash
pip install -e ".[dev]"

# 1) Dry-run (default) — lists local → gs:// paths; no network write
python3 -m zume_assets publish upload --lang es
python3 -m zume_assets publish upload --lang es --types 10,20,intensive --json

# 2) Real upload (overwrites existing objects at the same names)
python3 -m zume_assets publish upload --lang es --execute

# 3) Verify Downloads row filenames
python3 -m zume_assets publish verify-downloads --lang es
```

Spanish example expected objects:

- `gs://zume-file-mirror/es/Zume-Training-10-Session-es.pdf` / `.key` / `.pptx`
- `gs://zume-file-mirror/es/Zume-Training-20-Session-es.pdf` / `.key` / `.pptx`
- `gs://zume-file-mirror/es/Zume-Training-Intensive-es.pdf` / `.key` / `.pptx`

Public URL shape: `https://storage.googleapis.com/zume-file-mirror/{lang}/{filename}`.

## Overwrite (default)

Once Chris authorizes the upload stage (`--execute` / “upload to Google”), **always overwrite** objects that already exist at the same `gs://zume-file-mirror/{lang}/{filename}`. That is normal publish behavior — not a special ask. Do not prompt again about conflicts; do not add a refuse-if-exists guard. `gcloud storage cp` replaces in place.

## Rules

- Production upload = **PDF + Keynote + PPTX** (PPTX from Keynote export). Never restore `slides/assemble-pptx/`.
- Do **not** upload `build/{lang}/videos/` unless the user explicitly asks; then pass `--include-videos`.
- Dry-run by default; require `--execute` for real `gcloud storage cp`.
- `verify-downloads` asserts `guidebook_*`, `keynote_*`, and `powerpoint_*` fields match the stable `Zume-Training-…` names. It does **not** update downloads rows — if the API still lists old names, report the mismatch (admin/API update is a separate step).
- Keep deliverables under repo `output/{lang}/` only.

## Common mistakes

| Mistake | Fix |
|---|---|
| Upload without dry-run | Run without `--execute` first; show Chris the plan |
| Asking again about overwrite | Overwrite is default after `--execute` is authorized |
| Uploading videos by default | Omit `--include-videos` unless asked |
| Regenerating PPTX via assemble-pptx | Export from Keynote UI instead |
| Writing into Agent Store `docs/` | Upload from checkout `output/{lang}/` only |
| Missing `gcloud` | Install Cloud SDK + auth before `--execute` |
