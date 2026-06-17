from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall import protect_file_create, protect_file_delete
from runewall.core.log import ActionLog
from runewall.core.rollback import RollbackEngine


class ProtectFileCreateDeleteIntegrationTests(unittest.TestCase):
    def test_protected_file_create_can_be_rolled_back_and_deletes_created_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "new.txt"

            with protect_file_create("new.txt", root=root):
                target.write_text("new content", encoding="utf-8")

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None

            RollbackEngine(root=root).rollback(action.id)

            self.assertFalse(target.exists())

    def test_protected_file_delete_can_be_rolled_back_and_restores_deleted_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "old.txt"
            target.write_text("restore me", encoding="utf-8")

            with protect_file_delete("old.txt", root=root):
                target.unlink()

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None

            RollbackEngine(root=root).rollback(action.id)

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "restore me")


if __name__ == "__main__":
    unittest.main()
