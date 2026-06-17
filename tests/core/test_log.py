from __future__ import annotations

from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main
from runewall.core.db import database_path
from runewall.core.log import ActionLog
from runewall.core.models import Action


class ActionLogTests(unittest.TestCase):
    def test_init_creates_database_and_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            db_path = Path(temp_dir) / ".runewall" / "runewall.db"
            self.assertEqual(exit_code, 0)
            self.assertTrue(db_path.exists())

            with closing(sqlite3.connect(db_path)) as connection:
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

            self.assertTrue(
                {"actions", "snapshots", "rules", "checkpoints"}.issubset(table_names)
            )

    def test_can_save_and_list_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log = ActionLog(root=root)

            saved = log.add_action(
                Action(
                    action_type="file.write",
                    target="notes.txt",
                    params='{"content":"hello"}',
                    status="approved",
                )
            )

            actions = log.list_actions()

            self.assertTrue(database_path(root).exists())
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0].id, saved.id)
            self.assertEqual(actions[0].action_type, "file.write")
            self.assertEqual(actions[0].target, "notes.txt")
            self.assertEqual(actions[0].status, "approved")


if __name__ == "__main__":
    unittest.main()
