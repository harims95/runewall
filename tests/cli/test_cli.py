from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import EMPTY_LOG_MESSAGE, main
from runewall.core.config import config_path
from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.maps import SiteMapRegistry


class CliTests(unittest.TestCase):
    def test_init_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "runewall.db").exists())
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())
            self.assertIn("Initialized Runewall at", output.getvalue())

    def test_config_path_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "path"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue().strip()
        self.assertEqual(exit_code, 0)
        self.assertEqual(rendered, str(config_path(Path(temp_dir)).resolve()))

    def test_config_show_does_not_print_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                "\n".join(
                    [
                        "[safety]",
                        'default_policy = "review"',
                        "",
                        "[auth]",
                        'github_token_env = "GITHUB_TOKEN"',
                        'github_token = "super-secret-token"',
                    ]
                ),
                encoding="utf-8",
            )
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "show"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("[auth]", rendered)
        self.assertIn('github_token_env = "GITHUB_TOKEN"', rendered)
        self.assertIn('github_token = "***REDACTED***"', rendered)
        self.assertNotIn("super-secret-token", rendered)

    def test_log_command_with_empty_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["log"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), EMPTY_LOG_MESSAGE)

    def test_maps_list_prints_github_vercel_netlify_and_cloudflare(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "list"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("site_name\tbase_url\tflows", rendered)
        self.assertIn("GitHub", rendered)
        self.assertIn("https://github.com", rendered)
        self.assertIn("Vercel", rendered)
        self.assertIn("https://vercel.com", rendered)
        self.assertIn("Netlify", rendered)
        self.assertIn("https://app.netlify.com", rendered)
        self.assertIn("Cloudflare", rendered)
        self.assertIn("https://dash.cloudflare.com", rendered)

    def test_maps_path_prints_absolute_bundled_maps_path(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "path"])

        rendered = output.getvalue().strip()
        normalized = rendered.replace("\\", "/")
        self.assertEqual(exit_code, 0)
        self.assertTrue(Path(rendered).is_absolute())
        self.assertIn("maps/sites", normalized)

    def test_maps_show_github_prints_create_issue(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Base URL: https://github.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- create_issue", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: True", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: repo, title", rendered)

    def test_maps_show_vercel_prints_list_projects(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "vercel"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Vercel", rendered)
        self.assertIn("Base URL: https://vercel.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_projects", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_show_netlify_prints_list_sites(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "netlify"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Netlify", rendered)
        self.assertIn("Base URL: https://app.netlify.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_sites", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_show_cloudflare_prints_list_zones(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "cloudflare"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Cloudflare", rendered)
        self.assertIn("Base URL: https://dash.cloudflare.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_zones", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_show_unknown_site_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "unknown"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Site map not found: unknown")

    @patch.object(SiteMapRegistry, "bundled_maps_path")
    def test_maps_path_missing_directory_fails_clearly(self, mocked_path) -> None:
        mocked_path.return_value = Path("missing-maps-dir")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "path"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Bundled maps directory not found: missing-maps-dir")

    def test_maps_validate_prints_ok_for_github_vercel_netlify_and_cloudflare(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("github (GitHub)\tOK", rendered)
        self.assertIn("vercel (Vercel)\tOK", rendered)
        self.assertIn("netlify (Netlify)\tOK", rendered)
        self.assertIn("cloudflare (Cloudflare)\tOK", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_prints_dependency_checks(self, mocked_find_spec) -> None:
        def fake_find_spec(name: str) -> object | None:
            if name in {"httpx", "bs4"}:
                return object()
            return None

        mocked_find_spec.side_effect = fake_find_spec
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Dependency httpx: OK", rendered)
        self.assertIn("Dependency bs4: OK", rendered)
        self.assertIn("Bundled maps:", rendered)
        self.assertIn("Summary: WARN", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "super-secret-token"}, clear=True)
    def test_doctor_does_not_print_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["doctor"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("GITHUB_TOKEN: set", rendered)
        self.assertNotIn("super-secret-token", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_handles_missing_runewall_cleanly(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Runewall DB: missing", rendered)
        self.assertIn("Summary: WARN", rendered)

    def test_doctor_shows_config_present_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Config: present", rendered)

    def test_doctor_shows_config_missing_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Config: missing", rendered)

    def test_doctor_shows_map_execution_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: disabled", rendered)

    def test_doctor_shows_map_execution_enabled_when_config_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: ENABLED", rendered)

    def test_doctor_summary_is_warn_when_map_execution_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: ENABLED", rendered)
            self.assertIn("Summary: WARN", rendered)

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_github_create_issue(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                            "--input",
                            "body=Details",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: True", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("- repo=user/repo", rendered)
        self.assertIn("- title=Bug report", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_vercel_list_projects(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "vercel", "list_projects", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Vercel", rendered)
        self.assertIn("Flow name: list_projects", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /v9/projects", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_netlify_list_sites(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "netlify", "list_sites", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Netlify", rendered)
        self.assertIn("Flow name: list_sites", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /api/v1/sites", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_cloudflare_list_zones(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "cloudflare", "list_zones", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Cloudflare", rendered)
        self.assertIn("Flow name: list_zones", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /client/v4/zones", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_missing_required_input_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(
                [
                    "act",
                    "github",
                    "create_issue",
                    "--dry-run",
                    "--input",
                    "repo=user/repo",
                ]
            )

        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("Missing inputs: title", rendered)
        self.assertIn("Missing required inputs: title", rendered)

    def test_act_dry_run_with_init_logs_map_dry_run_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.target, "github:create_issue")
        self.assertEqual(action.status, "success")
        self.assertEqual(
            action.params,
            {"site": "github", "flow": "create_issue", "inputs": {"repo": "user/repo", "title": "Bug report"}},
        )
        self.assertEqual(
            action.result,
            {"risk_level": "low", "reversible": True, "requires_auth": True, "executed": False},
        )
        self.assertNotIn("Runewall is not initialized; dry run was not logged.", output.getvalue())

    def test_act_execute_is_blocked_by_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "failed")
        self.assertEqual(
            action.result,
            {"error": "Map execution is disabled by config. Set [maps] allow_execute = true to enable."},
        )
        self.assertEqual(
            output.getvalue().strip(),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    def test_act_dry_run_failed_logs_failed_if_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.status, "failed")
        self.assertEqual(
            action.result,
            {"error": "Missing required inputs: title"},
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_is_blocked_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            output.getvalue().strip(),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    def test_act_dry_run_unknown_site_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["act", "unknown", "create_issue", "--dry-run"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Site map not found: unknown")

    def test_act_dry_run_unknown_flow_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["act", "github", "unknown_flow", "--dry-run"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Flow not found for GitHub: unknown_flow")

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_allowed_reaches_existing_token_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                config_file = Path.cwd() / ".runewall" / "config.toml"
                config_file.write_text(
                    config_file.read_text(encoding="utf-8").replace("allow_execute = false", "allow_execute = true"),
                    encoding="utf-8",
                )
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "failed")
        self.assertEqual(action.result, {"error": "GITHUB_TOKEN is required to execute github:create_issue."})
        self.assertNotIn("GITHUB_TOKEN", str(action.params))
        self.assertEqual(output.getvalue().strip(), "GITHUB_TOKEN is required to execute github:create_issue.")

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_success_logs_map_execute_without_token(self, mocked_execute) -> None:
        mocked_execute.return_value = {
            "issue_url": "https://github.com/user/repo/issues/1",
            "issue_number": 1,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                config_file = Path.cwd() / ".runewall" / "config.toml"
                config_file.write_text(
                    config_file.read_text(encoding="utf-8").replace("allow_execute = false", "allow_execute = true"),
                    encoding="utf-8",
                )
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                            "--input",
                            "body=Details",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "success")
        self.assertEqual(
            action.result,
            {"issue_url": "https://github.com/user/repo/issues/1", "issue_number": 1},
        )
        self.assertNotIn("secret-token", str(action.params))
        self.assertNotIn("secret-token", str(action.result))
        self.assertIn("Created GitHub issue for user/repo.", output.getvalue())

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    def test_act_execute_unsupported_site_flow_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "vercel",
                            "list_projects",
                            "--execute",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Execution is not supported for vercel:list_projects.")

    def test_status_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output.getvalue().strip(),
                "Runewall is not initialized. Run `runewall init` first.",
            )

    def test_pending_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output.getvalue().strip(),
                "Runewall is not initialized. Run `runewall init` first.",
            )

    def test_pending_after_init_with_no_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "No pending actions.")

    def test_pending_shows_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                log.add_action(Action(action_type="file.write", target="done.txt", status="success"))
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("id\ttimestamp\taction_type\ttarget\tstatus", rendered)
            self.assertIn("file.delete", rendered)
            self.assertIn("old.txt", rendered)
            self.assertIn("pending", rendered)
            self.assertNotIn("done.txt", rendered)

    def test_status_after_init_with_no_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Database:", rendered)
            self.assertIn("Total actions: 0", rendered)
            self.assertIn("Success actions: 0", rendered)
            self.assertIn("Failed actions: 0", rendered)
            self.assertIn("Rolled back actions: 0", rendered)
            self.assertIn("Latest action: none", rendered)

    def test_status_after_at_least_one_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(
                    Action(
                        action_type="file.write",
                        target="demo.txt",
                        status="success",
                    )
                )
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Total actions: 1", rendered)
            self.assertIn("Success actions: 1", rendered)
            self.assertIn("Failed actions: 0", rendered)
            self.assertIn("Rolled back actions: 0", rendered)
            self.assertIn("Latest action:", rendered)
            self.assertIn("file.write", rendered)
            self.assertIn("demo.txt", rendered)

    def test_approve_changes_pending_to_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt"))
                with redirect_stdout(output):
                    exit_code = main(["approve", action.id])
                updated = log.get_action(action.id)
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "approved")
            self.assertIn(f"Approved action {action.id}.", output.getvalue())

    def test_reject_changes_pending_to_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt"))
                with redirect_stdout(output):
                    exit_code = main(["reject", action.id])
                updated = log.get_action(action.id)
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "rejected")
            self.assertIn(f"Rejected action {action.id}.", output.getvalue())

    def test_approving_non_existent_action_gives_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["approve", "missing-id"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), "Action not found: missing-id")

    def test_rejecting_non_existent_action_gives_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["reject", "missing-id"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), "Action not found: missing-id")

    def test_execute_non_approved_action_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                with redirect_stdout(output):
                    exit_code = main(["execute", action.id])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), f"Action {action.id} is not approved.")

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Main Heading", "Section Heading"],
            "text": "Hello world from Runewall. " * 20,
        },
    )
    def test_read_command_prints_structured_preview(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIn("Title: Example Page", rendered)
            self.assertIn("Headings:", rendered)
            self.assertIn("- Main Heading", rendered)
            self.assertIn("- Section Heading", rendered)
            self.assertIn("Text preview:", rendered)
            self.assertIn("Hello world from Runewall.", rendered)
            self.assertIn("Runewall is not initialized; read action was not logged.", rendered)

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Main Heading"],
            "text": "Hello world from Runewall.",
        },
    )
    def test_read_with_init_logs_web_read_success(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "web.read")
            self.assertEqual(action.target, "https://example.com")
            self.assertEqual(action.status, "success")
            self.assertEqual(action.params, {"mode": "universal_read"})
            self.assertEqual(action.result, {"title": "Example Page", "heading_count": 1, "text_length": 26})
            self.assertNotIn("Runewall is not initialized; read action was not logged.", output.getvalue())

    def test_config_set_maps_allow_execute_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "Updated config: maps.allow_execute = true")
            from runewall.core.config import load_config
            self.assertTrue(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_set_safety_max_snapshot_mb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "100"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "Updated config: safety.max_snapshot_mb = 100")
            from runewall.core.config import load_config
            self.assertEqual(load_config(Path(temp_dir)).safety.max_snapshot_mb, 100)

    def test_config_set_creates_config_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())
            from runewall.core.config import load_config
            self.assertTrue(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_set_unknown_key_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.unknown_key", "true"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Unknown config key: maps.unknown_key", output.getvalue())

    def test_config_set_invalid_boolean_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "yes"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid boolean for maps.allow_execute", output.getvalue())
        self.assertIn("Use true or false", output.getvalue())

    def test_config_set_invalid_integer_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "abc"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid integer for safety.max_snapshot_mb", output.getvalue())

    @patch("runewall.cli.main.read_url", side_effect=RuntimeError("network down"))
    def test_failed_read_logs_failed_if_db_exists(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "web.read")
            self.assertEqual(action.status, "failed")
            self.assertEqual(action.result, {"error": "network down"})
            self.assertEqual(output.getvalue().strip(), "Read failed: network down")


    def test_cleanup_snapshots_with_no_snapshots_dir_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "No snapshots directory found.")

    def test_cleanup_snapshots_reports_deleted_count(self) -> None:
        import os as _os
        import time as _time

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                snapshots_dir = Path.cwd() / ".runewall" / "snapshots"
                snapshots_dir.mkdir(parents=True, exist_ok=True)
                old_snap = snapshots_dir / "old_snap"
                old_snap.mkdir()
                old_time = _time.time() - 31 * 86400
                _os.utime(old_snap, (old_time, old_time))
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIn("Deleted 1 old snapshot(s).", output.getvalue())


    def test_status_json_before_init_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["status", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertFalse(data["initialized"])
            self.assertIn("database_path", data)

    def test_status_json_after_init_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["status", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertIn("total_actions", data)
            self.assertIn("success_count", data)
            self.assertIn("failed_count", data)
            self.assertIn("rolled_back_count", data)
            self.assertIn("pending_count", data)
            self.assertIn("latest_action", data)

    def test_log_json_empty_db_prints_empty_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["log", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertEqual(data, [])

    def test_log_json_after_action_includes_action_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(
                    action_type="file.write",
                    target="demo.txt",
                    status="success",
                    params={"mode": "overwrite"},
                    result={"bytes": 42},
                ))
                with redirect_stdout(output):
                    exit_code = main(["log", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertEqual(len(data), 1)
            entry = data[0]
            self.assertEqual(entry["action_type"], "file.write")
            self.assertEqual(entry["target"], "demo.txt")
            self.assertEqual(entry["status"], "success")
            self.assertEqual(entry["params"], {"mode": "overwrite"})
            self.assertEqual(entry["result"], {"bytes": 42})
            self.assertIn("id", entry)
            self.assertIn("timestamp", entry)

    def test_normal_status_and_log_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code_status = main(["status"])
                status_out = output.getvalue()
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code_log = main(["log"])
                log_out = output.getvalue()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code_status, 0)
            self.assertIn("Database:", status_out)
            self.assertIn("Total actions:", status_out)
            self.assertEqual(exit_code_log, 0)
            self.assertIn(EMPTY_LOG_MESSAGE, log_out)


    def test_pending_json_before_init_prints_initialized_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertFalse(data["initialized"])
            self.assertEqual(data["pending"], [])

    def test_pending_json_after_init_with_no_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertEqual(data["pending"], [])

    def test_pending_json_with_pending_action_includes_action_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(
                    action_type="file.delete",
                    target="old.txt",
                    status="pending",
                    params={"reason": "cleanup"},
                    result=None,
                ))
                log.add_action(Action(
                    action_type="file.write",
                    target="done.txt",
                    status="success",
                ))
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertEqual(len(data["pending"]), 1)
            entry = data["pending"][0]
            self.assertEqual(entry["action_type"], "file.delete")
            self.assertEqual(entry["target"], "old.txt")
            self.assertEqual(entry["status"], "pending")
            self.assertEqual(entry["params"], {"reason": "cleanup"})
            self.assertIn("id", entry)
            self.assertIn("timestamp", entry)

    def test_normal_pending_human_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIn("No pending actions.", output.getvalue())


    def test_act_dry_run_json_success_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run", "--json",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
                "--input", "body=Details",
            ])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertEqual(data["risk_level"], "low")
        self.assertTrue(data["reversible"])
        self.assertTrue(data["requires_auth"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertIn("provided_inputs", data)
        self.assertIn("ui_steps_count", data)

    def test_act_dry_run_json_missing_input_prints_json_error_and_exits_nonzero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run", "--json",
                "--input", "repo=user/repo",
            ])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertIn("Missing required inputs", data["error"])

    def test_act_dry_run_json_with_init_logs_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--dry-run", "--json",
                        "--input", "repo=user/repo",
                        "--input", "title=Bug",
                    ])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.status, "success")
        import json as _json
        _json.loads(output.getvalue())

    def test_act_json_without_dry_run_fails_clearly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--execute", "--json",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
            ])
        self.assertEqual(exit_code, 1)
        self.assertIn("--json requires --dry-run", output.getvalue())

    def test_act_dry_run_human_output_unchanged_after_json_added(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
            ])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Missing inputs: none", rendered)

    def test_maps_list_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("maps", data)
        self.assertIsInstance(data["maps"], list)

    def test_maps_list_json_includes_all_bundled_sites(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "list", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        keys = {entry["key"] for entry in data["maps"]}
        self.assertIn("github", keys)
        self.assertIn("vercel", keys)
        self.assertIn("netlify", keys)
        self.assertIn("cloudflare", keys)
        for entry in data["maps"]:
            self.assertIn("site_name", entry)
            self.assertIn("base_url", entry)
            self.assertIn("flow_count", entry)
            self.assertIn("flows", entry)

    def test_maps_show_json_github_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["key"], "github")
        self.assertEqual(data["site_name"], "GitHub")
        self.assertIn("base_url", data)
        self.assertIn("map_version", data)
        self.assertIn("schema_version", data)
        self.assertIn("flows", data)

    def test_maps_show_json_github_includes_create_issue(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "show", "github", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        flow_names = [f["name"] for f in data["flows"]]
        self.assertIn("create_issue", flow_names)
        flow = next(f for f in data["flows"] if f["name"] == "create_issue")
        self.assertEqual(flow["risk_level"], "low")
        self.assertTrue(flow["reversible"])
        self.assertTrue(flow["requires_auth"])
        self.assertIn("repo", flow["required_inputs"])
        self.assertIn("title", flow["required_inputs"])

    def test_maps_validate_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("ok", data)
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_maps_validate_json_returns_ok_true_for_bundled_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        for result in data["results"]:
            self.assertTrue(result["ok"])
            self.assertIsNone(result["error"])
            self.assertIn("key", result)
            self.assertIn("site_name", result)

    def test_maps_normal_human_output_unchanged_after_json_added(self) -> None:
        list_output = io.StringIO()
        with redirect_stdout(list_output):
            exit_code_list = main(["maps", "list"])
        self.assertEqual(exit_code_list, 0)
        self.assertIn("site_name\tbase_url\tflows", list_output.getvalue())
        self.assertIn("GitHub", list_output.getvalue())

        show_output = io.StringIO()
        with redirect_stdout(show_output):
            exit_code_show = main(["maps", "show", "github"])
        self.assertEqual(exit_code_show, 0)
        self.assertIn("Site name: GitHub", show_output.getvalue())

        validate_output = io.StringIO()
        with redirect_stdout(validate_output):
            exit_code_validate = main(["maps", "validate"])
        self.assertEqual(exit_code_validate, 0)
        self.assertIn("github (GitHub)\tOK", validate_output.getvalue())


if __name__ == "__main__":
    unittest.main()
