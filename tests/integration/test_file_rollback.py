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
from runewall.core.models import Action
from runewall.core.rollback import RollbackEngine
from runewall.core.snapshot import SnapshotEngine


class FileRollbackIntegrationTests(unittest.TestCase):
    def test_rollback_file_write_restores_old_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "notes.txt"
            target.write_text("before", encoding="utf-8")

            action = Action(action_type="file.write", target="notes.txt", status="approved")
            log = ActionLog(root=root)
            log.add_action(action)
            log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))

            target.write_text("after", encoding="utf-8")
            RollbackEngine(root=root).rollback(action.id)

            self.assertEqual(target.read_text(encoding="utf-8"), "before")

    def test_rollback_file_delete_restores_deleted_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "trash.txt"
            target.write_text("restore me", encoding="utf-8")

            action = Action(action_type="file.delete", target="trash.txt", status="approved")
            log = ActionLog(root=root)
            log.add_action(action)
            log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))

            target.unlink()
            RollbackEngine(root=root).rollback(action.id)

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "restore me")

    def test_rollback_file_create_deletes_created_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "created.txt"

            action = Action(action_type="file.create", target="created.txt", status="approved")
            log = ActionLog(root=root)
            log.add_action(action)
            log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))

            target.write_text("new", encoding="utf-8")
            RollbackEngine(root=root).rollback(action.id)

            self.assertFalse(target.exists())

    def test_cli_rollback_last_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "last.txt"
            target.write_text("before", encoding="utf-8")
            log = ActionLog(root=root)
            action = Action(action_type="file.write", target="last.txt", status="approved")
            log.add_action(action)
            log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))
            target.write_text("after", encoding="utf-8")

            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(root)
                with redirect_stdout(output):
                    exit_code = main(["rollback", "--last"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "before")
            self.assertIn("Rolled back last action.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
