from __future__ import annotations

from contextlib import closing
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    agent_id TEXT,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    params TEXT,
    risk_level TEXT NOT NULL DEFAULT 'low',
    status TEXT NOT NULL DEFAULT 'pending',
    rule_applied TEXT,
    snapshot_id TEXT,
    result TEXT,
    reversible INTEGER NOT NULL DEFAULT 1,
    reasoning TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL REFERENCES actions(id),
    type TEXT NOT NULL,
    target TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    size_bytes INTEGER
);

CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    policy TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    name TEXT,
    action_id TEXT NOT NULL REFERENCES actions(id)
);

CREATE INDEX IF NOT EXISTS idx_actions_ts ON actions(timestamp);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type);
"""


def project_state_dir(root: Path | None = None) -> Path:
    base = (root or Path.cwd()) / ".runewall"
    return base


def database_path(root: Path | None = None) -> Path:
    return project_state_dir(root) / "runewall.db"


def initialize_database(root: Path | None = None) -> Path:
    db_path = database_path(root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executescript(SCHEMA)
        connection.commit()
    return db_path


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection
