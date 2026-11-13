# PowerPoint assembly (python-pptx)

Build image-embedded widescreen PPTX from the presenter capture pack + GCS MP4s.

Default finished output is the repo checkout (never Agent Store `docs/`):

`output/en/Zume-Training-10-Session-en.pptx`

```bash
pip install -r slides/assemble-pptx/requirements.txt
python3 slides/assemble-pptx/assemble_en10.py \
  --pack /cursor/stores/.../media/en-10-presenter-captures \
  --output output/en/Zume-Training-10-Session-en.pptx
```

Prefetch videos only:

```bash
python3 slides/assemble-pptx/assemble_en10.py --download-videos-only
```
