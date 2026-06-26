from __future__ import annotations

from contextlib import closing, redirect_stdout
import gc
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main

# Fake tokens — chosen to be recognisable if they ever appear in output.
# They are never real credentials.
_TOKEN_GHP = "ghp_TEST_TOKEN_SHOULD_NOT_LEAK_123456789"
_TOKEN_SK = "sk-TEST_TOKEN_SHOULD_NOT_LEAK_123456789"
_TOKEN_GENERIC = "RUNEWALL_TEST_SECRET_VALUE"


def _all_action_log_text(db_path: Path) -> str:
    """Return every non-null text cell from the actions table as one string.

    Uses contextlib.closing so the connection is explicitly closed on exit,
    which matters on Windows where an un-closed SQLite handle blocks deletion.
    """
    with closing(sqlite3.connect(str(db_path))) as conn:
        rows = conn.execute(
            "SELECT id, agent_id, action_type, target, params, result, reasoning FROM actions"
        ).fetchall()
    return " ".join(str(cell) for row in rows for cell in row if cell is not None)


class TestTokenSafety(unittest.TestCase):
    """Prove that env-var token values are never echoed to stdout or written to
    the action log.  All tests use fake, recognisable sentinel values so any
    accidental inclusion is immediately visible in the assertion message."""

    # ------------------------------------------------------------------
    # doctor
    # ------------------------------------------------------------------

    def test_doctor_does_not_leak_github_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP, "VERCEL_TOKEN": _TOKEN_SK}, clear=False):
            with redirect_stdout(output):
                main(["doctor", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        self.assertNotIn(_TOKEN_SK, rendered)
        # Sanity-check: doctor actually detected the tokens as present.
        data = json.loads(rendered)
        self.assertEqual(data["auth"]["github_token"], "present")
        self.assertEqual(data["auth"]["vercel_token"], "present")

    def test_doctor_does_not_leak_generic_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"NETLIFY_TOKEN": _TOKEN_GENERIC}, clear=False):
            with redirect_stdout(output):
                main(["doctor", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GENERIC, rendered)
        data = json.loads(rendered)
        self.assertEqual(data["auth"]["netlify_token"], "present")

    # ------------------------------------------------------------------
    # config show
    # ------------------------------------------------------------------

    def test_config_show_does_not_leak_github_token_to_stdout(self) -> None:
        """Config show must print the env-var NAME (expected), not its VALUE."""
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP}, clear=False):
            with redirect_stdout(output):
                main(["config", "show", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        # The env-var name "GITHUB_TOKEN" IS expected to appear in config output.
        self.assertIn("GITHUB_TOKEN", rendered)

    # ------------------------------------------------------------------
    # policy audit / policy test
    # ------------------------------------------------------------------

    def test_policy_audit_does_not_leak_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP, "VERCEL_TOKEN": _TOKEN_SK}, clear=False):
            with redirect_stdout(output):
                main(["policy", "audit", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        self.assertNotIn(_TOKEN_SK, rendered)

    def test_policy_test_does_not_leak_sk_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_SK}, clear=False):
            with redirect_stdout(output):
                main(["policy", "test", "file.write", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_SK, rendered)

    def test_policy_explain_does_not_leak_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP}, clear=False):
            with redirect_stdout(output):
                main(["policy", "explain", "map.execute", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)

    # ------------------------------------------------------------------
    # dry-run (stdout)
    # ------------------------------------------------------------------

    def test_dry_run_does_not_leak_env_token_to_stdout(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP, "VERCEL_TOKEN": _TOKEN_SK}, clear=False):
            with redirect_stdout(output):
                main([
                    "act", "github", "create_issue",
                    "--dry-run", "--json",
                    "--input", "repo=user/repo",
                    "--input", "title=Bug report",
                ])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        self.assertNotIn(_TOKEN_SK, rendered)
        # Sanity-check: we actually received a dry-run result.
        data = json.loads(rendered)
        self.assertFalse(data["executed"])

    def test_dry_run_human_output_does_not_leak_env_token(self) -> None:
        """Non-JSON (human-readable) dry-run must also not echo env tokens."""
        output = io.StringIO()
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP}, clear=False):
            with redirect_stdout(output):
                main([
                    "act", "github", "create_issue",
                    "--dry-run",
                    "--input", "repo=user/repo",
                    "--input", "title=Bug report",
                ])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)

    # ------------------------------------------------------------------
    # dry-run (action log / SQLite)
    # ------------------------------------------------------------------

    def test_dry_run_does_not_write_env_token_to_action_log(self) -> None:
        """After a dry-run, the SQLite action log must not contain any token value."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            sink = io.StringIO()
            try:
                os.chdir(temp_dir)
                with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP, "VERCEL_TOKEN": _TOKEN_SK}, clear=False):
                    with redirect_stdout(sink):
                        main(["init"])
                    with redirect_stdout(sink):
                        main([
                            "act", "github", "create_issue",
                            "--dry-run", "--json",
                            "--input", "repo=user/repo",
                            "--input", "title=Bug report",
                        ])
            finally:
                os.chdir(original_cwd)

            db_path = Path(temp_dir) / ".runewall" / "runewall.db"
            self.assertTrue(db_path.exists(), "action log DB must exist after init + dry-run")
            log_text = _all_action_log_text(db_path)
            # Force GC so Windows releases any remaining SQLite file handles
            # before TemporaryDirectory.__exit__ tries to delete the directory.
            gc.collect()
            self.assertNotIn(_TOKEN_GHP, log_text)
            self.assertNotIn(_TOKEN_SK, log_text)

    # ------------------------------------------------------------------
    # MCP initialize
    # ------------------------------------------------------------------

    def test_mcp_initialize_does_not_leak_env_token(self) -> None:
        """MCP initialize response includes serverInfo but must not echo env tokens."""
        output = io.StringIO()
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        with patch.dict(os.environ, {"GITHUB_TOKEN": _TOKEN_GHP}, clear=False):
            with patch("sys.stdin", io.StringIO(request)):
                with redirect_stdout(output):
                    main(["mcp", "serve", "--once"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        data = json.loads(rendered)
        self.assertEqual(data["result"]["serverInfo"]["name"], "runewall")

    # ------------------------------------------------------------------
    # release check
    # ------------------------------------------------------------------

    def test_release_check_does_not_leak_env_tokens(self) -> None:
        output = io.StringIO()
        with patch.dict(
            os.environ,
            {
                "GITHUB_TOKEN": _TOKEN_GHP,
                "VERCEL_TOKEN": _TOKEN_SK,
                "NETLIFY_TOKEN": _TOKEN_GENERIC,
            },
            clear=False,
        ):
            with redirect_stdout(output):
                main(["release", "check", "--json"])
        rendered = output.getvalue()
        self.assertNotIn(_TOKEN_GHP, rendered)
        self.assertNotIn(_TOKEN_SK, rendered)
        self.assertNotIn(_TOKEN_GENERIC, rendered)
