"""Tripwire: prove that the patch targets used by the other security tests are live.

If _httpx_get or _httpx_post are ever renamed or removed in executor.py,
patch() would silently no-op and every safety test that patches those names
would pass with broken patches.  These tests catch that by (a) asserting the
attributes exist and (b) confirming that patching them actually intercepts calls.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import runewall.maps.executor as _executor


class TestPatchTargetsAreLive(unittest.TestCase):

    def test_httpx_get_attribute_exists(self) -> None:
        self.assertTrue(
            hasattr(_executor, "_httpx_get"),
            "_httpx_get not found in runewall.maps.executor — update patch targets in security tests",
        )

    def test_httpx_post_attribute_exists(self) -> None:
        self.assertTrue(
            hasattr(_executor, "_httpx_post"),
            "_httpx_post not found in runewall.maps.executor — update patch targets in security tests",
        )

    def test_patch_httpx_get_is_intercepted(self) -> None:
        mock = MagicMock(side_effect=AssertionError("patched"))
        with patch("runewall.maps.executor._httpx_get", mock):
            with self.assertRaises(AssertionError, msg="patch did not intercept _httpx_get"):
                _executor._httpx_get("https://example.com")

    def test_patch_httpx_post_is_intercepted(self) -> None:
        mock = MagicMock(side_effect=AssertionError("patched"))
        with patch("runewall.maps.executor._httpx_post", mock):
            with self.assertRaises(AssertionError, msg="patch did not intercept _httpx_post"):
                _executor._httpx_post("https://example.com")
