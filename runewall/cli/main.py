from __future__ import annotations

import argparse
from pathlib import Path

from runewall.core.db import database_path, initialize_database
from runewall.core.interceptor import ExecutionError, execute_approved_action
from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.core.rollback import RollbackEngine
from runewall.translate import read_url


EMPTY_LOG_MESSAGE = "No actions recorded yet."
NOT_INITIALIZED_MESSAGE = "Runewall is not initialized. Run `runewall init` first."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runewall")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Initialize .runewall in the current directory.")
    subcommands.add_parser("log", help="Show recorded actions.")
    subcommands.add_parser("pending", help="Show pending actions.")
    read_parser = subcommands.add_parser("read", help="Read a URL without a browser.")
    read_parser.add_argument("url")
    subcommands.add_parser("status", help="Show current Runewall status.")
    approve_parser = subcommands.add_parser("approve", help="Approve a pending action.")
    approve_parser.add_argument("action_id")
    reject_parser = subcommands.add_parser("reject", help="Reject a pending action.")
    reject_parser.add_argument("action_id")
    execute_parser = subcommands.add_parser("execute", help="Execute an approved action.")
    execute_parser.add_argument("action_id")
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
    if args.command == "pending":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            print(NOT_INITIALIZED_MESSAGE)
            return 0

        actions = log.list_pending_actions()
        if not actions:
            print("No pending actions.")
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
    if args.command == "read":
        log = ActionLog.open_existing(root=Path.cwd())
        try:
            content = read_url(args.url)
        except Exception as error:
            if log is not None:
                log.add_action(
                    Action(
                        action_type="web.read",
                        target=args.url,
                        status="failed",
                        params={"mode": "universal_read"},
                        result={"error": str(error)},
                        reversible=False,
                    )
                )
            print(f"Read failed: {error}")
            return 1

        if log is not None:
            log.add_action(
                Action(
                    action_type="web.read",
                    target=args.url,
                    status="success",
                    params={"mode": "universal_read"},
                    result={
                        "title": content["title"],
                        "heading_count": len(content["headings"]),
                        "text_length": len(content["text"]),
                    },
                    reversible=False,
                )
            )

        preview = content["text"][:200].strip()
        print(f"Title: {content['title']}")
        print("Headings:")
        if content["headings"]:
            for heading in content["headings"]:
                print(f"- {heading}")
        else:
            print("- none")
        print("Text preview:")
        print(preview)
        if log is None:
            print("Runewall is not initialized; read action was not logged.")
        return 0
    if args.command == "status":
        db_path = database_path(Path.cwd())
        if not db_path.exists():
            print(NOT_INITIALIZED_MESSAGE)
            return 0

        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            print(NOT_INITIALIZED_MESSAGE)
            return 0

        latest_action = log.get_last_action()
        print(f"Database: {log.db_path}")
        print(f"Total actions: {log.count_actions()}")
        print(f"Success actions: {log.count_actions_by_status('success')}")
        print(f"Failed actions: {log.count_actions_by_status('failed')}")
        print(f"Rolled back actions: {log.count_actions_by_status('rolled_back')}")
        if latest_action is None:
            print("Latest action: none")
        else:
            print(
                "Latest action: "
                f"{latest_action.id} | {latest_action.timestamp} | "
                f"{latest_action.action_type} | {latest_action.target} | {latest_action.status}"
            )
        return 0
    if args.command == "approve":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        action = log.get_action(args.action_id)
        if action is None:
            print(f"Action not found: {args.action_id}")
            return 1
        log.update_action_status(args.action_id, "approved")
        print(f"Approved action {args.action_id}.")
        return 0
    if args.command == "reject":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        action = log.get_action(args.action_id)
        if action is None:
            print(f"Action not found: {args.action_id}")
            return 1
        log.update_action_status(args.action_id, "rejected")
        print(f"Rejected action {args.action_id}.")
        return 0
    if args.command == "execute":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        try:
            execute_approved_action(args.action_id, root=Path.cwd())
        except ExecutionError as error:
            print(str(error))
            return 1
        except Exception as error:
            print(f"Execution failed for action {args.action_id}: {error}")
            return 1
        print(f"Executed action {args.action_id}.")
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
