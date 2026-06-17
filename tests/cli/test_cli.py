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
from runewall.core.log import ActionLog
from runewall.core.models import Action


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
            self.assertIn("Initialized Runewall at", output.getvalue())

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

    def test_maps_list_prints_github(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "list"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("site_name\tbase_url\tflows", rendered)
        self.assertIn("GitHub", rendered)
        self.assertIn("https://github.com", rendered)

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

    def test_maps_show_unknown_site_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "unknown"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Site map not found: unknown")

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
    def test_act_execute_missing_token_fails_clearly(self) -> None:
        output = io.StringIO()

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

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "GITHUB_TOKEN is required to execute github:create_issue.")

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_missing_token_logs_failed_if_initialized(self) -> None:
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
        self.assertEqual(action.result, {"error": "GITHUB_TOKEN is required to execute github:create_issue."})
        self.assertNotIn("GITHUB_TOKEN", str(action.params))

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
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(
                [
                    "act",
                    "github",
                    "delete_repository",
                    "--execute",
                    "--input",
                    "repo=user/repo",
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Flow not found for GitHub: delete_repository")

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


if __name__ == "__main__":
    unittest.main()
