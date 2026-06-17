from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeAlias
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_uuid() -> str:
    return str(uuid4())


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


@dataclass(slots=True)
class Action:
    action_type: str
    target: str
    params: JSONValue = None
    agent_id: str | None = None
    risk_level: str = "low"
    status: str = "pending"
    rule_applied: str | None = None
    snapshot_id: str | None = None
    result: JSONValue = None
    reversible: bool = True
    reasoning: str | None = None
    id: str = field(default_factory=new_uuid)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class Snapshot:
    action_id: str
    type: str
    target: str
    storage_path: str
    size_bytes: int | None = None
    id: str = field(default_factory=new_uuid)


@dataclass(slots=True)
class Rule:
    pattern: str
    policy: str
    id: str = field(default_factory=new_uuid)
    priority: int = 0


@dataclass(slots=True)
class Checkpoint:
    action_id: str
    id: str = field(default_factory=new_uuid)
    name: str | None = None
