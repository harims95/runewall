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
from runewall.core.rules import audit_policy_config, decision_for_policy, explain_policy, list_policies
from runewall.core.snapshot import cleanup_snapshots
from runewall.translate import read_url


EMPTY_LOG_MESSAGE = "No actions recorded yet."
NOT_INITIALIZED_MESSAGE = "Runewall is not initialized. Run `runewall init` first."
JSON_SCHEMA_DOC_PATH = Path("docs") / "agent-json-schema.md"
REQUIRED_JSON_FIELDS = (
    "ok",
    "error",
    "error_code",
    "executed",
    "policy",
    "decision",
    "policy_source",
    "policy_reason",
)
REQUIRED_JSON_ERROR_CODES = (
    "EXECUTION_DISABLED",
    "MISSING_TOKEN",
    "UNSUPPORTED_EXECUTION",
    "API_ERROR",
    "UNKNOWN_SITE",
    "UNKNOWN_FLOW",
    "INVALID_INPUT",
    "POLICY_BLOCKED",
)
RELEASE_EXAMPLES = (
    "runewall config profile safe",
    "runewall config validate",
    "runewall policy audit",
    "runewall maps lint --strict",
    "runewall doctor",
    "runewall release check",
    "runewall release json-check",
    "python -m pytest tests -v",
)
RELEASE_STATUS_READINESS = {
    "config": "ready",
    "policy": "ready",
    "maps": "ready",
    "json_contract": "ready",
    "doctor": "ready",
    "tests_manual": "python -m pytest tests -v",
}
RELEASE_STATUS_RECOMMENDED_COMMANDS = (
    "runewall release check",
    "runewall release json-check",
    "python -m pytest tests -v",
)
MCP_INITIAL_TOOLS = (
    "runewall.policy_test",
    "runewall.policy_audit",
    "runewall.dry_run",
    "runewall.release_check",
    "runewall.doctor",
    "runewall.maps_list",
    "runewall.maps_show",
)
MCP_LATER_TOOLS = (
    "runewall.execute",
    "runewall.approve",
    "runewall.reject",
    "runewall.rollback",
    "runewall.log",
)
SDK_AVAILABLE_FUNCTIONS = (
    "policy_test",
    "policy_audit",
    "release_check",
    "mcp_status",
    "dry_run",
)
SDK_NOT_EXPOSED_YET = (
    "execute",
    "approve",
    "reject",
    "rollback",
    "log",
)
COMMUNITY_MAPS_SUPPORTED = (
    "validate_local_map_files",
    "inspect_safety_posture",
)
COMMUNITY_MAPS_NOT_SUPPORTED_YET = (
    "remote_registry",
    "map_downloads",
    "signed_map_verification",
    "community_map_execution",
    "automatic_installation",
)
MCP_SUPPORTED_METHODS = ("initialize", "tools/list", "tools/call")
MCP_NOT_SUPPORTED_YET = (
    "runewall.execute",
    "runewall.approve",
    "runewall.reject",
    "runewall.rollback",
    "runewall.log",
    "http_server",
    "hosted_backend",
)
MCP_TOOL_DEFINITIONS = (
    {
        "name": "runewall.policy_test",
        "description": "Explain the policy decision for a Runewall action type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string"},
            },
            "required": ["action_type"],
        },
    },
    {
        "name": "runewall.policy_audit",
        "description": "Audit current Runewall policy and config safety posture.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "runewall.dry_run",
        "description": "Preview a Runewall action without calling external APIs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "site": {"type": "string"},
                "flow": {"type": "string"},
                "inputs": {"type": "object"},
            },
            "required": ["site", "flow"],
        },
    },
    {
        "name": "runewall.release_check",
        "description": "Run local release readiness checks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "runewall.doctor",
        "description": "Run local Runewall health checks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "runewall.maps_list",
        "description": "List available Runewall action maps.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "runewall.maps_show",
        "description": "Show details for a Runewall action map.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "site": {"type": "string"},
                "flow": {"type": "string"},
            },
            "required": ["site", "flow"],
        },
    },
)
RUNEWALL_VERSION = "0.4.0"


def _policy_audit_report(root: Path) -> dict[str, object]:
    raw_config = load_config_data(root)
    errors = validate_config_data(raw_config)
    if errors:
        return {"ok": False, "level": "INVALID", "warnings": [], "errors": errors}
    warnings = audit_policy_config(load_config(root))
    return {
        "ok": not warnings,
        "level": "OK" if not warnings else "WARN",
        "warnings": [{"key": warning.key, "message": warning.message} for warning in warnings],
    }


def _config_check_report(root: Path) -> dict[str, object]:
    errors = validate_config_data(load_config_data(root))
    return {"level": "OK" if not errors else "INVALID", "errors": errors}


