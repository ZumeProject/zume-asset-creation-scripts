#!/usr/bin/env python3
"""Unit tests for Keynote health helper (no live Keynote required)."""
from __future__ import annotations

import unittest
from unittest import mock

import keynote_health as kh


class KeynoteHealthUnitTests(unittest.TestCase):
    def test_ping_ok(self) -> None:
        with mock.patch.object(
            kh, "dismiss_modified_dialogs", return_value=kh.HealthResult(True, "clicked:0")
        ):
            with mock.patch.object(kh, "run_osascript", return_value=(0, "Keynote:1", "")):
                result = kh.ping()
        self.assertTrue(result.ok)
        self.assertIn("ping", result.detail)

    def test_ping_timeout(self) -> None:
        with mock.patch.object(
            kh, "dismiss_modified_dialogs", return_value=kh.HealthResult(True, "clicked:0")
        ):
            with mock.patch.object(kh, "run_osascript", return_value=(124, "", "TIMEOUT")):
                result = kh.ping()
        self.assertFalse(result.ok)
        self.assertIn("TIMEOUT", result.detail)

    def test_dismiss_modified_dialogs_ok(self) -> None:
        with mock.patch.object(kh, "run_osascript", return_value=(0, "clicked:1", "")):
            result = kh.dismiss_modified_dialogs()
        self.assertTrue(result.ok)
        self.assertIn("clicked", result.detail)

    def test_ensure_healthy_short_circuits_on_ok_ping(self) -> None:
        with mock.patch.object(kh, "ping", return_value=kh.HealthResult(True, "ping ok")):
            with mock.patch.object(kh, "relaunch") as relaunch:
                result = kh.ensure_healthy()
        self.assertTrue(result.ok)
        relaunch.assert_not_called()

    def test_ensure_healthy_relaunches_when_unhealthy(self) -> None:
        pings = [
            kh.HealthResult(False, "ping TIMEOUT"),
            kh.HealthResult(True, "ping Keynote:0"),
        ]

        def _ping(*_a, **_k):
            return pings.pop(0) if pings else kh.HealthResult(True, "ping ok")

        with mock.patch.object(kh, "ping", side_effect=_ping):
            with mock.patch.object(kh, "quit_clean", return_value=kh.HealthResult(True, "quit")):
                with mock.patch.object(
                    kh, "relaunch", return_value=kh.HealthResult(True, "relaunched", relaunched=True)
                ) as relaunch:
                    result = kh.ensure_healthy(max_restarts=1)
        self.assertTrue(result.ok)
        self.assertTrue(result.relaunched)
        relaunch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
