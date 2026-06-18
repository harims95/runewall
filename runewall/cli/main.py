from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

from runewall.core.config import config_path, ensure_config, format_config_data, load_config, load_config_data, set_config_value
from runewall.core.db import database_path, initialize_database, project_state_dir
from runewall.core.interceptor import ExecutionError, execute_approved_action
from runewall.core.log import ActionLog
from runewall.maps.executor import MapExecutionError, UnsupportedExecutionError, execute_map_action
from runewall.maps import SiteMapRegistry
from runewall.maps.planner import DryRunPlanner, dry_run_result, missing_inputs_error, render_plan
from runewall.maps.registry import FlowNotFoundError, SiteMapNotFoundError
from runewall.core.models import Action
from runewall.core.rollback import RollbackEngine
from runewall.core.snapshot import cleanup_snapshots
from runewall.translate import read_url


EMPTY_LOG_MESSAGE = "No actions recorded yet."
NOT_INITIALIZED_MESSAGE = "Runewall is not initialized. Run `runewall init` first."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runewall")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init", help="Initialize .runewall in the current directory.")
    log_parser = subcommands.add_parser("log", help="Show recorded actions.")
    log_parser.add_argument("--json", action="store_true", dest="json_output")
    act_parser = subcommands.add_parser("act", help="Plan a mapped site flow.")
    act_parser.add_argument("site")
    act_parser.add_argument("flow")
    act_parser.add_argument("--dry-run", action="store_true")
    act_parser.add_argument("--execute", action="store_true")
    act_parser.add_argument("--input", action="append", default=[])
    act_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_parser = subcommands.add_parser("maps", help="Inspect bundled site maps.")
    maps_subcommands = maps_parser.add_subparsers(dest="maps_command", required=True)
    maps_list_parser = maps_subcommands.add_parser("list", help="List bundled site maps.")
    maps_list_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_subcommands.add_parser("path", help="Show the bundled site maps directory.")
    maps_validate_parser = maps_subcommands.add_parser("validate", help="Validate bundled site maps.")
    maps_validate_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_show_parser = maps_subcommands.add_parser("show", help="Show a bundled site map.")
    maps_show_parser.add_argument("site")
    maps_show_parser.add_argument("--json", action="store_true", dest="json_output")
    config_parser = subcommands.add_parser("config", help="Inspect local Runewall config.")
    config_subcommands = config_parser.add_subparsers(dest="config_command", required=True)
    config_subcommands.add_parser("path", help="Show the local config path.")
    config_subcommands.add_parser("show", help="Show the local config.")
    config_set_parser = config_subcommands.add_parser("set", help="Set a config value.")
    config_set_parser.add_argument("key")
    config_set_parser.add_argument("value")
    subcommands.add_parser("doctor", help="Check local Runewall health.")
    pending_parser = subcommands.add_parser("pending", help="Show pending actions.")
    pending_parser.add_argument("--json", action="store_true", dest="json_output")
    read_parser = subcommands.add_parser("read", help="Read a URL without a browser.")
    read_parser.add_argument("url")
    status_parser = subcommands.add_parser("status", help="Show current Runewall status.")
    status_parser.add_argument("--json", action="store_true", dest="json_output")
    approve_parser = subcommands.add_parser("approve", help="Approve a pending action.")
    approve_parser.add_argument("action_id")
    reject_parser = subcommands.add_parser("reject", help="Reject a pending action.")
    reject_parser.add_argument("action_id")
    execute_parser = subcommands.add_parser("execute", help="Execute an approved action.")
    execute_parser.add_argument("action_id")
    rollback_parser = subcommands.add_parser("rollback", help="Rollback a recorded action.")
    rollback_parser.add_argument("action_id", nargs="?")
    rollback_parser.add_argument("--last", action="store_true")
    cleanup_parser = subcommands.add_parser("cleanup", help="Clean up old Runewall data.")
    cleanup_subcommands = cleanup_parser.add_subparsers(dest="cleanup_command", required=True)
    cleanup_subcommands.add_parser("snapshots", help="Delete snapshot directories older than retention period.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        db_path = initialize_database(Path.cwd())
        ensure_config(Path.cwd())
        print(f"Initialized Runewall at {db_path}")
        return 0
    if args.command == "config":
        if args.config_command == "path":
            print(str(config_path(Path.cwd()).resolve()))
            return 0
        if args.config_command == "show":
            print(format_config_data(load_config_data(Path.cwd())))
            return 0
        if args.config_command == "set":
            try:
                set_config_value(args.key, args.value, root=Path.cwd())
            except ValueError as error:
                print(str(error))
                return 1
            print(f"Updated config: {args.key} = {args.value}")
            return 0
    if args.command == "log":
        log = ActionLog(root=Path.cwd())
        actions = log.list_actions()

        if args.json_output:
            print(json.dumps([
                {
                    "id": action.id,
                    "timestamp": action.timestamp,
                    "action_type": action.action_type,
                    "target": action.target,
                    "status": action.status,
                    "params": action.params,
                    "result": action.result,
                }
                for action in actions
            ]))
            return 0

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
    if args.command == "act":
        if not args.dry_run and not args.execute:
            print("Choose --dry-run or --execute.")
            return 1
        if args.dry_run and args.execute:
            print("Choose only one of --dry-run or --execute.")
            return 1
        if args.json_output and not args.dry_run:
            print("--json requires --dry-run.")
            return 1

        log = ActionLog.open_existing(root=Path.cwd())
        inputs: dict[str, str] = {}
        for item in args.input:
            if "=" not in item:
                print(f"Invalid input: {item}")
                return 1
            key, value = item.split("=", 1)
            inputs[key] = value

        planner = DryRunPlanner()
        try:
            plan = planner.build_plan(args.site, args.flow, inputs)
        except SiteMapNotFoundError as error:
            if args.json_output:
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": str(error)}))
            else:
                print(str(error))
            return 1
        except FlowNotFoundError as error:
            if args.json_output:
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": str(error)}))
            else:
                print(str(error))
            return 1

        validation_error = missing_inputs_error(plan)

        if args.json_output:
            if validation_error is not None:
                if log is not None:
                    log.add_action(
                        Action(
                            action_type="map.dry_run",
                            target=f"{args.site}:{args.flow}",
                            status="failed",
                            params={"site": args.site, "flow": args.flow, "inputs": inputs},
                            result={"error": validation_error},
                            reversible=False,
                        )
                    )
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": validation_error}))
                return 1
            if log is not None:
                log.add_action(
                    Action(
                        action_type="map.dry_run",
                        target=f"{args.site}:{args.flow}",
                        status="success",
                        params={"site": args.site, "flow": args.flow, "inputs": inputs},
                        result=dry_run_result(plan),
                        reversible=False,
                    )
                )
            print(json.dumps({
                "ok": True,
                "executed": False,
                "site": args.site,
                "flow": args.flow,
                "description": plan.description,
                "risk_level": plan.risk_level,
                "reversible": plan.reversible,
                "requires_auth": plan.requires_auth,
                "provided_inputs": plan.provided_inputs,
                "missing_inputs": plan.missing_inputs,
                "api_path": plan.api_path,
                "ui_steps_count": plan.ui_steps_count,
            }))
            return 0

        if args.dry_run:
            print(render_plan(plan))
        if validation_error is not None:
            if log is not None:
                log.add_action(
                    Action(
                        action_type="map.dry_run" if args.dry_run else "map.execute",
                        target=f"{args.site}:{args.flow}",
                        status="failed",
                        params={"site": args.site, "flow": args.flow, "inputs": inputs},
                        result={"error": validation_error},
                        reversible=False,
                    )
                )
            print(validation_error)
            return 1

        if args.dry_run:
            if log is not None:
                log.add_action(
                    Action(
                        action_type="map.dry_run",
                        target=f"{args.site}:{args.flow}",
                        status="success",
                        params={"site": args.site, "flow": args.flow, "inputs": inputs},
                        result=dry_run_result(plan),
                        reversible=False,
                    )
                )
            else:
                print("Runewall is not initialized; dry run was not logged.")
            return 0

        try:
            result = execute_map_action(args.site, args.flow, inputs, root=Path.cwd())
        except (MapExecutionError, UnsupportedExecutionError) as error:
            if log is not None:
                log.add_action(
                    Action(
                        action_type="map.execute",
                        target=f"{args.site}:{args.flow}",
                        status="failed",
                        params={"site": args.site, "flow": args.flow, "inputs": inputs},
                        result={"error": str(error)},
                        reversible=False,
                    )
                )
            print(str(error))
            return 1

        if log is not None:
            log.add_action(
                Action(
                    action_type="map.execute",
                    target=f"{args.site}:{args.flow}",
                    status="success",
                    params={"site": args.site, "flow": args.flow, "inputs": inputs},
                    result=result,
                    reversible=False,
                )
            )
        else:
            print("Runewall is not initialized; execution was not logged.")

        print(f"Created GitHub issue for {inputs['repo']}.")
        if "issue_number" in result:
            print(f"Issue number: {result['issue_number']}")
        if "issue_url" in result:
            print(f"Issue URL: {result['issue_url']}")
        return 0
    if args.command == "maps":
        registry = SiteMapRegistry()
        if args.maps_command == "list":
            site_maps = registry.list_maps()

            if args.json_output:
                print(json.dumps({
                    "maps": [
                        {
                            "key": site_map.raw.get("_filename", "").removesuffix(".json"),
                            "site_name": site_map.site_name,
                            "base_url": site_map.base_url,
                            "flow_count": len(site_map.flows),
                            "flows": list(site_map.flows.keys()),
                        }
                        for site_map in site_maps
                    ]
                }))
                return 0

            if not site_maps:
                print("No bundled site maps found.")
                return 0

            print("site_name\tbase_url\tflows")
            for site_map in site_maps:
                print(
                    "\t".join(
                        [
                            site_map.site_name,
                            site_map.base_url,
                            str(len(site_map.flows)),
                        ]
                    )
                )
            return 0
        if args.maps_command == "path":
            maps_path = registry.bundled_maps_path()
            if not maps_path.is_dir():
                print(f"Bundled maps directory not found: {maps_path}")
                return 1
            print(str(maps_path))
            return 0
        if args.maps_command == "validate":
            results = registry.validate_bundled_maps()
            all_valid = all(r.ok for r in results)

            if args.json_output:
                print(json.dumps({
                    "ok": all_valid,
                    "results": [
                        {
                            "key": result.site_key,
                            "site_name": result.site_name,
                            "ok": result.ok,
                            "error": result.error,
                        }
                        for result in results
                    ]
                }))
                return 0 if all_valid else 1

            for result in results:
                label = result.site_name or result.site_key
                if result.ok:
                    print(f"{result.site_key} ({label})\tOK")
                else:
                    print(f"{result.site_key} ({label})\tFAIL\t{result.error}")
            return 0 if all_valid else 1
        if args.maps_command == "show":
            site_map = registry.load_site(args.site)
            if site_map is None:
                print(f"Site map not found: {args.site}")
                return 1

            if args.json_output:
                flows_json = []
                for flow_name, flow_data in site_map.flows.items():
                    required_inputs = [
                        input_name
                        for input_name, input_data in flow_data.get("inputs", {}).items()
                        if input_data.get("required") is True
                    ]
                    flows_json.append({
                        "name": flow_name,
                        "description": flow_data.get("description", ""),
                        "risk_level": flow_data.get("risk_level", ""),
                        "reversible": flow_data.get("reversible", False),
                        "requires_auth": flow_data.get("requires_auth", False),
                        "required_inputs": required_inputs,
                        "api_path": flow_data.get("api_path"),
                    })
                print(json.dumps({
                    "key": site_map.raw.get("_filename", "").removesuffix(".json"),
                    "site_name": site_map.site_name,
                    "base_url": site_map.base_url,
                    "map_version": site_map.map_version,
                    "schema_version": site_map.schema_version,
                    "flows": flows_json,
                }))
                return 0

            print(f"Site name: {site_map.site_name}")
            print(f"Base URL: {site_map.base_url}")
            print(f"Map version: {site_map.map_version}")
            print(f"Schema version: {site_map.schema_version}")
            print("Available flows:")
            for flow_name, flow_data in site_map.flows.items():
                required_inputs = [
                    input_name
                    for input_name, input_data in flow_data.get("inputs", {}).items()
                    if input_data.get("required") is True
                ]
                print(f"- {flow_name}")
                print(f"  description: {flow_data.get('description', '')}")
                print(f"  risk_level: {flow_data.get('risk_level', '')}")
                print(f"  reversible: {flow_data.get('reversible', False)}")
                print(f"  requires_auth: {flow_data.get('requires_auth', False)}")
                print(f"  required inputs: {', '.join(required_inputs) if required_inputs else 'none'}")
            return 0
    if args.command == "doctor":
        db_exists = database_path(Path.cwd()).exists()
        httpx_available = importlib.util.find_spec("httpx") is not None
        bs4_available = importlib.util.find_spec("bs4") is not None
        github_token_set = bool(os.environ.get("GITHUB_TOKEN"))
        maps_count = len(SiteMapRegistry().list_maps())
        config_exists = config_path(Path.cwd()).exists()
        allow_execute = load_config(Path.cwd()).maps.allow_execute

        print(f"Python: {sys.version.split()[0]}")
        print(f"Runewall DB: {'present' if db_exists else 'missing'}")
        print(f"Config: {'present' if config_exists else 'missing'}")
        print(f"Dependency httpx: {'OK' if httpx_available else 'MISSING'}")
        print(f"Dependency bs4: {'OK' if bs4_available else 'MISSING'}")
        print(f"GITHUB_TOKEN: {'set' if github_token_set else 'missing'}")
        print(f"Bundled maps: {maps_count}")
        print(f"Map execution: {'ENABLED' if allow_execute else 'disabled'}")

        if not httpx_available or not bs4_available:
            print("Summary: FAIL")
        elif not db_exists or not github_token_set or allow_execute:
            print("Summary: WARN")
        else:
            print("Summary: OK")
        return 0
    if args.command == "pending":
        log = ActionLog.open_existing(root=Path.cwd())

        if args.json_output:
            if log is None:
                print(json.dumps({"initialized": False, "pending": []}))
                return 0
            actions = log.list_pending_actions()
            print(json.dumps({
                "initialized": True,
                "pending": [
                    {
                        "id": action.id,
                        "timestamp": action.timestamp,
                        "action_type": action.action_type,
                        "target": action.target,
                        "status": action.status,
                        "params": action.params,
                        "result": action.result,
                    }
                    for action in actions
                ],
            }))
            return 0

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

        if args.json_output:
            if not db_path.exists():
                print(json.dumps({"initialized": False, "database_path": str(db_path)}))
                return 0
            log = ActionLog.open_existing(root=Path.cwd())
            if log is None:
                print(json.dumps({"initialized": False, "database_path": str(db_path)}))
                return 0
            latest_action = log.get_last_action()
            print(json.dumps({
                "initialized": True,
                "database_path": str(log.db_path),
                "total_actions": log.count_actions(),
                "success_count": log.count_actions_by_status("success"),
                "failed_count": log.count_actions_by_status("failed"),
                "rolled_back_count": log.count_actions_by_status("rolled_back"),
                "pending_count": log.count_actions_by_status("pending"),
                "latest_action": None if latest_action is None else {
                    "id": latest_action.id,
                    "timestamp": latest_action.timestamp,
                    "action_type": latest_action.action_type,
                    "target": latest_action.target,
                    "status": latest_action.status,
                },
            }))
            return 0

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

    if args.command == "cleanup":
        if args.cleanup_command == "snapshots":
            snapshots_dir = project_state_dir(Path.cwd()) / "snapshots"
            if not snapshots_dir.is_dir():
                print("No snapshots directory found.")
                return 0
            deleted = cleanup_snapshots(root=Path.cwd())
            print(f"Deleted {deleted} old snapshot(s).")
            return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
