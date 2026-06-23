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


def _error_result(message: str) -> dict[str, object]:
    return {"ok": False, "error": message}


def policy_test(action_type: str) -> dict[str, object]:
    if not isinstance(action_type, str) or not action_type.strip():
        return _error_result("action_type is required")
    return _policy_test_result(action_type, Path.cwd())


def policy_audit() -> dict[str, object]:
    return _policy_audit_result(Path.cwd())


def release_check() -> dict[str, object]:
    return _release_check_result(Path.cwd())


def mcp_status() -> dict[str, object]:
    return _mcp_status_result()


def dry_run(site: str, flow: str, inputs: dict | None = None) -> dict[str, object]:
    if not isinstance(site, str) or not site.strip():
        return _error_result("site is required")
    if not isinstance(flow, str) or not flow.strip():
        return _error_result("flow is required")
    if inputs is None:
        inputs = {}
    if not isinstance(inputs, dict):
        return _error_result("inputs must be a dict")

    result = _dry_run_mcp_result(site, flow, inputs, Path.cwd())
    if result is None:
        return _error_result("Map not found")
    return result
