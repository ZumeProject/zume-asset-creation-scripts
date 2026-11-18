---
name: mac-keynote-assemble
description: Use when assembling or repairing Zúme Keynote decks on macOS — image decks, video embed via Choose File, play-icon chrome, keynote_health hangs, or Creator Studio scripting in zume-asset-creation-scripts.
---

# Mac Keynote assemble + health

## Overview

Keynote decks are built only on **macOS** with Keynote Creator Studio. Drivers live under `slides/assemble-keynote/` and use `keynote_health` to recover from hangs.

## Before assemble (loud blockers)

```bash
python3 -m zume_assets prereqs --lang <lang>
```

`assemble_images_keynote.py` auto-runs the **full** readiness gate and aborts on any BLOCK. Must be clean for:

1. Vimeo map entry + local `output/{lang}/videos/` MP4s (`SOURCE.json`)
2. Capture pack: Agent Store `media/{lang}-{10|20|intensive}-presenter-captures/` (PNGs + `manifest.json`; sync MP4s into pack `videos/`)

Missing map/pack/videos → assemble exits with next steps. Escalate missing folder ids to Chris (do not invent). PDF-only success does **not** mean Keynote is ready.

## Normal rebuild

```bash
python3 slides/assemble-keynote/assemble_images_keynote.py --type <type> --lang <lang>
python3 slides/assemble-keynote/embed_videos_choose.py --type <type> --lang <lang> --promote
```

`--promote` copies the finished `.key` to `output/{lang}/`.

## Scripts

| Script | Role |
|---|---|
| `keynote_health.py` | Ping / clean-quit / relaunch; used by all drivers |
| `assemble_images_keynote.py` | Full-bleed PNG deck |
| `embed_videos_choose.py` | Insert → Choose File embed + play chrome |
| `overlay_video_icons.py` | Idempotent upper-left play icon (also called from embed) |

Icon asset: `slides/assets/video-play-icon.png` (tight left/top inset).

## Health rules

- Ping before work and during loops; on failure: kill runaway `osascript` → clean quit (then force) → relaunch → reopen → resume.
- Do not stack AppleScript against a stuck Keynote.
- Screen must be **unlocked** (System Events file dialogs fail while locked).

## Requirements

- Keynote Creator Studio (scripted as application `"Keynote"`)
- Local MP4s for every manifest video slide (from Vimeo download skill for that language)
- Never run these drivers on Linux CI

## Common mistakes

| Mistake | Fix |
|---|---|
| Using AppleScript `make new movie` | Broken in Creator Studio — use Choose File path |
| Skipping overlay / play chrome | Embed driver should run overlay; verify upper-left icons |
| Writing `.key` into Agent Store `docs/` | Promote to repo `output/{lang}/` only |
| Ignoring hang instead of `keynote_health` | Recover via health helper, then resume |
| Assembling without videos/map and calling it done | Run `prereqs`; fix BLOCKs or stop for Chris |
