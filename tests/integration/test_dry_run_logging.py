from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main
from runewall.core.log import ActionLog


class DryRunLoggingIntegrationTests(unittest.TestCase):
    def test_dry_run_without_init_works_but_does_not_log(self) -> None:
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
                        ]
                    )
                log = ActionLog.open_existing(root=Path.cwd())
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNone(log)
        self.assertIn("Runewall is not initialized; dry run was not logged.", output.getvalue())

    def test_dry_run_with_init_logs_map_dry_run_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
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


if __name__ == "__main__":
    unittest.main()
