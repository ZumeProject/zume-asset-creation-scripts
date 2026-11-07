"""Live zume6 API client for presenter, scripts, and activities."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.zume.training/api/v1"
SITE_BASE = "https://zume.training"


def _get_json(url: str, timeout: int = 60) -> Any:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "zume-assets/0.1"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_presenter_content(locale: str = "en", fallback: str = "en") -> dict[str, Any]:
    q = urlencode({"fallback": fallback})
    return _get_json(f"{API_BASE}/presenter/content/{locale}?{q}")


def fetch_script_by_video(video_key: str, language_id: str = "en") -> dict[str, Any] | None:
    q = urlencode({"language_id": language_id, "fallback_language_id": "en"})
    url = f"{API_BASE}/scripts/by-video/{video_key}?{q}"
    try:
        return _get_json(url)
    except Exception:
        return None


def fetch_activity(
    activity_key: str,
    language_id: str = "en",
    *,
    render_shortcodes: bool = True,
) -> dict[str, Any] | None:
    q = urlencode(
        {
            "language_id": language_id,
            "fallback_language_id": "en",
            "render_shortcodes": "true" if render_shortcodes else "false",
        }
    )
    url = f"{API_BASE}/activities/{activity_key}?{q}"
    try:
        return _get_json(url)
    except Exception:
        return None


def cache_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@lru_cache(maxsize=1)
def load_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent
