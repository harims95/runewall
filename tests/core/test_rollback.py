from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.core.rollback import RollbackEngine
from runewall.core.snapshot import SnapshotEngine


class RollbackEngineTests(unittest.TestCase):
    def test_rollback_missing_snapshot_gives_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            action = Action(action_type="file.write", target="notes.txt", status="approved")
            log = ActionLog(root=root)
            log.add_action(action)

            with self.assertRaisesRegex(ValueError, "Missing snapshot for action"):
                RollbackEngine(root=root).rollback(action.id)

    def test_rollback_updates_action_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "notes.txt"
            target.write_text("before", encoding="utf-8")
            action = Action(action_type="file.write", target="notes.txt", status="approved")
            log = ActionLog(root=root)
            log.add_action(action)
            snapshot = SnapshotEngine(root=root).create_snapshot(action)
            log.add_snapshot(snapshot)
            target.write_text("after", encoding="utf-8")

            RollbackEngine(root=root).rollback(action.id)
            updated = log.get_action(action.id)

            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "rolled_back")


if __name__ == "__main__":
    unittest.main()
