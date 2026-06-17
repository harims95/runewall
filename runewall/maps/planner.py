from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry import SiteMapRegistry


@dataclass(frozen=True)
class DryRunPlan:
    site_name: str
    flow_name: str
    description: str
    risk_level: str
    reversible: bool
    requires_auth: bool
    provided_inputs: dict[str, str]
    missing_inputs: list[str]
    api_path: dict[str, Any] | None
    ui_steps_count: int


class DryRunPlanner:
    def __init__(self, registry: SiteMapRegistry | None = None) -> None:
        self.registry = registry or SiteMapRegistry()

    def build_plan(self, site_key: str, flow_name: str, inputs: dict[str, str]) -> DryRunPlan:
        site_map = self.registry.require_site(site_key)
        flow = self.registry.require_flow(site_map, flow_name)
        missing_inputs = self._missing_required_inputs(flow, inputs)
        return DryRunPlan(
            site_name=site_map.site_name,
            flow_name=flow_name,
            description=str(flow.get("description", "")),
            risk_level=str(flow.get("risk_level", "")),
            reversible=bool(flow.get("reversible", False)),
            requires_auth=bool(flow.get("requires_auth", False)),
            provided_inputs=inputs,
            missing_inputs=missing_inputs,
            api_path=flow.get("api_path") if isinstance(flow.get("api_path"), dict) else None,
            ui_steps_count=len(flow["ui_steps"]) if isinstance(flow.get("ui_steps"), list) else 0,
        )

    def _missing_required_inputs(self, flow: dict[str, Any], inputs: dict[str, str]) -> list[str]:
        flow_inputs = flow.get("inputs", {})
        if not isinstance(flow_inputs, dict):
            return []
        return [
            input_name
            for input_name, input_data in flow_inputs.items()
            if isinstance(input_data, dict) and input_data.get("required") is True and input_name not in inputs
        ]


def dry_run_result(plan: DryRunPlan) -> dict[str, Any]:
    return {
        "risk_level": plan.risk_level,
        "reversible": plan.reversible,
        "requires_auth": plan.requires_auth,
        "executed": False,
    }


def missing_inputs_error(plan: DryRunPlan) -> str | None:
    if not plan.missing_inputs:
        return None
    return f"Missing required inputs: {', '.join(plan.missing_inputs)}"


def render_plan(plan: DryRunPlan) -> str:
    lines = [
        f"Site name: {plan.site_name}",
        f"Flow name: {plan.flow_name}",
        f"Description: {plan.description}",
        f"Risk level: {plan.risk_level}",
        f"Reversible: {plan.reversible}",
        f"Requires auth: {plan.requires_auth}",
        "Provided inputs:",
    ]

    if plan.provided_inputs:
        for key, value in plan.provided_inputs.items():
            lines.append(f"- {key}={value}")
    else:
        lines.append("- none")

    if plan.missing_inputs:
        lines.append(f"Missing inputs: {', '.join(plan.missing_inputs)}")
    else:
        lines.append("Missing inputs: none")

    if plan.api_path is not None:
        method = str(plan.api_path.get("method", ""))
        url = str(plan.api_path.get("url", ""))
        lines.append(f"API path: {method} {url}".strip())

    if plan.ui_steps_count:
        lines.append(f"UI steps count: {plan.ui_steps_count}")

    return "\n".join(lines)
