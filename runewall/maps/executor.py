from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from runewall.core.config import load_config

class MapExecutionError(RuntimeError):
    """Raised when mapped execution cannot complete safely."""


class UnsupportedExecutionError(MapExecutionError):
    """Raised when a mapped execution path is not implemented."""

def execute_map_action(site: str, flow: str, inputs: dict[str, str], root: Path | None = None) -> dict[str, Any]:
    normalized_site = site.strip().lower()
    normalized_flow = flow.strip()
    if not _is_supported_execution(normalized_site, normalized_flow):
        raise UnsupportedExecutionError(f"Execution is not supported for {site}:{flow}.")
    if not load_config(root).maps.allow_execute:
        raise MapExecutionError(
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable."
        )

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise MapExecutionError("GITHUB_TOKEN is required to execute github:create_issue.")

    repo = inputs["repo"]
    response = _httpx_post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": inputs["title"],
            "body": inputs.get("body", ""),
        },
        timeout=30.0,
    )

    if response.status_code >= 400:
        detail = _error_detail(response)
        raise MapExecutionError(f"GitHub create_issue failed: {response.status_code} {detail}")

    payload = response.json()
    result: dict[str, Any] = {}
    if "html_url" in payload:
        result["issue_url"] = payload["html_url"]
    if "number" in payload:
        result["issue_number"] = payload["number"]
    return result


def _is_supported_execution(site: str, flow: str) -> bool:
    return site == "github" and flow == "create_issue"


def _httpx_post(*args: Any, **kwargs: Any) -> Any:
    import httpx

    return httpx.post(*args, **kwargs)


def _error_detail(response: Any) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or "unknown error"
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return "unknown error"
