from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Action:
    action_type: str
    target: str
    params: str | None = None
    agent_id: str | None = None
    risk_level: str = "low"
    status: str = "pending"
    rule_applied: str | None = None
    snapshot_id: str | None = None
    result: str | None = None
    reversible: bool = True
    reasoning: str | None = None
    id: str | None = None
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class Snapshot:
    action_id: str
    type: str
    target: str
    storage_path: str
    size_bytes: int | None = None
    id: str | None = None


@dataclass(slots=True)
class Rule:
    pattern: str
    policy: str
    priority: int = 0
    id: int | None = None


@dataclass(slots=True)
class Checkpoint:
    action_id: str
    name: str | None = None
    id: str | None = None
