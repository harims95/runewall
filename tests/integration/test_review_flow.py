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

from runewall import protect_file_delete
from runewall.core.interceptor import PendingReviewError
from runewall.core.log import ActionLog
from runewall.cli.main import main


class ReviewFlowIntegrationTests(unittest.TestCase):
    def test_review_action_can_be_approved_later(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "old.txt"
            target.write_text("before", encoding="utf-8")

            with self.assertRaises(PendingReviewError):
                with protect_file_delete("old.txt", root=root, require_review=True):
                    target.unlink()

            log = ActionLog(root=root)
            pending = log.list_pending_actions()
            self.assertEqual(len(pending), 1)

            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(root)
                with redirect_stdout(output):
                    exit_code = main(["approve", pending[0].id])
            finally:
                os.chdir(original_cwd)

            updated = log.get_action(pending[0].id)
            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "approved")


if __name__ == "__main__":
    unittest.main()