def _maps_lint_report() -> dict[str, object]:
    registry = SiteMapRegistry()
    validation_results = registry.validate_bundled_maps()
    lint_errors: list[dict[str, str]] = []
    lint_warnings: list[dict[str, str]] = []

    for result in validation_results:
        if not result.ok and result.error is not None:
            lint_errors.append({"key": result.site_key, "message": result.error})

    for site_map in registry.list_maps():
        key = site_map.raw.get("_filename", "").removesuffix(".json")
        warnings, errors = lint_map(site_map)
        lint_warnings.extend({"key": key, "message": warning} for warning in warnings)
        lint_errors.extend({"key": key, "message": error} for error in errors)

    return {
        "level": "OK" if not lint_errors and not lint_warnings else "FAIL",
        "errors": lint_errors,
        "warnings": lint_warnings,
    }


def _doctor_basics_report(root: Path) -> dict[str, object]:
    warnings: list[dict[str, str]] = []

    if not database_path(root).exists():
        warnings.append({"key": "database", "message": "Runewall DB is missing"})
    if not config_path(root).exists():
        warnings.append({"key": "config", "message": "config file is missing"})
    if importlib.util.find_spec("httpx") is None:
        warnings.append({"key": "dependencies.httpx", "message": "httpx is missing"})
    if importlib.util.find_spec("bs4") is None:
        warnings.append({"key": "dependencies.bs4", "message": "bs4 is missing"})
    maps_count = len(SiteMapRegistry().list_maps())
    if maps_count <= 0:
        warnings.append({"key": "maps", "message": "no bundled maps found"})

    return {"level": "OK" if not warnings else "WARN", "warnings": warnings}


def _release_check_report(root: Path) -> dict[str, object]:
    config_check = _config_check_report(root)
    policy_audit = _policy_audit_report(root)
    maps_lint = _maps_lint_report()
    doctor_basics = _doctor_basics_report(root)

    if config_check["level"] != "OK" or policy_audit["level"] == "INVALID":
        level = "FAIL"
    elif maps_lint["level"] != "OK":
        level = "FAIL"
    elif policy_audit["level"] == "WARN" or doctor_basics["level"] == "WARN":
        level = "WARN"
    else:
        level = "OK"

    return {
        "ok": level == "OK",
        "level": level,
        "checks": {
            "config": config_check,
            "policy_audit": policy_audit,
            "maps_lint": maps_lint,
            "doctor_basics": doctor_basics,
        },
    }


def _release_json_check_report(root: Path) -> dict[str, object]:
    doc_path = root / JSON_SCHEMA_DOC_PATH
    report = {
        "ok": True,
        "level": "OK",
        "missing_fields": [],
        "missing_error_codes": [],
        "path": JSON_SCHEMA_DOC_PATH.as_posix(),
    }

    if not doc_path.exists():
        report["ok"] = False
        report["level"] = "WARN"
        report["message"] = f"{JSON_SCHEMA_DOC_PATH.as_posix()} is missing."
        return report

    doc_text = doc_path.read_text(encoding="utf-8")
    missing_fields = [field for field in REQUIRED_JSON_FIELDS if field not in doc_text]
    missing_error_codes = [code for code in REQUIRED_JSON_ERROR_CODES if code not in doc_text]

    if missing_fields or missing_error_codes:
        report["ok"] = False
        report["level"] = "WARN"
        report["missing_fields"] = missing_fields
        report["missing_error_codes"] = missing_error_codes

    return report


def _jsonrpc_response(message_id: object, *, result: dict[str, object] | None = None, error: dict[str, object] | None = None) -> dict[str, object]:
    response: dict[str, object] = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result if result is not None else {}
    return response


def _policy_test_result(action_type: str, root: Path) -> dict[str, object]:
    explanation = explain_policy(action_type, load_config(root))
    decision = decision_for_policy(explanation.policy)
    return {
        "ok": True,
        "action_type": explanation.action_type,
        "policy": explanation.policy_name,
        "decision": decision,
        "source": explanation.source,
        "reason": explanation.reason,
    }


def _policy_audit_result(root: Path) -> dict[str, object]:
    return _policy_audit_report(root)


def _release_check_result(root: Path) -> dict[str, object]:
    return _release_check_report(root)


