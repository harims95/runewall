from __future__ import annotations

from contextlib import closing
import json
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

    def test_create_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log = ActionLog(root=root)

            saved = log.add_action(
                Action(
                    action_type="file.write",
                    target="notes.txt",
                    params={"content": "hello"},
                    status="approved",
                    result={"ok": True},
                )
            )

            self.assertTrue(database_path(root).exists())
            self.assertRegex(saved.id, r"^[0-9a-f\-]{36}$")
            self.assertTrue(saved.timestamp.endswith("Z"))

            with closing(sqlite3.connect(database_path(root))) as connection:
                row = connection.execute(
                    "SELECT params, result FROM actions WHERE id = ?",
                    (saved.id,),
                ).fetchone()

            self.assertEqual(json.loads(row[0]), {"content": "hello"})
            self.assertEqual(json.loads(row[1]), {"ok": True})

    def test_get_action_by_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = ActionLog(root=Path(temp_dir))
            saved = log.add_action(
                Action(
                    action_type="shell.exec",
                    target="echo hello",
                    params={"cwd": "."},
                )
            )

            loaded = log.get_action(saved.id)

            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.id, saved.id)
            self.assertEqual(loaded.params, {"cwd": "."})

    def test_list_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = ActionLog(root=Path(temp_dir))
            first = log.add_action(Action(action_type="file.read", target="a.txt"))
            second = log.add_action(Action(action_type="file.write", target="b.txt"))

            actions = log.list_actions()

            self.assertEqual([action.id for action in actions], [first.id, second.id])

    def test_update_action_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = ActionLog(root=Path(temp_dir))
            saved = log.add_action(Action(action_type="file.delete", target="old.txt"))

            updated = log.update_action_status(saved.id, "approved")
            loaded = log.get_action(saved.id)

            self.assertTrue(updated)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.status, "approved")

    def test_empty_log_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = ActionLog(root=Path(temp_dir))

            actions = log.list_actions()

            self.assertEqual(actions, [])


if __name__ == "__main__":
    unittest.main()
