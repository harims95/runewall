from __future__ import annotations

from pathlib import Path

from runewall.cli.main import (
    _dry_run_mcp_result,
    _mcp_status_result,
    _policy_audit_result,
    _policy_test_result,
    _release_check_result,
)

__all__ = ["policy_test", "policy_audit", "release_check", "mcp_status", "dry_run"]


def _error_result(message: str, error_code: str) -> dict[str, object]:
    return {"ok": False, "error": message, "error_code": error_code}


def policy_test(action_type: str) -> dict[str, object]:
    if not isinstance(action_type, str) or not action_type.strip():
        return _error_result("action_type is required", "missing_action_type")
    try:
        return _policy_test_result(action_type, Path.cwd())
    except Exception as exc:
        return _error_result(str(exc), "sdk_internal_error")


def policy_audit() -> dict[str, object]:
    try:
        return _policy_audit_result(Path.cwd())
    except Exception as exc:
        return _error_result(str(exc), "sdk_internal_error")


def release_check() -> dict[str, object]:
    try:
        return _release_check_result(Path.cwd())
    except Exception as exc:
        return _error_result(str(exc), "sdk_internal_error")


def mcp_status() -> dict[str, object]:
    try:
        return _mcp_status_result()
    except Exception as exc:
        return _error_result(str(exc), "sdk_internal_error")


def dry_run(site: str, flow: str, inputs: dict | None = None) -> dict[str, object]:
    if not isinstance(site, str) or not site.strip():
        return _error_result("site is required", "missing_site")
    if not isinstance(flow, str) or not flow.strip():
        return _error_result("flow is required", "missing_flow")
    if inputs is None:
        inputs = {}
    if not isinstance(inputs, dict):
        return _error_result("inputs must be a dict", "invalid_inputs")

    try:
        result = _dry_run_mcp_result(site, flow, inputs, Path.cwd())
    except Exception as exc:
        return _error_result(str(exc), "sdk_internal_error")
    if result is None:
        return _error_result("Map not found", "map_not_found")
    return result
