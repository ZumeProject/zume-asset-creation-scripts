#!/usr/bin/env python3
"""Download training MP4s from the Vimeo folder mapped for a language.

Uses ``slide-builder/parts/vimeo-folders.json`` (same map as slide-builder).
For English this is folder ``21862752``; for Spanish (``es``) it is ``269525``.

Requires env (or slide-builder/.env / repo .env):
  VIMEO_ACCESS_TOKEN (or VIMEO_PERSONAL_ACCESS_TOKEN)
  VIMEO_CLIENT_ID (or VIMEO_CLIENT_IDENTIFIER)
  VIMEO_CLIENT_SECRET (or VIMEO_CLIENT_SECRETS)

Writes numbered files to --out (default: output/{lang}/videos/{id}.mp4) plus
SOURCE.json provenance so assemble can refuse GCS / stale caches.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vimeo_folder import (  # noqa: E402
    EN_VIMEO_FOLDER_ID,
    EN_VIMEO_USER_ID,
    assert_en_folder_id,
    folder_id_for_language,
    numeric_id_from_title,
    write_provenance,
)

MIN_MP4_BYTES = 100_000
ENV_FILES = (
    REPO_ROOT / "slide-builder" / ".env",
    REPO_ROOT / ".env",
)


def load_dotenv_files() -> None:
    for path in ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export ") :].strip()
            if key in os.environ and os.environ[key]:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


def _first_env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def require_credentials() -> tuple[str, str, str]:
    load_dotenv_files()
    token = _first_env("VIMEO_ACCESS_TOKEN", "VIMEO_PERSONAL_ACCESS_TOKEN")
    client_id = _first_env("VIMEO_CLIENT_ID", "VIMEO_CLIENT_IDENTIFIER")
    client_secret = _first_env("VIMEO_CLIENT_SECRET", "VIMEO_CLIENT_SECRETS")
    if not token:
        raise SystemExit(
            "Missing VIMEO_ACCESS_TOKEN / VIMEO_PERSONAL_ACCESS_TOKEN. Set it in "
            "the environment or repo .env."
        )
    return client_id or "unused", client_secret or "unused", token


def get_client():
    try:
        import vimeo
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "PyVimeo is required. Install with: pip install -r slide-builder/requirements.txt"
        ) from exc
    client_id, client_secret, token = require_credentials()
    return vimeo.VimeoClient(token=token, key=client_id, secret=client_secret)


def list_folder_videos(client, folder_id: str) -> list[dict[str, Any]]:
    endpoints = [
        f"/me/projects/{folder_id}/videos",
        f"/me/folders/{folder_id}/videos",
        f"/users/{EN_VIMEO_USER_ID}/projects/{folder_id}/videos",
        f"/users/{EN_VIMEO_USER_ID}/folders/{folder_id}/videos",
        f"/users/me/projects/{folder_id}/videos",
        f"/users/me/folders/{folder_id}/videos",
    ]
    videos: list[dict[str, Any]] = []
    last_error = ""
    for endpoint in endpoints:
        page = 1
        page_videos: list[dict[str, Any]] = []
        while True:
            response = client.get(
                endpoint,
                params={
                    "page": page,
                    "per_page": 100,
                    "fields": "uri,name,duration,link",
                },
            )
            if response.status_code >= 400:
                last_error = f"{endpoint} -> {response.status_code} {response.text[:200]}"
                page_videos = []
                break
            payload = response.json()
            batch = payload.get("data") or []
            page_videos.extend(batch)
            paging = payload.get("paging") or {}
            if not paging.get("next"):
                break
            page += 1
        if page_videos:
            videos = page_videos
            print(f"listed {len(videos)} videos via {endpoint}", flush=True)
            break
    if not videos:
        raise SystemExit(f"Could not list Vimeo folder {folder_id}. Last error: {last_error}")
    for video in videos:
        video["id"] = str(video.get("uri", "")).rstrip("/").split("/")[-1]
    return videos


def highest_download_link(client, video_id: str) -> tuple[str, str]:
    response = client.get(f"/videos/{video_id}", params={"fields": "download,name"})
    if response.status_code >= 400:
        raise RuntimeError(f"video {video_id} info failed: {response.status_code}")
    info = response.json()
    downloads = info.get("download") or []
    if not downloads:
        raise RuntimeError(
            f"video {video_id} has no download[] links (token needs download scope)"
        )
    best = max(
        downloads,
        key=lambda item: int(item.get("width") or 0) * int(item.get("height") or 0),
    )
    return str(best["link"]), str(best.get("quality") or "unknown")


def download_file(url: str, dest: Path, *, attempts: int = 4) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".partial")
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with requests.get(url, stream=True, timeout=300) as response:
                response.raise_for_status()
                with open(tmp, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
            size = tmp.stat().st_size
            if size < MIN_MP4_BYTES:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"downloaded file too small ({size} bytes): {dest.name}")
            tmp.replace(dest)
            return size
        except (requests.RequestException, RuntimeError, OSError) as exc:
            last_error = exc
            tmp.unlink(missing_ok=True)
            print(f"retry {attempt}/{attempts} {dest.name}: {exc}", flush=True)
            time.sleep(min(30, 2 * attempt))
    raise RuntimeError(f"download failed for {dest.name}: {last_error}")


def process_one(
    client,
    video: dict[str, Any],
    out_dir: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    title = str(video.get("name") or "")
    video_id = str(video["id"])
    number = numeric_id_from_title(title)
    if number is None:
        return {
            "status": "skip",
            "reason": "no_numeric_id",
            "vimeo_id": video_id,
            "title": title,
        }
    dest = out_dir / f"{number}.mp4"
    if dest.exists() and dest.stat().st_size >= MIN_MP4_BYTES and not force:
        return {
            "status": "cached",
            "training_id": number,
            "vimeo_id": video_id,
            "title": title,
            "path": str(dest),
            "bytes": dest.stat().st_size,
        }
    try:
        link, quality = highest_download_link(client, video_id)
        size = download_file(link, dest)
    except Exception as exc:  # noqa: BLE001 — surface as failed result for pool
        return {
            "status": "failed",
            "training_id": number,
            "vimeo_id": video_id,
            "title": title,
            "error": str(exc),
        }
    return {
        "status": "downloaded",
        "training_id": number,
        "vimeo_id": video_id,
        "title": title,
        "quality": quality,
        "path": str(dest),
        "bytes": size,
    }


def maybe_alias_20(out_dir: Path, by_training: dict[str, Any]) -> dict[str, Any] | None:
    """If folder has 19 but not 20, alias 20.mp4 from 19 (Faithfulness / t20_b)."""
    has_19 = (out_dir / "19.mp4").exists() and "19" in by_training
    has_20 = (out_dir / "20.mp4").exists() and "20" in by_training
    if has_19 and not has_20:
        src = out_dir / "19.mp4"
        dest = out_dir / "20.mp4"
        if not dest.exists():
            dest.write_bytes(src.read_bytes())
        alias = {
            "from": "19",
            "reason": "t20_b / Faithfulness slot; folder has 19 only",
            "bytes": dest.stat().st_size,
            "path": str(dest),
            "status": "aliased",
            "title": by_training["19"].get("title"),
            "vimeo_id": by_training["19"].get("vimeo_id"),
        }
        by_training["20"] = {
            "vimeo_id": alias["vimeo_id"],
            "title": alias["title"],
            "bytes": alias["bytes"],
            "path": alias["path"],
            "status": "aliased",
            "quality": by_training["19"].get("quality"),
        }
        print(f"aliased 20.mp4 from 19.mp4 ({alias['bytes']} bytes)", flush=True)
        return {"20": {"from": "19", "reason": alias["reason"]}}
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", default="en", help="Language code (es, en, …)")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--folder-id", default=None, help="Override folder id (must match map)")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument(
        "--no-alias-20",
        action="store_true",
        help="Do not copy 19.mp4 → 20.mp4 when 20 is missing",
    )
    args = parser.parse_args(argv)

    lang = args.lang.strip().lower()
    try:
        folder_id, display_name = folder_id_for_language(lang)
    except KeyError:
        raise SystemExit(
            f"No Vimeo folder mapped for language_code={lang!r} in "
            "slide-builder/parts/vimeo-folders.json. "
            "Known production ids: en→21862752, es→269525. "
            "Do not invent a folder id. Ask Chris for this language’s Vimeo folder "
            f"(user 75461893), add the map entry, then re-run. "
            f"Checklist: python3 -m zume_assets prereqs --lang {lang}"
        ) from None
    if lang == "en":
        assert_en_folder_id()
        folder_id = EN_VIMEO_FOLDER_ID
    if args.folder_id and str(args.folder_id) != str(folder_id):
        raise SystemExit(
            f"--folder-id {args.folder_id} does not match mapped {lang} folder {folder_id}"
        )

    out_dir = args.out or (REPO_ROOT / "output" / lang / "videos")
    folder_url = f"https://vimeo.com/user/{EN_VIMEO_USER_ID}/folder/{folder_id}"

    client = get_client()
    videos = list_folder_videos(client, folder_id)
    print(
        f"lang={lang} name={display_name!r} folder={folder_url} videos={len(videos)}",
        flush=True,
    )
    for video in videos:
        number = numeric_id_from_title(str(video.get("name") or ""))
        print(f"  {number!s:>3}  {video['id']}  {video.get('name')}", flush=True)
    if args.list_only:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = [
            pool.submit(process_one, client, video, out_dir, force=args.force)
            for video in videos
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{result.get('status')} id={result.get('training_id')} "
                f"vimeo={result.get('vimeo_id')} title={result.get('title')!r}",
                flush=True,
            )

    by_training: dict[str, Any] = {}
    for result in results:
        training_id = result.get("training_id")
        if training_id is None:
            continue
        by_training[str(training_id)] = {
            "vimeo_id": result.get("vimeo_id"),
            "title": result.get("title"),
            "bytes": result.get("bytes"),
            "path": result.get("path"),
            "status": result.get("status"),
            "quality": result.get("quality"),
        }

    aliases = None if args.no_alias_20 else maybe_alias_20(out_dir, by_training)

    provenance: dict[str, Any] = {
        "source": "vimeo",
        "language_code": lang,
        "user_id": EN_VIMEO_USER_ID,
        "folder_id": folder_id,
        "folder_url": folder_url,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "video_count": len(by_training),
        "videos": by_training,
    }
    if aliases:
        provenance["aliases"] = aliases
    path = write_provenance(out_dir, provenance)
    print(f"wrote provenance {path} ({len(by_training)} numbered videos)", flush=True)

    failed = [r for r in results if r.get("status") not in {"downloaded", "cached", "skip"}]
    if failed:
        return 2
    if len(by_training) < 20:
        print(f"warn: only {len(by_training)} numbered videos mapped", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
