# Publish approved language packs to GCS

Upload finished **PDF + Keynote** from `output/{lang}/` to the Resources bucket, then verify the language Downloads listing.

## Bucket layout

| Piece | Value |
|---|---|
| Bucket | `zume-file-mirror` |
| Object prefix | `gs://zume-file-mirror/{lang}/` |
| Public URL | `https://storage.googleapis.com/zume-file-mirror/{lang}/{filename}` |
| Downloads API | `GET https://api.zume.training/api/v1/downloads/{lang}` |

Production filenames (PDF + Keynote only):

- `Zume-Training-10-Session-{lang}.pdf` / `.key`
- `Zume-Training-20-Session-{lang}.pdf` / `.key`
- `Zume-Training-Intensive-{lang}.pdf` / `.key`

Do **not** upload PPTX. Do **not** upload `output/{lang}/videos/` unless `--include-videos`.

## CLI

```bash
# Dry-run (default)
python3 -m zume_assets publish upload --lang es

# Real upload (requires gcloud + auth)
python3 -m zume_assets publish upload --lang es --execute

# Verify Downloads row
python3 -m zume_assets publish verify-downloads --lang es
```

Implementation: `zume_assets/publish/`. Agent skill: `skills/publish-gcs-assets/SKILL.md`.

## Mac prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) so `gcloud` is on `PATH`.
2. Authenticate with an account that can write `zume-file-mirror`:
   - `gcloud auth application-default login`, or
   - `gcloud auth login`
3. Local approved pack under `<repo>/output/{lang}/`.

Never log or commit credentials.

## Notes

- Dry-run by default; `--execute` required for `gcloud storage cp`.
- `verify-downloads` is read-only: it asserts guidebook_* / keynote_* filenames. Updating downloads rows in zume6 remains a separate admin/API step when names must change.
- PPTX / powerpoint_* fields may still appear on the API row; this pipeline ignores them.
