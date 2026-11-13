# Presenter slide capture (Playwright)

Capture live presenter slideshow frames as PNGs for PPTX/Keynote assembly.

## EN 10

```bash
pip install -r slides/capture/requirements.txt
playwright install chromium
# Prefer Chris's local zume6
export PRESENTER_BASE_URL=http://127.0.0.1:3000
python3 slides/capture/capture_en10.py
```

Writes ordered pack to the Project store:

`/cursor/stores/.../media/en-10-presenter-captures/{pngs,manifest.json}`

Viewport: 1846×1034 @ deviceScaleFactor 2 (3692×2068), matching reference PPSX media.
