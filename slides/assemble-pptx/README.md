# PowerPoint assembly (python-pptx)

Build image-embedded widescreen PPTX from the presenter capture pack + local MP4s.
Video/thought slides get a full-bleed MP4 plus the upper-left play-icon chrome
(`slides/assets/video-play-icon.png`).

Canonical EN MP4s come from Vimeo folder
[21862752](https://vimeo.com/user/75461893/folder/21862752) via
`slides/videos/download_en_vimeo.py` (not the GCS `zume-file-mirror` set).

Default finished output is the repo checkout (never Agent Store `docs/`):

`output/en/Zume-Training-10-Session-en.pptx`

```bash
pip install -r slides/assemble-pptx/requirements.txt
python3 slides/videos/download_en_vimeo.py --out output/en/videos
python3 slides/assemble-pptx/assemble_en10.py \
  --pack /cursor/stores/.../media/en-10-presenter-captures \
  --output output/en/Zume-Training-10-Session-en.pptx
```

All course types:

```bash
python3 slides/assemble-pptx/assemble_presenter.py --type 10
python3 slides/assemble-pptx/assemble_presenter.py --type 20
python3 slides/assemble-pptx/assemble_presenter.py --type intensive
```

Prefetch videos only (requires Vimeo provenance under `--videos`):

```bash
python3 slides/videos/download_en_vimeo.py --out output/en/videos
python3 slides/assemble-pptx/assemble_en10.py --download-videos-only
```
