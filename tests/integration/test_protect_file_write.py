from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall import protect_file_write
from runewall.core.log import ActionLog
from runewall.core.rollback import RollbackEngine


class ProtectFileWriteIntegrationTests(unittest.TestCase):
    def test_protected_file_write_can_be_rolled_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "demo.txt"
            target.write_text("before", encoding="utf-8")

            with protect_file_write("demo.txt", root=root):
                target.write_text("after", encoding="utf-8")

            action = ActionLog(root=root).get_last_action()
            self.assertIsNotNone(action)
            assert action is not None

            RollbackEngine(root=root).rollback(action.id)

            self.assertEqual(target.read_text(encoding="utf-8"), "before")


if __name__ == "__main__":
    unittest.main()
