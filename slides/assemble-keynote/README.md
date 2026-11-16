# Keynote assembly (macOS / Creator Studio)

Scripts for building 16:9 image decks and embedding MP4s via Insert → Choose File
(AppleScript `make new movie` is broken in Keynote Creator Studio).

## Scripts

- `assemble_images_keynote.py` — build full-bleed PNG Keynote from a capture pack
- `embed_videos_choose.py` — replace video slides with local MP4s (29 for EN courses)

## Requirements

- Keynote Creator Studio (scripted as application `"Keynote"`)
- macOS screen **unlocked** (System Events file dialogs fail while locked)
- Capture packs under the Project Agent Store `media/en-{20,intensive}-presenter-captures/`

## Outputs

Deliverables go to `/Users/chris/Documents/ZUME/zume-asset-creation-scripts-1/output/en/`
(not Agent Store `docs/`).
