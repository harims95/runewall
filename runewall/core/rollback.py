from __future__ import annotations

from pathlib import Path
import shutil

from .log import ActionLog
from .snapshot import SnapshotEngine


class RollbackEngine:
    """Restore files from snapshots for supported file actions."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root
        self._log = ActionLog(root=root)
        self._snapshot_engine = SnapshotEngine(root=root)

    def rollback(self, action_id: str) -> None:
        action = self._log.get_action(action_id)
        if action is None:
            raise ValueError(f"Action not found: {action_id}")

        snapshot = self._log.get_latest_snapshot_for_action(action_id)
        if snapshot is None:
            raise ValueError(f"Missing snapshot for action: {action_id}")

        target_path = self._snapshot_engine.target_path_for_snapshot(snapshot)

        if action.action_type in {"file.write", "file.delete"}:
            source_path = self._snapshot_engine.copied_file_path(snapshot)
            if not source_path.is_file():
                raise ValueError(f"Missing snapshot file for action: {action_id}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
        elif action.action_type == "file.create":
            if target_path.exists():
                target_path.unlink()
        else:
            raise ValueError(f"Unsupported rollback action type: {action.action_type}")

        self._log.update_action_status(action_id, "rolled_back")

    def rollback_last(self) -> None:
        action = self._log.get_last_action()
        if action is None:
            raise ValueError("No actions recorded yet.")
        self.rollback(action.id)
