from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .log import ActionLog
from .models import Action, Rule
from .rules import AUTO, BLOCK, REVIEW, SNAPSHOT, RulesEngine
from .snapshot import SnapshotEngine


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
        target=str(target_path),
        status="pending",
    )
    rules_engine = RulesEngine(rules=rules)
    policy = rules_engine.evaluate(action)
    action.rule_applied = policy

    if policy == BLOCK:
        raise PermissionError(f"{action_type} is blocked under policy {policy}")
    if policy == REVIEW and not allow_review_override:
        raise PermissionError(f"{action_type} requires approval under policy {policy}")

    log = ActionLog(root=resolved_root)
    snapshot_engine = SnapshotEngine(root=resolved_root)

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
