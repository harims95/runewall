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

    resolved_root = root or Path.cwd()
    target_path = Path(target)
    action = Action(
        action_type="file.write",
        target=str(target_path),
        status="pending",
    )
    rules_engine = RulesEngine(rules=rules)
    policy = rules_engine.evaluate(action)
    action.rule_applied = policy

    if policy in {REVIEW, BLOCK}:
        raise PermissionError(f"file.write requires approval under policy {policy}")

    log = ActionLog(root=resolved_root)
    snapshot_engine = SnapshotEngine(root=resolved_root)

    if policy == SNAPSHOT:
        snapshot = snapshot_engine.create_snapshot(action)
        action.snapshot_id = snapshot.id
        log.add_action(action)
        log.add_snapshot(snapshot)
    elif policy == AUTO:
        log.add_action(action)
    else:
        raise ValueError(f"Unsupported file.write policy: {policy}")

    try:
        yield
    except Exception:
        log.update_action_status(action.id, "failed")
        raise
    else:
        log.update_action_status(action.id, "success")
