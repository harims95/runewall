from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.core.snapshot import SnapshotEngine, cleanup_snapshots


class SnapshotEngineTests(unittest.TestCase):
    def test_default_limit_remains_500mb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = SnapshotEngine(root=Path(temp_dir))

            self.assertEqual(engine._max_file_size_bytes, 500 * 1024 * 1024)

    def test_config_value_overrides_default_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".runewall"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "config.toml").write_text(
                "[safety]\nmax_snapshot_mb = 1\n",
                encoding="utf-8",
            )

            engine = SnapshotEngine(root=root)

            self.assertEqual(engine._max_file_size_bytes, 1 * 1024 * 1024)

    def test_explicit_max_snapshot_mb_overrides_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".runewall"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "config.toml").write_text(
                "[safety]\nmax_snapshot_mb = 1\n",
                encoding="utf-8",
            )

            engine = SnapshotEngine(root=root, max_snapshot_mb=2)

            self.assertEqual(engine._max_file_size_bytes, 2 * 1024 * 1024)

    def test_file_write_snapshots_old_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "docs" / "notes.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("before write", encoding="utf-8")

            action = Action(action_type="file.write", target="docs/notes.txt")
            snapshot = SnapshotEngine(root=root).create_snapshot(action)
            ActionLog(root=root).add_snapshot(snapshot)

            copied = root / ".runewall" / "snapshots" / snapshot.id / "files" / "docs" / "notes.txt"
            meta = root / ".runewall" / "snapshots" / snapshot.id / "meta.json"

            self.assertEqual(copied.read_text(encoding="utf-8"), "before write")
            self.assertTrue(meta.exists())
            self.assertEqual(json.loads(meta.read_text(encoding="utf-8"))["snapshot_kind"], "file_copy")

    def test_file_delete_snapshots_deleted_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "trash.txt"
            target.write_text("delete me", encoding="utf-8")

            action = Action(action_type="file.delete", target="trash.txt")
            snapshot = SnapshotEngine(root=root).create_snapshot(action)

            copied = root / ".runewall" / "snapshots" / snapshot.id / "files" / "trash.txt"
            self.assertEqual(copied.read_text(encoding="utf-8"), "delete me")

    def test_file_create_records_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            action = Action(action_type="file.create", target="new.txt")

            snapshot = SnapshotEngine(root=root).create_snapshot(action)

            snapshot_dir = root / ".runewall" / "snapshots" / snapshot.id
            meta = json.loads((snapshot_dir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["snapshot_kind"], "metadata")
            self.assertEqual(meta["target"], "new.txt")
            self.assertFalse((snapshot_dir / "files").exists())

    def test_missing_file_raises_clear_error_for_write_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            engine = SnapshotEngine(root=root)

            with self.assertRaisesRegex(FileNotFoundError, "Cannot snapshot missing file for file.write"):
                engine.create_snapshot(Action(action_type="file.write", target="missing.txt"))

            with self.assertRaisesRegex(FileNotFoundError, "Cannot snapshot missing file for file.delete"):
                engine.create_snapshot(Action(action_type="file.delete", target="missing.txt"))

    def test_oversized_file_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "large.bin"
            target.write_bytes(b"1234567890")
            engine = SnapshotEngine(root=root, max_file_size_bytes=4)

            with self.assertRaisesRegex(ValueError, "File is too large to snapshot"):
                engine.create_snapshot(Action(action_type="file.write", target="large.bin"))

    def test_oversized_file_uses_configured_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".runewall"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "config.toml").write_text(
                "[safety]\nmax_snapshot_mb = 1\n",
                encoding="utf-8",
            )
            target = root / "too-large.bin"
            target.write_bytes(b"x" * (1024 * 1024 + 1))
            engine = SnapshotEngine(root=root)

            with self.assertRaisesRegex(ValueError, "File is too large to snapshot"):
                engine.create_snapshot(Action(action_type="file.write", target="too-large.bin"))


class SnapshotCleanupTests(unittest.TestCase):
    def _make_snapshots_dir(self, root: Path) -> Path:
        snapshots_dir = root / ".runewall" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        return snapshots_dir

    def _make_snapshot_dir(self, snapshots_dir: Path, name: str, age_days: float) -> Path:
        snap = snapshots_dir / name
        snap.mkdir()
        old_time = time.time() - age_days * 86400
        os.utime(snap, (old_time, old_time))
        return snap

    def test_old_snapshot_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshots_dir = self._make_snapshots_dir(root)
            snap = self._make_snapshot_dir(snapshots_dir, "old_snap", age_days=31)

            deleted = cleanup_snapshots(root=root, snapshot_days=30)

            self.assertEqual(deleted, 1)
            self.assertFalse(snap.exists())

    def test_recent_snapshot_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshots_dir = self._make_snapshots_dir(root)
            snap = self._make_snapshot_dir(snapshots_dir, "recent_snap", age_days=1)

            deleted = cleanup_snapshots(root=root, snapshot_days=30)

            self.assertEqual(deleted, 0)
            self.assertTrue(snap.exists())

    def test_config_retention_value_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".runewall"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "config.toml").write_text(
                "[retention]\nsnapshot_days = 7\n", encoding="utf-8"
            )
            snapshots_dir = self._make_snapshots_dir(root)
            old_snap = self._make_snapshot_dir(snapshots_dir, "old_snap", age_days=8)
            new_snap = self._make_snapshot_dir(snapshots_dir, "new_snap", age_days=6)

            deleted = cleanup_snapshots(root=root)

            self.assertEqual(deleted, 1)
            self.assertFalse(old_snap.exists())
            self.assertTrue(new_snap.exists())

    def test_default_retention_is_30_days_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshots_dir = self._make_snapshots_dir(root)
            old_snap = self._make_snapshot_dir(snapshots_dir, "old_snap", age_days=31)
            new_snap = self._make_snapshot_dir(snapshots_dir, "new_snap", age_days=29)

            deleted = cleanup_snapshots(root=root)

            self.assertEqual(deleted, 1)
            self.assertFalse(old_snap.exists())
            self.assertTrue(new_snap.exists())

    def test_empty_snapshots_directory_deletes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._make_snapshots_dir(root)

            deleted = cleanup_snapshots(root=root, snapshot_days=30)

            self.assertEqual(deleted, 0)


if __name__ == "__main__":
    unittest.main()
