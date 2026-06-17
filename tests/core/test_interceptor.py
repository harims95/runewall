from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall import protect_file_create, protect_file_delete, protect_file_write
from runewall.core.log import ActionLog


class ProtectFileWriteTests(unittest.TestCase):
    def test_protected_file_write_snapshots_old_content_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "demo.txt"
            target.write_text("before", encoding="utf-8")

            with protect_file_write("demo.txt", root=root):
                target.write_text("after", encoding="utf-8")

            log = ActionLog(root=root)
            action = log.get_last_action()

            self.assertIsNotNone(action)
            assert action is not None
            snapshot = log.get_latest_snapshot_for_action(action.id)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            copied = Path(snapshot.storage_path) / "files" / "demo.txt"
            self.assertEqual(copied.read_text(encoding="utf-8"), "before")

    def test_protected_file_write_logs_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "demo.txt"
            target.write_text("before", encoding="utf-8")

            with protect_file_write("demo.txt", root=root):
                target.write_text("after", encoding="utf-8")

            action = ActionLog(root=root).get_last_action()

            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "file.write")
            self.assertEqual(action.target, "demo.txt")
            self.assertEqual(action.status, "success")
            self.assertEqual(action.rule_applied, "SNAPSHOT")

    def test_failure_inside_context_marks_action_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "demo.txt"
            target.write_text("before", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "boom"):
                with protect_file_write("demo.txt", root=root):
                    raise RuntimeError("boom")

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.status, "failed")

    def test_protected_file_create_logs_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "new.txt"

            with protect_file_create("new.txt", root=root):
                target.write_text("new content", encoding="utf-8")

            action = ActionLog(root=root).get_last_action()

            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "file.create")
            self.assertEqual(action.target, "new.txt")
            self.assertEqual(action.status, "success")
            self.assertEqual(action.rule_applied, "SNAPSHOT")

    def test_protected_file_delete_snapshots_old_content_before_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "old.txt"
            target.write_text("before delete", encoding="utf-8")

            with protect_file_delete("old.txt", root=root):
                target.unlink()

            log = ActionLog(root=root)
            action = log.get_last_action()

            self.assertIsNotNone(action)
            assert action is not None
            snapshot = log.get_latest_snapshot_for_action(action.id)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            copied = Path(snapshot.storage_path) / "files" / "old.txt"
            self.assertEqual(copied.read_text(encoding="utf-8"), "before delete")

    def test_failure_inside_create_context_marks_action_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            with self.assertRaisesRegex(RuntimeError, "boom"):
                with protect_file_create("new.txt", root=root):
                    raise RuntimeError("boom")

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.status, "failed")

    def test_failure_inside_delete_context_marks_action_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "old.txt"
            target.write_text("before", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "boom"):
                with protect_file_delete("old.txt", root=root):
                    raise RuntimeError("boom")

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.status, "failed")


if __name__ == "__main__":
    unittest.main()
