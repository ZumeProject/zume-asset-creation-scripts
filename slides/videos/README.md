# Training videos (Vimeo)

Folder IDs live in `slide-builder/parts/vimeo-folders.json`.

| Lang | Folder | URL |
|---|---|---|
| `en` | `21862752` | https://vimeo.com/user/75461893/folder/21862752 |
| `es` | `269525` | https://vimeo.com/user/75461893/folder/269525 |

## Download

```bash
# Needs VIMEO_ACCESS_TOKEN or VIMEO_PERSONAL_ACCESS_TOKEN (+ client id/secret aliases) in env or repo .env
# Never print or commit those secrets.
pip install -r slide-builder/requirements.txt

# Any mapped language (writes output/{lang}/videos + SOURCE.json; gitignored)
python3 slides/videos/download_lang_vimeo.py --lang es
python3 slides/videos/download_lang_vimeo.py --lang en

# EN-only wrapper (same folder; kept for older docs/scripts)
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Writes numbered `output/{lang}/videos/{id}.mp4` plus `SOURCE.json` provenance
(`source=vimeo`, `folder_id`, optional `language_code`). That directory is
gitignored (`output/**/videos/`).

If the folder has `19` but not `20`, `download_lang_vimeo.py` aliases `20.mp4`
from `19.mp4` (Faithfulness / `t20_b`).

Production default is **Vimeo**, not GCS / `zume-file-mirror`. Do not silently
substitute mirror MP4s when rebuilding decks.

## Assemble after download

Copy or link the numbered MP4s into the capture pack’s `videos/` as required by
Keynote embed, then:

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang es
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang es --promote
```
