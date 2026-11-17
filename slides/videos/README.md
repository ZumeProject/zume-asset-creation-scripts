# EN training videos (Vimeo)

Canonical English source:

https://vimeo.com/user/75461893/folder/21862752

That folder ID (`21862752`) is also the `en` entry in
`slide-builder/parts/vimeo-folders.json`.

## Download

```bash
# Needs VIMEO_ACCESS_TOKEN or VIMEO_PERSONAL_ACCESS_TOKEN (+ client id/secret aliases) in env or repo .env
pip install -r slide-builder/requirements.txt
python3 slides/videos/download_en_vimeo.py --out output/en/videos
```

Writes numbered `output/en/videos/{id}.mp4` plus `SOURCE.json` provenance
(`folder_id=21862752`). Keynote assemble requires that provenance and will
not silently pull `zume-file-mirror` GCS MP4s unless you pass `--allow-gcs-fallback`.

## Assemble after download

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```
