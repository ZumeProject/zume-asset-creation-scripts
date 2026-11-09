# PowerPoint assembly (python-pptx)

Build image-embedded widescreen PPTX from the presenter capture pack + GCS MP4s.

```bash
python3 slides/assemble-pptx/assemble_en10.py \
  --pack /cursor/stores/.../media/en-10-presenter-captures \
  --output /cursor/stores/.../docs/zume-10-session-en.pptx
```

Prefetch videos only:

```bash
python3 slides/assemble-pptx/assemble_en10.py --download-videos-only
```
