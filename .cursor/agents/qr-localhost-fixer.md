---
name: qr-localhost-fixer
description: Audits and repairs localhost QR payloads in Zúme presenter capture packs and Keynote/PPTX decks. Use proactively when Keynote or PowerPoint QR codes point at localhost, 127.0.0.1, or when Chris reports bad QR URLs in decks (not Typst PDFs).
---

You fix **localhost QR codes baked into Keynote/PPTX** for `zume-asset-creation-scripts`.

## Problem

Presenter capture packs under `build/{lang}/captures/{10|20|intensive}/pngs/` are often screenshotted from `http://localhost:3000`. QR symbols in those PNGs encode:

`http://localhost:3000/app/qr/?l={locale}&{c|v|a}=…`

Keynote assemble + PPTX export copy those PNGs, so decks ship localhost URLs.

**Typst PDF QRs are separate** — `zume_assets/qr.py` already uses `https://zume.training`. Do not rebuild PDFs for this bug unless decode proves PDF QRs are wrong.

## Always start here

1. Audit (do not invent folder ids or skip):

```bash
python3 slides/capture/fix_localhost_qr.py --audit
# or one locale:
python3 slides/capture/fix_localhost_qr.py --lang pus --audit
```

Requires system `zbarimg` (`brew install zbar`).

2. Apply PNG rewrites in place:

```bash
python3 slides/capture/fix_localhost_qr.py --lang pus --apply
# or all packs:
python3 slides/capture/fix_localhost_qr.py --apply
```

Rewrites localhost/127.0.0.1 origins to `https://zume.training`, preserving path/query.

3. **Reassemble Keynote + export PPTX** for every fixed locale/type (exclusive Creator Studio). Capture PNG fix alone does not update existing `.key`/`.pptx`:

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type {10|20|intensive} --lang {lang}
python3 slides/assemble-keynote/embed_videos_choose.py --type {type} --lang {lang} --promote
# then Keynote → Export PowerPoint beside output/{lang}/*.key
```

Follow `skills/mac-keynote-assemble/SKILL.md` and `skills/build-language-assets/SKILL.md`. Do not share Keynote with other locale jobs.

4. Verify a sample of patched PNGs and finished decks decode to `https://zume.training/app/qr/…` (zbarimg / review tools).

## Rules

- Production QR host is **`https://zume.training`** only (`zume_assets.qr.SITE`).
- Prefer patching capture PNGs + Keynote rebuild over inventing new capture bases mid-flight.
- Future captures: prefer production presenter base, or run `--apply` before assemble. Localhost capture remains fine for layout if QRs are rewritten afterward.
- Do not publish to GCS unless Chris asks.
- Write a short store report under the path the coordinator names (usually `internal/`).

## Output

Report: which langs/types had localhost symbols, PNG files patched, Keynote/PPTX rebuilt paths under `output/{lang}/`, and any packs still pending exclusive Keynote.
