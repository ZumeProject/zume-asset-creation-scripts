#!/usr/bin/env python3
"""Gentle Keynote health checks for Mac assemble/embed loops.

Detects hung/unresponsive Keynote (Creator Studio), clean-quits or force-quits,
relaunches, and signals callers to resume. Prefer short pings and avoid stacking
AppleScript while the app is stuck.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable


APP_NAME = "Keynote"  # Creator Studio still scripts as "Keynote"
PROCESS_NAMES = ("Keynote Creator Studio", "Keynote")


@dataclass
class HealthResult:
    ok: bool
    detail: str
    relaunched: bool = False


def _pkill(pattern: str) -> None:
    subprocess.run(["pkill", "-f", pattern], check=False, capture_output=True)


def kill_osascript() -> None:
    """Stop runaway AppleScript so we never hammer a stuck Keynote."""
    _pkill("osascript")


def run_osascript(script: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run osascript with a hard timeout; kill osascript on hang."""
    try:
        r = subprocess.run(
            ["osascript"],
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except subprocess.TimeoutExpired:
        kill_osascript()
        return 124, "", "TIMEOUT"


def keynote_running() -> bool:
    r = subprocess.run(["pgrep", "-f", "Keynote"], capture_output=True, text=True)
    return r.returncode == 0 and bool((r.stdout or "").strip())


def ping(timeout: int = 12) -> HealthResult:
    """Return ok if Keynote answers a tiny AppleScript ping."""
    code, out, err = run_osascript(
        f'''
tell application "{APP_NAME}"
  return (name as text) & ":" & (count of documents as text)
end tell
''',
        timeout=timeout,
    )
    if code == 0 and out:
        return HealthResult(True, f"ping {out}")
    if code == 124:
        return HealthResult(False, "ping TIMEOUT")
    return HealthResult(False, f"ping fail code={code} err={(err or out)[:160]}")


def quit_clean(timeout: int = 25) -> HealthResult:
    """Ask Keynote to quit; do not force yet."""
    kill_osascript()
    code, out, err = run_osascript(
        f'''
tell application "{APP_NAME}"
  try
    repeat with d in (get documents)
      try
        close d saving yes
      end try
    end repeat
  end try
  quit
end tell
''',
        timeout=timeout,
    )
    time.sleep(2)
    if not keynote_running():
        return HealthResult(True, "quit clean")
    return HealthResult(False, f"quit incomplete code={code} {(err or out)[:120]}")


def force_quit() -> None:
    kill_osascript()
    for name in PROCESS_NAMES:
        subprocess.run(["killall", "-9", name], check=False, capture_output=True)
    _pkill("Keynote Creator Studio")
    _pkill("/MacOS/Keynote")
    time.sleep(2)


def relaunch(wait_s: float = 8.0) -> HealthResult:
    """Open Keynote Creator Studio and wait until ping succeeds."""
    force_quit()
    subprocess.run(
        ["open", "-a", "Keynote Creator Studio"],
        check=False,
        capture_output=True,
    )
    deadline = time.time() + max(wait_s, 5.0)
    last = HealthResult(False, "relaunch waiting")
    while time.time() < deadline:
        time.sleep(1.5)
        last = ping(timeout=10)
        if last.ok:
            last.relaunched = True
            last.detail = f"relaunched; {last.detail}"
            return last
    # One more open attempt
    subprocess.run(
        ["open", "-a", "Keynote Creator Studio"],
        check=False,
        capture_output=True,
    )
    time.sleep(3)
    last = ping(timeout=12)
    last.relaunched = True
    if not last.ok:
        last.detail = f"relaunch ping failed: {last.detail}"
    else:
        last.detail = f"relaunched; {last.detail}"
    return last


def ensure_healthy(
    *,
    log: Callable[[str], None] | None = None,
    max_restarts: int = 2,
) -> HealthResult:
    """Ping Keynote; on failure quit/relaunch up to max_restarts times."""

    def _log(msg: str) -> None:
        if log:
            log(msg)
        else:
            print(msg, flush=True)

    result = ping()
    if result.ok:
        return result

    _log(f"keynote unhealthy: {result.detail}")
    for attempt in range(1, max_restarts + 1):
        _log(f"keynote recovery attempt {attempt}/{max_restarts}")
        q = quit_clean()
        if not q.ok:
            _log(f"clean quit failed ({q.detail}); force quitting")
            force_quit()
        r = relaunch()
        _log(r.detail)
        if r.ok:
            return r
    return HealthResult(False, "keynote still unhealthy after relaunches")


def with_health(
    action: Callable[[], bool],
    *,
    log: Callable[[str], None] | None = None,
    retries: int = 1,
) -> bool:
    """Run action; if it fails or Keynote dies, recover and retry once."""

    def _log(msg: str) -> None:
        if log:
            log(msg)
        else:
            print(msg, flush=True)

    healthy = ensure_healthy(log=_log)
    if not healthy.ok:
        _log(f"abort: {healthy.detail}")
        return False

    for attempt in range(retries + 1):
        try:
            if action():
                return True
        except Exception as exc:  # noqa: BLE001
            _log(f"action error: {exc}")
        # Failed — check health and maybe relaunch
        h = ping(timeout=10)
        if not h.ok:
            _log(f"post-fail ping: {h.detail}")
            ensure_healthy(log=_log, max_restarts=1)
        elif attempt < retries:
            _log("action failed with Keynote still up; retrying once")
            time.sleep(1)
    return False