def _doctor_result(root: Path) -> dict[str, object]:
    db_exists = database_path(root).exists()
    httpx_available = importlib.util.find_spec("httpx") is not None
    bs4_available = importlib.util.find_spec("bs4") is not None
    maps_count = len(SiteMapRegistry().list_maps())
    config_exists = config_path(root).exists()
    cfg = load_config(root)
    policy_audit = _policy_audit_result(root)
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

    if not httpx_available or not bs4_available or policy_audit["level"] == "INVALID":
        summary = "FAIL"
    elif not db_exists or not github_token_set or not vercel_token_set or not netlify_token_set or not supabase_token_set or not cloudflare_token_set or allow_execute or policy_audit["level"] == "WARN":
        summary = "WARN"
    else:
        summary = "OK"

    return {
        "python": {"version": sys.version.split()[0], "ok": True},
        "database": {"present": db_exists, "path": str(database_path(root))},
        "config": {
            "present": config_exists,
            "path": str(config_path(root).resolve()),
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
        "policy_audit": policy_audit,
        "summary": summary,
    }


def _mcp_status_result() -> dict[str, object]:
    return {
        "ok": True,
        "mcp": {
            "mode": "stdio",
            "methods": list(MCP_SUPPORTED_METHODS),
            "supported_tools": list(MCP_INITIAL_TOOLS),
            "not_supported_yet": list(MCP_NOT_SUPPORTED_YET),
            "safety": {
                "local_only": True,
                "dry_run_external_api_calls": False,
                "token_storage": False,
                "token_printing": False,
                "execute_exposed": False,
            },
        },
    }


def _sdk_status_result() -> dict[str, object]:
    return {
        "ok": True,
        "sdk": {
            "status": "preview",
            "available_functions": list(SDK_AVAILABLE_FUNCTIONS),
            "not_exposed_yet": list(SDK_NOT_EXPOSED_YET),
            "safety": {
                "local_only": True,
                "dry_run_external_api_calls": False,
                "token_storage": False,
                "token_printing": False,
                "execute_exposed": False,
            },
        },
    }


def _community_maps_status_result() -> dict[str, object]:
    return {
        "ok": True,
        "community_maps": {
            "mode": "local-files-only",
            "supported": list(COMMUNITY_MAPS_SUPPORTED),
            "not_supported_yet": list(COMMUNITY_MAPS_NOT_SUPPORTED_YET),
            "safety": {
                "dry_run_first": True,
                "secrets_in_map_files": False,
                "tokens_from_env_only": True,
                "execute_enabled_for_community_maps": False,
            },
        },
    }


def _community_maps_human_label(value: str) -> str:
    return value.replace("_", " ")


def _maps_list_result(*, category: str | None = None, tag: str | None = None) -> dict[str, object]:
    site_maps = SiteMapRegistry().list_maps()
    if category:
        site_maps = [m for m in site_maps if m.category == category]
    if tag:
        site_maps = [m for m in site_maps if tag in m.tags]
    return {
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
    }


def _maps_show_result(site: str, *, flow: str | None = None) -> dict[str, object] | None:
    site_map = SiteMapRegistry().load_site(site)
    if site_map is None:
        return None

    flows_json = []
    flow_items = [(flow, site_map.flows.get(flow))] if flow is not None else list(site_map.flows.items())
    for flow_name, flow_data in flow_items:
        if flow_data is None:
            return None
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

    return {
        "key": site_map.raw.get("_filename", "").removesuffix(".json"),
        "site_name": site_map.site_name,
        "base_url": site_map.base_url,
        "map_version": site_map.map_version,
        "schema_version": site_map.schema_version,
        "category": site_map.category,
        "tags": site_map.tags,
        "flows": flows_json,
    }


def _dry_run_mcp_result(site: str, flow: str, inputs: dict[str, object], root: Path) -> dict[str, object] | None:
    planner = DryRunPlanner()
    normalized_inputs = {str(key): str(value) for key, value in inputs.items()}
    try:
        plan = planner.build_plan(site, flow, normalized_inputs)
    except (SiteMapNotFoundError, FlowNotFoundError):
        return None

    policy_explanation = explain_policy("map.dry_run", load_config(root))
    policy_decision = decision_for_policy(policy_explanation.policy)
    return {
        "ok": True,
        "dry_run": True,
        "executed": False,
        "site": site,
        "flow": flow,
        "description": plan.description,
        "risk_level": plan.risk_level,
        "reversible": plan.reversible,
        "requires_auth": plan.requires_auth,
        "provided_inputs": plan.provided_inputs,
        "missing_inputs": plan.missing_inputs,
        "api_path": plan.api_path,
        "ui_steps_count": plan.ui_steps_count,
        "policy": policy_explanation.policy_name,
        "decision": policy_decision,
        "policy_source": policy_explanation.source,
        "policy_reason": policy_explanation.reason,
        "action_preview": dry_run_result(plan),
    }


def _mcp_once_response(raw_message: str) -> dict[str, object]:
    try:
        request = json.loads(raw_message)
    except json.JSONDecodeError:
        return _jsonrpc_response(None, error={"code": -32700, "message": "Parse error"})

    if not isinstance(request, dict) or not isinstance(request.get("method"), str):
        return _jsonrpc_response(request.get("id") if isinstance(request, dict) else None, error={"code": -32600, "message": "Invalid Request"})

    message_id = request.get("id")
    method = request["method"]

    if method == "initialize":
        return _jsonrpc_response(
            message_id,
            result={
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "runewall",
                    "version": RUNEWALL_VERSION,
                },
                "capabilities": {
                    "tools": {},
                },
            },
        )
    if method == "tools/list":
        return _jsonrpc_response(message_id, result={"tools": list(MCP_TOOL_DEFINITIONS)})
    if method == "tools/call":
        params = request.get("params")
        if not isinstance(params, dict):
            return _jsonrpc_response(message_id, error={"code": -32602, "message": "Unknown tool"})
        tool_name = params.get("name")
        if tool_name == "runewall.policy_test":
            arguments = params.get("arguments")
            if not isinstance(arguments, dict) or not isinstance(arguments.get("action_type"), str):
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Missing required argument: action_type"})
            tool_result = _policy_test_result(arguments["action_type"], Path.cwd())
        elif tool_name == "runewall.policy_audit":
            tool_result = _policy_audit_result(Path.cwd())
        elif tool_name == "runewall.release_check":
            tool_result = _release_check_result(Path.cwd())
        elif tool_name == "runewall.doctor":
            tool_result = _doctor_result(Path.cwd())
        elif tool_name == "runewall.maps_list":
            tool_result = _maps_list_result()
        elif tool_name == "runewall.maps_show":
            arguments = params.get("arguments")
            if not isinstance(arguments, dict) or not isinstance(arguments.get("site"), str):
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Missing required argument: site"})
            if not isinstance(arguments.get("flow"), str):
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Missing required argument: flow"})
            tool_result = _maps_show_result(arguments["site"], flow=arguments["flow"])
            if tool_result is None:
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Map not found"})
        elif tool_name == "runewall.dry_run":
            arguments = params.get("arguments")
            if not isinstance(arguments, dict) or not isinstance(arguments.get("site"), str):
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Missing required argument: site"})
            if not isinstance(arguments.get("flow"), str):
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Missing required argument: flow"})
            inputs = arguments.get("inputs", {})
            if not isinstance(inputs, dict):
                inputs = {}
            tool_result = _dry_run_mcp_result(arguments["site"], arguments["flow"], inputs, Path.cwd())
            if tool_result is None:
                return _jsonrpc_response(message_id, error={"code": -32602, "message": "Map not found"})
        else:
            return _jsonrpc_response(message_id, error={"code": -32602, "message": "Unknown tool"})
        return _jsonrpc_response(
            message_id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result),
                    }
                ],
                "isError": False,
            },
        )
    return _jsonrpc_response(message_id, error={"code": -32601, "message": "Method not found"})


