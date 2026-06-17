from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .log import ActionLog
from .models import Action, Rule
from .rules import AUTO, BLOCK, REVIEW, SNAPSHOT, RulesEngine
from .snapshot import SnapshotEngine


class PendingReviewError(RuntimeError):
    """Raised when an action is logged as pending human review."""


class ExecutionError(RuntimeError):
    """Raised when delayed execution cannot proceed."""


@contextmanager
def protect_file_write(
    target: str | Path,
    *,
    root: Path | None = None,
    rules: list[Rule] | None = None,
) -> Iterator[None]:
    """Protect a single file write using the current rules, log, and snapshot layers."""

    with _protect_file_action(
        action_type="file.write",
        target=target,
        root=root,
        rules=rules,
    ):
        yield


@contextmanager
def protect_file_create(
    target: str | Path,
    *,
    root: Path | None = None,
    rules: list[Rule] | None = None,
) -> Iterator[None]:
    """Protect a single file creation using metadata-only snapshots."""

    with _protect_file_action(
        action_type="file.create",
        target=target,
        root=root,
        rules=rules,
    ):
        yield


@contextmanager
def protect_file_delete(
    target: str | Path,
    *,
    root: Path | None = None,
    rules: list[Rule] | None = None,
    require_review: bool = False,
) -> Iterator[None]:
    """Protect a single file delete while allowing an explicit review bypass for now."""

    with _protect_file_action(
        action_type="file.delete",
        target=target,
        root=root,
        rules=rules,
        allow_review_override=not require_review,
    ):
        yield


@contextmanager
def _protect_file_action(
    *,
    action_type: str,
    target: str | Path,
    root: Path | None,
    rules: list[Rule] | None,
    allow_review_override: bool = False,
) -> Iterator[None]:
    """Shared context manager for the current file safety loop."""

    resolved_root = root or Path.cwd()
    target_path = Path(target)
    action = Action(
        action_type=action_type,
        params={"path": str(target_path)},
        target=str(target_path),
        status="pending",
    )
    rules_engine = RulesEngine(rules=rules)
    policy = rules_engine.evaluate(action)
    action.rule_applied = policy

    log = ActionLog(root=resolved_root)
    snapshot_engine = SnapshotEngine(root=resolved_root)

    if policy == BLOCK:
        action.status = "blocked"
        log.add_action(action)
        raise PermissionError(f"{action_type} is blocked under policy {policy}")
    if policy == REVIEW and not allow_review_override:
        log.add_action(action)
        raise PendingReviewError(f"{action_type} is pending review")

    if policy == SNAPSHOT or (policy == REVIEW and allow_review_override):
        snapshot = snapshot_engine.create_snapshot(action)
        action.snapshot_id = snapshot.id
        log.add_action(action)
        log.add_snapshot(snapshot)
    elif policy == AUTO:
        log.add_action(action)
    else:
        raise ValueError(f"Unsupported {action_type} policy: {policy}")

    try:
        yield
    except Exception:
        log.update_action_status(action.id, "failed")
        raise
    else:
        log.update_action_status(action.id, "success")


def execute_approved_action(action_id: str, *, root: Path | None = None) -> None:
    """Execute a previously approved action when supported."""

    resolved_root = root or Path.cwd()
    log = ActionLog(root=resolved_root)
    action = log.get_action(action_id)
    if action is None:
        raise ExecutionError(f"Action not found: {action_id}")
    if action.status != "approved":
        raise ExecutionError(f"Action {action_id} is not approved.")
    if action.action_type != "file.delete":
        raise ExecutionError(f"Unsupported approved action type: {action.action_type}")

    snapshot_engine = SnapshotEngine(root=resolved_root)
    target_path = resolved_root / action.target if not Path(action.target).is_absolute() else Path(action.target)

    try:
        snapshot = snapshot_engine.create_snapshot(action)
        log.add_snapshot(snapshot)
        log.update_action_snapshot_id(action.id, snapshot.id)
        target_path.unlink()
    except Exception:
        log.update_action_status(action.id, "failed")
        raise
    else:
        log.update_action_status(action.id, "success")
