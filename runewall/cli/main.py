from __future__ import annotations

import argparse
from pathlib import Path

from runewall.core.db import initialize_database
from runewall.core.log import ActionLog
from runewall.core.rollback import RollbackEngine


EMPTY_LOG_MESSAGE = "No actions recorded yet."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runewall")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Initialize .runewall in the current directory.")
    subcommands.add_parser("log", help="Show recorded actions.")
    rollback_parser = subcommands.add_parser("rollback", help="Rollback a recorded action.")
    rollback_parser.add_argument("action_id", nargs="?")
    rollback_parser.add_argument("--last", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        db_path = initialize_database(Path.cwd())
        print(f"Initialized Runewall at {db_path}")
        return 0
    if args.command == "log":
        log = ActionLog(root=Path.cwd())
        actions = log.list_actions()
        if not actions:
            print(EMPTY_LOG_MESSAGE)
            return 0

        print("id\ttimestamp\taction_type\ttarget\tstatus")
        for action in actions:
            print(
                "\t".join(
                    [
                        action.id,
                        action.timestamp,
                        action.action_type,
                        action.target,
                        action.status,
                    ]
                )
            )
        return 0
    if args.command == "rollback":
        engine = RollbackEngine(root=Path.cwd())
        if args.last:
            engine.rollback_last()
            print("Rolled back last action.")
            return 0
        if args.action_id:
            engine.rollback(args.action_id)
            print(f"Rolled back action {args.action_id}.")
            return 0
        parser.error("rollback requires an action ID or --last")

    parser.error(f"Unknown command: {args.command}")
    return 2
