# Keynote assembly (macOS / Creator Studio)

Scripts for building 16:9 image decks, embedding MP4s via Insert → Choose File
(AppleScript `make new movie` is broken in Keynote Creator Studio), and restoring
the upper-left video/thumbnail play-icon chrome on every video slide.

## Scripts

- `keynote_health.py` — ping / clean-quit / relaunch helper (used by all Keynote drivers)
- `assemble_images_keynote.py` — build full-bleed PNG Keynote from a capture pack
- `embed_videos_choose.py` — embed local MP4s **and** ensure upper-left play icons (calls overlay)
- `overlay_video_icons.py` — idempotent play-icon pass (also invoked from embed)

## Normal rebuild (any language / course)

Capture pack layout: `build/{lang}/captures/{10|20|intensive}/`. `videos/` links to `build/{lang}/videos`.

```bash
# 1) Image deck from PNGs
python3 slides/assemble-keynote/assemble_images_keynote.py --type 10 --lang en

# 2) Embed MP4s + upper-left video chrome (health-checked loop)
python3 slides/assemble-keynote/embed_videos_choose.py --type 10 --lang en --promote
```

`--lang` / `--type` select the pack and `output/{lang}/Zume-Training-*-{lang}.key`.
Other locales use the same commands with `--lang ky` (etc.) once that pack exists.

Production deck format is Keynote only (PPTX assembly was removed). Shared icon
asset: `slides/assets/video-play-icon.png`.

## Health / hang recovery

Drivers ping Keynote before work and every few slides. On timeout or failed ping
they: kill runaway `osascript` → clean quit (then force-quit if needed) → relaunch
Creator Studio → reopen the deck → resume. Do not stack AppleScript against a
stuck Keynote.

## Requirements

- Keynote Creator Studio (scripted as application `"Keynote"`)
- macOS screen **unlocked** (System Events file dialogs fail while locked)
- Capture packs under `build/{lang}/captures/{type}/`

## Outputs

Deliverables go to the repo checkout `output/{lang}/` (not Agent Store `docs/`).
