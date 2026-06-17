from __future__ import annotations

import json
from pathlib import Path
import shutil
import time

from .config import load_config
from .db import project_state_dir
from .models import Action, Snapshot

DEFAULT_MAX_FILE_SNAPSHOT_SIZE = 500 * 1024 * 1024


def cleanup_snapshots(root: Path | None = None, snapshot_days: int | None = None) -> int:
    resolved_root = (root or Path.cwd()).resolve()
    if snapshot_days is None:
        snapshot_days = load_config(resolved_root).retention.snapshot_days
    snapshots_dir = project_state_dir(resolved_root) / "snapshots"
    cutoff = time.time() - snapshot_days * 86400
    deleted = 0
    for entry in snapshots_dir.iterdir():
        if entry.is_dir() and entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry)
            deleted += 1
    return deleted


class SnapshotEngine:
    """Create reversible file snapshots for core file actions."""

    def __init__(
        self,
        root: Path | None = None,
        max_file_size_bytes: int | None = None,
        max_snapshot_mb: int | None = None,
    ) -> None:
        self._root = (root or Path.cwd()).resolve()
        self._max_file_size_bytes = self._resolve_max_file_size_bytes(
            self._root,
            max_file_size_bytes=max_file_size_bytes,
            max_snapshot_mb=max_snapshot_mb,
        )

    def create_snapshot(self, action: Action) -> Snapshot:
        target_path = self._resolve_target(action.target)
        snapshot = Snapshot(
            action_id=action.id,
            type=self._snapshot_kind_for(action.action_type),
            target=action.target,
            storage_path="",
            reversible=action.reversible,
        )

        snapshot_dir = self._snapshot_dir(snapshot.id)
        snapshot.storage_path = str(snapshot_dir.resolve())
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        if action.action_type in {"file.write", "file.delete"}:
            self._require_existing_file(target_path, action.action_type)
            file_size = target_path.stat().st_size
            self._ensure_within_size_limit(file_size, target_path)
            destination = snapshot_dir / "files" / self._relative_target(target_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, destination)
            snapshot.size_bytes = file_size
        elif action.action_type == "file.create":
            snapshot.size_bytes = None
        else:
            raise ValueError(f"Unsupported snapshot action type: {action.action_type}")

        self._write_meta(snapshot_dir / "meta.json", snapshot, action)
        return snapshot

    def target_path_for_snapshot(self, snapshot: Snapshot) -> Path:
        return self._resolve_target(snapshot.target)

    def copied_file_path(self, snapshot: Snapshot) -> Path:
        snapshot_dir = Path(snapshot.storage_path)
        return snapshot_dir / "files" / self._relative_target(self.target_path_for_snapshot(snapshot))

    @staticmethod
    def meta_path(snapshot: Snapshot) -> Path:
        return Path(snapshot.storage_path) / "meta.json"

    def _snapshot_dir(self, snapshot_id: str) -> Path:
        return project_state_dir(self._root) / "snapshots" / snapshot_id

    def _resolve_target(self, target: str) -> Path:
        path = Path(target)
        if path.is_absolute():
            return path
        return (self._root / path).resolve()

    def _relative_target(self, path: Path) -> Path:
        try:
            return path.resolve().relative_to(self._root)
        except ValueError:
            return Path(path.name)

    @staticmethod
    def _snapshot_kind_for(action_type: str) -> str:
        if action_type == "file.create":
            return "metadata"
        return "file_copy"

    @staticmethod
    def _require_existing_file(path: Path, action_type: str) -> None:
        if not path.is_file():
            raise FileNotFoundError(
                f"Cannot snapshot missing file for {action_type}: {path}"
            )

    def _ensure_within_size_limit(self, size_bytes: int, path: Path) -> None:
        if size_bytes > self._max_file_size_bytes:
            raise ValueError(
                f"File is too large to snapshot ({size_bytes} bytes > {self._max_file_size_bytes} bytes): {path}"
            )

    @staticmethod
    def _resolve_max_file_size_bytes(
        root: Path,
        *,
        max_file_size_bytes: int | None,
        max_snapshot_mb: int | None,
    ) -> int:
        if max_file_size_bytes is not None:
            return max_file_size_bytes
        if max_snapshot_mb is not None:
            return max_snapshot_mb * 1024 * 1024
        return load_config(root).safety.max_snapshot_mb * 1024 * 1024

    @staticmethod
    def _write_meta(meta_path: Path, snapshot: Snapshot, action: Action) -> None:
        meta = {
            "snapshot_id": snapshot.id,
            "action_id": action.id,
            "action_type": action.action_type,
            "target": action.target,
            "timestamp": snapshot.timestamp,
            "snapshot_kind": snapshot.type,
            "reversible": snapshot.reversible,
        }
        meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
