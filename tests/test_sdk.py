from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runewall.sdk as sdk
from runewall.cli.main import main


class SdkTests(unittest.TestCase):
    def test_policy_test_returns_dict(self) -> None:
        result = sdk.policy_test("map.execute")
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertEqual(result["action_type"], "map.execute")

    def test_policy_test_empty_returns_missing_action_type(self) -> None:
        result = sdk.policy_test("")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "missing_action_type")

    def test_policy_audit_returns_dict(self) -> None:
        result = sdk.policy_audit()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("level", result)

    def test_release_check_returns_structured_status(self) -> None:
        result = sdk.release_check()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("checks", result)

    def test_mcp_status_returns_supported_tools(self) -> None:
        result = sdk.mcp_status()
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertIn("mcp", result)
        self.assertIn("supported_tools", result["mcp"])
        self.assertIn("runewall.dry_run", result["mcp"]["supported_tools"])

    def test_dry_run_returns_dict(self) -> None:
        result = sdk.dry_run("github", "create_issue", {"repo": "user/repo", "title": "Bug"})
        self.assertIsInstance(result, dict)
        self.assertTrue(result["ok"])
        self.assertEqual(result["site"], "github")
        self.assertEqual(result["flow"], "create_issue")
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["executed"])

    def test_dry_run_matches_cli_dry_run_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                sdk_result = sdk.dry_run("github", "create_issue", {"repo": "user/repo", "title": "Bug"})
                with redirect_stdout(output):
                    exit_code = main([
                        "act",
                        "github",
                        "create_issue",
                        "--dry-run",
                        "--json",
                        "--input",
                        "repo=user/repo",
                        "--input",
                        "title=Bug",
                    ])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertTrue(sdk_result["ok"])
        self.assertTrue(sdk_result["dry_run"])
        self.assertFalse(sdk_result["executed"])
        self.assertEqual(sdk_result["site"], "github")
        self.assertEqual(sdk_result["flow"], "create_issue")
        self.assertNotIn("result", sdk_result)

        import json as _json
        cli_result = _json.loads(output.getvalue())
        self.assertTrue(cli_result["ok"])
        self.assertFalse(cli_result["executed"])
        self.assertEqual(cli_result["site"], "github")
        self.assertEqual(cli_result["flow"], "create_issue")
        self.assertNotIn("result", cli_result)

        for key in ("site", "flow", "description", "risk_level", "reversible", "requires_auth", "api_path", "policy", "decision"):
            self.assertEqual(sdk_result[key], cli_result[key])

    def test_dry_run_missing_site_returns_error_code(self) -> None:
        result = sdk.dry_run("", "create_issue", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "missing_site")

    def test_dry_run_missing_flow_returns_error_code(self) -> None:
        result = sdk.dry_run("github", "", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "missing_flow")

    def test_dry_run_invalid_inputs_returns_error_code(self) -> None:
        result = sdk.dry_run("github", "create_issue", "bad")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "invalid_inputs")

    def test_dry_run_unknown_map_returns_structured_error(self) -> None:
        result = sdk.dry_run("unknown", "missing", {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "map_not_found")

    def test_sdk_has_no_execute_function(self) -> None:
        self.assertFalse(hasattr(sdk, "execute"))
        self.assertNotIn("execute", getattr(sdk, "__all__", []))


if __name__ == "__main__":
    unittest.main()
