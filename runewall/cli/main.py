from __future__ import annotations

import argparse
from pathlib import Path

from runewall.core.db import initialize_database
from runewall.core.log import ActionLog


EMPTY_LOG_MESSAGE = "No actions recorded yet."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runewall")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Initialize .runewall in the current directory.")
    subcommands.add_parser("log", help="Show recorded actions.")
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

    parser.error(f"Unknown command: {args.command}")
    return 2
