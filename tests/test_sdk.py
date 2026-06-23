from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runewall.sdk as sdk


class SdkTests(unittest.TestCase):
    def test_policy_test_returns_dict(self) -> None:
        result = sdk.policy_test("map.execute")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["action_type"], "map.execute")

    def test_policy_audit_returns_dict(self) -> None:
        result = sdk.policy_audit()
        self.assertIsInstance(result, dict)
        self.assertIn("level", result)

    def test_release_check_returns_structured_status(self) -> None:
        result = sdk.release_check()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("checks", result)

    def test_mcp_status_returns_supported_tools(self) -> None:
        result = sdk.mcp_status()
        self.assertIsInstance(result, dict)
        self.assertIn("mcp", result)
        self.assertIn("supported_tools", result["mcp"])
        self.assertIn("runewall.dry_run", result["mcp"]["supported_tools"])

    def test_dry_run_returns_dict(self) -> None:
        result = sdk.dry_run("github", "create_issue", {"repo": "user/repo", "title": "Bug"})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["site"], "github")
        self.assertEqual(result["flow"], "create_issue")

    def test_sdk_has_no_execute_function(self) -> None:
        self.assertFalse(hasattr(sdk, "execute"))


if __name__ == "__main__":
    unittest.main()
