from __future__ import annotations

from contextlib import closing
from dataclasses import replace
from pathlib import Path
import sqlite3
from uuid import uuid4

from .db import connect, database_path, initialize_database
from .models import Action


class ActionLog:
    """Small SQLite-backed repository for actions."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root
        self._db_path = initialize_database(root)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def add_action(self, action: Action) -> Action:
        action_id = action.id or str(uuid4())
        stored = replace(action, id=action_id)
        with closing(connect(self._db_path)) as connection:
            connection.execute(
                """
                INSERT INTO actions (
                    id, timestamp, agent_id, action_type, target, params, risk_level,
                    status, rule_applied, snapshot_id, result, reversible, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.id,
                    stored.timestamp,
                    stored.agent_id,
                    stored.action_type,
                    stored.target,
                    stored.params,
                    stored.risk_level,
                    stored.status,
                    stored.rule_applied,
                    stored.snapshot_id,
                    stored.result,
                    int(stored.reversible),
                    stored.reasoning,
                ),
            )
            connection.commit()
        return stored

    def list_actions(self) -> list[Action]:
        with closing(connect(self._db_path)) as connection:
            rows = connection.execute(
                """
                SELECT id, timestamp, agent_id, action_type, target, params, risk_level,
                       status, rule_applied, snapshot_id, result, reversible, reasoning
                FROM actions
                ORDER BY timestamp ASC, id ASC
                """
            ).fetchall()
        return [self._row_to_action(row) for row in rows]

    @staticmethod
    def _row_to_action(row: sqlite3.Row) -> Action:
        return Action(
            id=row["id"],
            timestamp=row["timestamp"],
            agent_id=row["agent_id"],
            action_type=row["action_type"],
            target=row["target"],
            params=row["params"],
            risk_level=row["risk_level"],
            status=row["status"],
            rule_applied=row["rule_applied"],
            snapshot_id=row["snapshot_id"],
            result=row["result"],
            reversible=bool(row["reversible"]),
            reasoning=row["reasoning"],
        )


def open_default_log(root: Path | None = None) -> ActionLog:
    return ActionLog(root=root)
