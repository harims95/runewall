from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import sys

from runewall.core.config import config_path, CONFIG_PROFILES, ensure_config, format_config_data, load_config, load_config_data, RESET_CONFIG_TEXT, safe_config_dict, set_config_value, validate_config_data
from runewall.core.db import database_path, initialize_database, project_state_dir
from runewall.core.interceptor import ExecutionError, execute_approved_action
from runewall.core.log import ActionLog
from runewall.maps.executor import MapExecutionError, UnsupportedExecutionError, execute_map_action
from runewall.maps import SiteMapRegistry
from runewall.maps.registry import lint_map
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
    init_parser = subcommands.add_parser("init", help="Initialize .runewall in the current directory.")
    init_parser.add_argument("--json", action="store_true", dest="json_output")
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
    maps_list_parser.add_argument("--category", default=None)
    maps_list_parser.add_argument("--tag", default=None)
    maps_search_parser = maps_subcommands.add_parser("search", help="Search bundled site maps.")
    maps_search_parser.add_argument("query")
    maps_search_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_lint_parser = maps_subcommands.add_parser("lint", help="Lint bundled maps for quality warnings.")
    maps_lint_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_lint_parser.add_argument("--strict", action="store_true")
    maps_export_parser = maps_subcommands.add_parser("export", help="Export all bundled maps as JSON.")
    maps_export_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_stats_parser = maps_subcommands.add_parser("stats", help="Show map statistics.")
    maps_stats_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_subcommands.add_parser("path", help="Show the bundled site maps directory.")
    maps_validate_parser = maps_subcommands.add_parser("validate", help="Validate bundled site maps.")
    maps_validate_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_show_parser = maps_subcommands.add_parser("show", help="Show a bundled site map.")
    maps_show_parser.add_argument("site")
    maps_show_parser.add_argument("--json", action="store_true", dest="json_output")
    config_parser = subcommands.add_parser("config", help="Inspect local Runewall config.")
    config_subcommands = config_parser.add_subparsers(dest="config_command", required=True)
    config_path_parser = config_subcommands.add_parser("path", help="Show the local config path.")
    config_path_parser.add_argument("--json", action="store_true", dest="json_output")
    config_show_parser = config_subcommands.add_parser("show", help="Show the local config.")
    config_show_parser.add_argument("--json", action="store_true", dest="json_output")
    config_set_parser = config_subcommands.add_parser("set", help="Set a config value.")
    config_set_parser.add_argument("key")
    config_set_parser.add_argument("value")
    config_set_parser.add_argument("--json", action="store_true", dest="json_output")
    config_validate_parser = config_subcommands.add_parser("validate", help="Validate local config.")
    config_validate_parser.add_argument("--json", action="store_true", dest="json_output")
    config_reset_parser = config_subcommands.add_parser("reset", help="Reset config to safe defaults.")
    config_reset_parser.add_argument("--json", action="store_true", dest="json_output")
    config_profile_parser = config_subcommands.add_parser("profile", help="Apply a named config profile.")
    config_profile_parser.add_argument("name")
    config_profile_parser.add_argument("--json", action="store_true", dest="json_output")
    version_parser = subcommands.add_parser("version", help="Print Runewall version.")
    version_parser.add_argument("--json", action="store_true", dest="json_output")
    doctor_parser = subcommands.add_parser("doctor", help="Check local Runewall health.")
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")
    pending_parser = subcommands.add_parser("pending", help="Show pending actions.")
    pending_parser.add_argument("--json", action="store_true", dest="json_output")
    read_parser = subcommands.add_parser("read", help="Read a URL without a browser.")
    read_parser.add_argument("url")
    read_parser.add_argument("--json", action="store_true", dest="json_output")
    status_parser = subcommands.add_parser("status", help="Show current Runewall status.")
    status_parser.add_argument("--json", action="store_true", dest="json_output")
    approve_parser = subcommands.add_parser("approve", help="Approve a pending action.")
    approve_parser.add_argument("action_id")
    approve_parser.add_argument("--json", action="store_true", dest="json_output")
    reject_parser = subcommands.add_parser("reject", help="Reject a pending action.")
    reject_parser.add_argument("action_id")
    reject_parser.add_argument("--json", action="store_true", dest="json_output")
    execute_parser = subcommands.add_parser("execute", help="Execute an approved action.")
    execute_parser.add_argument("action_id")
    execute_parser.add_argument("--json", action="store_true", dest="json_output")
    rollback_parser = subcommands.add_parser("rollback", help="Rollback a recorded action.")
    rollback_parser.add_argument("action_id", nargs="?")
    rollback_parser.add_argument("--last", action="store_true")
    rollback_parser.add_argument("--json", action="store_true", dest="json_output")
    cleanup_parser = subcommands.add_parser("cleanup", help="Clean up old Runewall data.")
    cleanup_subcommands = cleanup_parser.add_subparsers(dest="cleanup_command", required=True)
    cleanup_snapshots_parser = cleanup_subcommands.add_parser("snapshots", help="Delete snapshot directories older than retention period.")
    cleanup_snapshots_parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        db_path = initialize_database(Path.cwd())
        ensure_config(Path.cwd())
        if args.json_output:
            print(json.dumps({
                "ok": True,
                "initialized": True,
                "database_path": str(db_path),
                "config_path": str(config_path(Path.cwd()).resolve()),
            }))
            return 0
        print(f"Initialized Runewall at {db_path}")
        return 0
    if args.command == "config":
        if args.config_command == "path":
            path = config_path(Path.cwd()).resolve()
            if args.json_output:
                print(json.dumps({"path": str(path), "exists": path.exists()}))
                return 0
            print(str(path))
            return 0
        if args.config_command == "show":
            if args.json_output:
                exists = config_path(Path.cwd()).exists()
                safe = safe_config_dict(load_config(Path.cwd()))
                if exists:
                    print(json.dumps({"config": safe}))
                else:
                    print(json.dumps({"exists": False, "config": safe}))
                return 0
            print(format_config_data(load_config_data(Path.cwd())))
            return 0
        if args.config_command == "set":
            try:
                set_config_value(args.key, args.value, root=Path.cwd())
            except ValueError as error:
                if args.json_output:
                    print(json.dumps({"ok": False, "key": args.key, "error": str(error)}))
                    return 1
                print(str(error))
                return 1
            if args.json_output:
                section, field = args.key.split(".", 1)
                typed_value = getattr(getattr(load_config(Path.cwd()), section), field)
                print(json.dumps({
                    "ok": True,
                    "key": args.key,
                    "value": typed_value,
                    "config_path": str(config_path(Path.cwd()).resolve()),
                }))
                return 0
            print(f"Updated config: {args.key} = {args.value}")
            return 0
        if args.config_command == "validate":
            raw = load_config_data(Path.cwd())
            errors = validate_config_data(raw)
            if args.json_output:
                print(json.dumps({"ok": not errors, "errors": errors}))
                return 0 if not errors else 1
            if not errors:
                print("Config: OK")
            else:
                print("Config: INVALID")
                for err in errors:
                    print(f"  - {err['key']}: {err['message']}")
            return 0 if not errors else 1
        if args.config_command == "reset":
            path = config_path(Path.cwd())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(RESET_CONFIG_TEXT, encoding="utf-8")
            if args.json_output:
                print(json.dumps({"ok": True, "path": str(path.resolve()), "reset": True}))
                return 0
            print(f"Config reset to defaults: {path}")
            return 0
        if args.config_command == "profile":
            known = list(CONFIG_PROFILES)
            if args.name not in CONFIG_PROFILES:
                if args.json_output:
                    print(json.dumps({"ok": False, "profile": args.name, "error": f"Unknown config profile: {args.name}", "known_profiles": known}))
                    return 1
                print(f"Unknown config profile: {args.name}")
                print(f"Known profiles: {', '.join(known)}")
                return 1
            path = config_path(Path.cwd())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(CONFIG_PROFILES[args.name], encoding="utf-8")
            if args.json_output:
                print(json.dumps({"ok": True, "profile": args.name, "path": str(path.resolve()), "applied": True}))
                return 0
            print(f"Applied config profile: {args.name}")
            print(f"Path: {path.resolve()}")
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
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": f"Unknown site: {args.site}", "error_code": "UNKNOWN_SITE"}))
            else:
                print(str(error))
            return 1
        except FlowNotFoundError as error:
            if args.json_output:
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": f"Unknown flow: {args.flow}", "error_code": "UNKNOWN_FLOW"}))
            else:
                print(str(error))
            return 1

        validation_error = missing_inputs_error(plan)

        if args.json_output and args.dry_run:
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
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": validation_error, "error_code": "INVALID_INPUT"}))
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
            if args.json_output and not args.dry_run:
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": validation_error, "error_code": "INVALID_INPUT"}))
                return 1
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
            if args.json_output:
                print(json.dumps({"ok": False, "executed": False, "site": args.site, "flow": args.flow, "error": str(error), "error_code": getattr(error, "error_code", "UNKNOWN_ERROR")}))
                return 1
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
            if not args.json_output:
                print("Runewall is not initialized; execution was not logged.")

        if args.json_output:
            print(json.dumps({"ok": True, "executed": True, "site": args.site, "flow": args.flow, "result": result}))
            return 0

        if args.site.lower() == "vercel":
            print(f"Listed {result['project_count']} Vercel project(s).")
        elif args.site.lower() == "netlify":
            print(f"Listed {result['site_count']} Netlify site(s).")
        elif args.site.lower() == "supabase":
            print(f"Listed {result['project_count']} Supabase project(s).")
        elif args.site.lower() == "cloudflare":
            print(f"Listed {result['zone_count']} Cloudflare zone(s).")
        else:
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
            if args.category:
                site_maps = [m for m in site_maps if m.category == args.category]
            if args.tag:
                site_maps = [m for m in site_maps if args.tag in m.tags]

            if args.json_output:
                print(json.dumps({
                    "maps": [
                        {
                            "key": site_map.raw.get("_filename", "").removesuffix(".json"),
                            "site_name": site_map.site_name,
                            "base_url": site_map.base_url,
                            "category": site_map.category,
                            "tags": site_map.tags,
                            "flow_count": len(site_map.flows),
                            "flows": list(site_map.flows.keys()),
                        }
                        for site_map in site_maps
                    ]
                }))
                return 0

            if not site_maps:
                print("No maps found.")
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
        if args.maps_command == "search":
            results = registry.search_maps(args.query)
            if args.json_output:
                print(json.dumps({
                    "query": args.query,
                    "count": len(results),
                    "maps": [
                        {
                            "key": sm.raw.get("_filename", "").removesuffix(".json"),
                            "site_name": sm.site_name,
                            "base_url": sm.base_url,
                            "category": sm.category,
                            "tags": sm.tags,
                            "flow_count": len(sm.flows),
                            "flows": list(sm.flows.keys()),
                        }
                        for sm in results
                    ],
                }))
                return 0
            if not results:
                print("No maps found.")
                return 0
            print("site_name\tbase_url\tflows")
            for sm in results:
                print("\t".join([sm.site_name, sm.base_url, str(len(sm.flows))]))
            return 0
        if args.maps_command == "lint":
            site_maps = registry.list_maps()
            lint_results = []
            total_warnings = 0
            total_errors = 0
            for site_map in site_maps:
                key = site_map.raw.get("_filename", "").removesuffix(".json")
                warnings, errors = lint_map(site_map)
                total_warnings += len(warnings)
                total_errors += len(errors)
                lint_results.append((key, site_map.site_name, warnings, errors))

            has_errors = total_errors > 0
            strict = args.strict
            should_fail = has_errors or (strict and total_warnings > 0)

            if args.json_output:
                print(json.dumps({
                    "strict": strict,
                    "ok": not should_fail,
                    "warning_count": total_warnings,
                    "error_count": total_errors,
                    "results": [
                        {
                            "key": key,
                            "site_name": site_name,
                            "warnings": warnings,
                            "errors": errors,
                        }
                        for key, site_name, warnings, errors in lint_results
                    ],
                }))
                return 0 if not should_fail else 1

            if strict:
                print("Map lint results (strict mode)")
            else:
                print("Map lint results")
            for key, _site_name, warnings, errors in lint_results:
                issues = warnings + errors
                if not issues:
                    print(f"{key}: OK")
                else:
                    label = "ERROR" if errors else "WARN"
                    print(f"{key}: {label}")
                    for issue in issues:
                        print(f"  - {issue}")
            return 0 if not should_fail else 1
        if args.maps_command == "export":
            if not args.json_output:
                print("Use `runewall maps export --json` to export the map registry.")
                return 0
            site_maps = registry.list_maps()
            export_maps = []
            for site_map in site_maps:
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
                export_maps.append({
                    "key": site_map.raw.get("_filename", "").removesuffix(".json"),
                    "site_name": site_map.site_name,
                    "base_url": site_map.base_url,
                    "map_version": site_map.map_version,
                    "schema_version": site_map.schema_version,
                    "category": site_map.category,
                    "tags": site_map.tags,
                    "flows": flows_json,
                })
            print(json.dumps({"maps": export_maps}))
            return 0
        if args.maps_command == "stats":
            site_maps = registry.list_maps()
            real_execution_keys = {"github", "vercel", "netlify", "supabase", "cloudflare"}
            total_maps = len(site_maps)
            total_flows = sum(len(sm.flows) for sm in site_maps)
            categories: dict[str, int] = {}
            for sm in site_maps:
                if sm.category:
                    categories[sm.category] = categories.get(sm.category, 0) + 1
            keys = [sm.raw.get("_filename", "").removesuffix(".json") for sm in site_maps]
            real_execution_maps = sorted(k for k in keys if k in real_execution_keys)
            dry_run_only_maps = sorted(k for k in keys if k not in real_execution_keys)

            if args.json_output:
                print(json.dumps({
                    "total_maps": total_maps,
                    "total_flows": total_flows,
                    "categories": categories,
                    "real_execution_maps": real_execution_maps,
                    "dry_run_only_maps": dry_run_only_maps,
                }))
                return 0

            print(f"Total maps: {total_maps}")
            print(f"Total flows: {total_flows}")
            print("Categories:")
            for cat, count in sorted(categories.items()):
                print(f"  {cat}: {count}")
            print(f"Real execution: {', '.join(real_execution_maps) if real_execution_maps else 'none'}")
            print(f"Dry-run only: {', '.join(dry_run_only_maps)}")
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
                    "category": site_map.category,
                    "tags": site_map.tags,
                    "flows": flows_json,
                }))
                return 0

            print(f"Site name: {site_map.site_name}")
            print(f"Base URL: {site_map.base_url}")
            print(f"Map version: {site_map.map_version}")
            print(f"Schema version: {site_map.schema_version}")
            if site_map.category:
                print(f"Category: {site_map.category}")
            if site_map.tags:
                print(f"Tags: {', '.join(site_map.tags)}")
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
    if args.command == "version":
        ver = importlib.metadata.version("runewall")
        if args.json_output:
            print(json.dumps({"name": "runewall", "version": ver}))
            return 0
        print(f"Runewall {ver}")
        return 0
    if args.command == "doctor":
        db_exists = database_path(Path.cwd()).exists()
        httpx_available = importlib.util.find_spec("httpx") is not None
        bs4_available = importlib.util.find_spec("bs4") is not None
        maps_count = len(SiteMapRegistry().list_maps())
        config_exists = config_path(Path.cwd()).exists()
        cfg = load_config(Path.cwd())
        allow_execute = cfg.maps.allow_execute

        github_env = cfg.auth.github_token_env
        vercel_env = cfg.auth.vercel_token_env
        netlify_env = cfg.auth.netlify_token_env
        supabase_env = cfg.auth.supabase_access_token_env
        cloudflare_env = cfg.auth.cloudflare_api_token_env

        github_token_set = bool(os.environ.get(github_env))
        vercel_token_set = bool(os.environ.get(vercel_env))
        netlify_token_set = bool(os.environ.get(netlify_env))
        supabase_token_set = bool(os.environ.get(supabase_env))
        cloudflare_token_set = bool(os.environ.get(cloudflare_env))

        if not httpx_available or not bs4_available:
            summary = "FAIL"
        elif not db_exists or not github_token_set or not vercel_token_set or not netlify_token_set or not supabase_token_set or not cloudflare_token_set or allow_execute:
            summary = "WARN"
        else:
            summary = "OK"

        if args.json_output:
            print(json.dumps({
                "python": {"version": sys.version.split()[0], "ok": True},
                "database": {"present": db_exists, "path": str(database_path(Path.cwd()))},
                "config": {
                    "present": config_exists,
                    "path": str(config_path(Path.cwd()).resolve()),
                    "map_execution": "ENABLED" if allow_execute else "disabled",
                },
                "dependencies": {"httpx": httpx_available, "bs4": bs4_available},
                "auth": {
                    "github_token": "present" if github_token_set else "missing",
                    "vercel_token": "present" if vercel_token_set else "missing",
                    "netlify_token": "present" if netlify_token_set else "missing",
                    "supabase_access_token": "present" if supabase_token_set else "missing",
                    "cloudflare_api_token": "present" if cloudflare_token_set else "missing",
                    "github": {"env": github_env, "status": "present" if github_token_set else "missing"},
                    "vercel": {"env": vercel_env, "status": "present" if vercel_token_set else "missing"},
                    "netlify": {"env": netlify_env, "status": "present" if netlify_token_set else "missing"},
                    "supabase": {"env": supabase_env, "status": "present" if supabase_token_set else "missing"},
                    "cloudflare": {"env": cloudflare_env, "status": "present" if cloudflare_token_set else "missing"},
                },
                "maps": {"bundled_count": maps_count},
                "summary": summary,
            }))
            return 0

        print(f"Python: {sys.version.split()[0]}")
        print(f"Runewall DB: {'present' if db_exists else 'missing'}")
        print(f"Config: {'present' if config_exists else 'missing'}")
        print(f"Dependency httpx: {'OK' if httpx_available else 'MISSING'}")
        print(f"Dependency bs4: {'OK' if bs4_available else 'MISSING'}")
        print(f"{github_env}: {'set' if github_token_set else 'missing'}")
        print(f"{vercel_env}: {'set' if vercel_token_set else 'missing'}")
        print(f"{netlify_env}: {'set' if netlify_token_set else 'missing'}")
        print(f"{supabase_env}: {'set' if supabase_token_set else 'missing'}")
        print(f"{cloudflare_env}: {'set' if cloudflare_token_set else 'missing'}")
        print(f"Bundled maps: {maps_count}")
        print(f"Map execution: {'ENABLED' if allow_execute else 'disabled'}")
        print(f"Summary: {summary}")
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
            if args.json_output:
                print(json.dumps({"ok": False, "url": args.url, "error": str(error)}))
                return 1
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

        if args.json_output:
            print(json.dumps({
                "ok": True,
                "url": content.get("url", args.url),
                "title": content["title"],
                "headings": content["headings"],
                "text": content["text"],
                "logged": log is not None,
            }))
            return 0

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
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": NOT_INITIALIZED_MESSAGE}))
                return 1
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        action = log.get_action(args.action_id)
        if action is None:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": f"Action not found: {args.action_id}"}))
                return 1
            print(f"Action not found: {args.action_id}")
            return 1
        log.update_action_status(args.action_id, "approved")
        if args.json_output:
            print(json.dumps({"ok": True, "action_id": args.action_id, "status": "approved"}))
            return 0
        print(f"Approved action {args.action_id}.")
        return 0
    if args.command == "reject":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": NOT_INITIALIZED_MESSAGE}))
                return 1
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        action = log.get_action(args.action_id)
        if action is None:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": f"Action not found: {args.action_id}"}))
                return 1
            print(f"Action not found: {args.action_id}")
            return 1
        log.update_action_status(args.action_id, "rejected")
        if args.json_output:
            print(json.dumps({"ok": True, "action_id": args.action_id, "status": "rejected"}))
            return 0
        print(f"Rejected action {args.action_id}.")
        return 0
    if args.command == "execute":
        log = ActionLog.open_existing(root=Path.cwd())
        if log is None:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": NOT_INITIALIZED_MESSAGE}))
                return 1
            print(NOT_INITIALIZED_MESSAGE)
            return 0
        try:
            execute_approved_action(args.action_id, root=Path.cwd())
        except ExecutionError as error:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": str(error)}))
                return 1
            print(str(error))
            return 1
        except Exception as error:
            if args.json_output:
                print(json.dumps({"ok": False, "action_id": args.action_id, "error": f"Execution failed for action {args.action_id}: {error}"}))
                return 1
            print(f"Execution failed for action {args.action_id}: {error}")
            return 1
        if args.json_output:
            print(json.dumps({"ok": True, "action_id": args.action_id, "status": "success"}))
            return 0
        print(f"Executed action {args.action_id}.")
        return 0
    if args.command == "rollback":
        engine = RollbackEngine(root=Path.cwd())
        if args.last:
            if args.json_output:
                last_action = ActionLog(root=Path.cwd()).get_last_action()
                if last_action is None:
                    print(json.dumps({"ok": False, "action_id": None, "error": "No actions recorded yet."}))
                    return 1
                try:
                    engine.rollback(last_action.id)
                    print(json.dumps({"ok": True, "action_id": last_action.id, "status": "rolled_back"}))
                    return 0
                except Exception as error:
                    print(json.dumps({"ok": False, "action_id": last_action.id, "error": str(error)}))
                    return 1
            engine.rollback_last()
            print("Rolled back last action.")
            return 0
        if args.action_id:
            if args.json_output:
                try:
                    engine.rollback(args.action_id)
                    print(json.dumps({"ok": True, "action_id": args.action_id, "status": "rolled_back"}))
                    return 0
                except Exception as error:
                    print(json.dumps({"ok": False, "action_id": args.action_id, "error": str(error)}))
                    return 1
            engine.rollback(args.action_id)
            print(f"Rolled back action {args.action_id}.")
            return 0
        parser.error("rollback requires an action ID or --last")

    if args.command == "cleanup":
        if args.cleanup_command == "snapshots":
            snapshots_dir = project_state_dir(Path.cwd()) / "snapshots"

            if args.json_output:
                if not snapshots_dir.is_dir():
                    print(json.dumps({"ok": True, "snapshots_directory_exists": False, "deleted_count": 0}))
                    return 0
                retention_days = load_config(Path.cwd()).retention.snapshot_days
                deleted = cleanup_snapshots(root=Path.cwd())
                print(json.dumps({"ok": True, "snapshots_directory_exists": True, "deleted_count": deleted, "retention_days": retention_days}))
                return 0

            if not snapshots_dir.is_dir():
                print("No snapshots directory found.")
                return 0
            deleted = cleanup_snapshots(root=Path.cwd())
            print(f"Deleted {deleted} old snapshot(s).")
            return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