def _mcp_serve_stream(input_stream: object, output_stream: object) -> None:
    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue
        output_stream.write(json.dumps(_mcp_once_response(line), separators=(",", ":")))
        output_stream.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="runewall",
        description="Runewall is a local-first safety/runtime layer for AI agents.",
        epilog=(
            "Major commands:\n"
            "  init     initialize local Runewall state\n"
            "  status   show local runtime status\n"
            "  log      show action log\n"
            "  act      dry-run or execute mapped actions\n"
            "  maps     inspect bundled action maps\n"
            "  sdk      inspect Python SDK preview surface\n"
            "  config   inspect and manage local config\n"
            "  mcp      inspect planned MCP tool surface\n"
            "  policy   explain, test, list, and audit safety policies\n"
            "  doctor   check local runtime health\n"
            "  release  run release readiness checks\n"
            "  read     read a URL through Runewall\n"
            "  cleanup  clean old local artifacts"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    init_parser = subcommands.add_parser(
        "init",
        help="Initialize local Runewall state.",
        description="Initialize local Runewall state in the current directory.",
    )
    init_parser.add_argument("--json", action="store_true", dest="json_output")
    log_parser = subcommands.add_parser("log", help="Show action log.", description="Show the local Runewall action log.")
    log_parser.add_argument("--json", action="store_true", dest="json_output")
    act_parser = subcommands.add_parser(
        "act",
        help="Dry-run or execute mapped actions.",
        description="Dry-run or execute a mapped action flow.",
        epilog=(
            "Examples:\n"
            "  runewall act github create_issue --dry-run --input repo=user/repo --input title=\"Bug\"\n"
            "  runewall act vercel list_projects --execute --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    act_parser.add_argument("site")
    act_parser.add_argument("flow")
    act_parser.add_argument("--dry-run", action="store_true")
    act_parser.add_argument("--execute", action="store_true")
    act_parser.add_argument("--input", action="append", default=[])
    act_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_parser = subcommands.add_parser(
        "maps",
        help="Inspect bundled action maps.",
        description="Inspect bundled action maps.",
        epilog=(
            "Examples:\n"
            "  runewall maps list\n"
            "  runewall maps lint --strict\n"
            "  runewall maps show github --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
    maps_community_parser = maps_subcommands.add_parser("community", help="Inspect local community map foundation.")
    maps_community_subcommands = maps_community_parser.add_subparsers(dest="maps_community_command", required=True)
    maps_community_status_parser = maps_community_subcommands.add_parser("status", help="Show community maps status.")
    maps_community_status_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_community_list_parser = maps_community_subcommands.add_parser("list", help="List imported local community maps.")
    maps_community_list_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_community_import_parser = maps_community_subcommands.add_parser("import", help="Validate and copy a local community map file.")
    maps_community_import_parser.add_argument("path")
    maps_community_import_parser.add_argument("--json", action="store_true", dest="json_output")
    maps_community_validate_parser = maps_community_subcommands.add_parser("validate", help="Validate a local community map file.")
    maps_community_validate_parser.add_argument("path")
    maps_community_validate_parser.add_argument("--json", action="store_true", dest="json_output")
    sdk_parser = subcommands.add_parser(
        "sdk",
        help="Inspect Python SDK preview surface.",
        description="Inspect the local Runewall Python SDK preview surface.",
    )
    sdk_subcommands = sdk_parser.add_subparsers(dest="sdk_command", required=True)
    sdk_status_parser = sdk_subcommands.add_parser("status", help="Show Python SDK preview status.")
    sdk_status_parser.add_argument("--json", action="store_true", dest="json_output")
    config_parser = subcommands.add_parser(
        "config",
        help="Inspect and manage local config.",
        description="Inspect and manage local Runewall config.",
        epilog=(
            "Examples:\n"
            "  runewall config show\n"
            "  runewall config set maps.allow_execute true\n"
            "  runewall config validate"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
    mcp_parser = subcommands.add_parser(
        "mcp",
        help="Inspect planned MCP tool surface.",
        description="Inspect planned Runewall MCP tool surface.",
    )
    mcp_subcommands = mcp_parser.add_subparsers(dest="mcp_command", required=True)
    mcp_tools_parser = mcp_subcommands.add_parser("tools", help="List planned MCP tools.")
    mcp_tools_parser.add_argument("--json", action="store_true", dest="json_output")
    mcp_status_parser = mcp_subcommands.add_parser("status", help="Show MCP readiness and supported tool surface.")
    mcp_status_parser.add_argument("--json", action="store_true", dest="json_output")
    mcp_serve_parser = mcp_subcommands.add_parser("serve", help="Run a local MCP stdio skeleton.")
    mcp_serve_parser.add_argument("--once", action="store_true")
    policy_parser = subcommands.add_parser(
        "policy",
        help="Explain, test, list, and audit safety policies.",
        description="Explain, test, list, and audit Runewall safety policies.",
        epilog=(
            "Examples:\n"
            "  runewall policy explain file.write\n"
            "  runewall policy test map.execute --json\n"
            "  runewall policy audit"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    policy_subcommands = policy_parser.add_subparsers(dest="policy_command", required=True)
    policy_explain_parser = policy_subcommands.add_parser("explain", help="Explain which policy applies to an action type.")
    policy_explain_parser.add_argument("action_type")
    policy_explain_parser.add_argument("--json", action="store_true", dest="json_output")
    policy_list_parser = policy_subcommands.add_parser("list", help="List effective policies for standard action types.")
    policy_list_parser.add_argument("--json", action="store_true", dest="json_output")
    policy_test_parser = policy_subcommands.add_parser("test", help="Show the effective policy decision for an action type.")
    policy_test_parser.add_argument("action_type")
    policy_test_parser.add_argument("--json", action="store_true", dest="json_output")
    policy_audit_parser = policy_subcommands.add_parser("audit", help="Audit the current config for risky policy settings.")
    policy_audit_parser.add_argument("--json", action="store_true", dest="json_output")
    version_parser = subcommands.add_parser("version", help="Print Runewall version.")
    version_parser.add_argument("--json", action="store_true", dest="json_output")
    doctor_parser = subcommands.add_parser(
        "doctor",
        help="Check local runtime health.",
        description="Check local Runewall runtime health.",
        epilog=(
            "Examples:\n"
            "  runewall doctor\n"
            "  runewall doctor --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    doctor_parser.add_argument("--json", action="store_true", dest="json_output")
    pending_parser = subcommands.add_parser("pending", help="Show pending actions.")
    pending_parser.add_argument("--json", action="store_true", dest="json_output")
    read_parser = subcommands.add_parser("read", help="Read a URL through Runewall.", description="Read a URL through Runewall without a browser.")
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
    cleanup_parser = subcommands.add_parser("cleanup", help="Clean old local artifacts.", description="Clean old local Runewall artifacts.")
    cleanup_subcommands = cleanup_parser.add_subparsers(dest="cleanup_command", required=True)
    cleanup_snapshots_parser = cleanup_subcommands.add_parser("snapshots", help="Delete snapshot directories older than retention period.")
    cleanup_snapshots_parser.add_argument("--json", action="store_true", dest="json_output")
    release_parser = subcommands.add_parser(
        "release",
        help="Run release readiness checks.",
        description="Run local release readiness checks.",
        epilog=(
            "Examples:\n"
            "  runewall release check\n"
            "  runewall release check --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    release_subcommands = release_parser.add_subparsers(dest="release_command", required=True)
    release_check_parser = release_subcommands.add_parser("check", help="Check whether the local project is ready for a safe release checkpoint.")
    release_check_parser.add_argument("--json", action="store_true", dest="json_output")
    release_json_check_parser = release_subcommands.add_parser("json-check", help="Check whether the agent-facing JSON contract docs are complete.")
    release_json_check_parser.add_argument("--json", action="store_true", dest="json_output")
    release_examples_parser = release_subcommands.add_parser("examples", help="Show curated safe release example commands.")
    release_examples_parser.add_argument("--json", action="store_true", dest="json_output")
    release_status_parser = release_subcommands.add_parser("status", help="Show a simple release readiness summary.")
    release_status_parser.add_argument("--json", action="store_true", dest="json_output")
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
    if args.command == "mcp":
        if args.mcp_command == "tools":
            if args.json_output:
                print(json.dumps({
                    "ok": True,
                    "initial_tools": list(MCP_INITIAL_TOOLS),
                    "later_tools": list(MCP_LATER_TOOLS),
                }))
                return 0
            print("MCP tools")
            print("")
            print("Initial:")
            for tool in MCP_INITIAL_TOOLS:
                print(f"- {tool}")
            print("")
            print("Later:")
            for tool in MCP_LATER_TOOLS:
                print(f"- {tool}")
            return 0
        if args.mcp_command == "status":
            result = _mcp_status_result()
            if args.json_output:
                print(json.dumps(result))
                return 0
            print("MCP status")
            print("")
            print("Mode:")
            print("")
            print("* continuous stdio serve supported")
            print("* stdio --once supported")
            print("")
            print("Supported methods:")
            print("")
            for method in result["mcp"]["methods"]:
                print(f"* {method}")
            print("")
            print("Supported tools:")
            print("")
            for tool in result["mcp"]["supported_tools"]:
                print(f"* {tool}")
            print("")
            print("Not supported yet:")
            print("")
            for item in result["mcp"]["not_supported_yet"]:
                print(f"* {item}")
            print("")
            print("Safety:")
            print("")
            print("* local-only")
            print("* dry-run does not call external APIs")
            print("* no token storage")
            print("* no token printing")
            print("* execute not exposed through MCP")
            return 0
        if args.mcp_command == "serve":
            if args.once:
                print(json.dumps(_mcp_once_response(sys.stdin.read())))
                return 0
            _mcp_serve_stream(sys.stdin, sys.stdout)
            return 0
    if args.command == "sdk":
        if args.sdk_command == "status":
            result = _sdk_status_result()
            if args.json_output:
                print(json.dumps(result))
                return 0
            print("Python SDK status")
            print("")
            print("Available functions:")
            print("")
            for function_name in result["sdk"]["available_functions"]:
                print(f"* {function_name}")
            print("")
            print("Not exposed yet:")
            print("")
            for function_name in result["sdk"]["not_exposed_yet"]:
                print(f"* {function_name}")
            print("")
            print("Safety:")
            print("")
            print("* local-only")
            print("* dry_run does not call external APIs")
            print("* no token storage")
            print("* no token printing")
            print("* execute not exposed")
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
    if args.command == "policy":
        if args.policy_command == "audit":
            audit = _policy_audit_result(Path.cwd())
            if audit["level"] == "INVALID":
                if args.json_output:
                    print(json.dumps(audit))
                    return 1
                print("Policy audit: INVALID")
                for error in audit["errors"]:
                    print(f"- {error['key']} {error['message']}")
                return 1
            if args.json_output:
                print(json.dumps(audit))
                return 0 if audit["ok"] else 1
            if audit["level"] == "OK":
                print("Policy audit: OK")
                print("No risky policy settings found.")
                return 0
            print("Policy audit: WARN")
            for warning in audit["warnings"]:
                print(f"- {warning['key']} is true; {warning['message']}." if warning["key"] == "maps.allow_execute" else f"- {warning['key']} is auto; {warning['message']}.")
            return 1
        if args.policy_command == "explain":
            explanation = explain_policy(args.action_type, load_config(Path.cwd()))
            if args.json_output:
                print(json.dumps({
                    "ok": True,
                    "action_type": explanation.action_type,
                    "policy": explanation.policy_name,
                    "source": explanation.source,
                    "reason": explanation.reason,
                }))
                return 0
            print(f"Action: {explanation.action_type}")
            print(f"Policy: {explanation.policy_name}")
            print(f"Source: {explanation.source_label}")
            print(f"Reason: {explanation.reason}")
            return 0
        if args.policy_command == "list":
            policies = list_policies(load_config(Path.cwd()))
            if args.json_output:
                print(json.dumps({
                    "ok": True,
                    "policies": {
                        action_type: {
                            "policy": explanation.policy_name,
                            "source": explanation.source,
                            "reason": explanation.reason,
                        }
                        for action_type, explanation in policies.items()
                    },
                }))
                return 0
            print("Policy rules")
            for action_type, explanation in policies.items():
                print(f"{action_type}: {explanation.policy_name}")
            return 0
        if args.policy_command == "test":
            explanation = explain_policy(args.action_type, load_config(Path.cwd()))
            decision = decision_for_policy(explanation.policy)
            if args.json_output:
                print(json.dumps(_policy_test_result(args.action_type, Path.cwd())))
                return 0
            print(f"Action: {explanation.action_type}")
            print(f"Policy: {explanation.policy_name}")
            print(f"Decision: {decision}")
            print(f"Source: {explanation.source_label}")
            print(f"Reason: {explanation.reason}")
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
        policy_explanation = explain_policy("map.dry_run", load_config(Path.cwd()))
        policy_decision = decision_for_policy(policy_explanation.policy)

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
                "policy": policy_explanation.policy_name,
                "decision": policy_decision,
                "policy_source": policy_explanation.source,
                "policy_reason": policy_explanation.reason,
            }))
            return 0

        if args.dry_run:
            print(render_plan(plan))
            print(f"Policy: {policy_explanation.policy_name}")
            print(f"Decision: {policy_decision}")
            print(f"Source: {policy_explanation.source_label}")
            print(f"Reason: {policy_explanation.reason}")
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

        execute_policy_explanation = explain_policy("map.execute", load_config(Path.cwd()))
        execute_policy_decision = decision_for_policy(execute_policy_explanation.policy)
        if execute_policy_decision == "blocked":
            error_message = "Execution blocked by policy for map.execute."
            if log is not None:
                log.add_action(
                    Action(
                        action_type="map.execute",
                        target=f"{args.site}:{args.flow}",
                        status="failed",
                        params={"site": args.site, "flow": args.flow, "inputs": inputs},
                        result={"error": error_message},
                        reversible=False,
                    )
                )
            if args.json_output:
                print(json.dumps({
                    "ok": False,
                    "executed": False,
                    "site": args.site,
                    "flow": args.flow,
                    "error": error_message,
                    "error_code": "POLICY_BLOCKED",
                    "policy": execute_policy_explanation.policy_name,
                    "decision": execute_policy_decision,
                    "policy_source": execute_policy_explanation.source,
                    "policy_reason": execute_policy_explanation.reason,
                }))
                return 1
            print("Map execution blocked by policy: map.execute")
            return 1

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
                print(json.dumps({
                    "ok": False,
                    "executed": False,
                    "site": args.site,
                    "flow": args.flow,
                    "error": str(error),
                    "error_code": getattr(error, "error_code", "UNKNOWN_ERROR"),
                    "policy": execute_policy_explanation.policy_name,
                    "decision": execute_policy_decision,
                    "policy_source": execute_policy_explanation.source,
                    "policy_reason": execute_policy_explanation.reason,
                }))
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
            print(json.dumps({
                "ok": True,
                "executed": True,
                "site": args.site,
                "flow": args.flow,
                "result": result,
                "policy": execute_policy_explanation.policy_name,
                "decision": execute_policy_decision,
                "policy_source": execute_policy_explanation.source,
                "policy_reason": execute_policy_explanation.reason,
            }))
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
        if args.maps_command == "community":
            if args.maps_community_command == "status":
                result = _community_maps_status_result()
                if args.json_output:
                    print(json.dumps(result))
                    return 0
                print("Community maps status")
                print("")
                print("Mode:")
                print("")
                print("* local files only")
                print("")
                print("Supported:")
                print("")
                for item in result["community_maps"]["supported"]:
                    print(f"* {_community_maps_human_label(item)}")
                print("")
                print("Not supported yet:")
                print("")
                for item in result["community_maps"]["not_supported_yet"]:
                    print(f"* {_community_maps_human_label(item)}")
                print("")
                print("Safety:")
                print("")
                print("* dry-run first")
                print("* no secrets in map files")
                print("* tokens from env vars only")
                print("* execute disabled for community maps")
                return 0
            if args.maps_community_command == "validate":
                report = registry.validate_community_map_file(Path(args.path))
                if args.json_output:
                    print(json.dumps({
                        "ok": report.ok,
                        "path": report.path,
                        "errors": report.errors,
                        "warnings": report.warnings,
                    }))
                    return 0 if report.ok else 1
                print("Community map validation: OK" if report.ok else "Community map validation: FAILED")
                for error in report.errors:
                    print(f"* {error}")
                for warning in report.warnings:
                    print(f"* {warning}")
                return 0 if report.ok else 1
            if args.maps_community_command == "import":
                report = registry.import_community_map_file(Path(args.path), Path.cwd())
                if args.json_output:
                    payload = {
                        "ok": report.ok,
                        "source": report.source,
                        "validated": report.validated,
                        "execute_enabled": report.execute_enabled,
                    }
                    if report.ok:
                        payload["destination"] = report.destination
                    else:
                        payload["errors"] = report.errors
                    print(json.dumps(payload))
                    return 0 if report.ok else 1
                print("Community map import: OK" if report.ok else "Community map import: FAILED")
                if report.ok:
                    print(f"Imported to: {report.destination}")
                else:
                    for error in report.errors:
                        print(f"- {error}")
                return 0 if report.ok else 1
            if args.maps_community_command == "list":
                community_maps = [path.name for path in registry.list_community_map_files(Path.cwd())]
                if args.json_output:
                    print(json.dumps({"ok": True, "community_maps": community_maps}))
                    return 0
                print("Community maps")
                if not community_maps:
                    print("No community maps imported.")
                    return 0
                for name in community_maps:
                    print(f"- {name}")
                return 0
        if args.maps_command == "list":
            site_maps = registry.list_maps()
            if args.category:
                site_maps = [m for m in site_maps if m.category == args.category]
            if args.tag:
                site_maps = [m for m in site_maps if args.tag in m.tags]

            if args.json_output:
                print(json.dumps(_maps_list_result(category=args.category, tag=args.tag)))
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
                print(json.dumps(_maps_show_result(args.site)))
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
        ver = RUNEWALL_VERSION
        if args.json_output:
            print(json.dumps({"name": "runewall", "version": ver}))
            return 0
        print(f"Runewall {ver}")
        return 0
    if args.command == "doctor":
        report = _doctor_result(Path.cwd())
        cfg = load_config(Path.cwd())
        policy_audit = report["policy_audit"]
        allow_execute = cfg.maps.allow_execute

        github_env = cfg.auth.github_token_env
        vercel_env = cfg.auth.vercel_token_env
        netlify_env = cfg.auth.netlify_token_env
        supabase_env = cfg.auth.supabase_access_token_env
        cloudflare_env = cfg.auth.cloudflare_api_token_env

        github_token_set = report["auth"]["github"]["status"] == "present"
        vercel_token_set = report["auth"]["vercel"]["status"] == "present"
        netlify_token_set = report["auth"]["netlify"]["status"] == "present"
        supabase_token_set = report["auth"]["supabase"]["status"] == "present"
        cloudflare_token_set = report["auth"]["cloudflare"]["status"] == "present"
        db_exists = report["database"]["present"]
        config_exists = report["config"]["present"]
        httpx_available = report["dependencies"]["httpx"]
        bs4_available = report["dependencies"]["bs4"]
        maps_count = report["maps"]["bundled_count"]
        summary = report["summary"]

        if args.json_output:
            print(json.dumps(report))
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
        print(f"Policy audit: {policy_audit['level']}")
        if policy_audit["level"] == "WARN":
            for warning in policy_audit["warnings"]:
                print(f"- {warning['key']} is true; {warning['message']}." if warning["key"] == "maps.allow_execute" else f"- {warning['key']} is auto; {warning['message']}.")
        if policy_audit["level"] == "INVALID":
            for error in policy_audit["errors"]:
                print(f"- {error['key']}: {error['message']}")
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

    if args.command == "release":
        if args.release_command == "check":
            report = _release_check_result(Path.cwd())
            if args.json_output:
                print(json.dumps(report))
                return 0 if report["ok"] else 1

            print(f"Release check: {report['level']}")
            print(f"Config: {report['checks']['config']['level']}")
            if report["checks"]["config"]["level"] != "OK":
                for error in report["checks"]["config"]["errors"]:
                    print(f"- {error['key']}: {error['message']}")

            print(f"Policy audit: {report['checks']['policy_audit']['level']}")
            for warning in report["checks"]["policy_audit"]["warnings"]:
                print(f"- {warning['key']} is true; {warning['message']}." if warning["key"] == "maps.allow_execute" else f"- {warning['key']} is auto; {warning['message']}.")
            if report["checks"]["policy_audit"]["level"] == "INVALID":
                for error in report["checks"]["policy_audit"]["errors"]:
                    print(f"- {error['key']}: {error['message']}")

            print(f"Maps strict lint: {report['checks']['maps_lint']['level']}")
            for warning in report["checks"]["maps_lint"]["warnings"]:
                print(f"- {warning['key']}: {warning['message']}")
            for error in report["checks"]["maps_lint"]["errors"]:
                print(f"- {error['key']}: {error['message']}")

            print(f"Doctor basics: {report['checks']['doctor_basics']['level']}")
            for warning in report["checks"]["doctor_basics"]["warnings"]:
                print(f"- {warning['message']}")

            return 0 if report["ok"] else 1
        if args.release_command == "json-check":
            report = _release_json_check_report(Path.cwd())
            if args.json_output:
                print(json.dumps(report))
                return 0 if report["ok"] else 1

            print(f"JSON contract check: {report['level']}")
            if report["ok"]:
                print("docs/agent-json-schema.md includes required agent JSON fields and error codes.")
                return 0
            if "message" in report:
                print(f"- {report['message']}")
            for field in report["missing_fields"]:
                print(f"- docs/agent-json-schema.md is missing required field: {field}")
            for code in report["missing_error_codes"]:
                print(f"- docs/agent-json-schema.md is missing stable error code: {code}")
            return 1
        if args.release_command == "examples":
            if args.json_output:
                print(json.dumps({"ok": True, "examples": list(RELEASE_EXAMPLES)}))
                return 0
            print("Release examples")
            for example in RELEASE_EXAMPLES:
                print(f"- {example}")
            return 0
        if args.release_command == "status":
            report = {
                "ok": True,
                "readiness": RELEASE_STATUS_READINESS,
                "recommended_commands": list(RELEASE_STATUS_RECOMMENDED_COMMANDS),
            }
            if args.json_output:
                print(json.dumps(report))
                return 0
            print("Release status")
            print("Config: ready")
            print("Policy: ready")
            print("Maps: ready")
            print("JSON contract: ready")
            print("Doctor: ready")
            print("Tests: run manually with python -m pytest tests -v")
            print("")
            print("Recommended final check:")
            for command in RELEASE_STATUS_RECOMMENDED_COMMANDS:
                print(command)
            return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
