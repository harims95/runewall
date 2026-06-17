from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3

from .db import connect, initialize_database
from .models import Action, Snapshot


class ActionLog:
    """Small SQLite-backed repository for actions."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root
        self._db_path = initialize_database(root)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def add_action(self, action: Action) -> Action:
        with closing(connect(self._db_path)) as connection:
            connection.execute(
                """
                INSERT INTO actions (
                    id, timestamp, agent_id, action_type, target, params, risk_level,
                    status, rule_applied, snapshot_id, result, reversible, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.id,
                    action.timestamp,
                    action.agent_id,
                    action.action_type,
                    action.target,
                    self._dump_json(action.params),
                    action.risk_level,
                    action.status,
                    action.rule_applied,
                    action.snapshot_id,
                    self._dump_json(action.result),
                    int(action.reversible),
                    action.reasoning,
                ),
            )
            connection.commit()
        return action

    def get_action(self, action_id: str) -> Action | None:
        with closing(connect(self._db_path)) as connection:
            row = connection.execute(
                """
                SELECT id, timestamp, agent_id, action_type, target, params, risk_level,
                       status, rule_applied, snapshot_id, result, reversible, reasoning
                FROM actions
                WHERE id = ?
                """,
                (action_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_action(row)

    def list_actions(self, limit: int = 50) -> list[Action]:
        with closing(connect(self._db_path)) as connection:
            rows = connection.execute(
                """
                SELECT id, timestamp, agent_id, action_type, target, params, risk_level,
                       status, rule_applied, snapshot_id, result, reversible, reasoning
                FROM actions
                ORDER BY timestamp ASC, id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_action(row) for row in rows]

    def update_action_status(self, action_id: str, status: str) -> bool:
        with closing(connect(self._db_path)) as connection:
            cursor = connection.execute(
                "UPDATE actions SET status = ? WHERE id = ?",
                (status, action_id),
            )
            connection.commit()
        return cursor.rowcount > 0

    def add_snapshot(self, snapshot: Snapshot) -> Snapshot:
        with closing(connect(self._db_path)) as connection:
            connection.execute(
                """
                INSERT INTO snapshots (id, action_id, type, target, storage_path, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.action_id,
                    snapshot.type,
                    snapshot.target,
                    snapshot.storage_path,
                    snapshot.size_bytes,
                ),
            )
            connection.commit()
        return snapshot

    @staticmethod
    def _row_to_action(row: sqlite3.Row) -> Action:
        return Action(
            id=row["id"],
            timestamp=row["timestamp"],
            agent_id=row["agent_id"],
            action_type=row["action_type"],
            target=row["target"],
            params=ActionLog._load_json(row["params"]),
            risk_level=row["risk_level"],
            status=row["status"],
            rule_applied=row["rule_applied"],
            snapshot_id=row["snapshot_id"],
            result=ActionLog._load_json(row["result"]),
            reversible=bool(row["reversible"]),
            reasoning=row["reasoning"],
        )

    @staticmethod
    def _dump_json(value: object) -> str | None:
        if value is None:
            return None
        return json.dumps(value, sort_keys=True)

    @staticmethod
    def _load_json(value: str | None) -> object:
        if value is None:
            return None
        return json.loads(value)


def open_default_log(root: Path | None = None) -> ActionLog:
    return ActionLog(root=root)
