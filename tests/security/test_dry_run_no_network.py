from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main

# Sentinel: if either httpx helper is called during a dry-run the test fails.
_NETWORK_SENTINEL = MagicMock(side_effect=AssertionError("dry-run must not make network calls"))


def _no_network():
    """Context manager that blocks all httpx calls in the executor."""
    return (
        patch("runewall.maps.executor._httpx_get", new_callable=lambda: lambda *a, **kw: MagicMock(side_effect=AssertionError("httpx.get called during dry-run"))),
        patch("runewall.maps.executor._httpx_post", new_callable=lambda: lambda *a, **kw: MagicMock(side_effect=AssertionError("httpx.post called during dry-run"))),
    )


class TestDryRunNoNetwork(unittest.TestCase):
    """Prove that dry-run commands never trigger external network calls.

    Each test patches the two httpx helpers in executor.py so that any
    accidental call immediately raises AssertionError.  The patches also
    expose Mock objects so we can assertNotCalled() for extra clarity.
    """

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _capture_dry_run(*args: str) -> tuple[int, str]:
        """Run main() and return (exit_code, stdout)."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(list(args))
        return code, out.getvalue()

    # ------------------------------------------------------------------
    # dry-run: github create_issue
    # ------------------------------------------------------------------

    def test_github_dry_run_json_does_not_call_network(self) -> None:
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called during dry-run"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called during dry-run"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "github", "create_issue",
                    "--dry-run", "--json",
                    "--input", "repo=user/repo",
                    "--input", "title=Test issue",
                )
        self.assertEqual(code, 0)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")

    def test_github_dry_run_human_does_not_call_network(self) -> None:
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called during dry-run"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called during dry-run"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "github", "create_issue",
                    "--dry-run",
                    "--input", "repo=user/repo",
                    "--input", "title=Test issue",
                )
        self.assertEqual(code, 0)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        self.assertIn("dry_run", rendered.lower().replace("-", "_").replace(" ", "_"))

    # ------------------------------------------------------------------
    # dry-run: vercel list_projects
    # ------------------------------------------------------------------

    def test_vercel_dry_run_json_does_not_call_network(self) -> None:
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called during dry-run"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called during dry-run"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "vercel", "list_projects",
                    "--dry-run", "--json",
                )
        self.assertEqual(code, 0)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "vercel")

    # ------------------------------------------------------------------
    # dry-run: netlify list_sites
    # ------------------------------------------------------------------

    def test_netlify_dry_run_json_does_not_call_network(self) -> None:
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called during dry-run"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called during dry-run"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "netlify", "list_sites",
                    "--dry-run", "--json",
                )
        self.assertEqual(code, 0)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertFalse(data["executed"])

    # ------------------------------------------------------------------
    # MCP dry_run tool call
    # ------------------------------------------------------------------

    def test_mcp_dry_run_tool_does_not_call_network(self) -> None:
        mcp_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "runewall.dry_run",
                "arguments": {
                    "site": "github",
                    "flow": "create_issue",
                    "inputs": {"repo": "user/repo", "title": "Test issue"},
                },
            },
        })
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called during MCP dry_run"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called during MCP dry_run"))
        out = io.StringIO()
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                with patch("sys.stdin", io.StringIO(mcp_request)):
                    with redirect_stdout(out):
                        code = main(["mcp", "serve", "--once"])
        self.assertEqual(code, 0)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        response = json.loads(out.getvalue())
        self.assertNotIn("error", response)
        tool_result = json.loads(response["result"]["content"][0]["text"])
        self.assertFalse(tool_result["executed"])
        self.assertTrue(tool_result["dry_run"])

    # ------------------------------------------------------------------
    # execution gate: --execute blocked by default config
    # ------------------------------------------------------------------

    def test_execute_blocked_by_default_config_and_does_not_call_network(self) -> None:
        """--execute must fail with EXECUTION_DISABLED when maps.allow_execute=false (default)."""
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called when execution is disabled"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called when execution is disabled"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "github", "create_issue",
                    "--execute", "--json",
                    "--input", "repo=user/repo",
                    "--input", "title=Test issue",
                )
        self.assertEqual(code, 1)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["error_code"], "EXECUTION_DISABLED")

    def test_execute_vercel_blocked_by_default_config(self) -> None:
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called when execution is disabled"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called when execution is disabled"))
        with patch("runewall.maps.executor._httpx_get", mock_get):
            with patch("runewall.maps.executor._httpx_post", mock_post):
                code, rendered = self._capture_dry_run(
                    "act", "vercel", "list_projects",
                    "--execute", "--json",
                )
        self.assertEqual(code, 1)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertEqual(data["error_code"], "EXECUTION_DISABLED")

    # ------------------------------------------------------------------
    # execute with allow_execute=true requires token (no token → blocked before network)
    # ------------------------------------------------------------------

    def test_execute_with_allow_execute_true_but_no_token_does_not_call_network(self) -> None:
        """Even with allow_execute=true, missing token must block before any network call."""
        mock_get = MagicMock(side_effect=AssertionError("httpx.get must not be called without a token"))
        mock_post = MagicMock(side_effect=AssertionError("httpx.post must not be called without a token"))
        # Patch allow_execute to True but provide no GITHUB_TOKEN
        from runewall.core.config import MapsConfig, RunewallConfig
        safe_config_no_token = RunewallConfig(maps=MapsConfig(allow_execute=True))
        with patch("runewall.maps.executor.load_config", return_value=safe_config_no_token):
            with patch("runewall.maps.executor._httpx_get", mock_get):
                with patch("runewall.maps.executor._httpx_post", mock_post):
                    with patch("os.environ.get", return_value=None):
                        code, rendered = self._capture_dry_run(
                            "act", "github", "create_issue",
                            "--execute", "--json",
                            "--input", "repo=user/repo",
                            "--input", "title=Test issue",
                        )
        self.assertEqual(code, 1)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        data = json.loads(rendered)
        self.assertFalse(data["executed"])
        self.assertEqual(data["error_code"], "MISSING_TOKEN")
