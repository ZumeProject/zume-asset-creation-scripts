# PowerPoint assembly (python-pptx)

Build image-embedded widescreen PPTX from the presenter capture pack + GCS MP4s.
Video/thought slides get a full-bleed MP4 plus the upper-left play-icon chrome
(`slides/assets/video-play-icon.png`).

Default finished output is the repo checkout (never Agent Store `docs/`):

`output/en/Zume-Training-10-Session-en.pptx`

```bash
pip install -r slides/assemble-pptx/requirements.txt
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

Prefetch videos only:

```bash
python3 slides/assemble-pptx/assemble_en10.py --download-videos-only
```
