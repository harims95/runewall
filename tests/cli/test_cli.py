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


if __name__ == "__main__":
    unittest.main()
