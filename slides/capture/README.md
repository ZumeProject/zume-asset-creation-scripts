# Presenter slide capture (Playwright)

Capture live presenter slideshow frames as PNGs for Keynote assembly.

**Production packs must use `https://zume.training`.** Capturing against
`http://localhost:3000` bakes QR payloads like `http://localhost:3000/app/qr/…`
into the PNGs (and then into Keynote). Spanish packs that used production are
correct; localhost-captured packs are not.

## Production capture (default)

```bash
pip install -r slides/capture/requirements.txt
playwright install chromium

python3 slides/capture/capture_presenter.py --lang pus --type 10
# optional: refresh only slides whose QR is not zume.training
python3 slides/capture/capture_presenter.py --lang pus --type 10 --invalidate-nonprod-qr
```

Override with `$PRESENTER_BASE_URL` or `--base` if needed. Non-production bases
are refused unless you pass `--allow-localhost`.

## Local smoke only

```bash
# Prefer hostname "localhost" — Next.js 16 blocks 127.0.0.1 for HMR/dev assets
# unless allowedDevOrigins is set, which leaves the presenter stuck on Loading.
python3 slides/capture/capture_presenter.py --lang en --type 10 \
  --base http://localhost:3000 --allow-localhost --limit 5
```

Legacy EN-10 helper (still defaults to local; prefer `capture_presenter.py`):

```bash
export PRESENTER_BASE_URL=http://127.0.0.1:3000
python3 slides/capture/capture_en10.py
```

Writes the capture pack (intermediate PNGs + manifest) to the Project store:

`/cursor/stores/.../media/{lang}-{10|20|intensive}-presenter-captures/{pngs,manifest.json}`

Finished Keynote decks assembled from this pack belong under the repo
`output/{lang}/` directory — never Agent Store `docs/`.

Viewport: 1920×1080 @ deviceScaleFactor 2 (3840×2160) for `capture_presenter.py`.
