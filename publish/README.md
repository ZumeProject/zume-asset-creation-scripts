# Publish approved language packs to GCS

Upload finished **PDF + Keynote + PPTX** from `output/{lang}/` to the Resources bucket, then verify the language Downloads listing.

## Bucket layout

| Piece | Value |
|---|---|
| Bucket | `zume-file-mirror` |
| Object prefix | `gs://zume-file-mirror/{lang}/` |
| Public URL | `https://storage.googleapis.com/zume-file-mirror/{lang}/{filename}` |
| Downloads API | `GET https://api.zume.training/api/v1/downloads/{lang}` |

Production filenames (same stem for all three):

- `Zume-Training-10-Session-{lang}.pdf` / `.key` / `.pptx`
- `Zume-Training-20-Session-{lang}.pdf` / `.key` / `.pptx`
- `Zume-Training-Intensive-{lang}.pdf` / `.key` / `.pptx`

PPTX comes from **Keynote → Export To → PowerPoint** during review (not `slides/assemble-pptx/`, which stays removed).

Do **not** upload `build/{lang}/videos/` unless `--include-videos`.

## Overwrite (default)

After upload is authorized (`--execute`), `gcloud storage cp` **always overwrites** an existing object at the same path. That is the normal publish path — no second confirmation and no refuse-if-exists guard.

## CLI

```bash
# Dry-run (default)
python3 -m zume_assets publish upload --lang es

# Real upload (requires gcloud + auth; overwrites same filenames)
python3 -m zume_assets publish upload --lang es --execute

# Verify Downloads row (guidebook_* / keynote_* / powerpoint_*)
python3 -m zume_assets publish verify-downloads --lang es
```

Implementation: `zume_assets/publish/`. Agent skill: `skills/publish-gcs-assets/SKILL.md`.

## Mac prerequisites

1. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) so `gcloud` is on `PATH`.
2. Authenticate with an account that can write `zume-file-mirror`:
   - `gcloud auth application-default login`, or
   - `gcloud auth login`
3. Local approved pack under `<repo>/output/{lang}/` (PDF + Keynote + PPTX).

Never log or commit credentials.

## Notes

- Dry-run by default; `--execute` required for `gcloud storage cp`.
- `verify-downloads` is read-only: it asserts guidebook_*, keynote_*, and powerpoint_* filenames. Updating downloads rows in zume6 remains a separate admin/API step when names must change.
- Build CLI still rejects `--targets pptx`; Keynote export is the PPTX path for publish.
