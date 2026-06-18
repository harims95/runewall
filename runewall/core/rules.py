from __future__ import annotations

from fnmatch import fnmatchcase

from .config import RunewallConfig
from .models import Action, Rule, RulePolicy

AUTO: RulePolicy = "AUTO"
SNAPSHOT: RulePolicy = "SNAPSHOT"
REVIEW: RulePolicy = "REVIEW"
BLOCK: RulePolicy = "BLOCK"

DEFAULT_POLICIES: dict[str, RulePolicy] = {
    "file.read": AUTO,
    "file.create": SNAPSHOT,
    "file.write": SNAPSHOT,
    "file.delete": REVIEW,
    "shell.exec": REVIEW,
    "email.send": REVIEW,
}

_ACTION_TYPE_MAP: dict[str, str] = {
    "file_read": "file.read",
    "file_write": "file.write",
    "file_create": "file.create",
    "file_delete": "file.delete",
    "web_read": "web.read",
    "map_dry_run": "map.dry_run",
    "map_execute": "map.execute",
}

_POLICY_MAP: dict[str, RulePolicy] = {
    "auto": AUTO,
    "snapshot": SNAPSHOT,
    "review": REVIEW,
    "block": BLOCK,
}


class RulesEngine:
    """Evaluate actions against explicit rules and safe defaults."""

    def __init__(self, rules: list[Rule] | None = None, unknown_policy: RulePolicy | None = None) -> None:
        self._rules = sorted(rules or [], key=lambda rule: rule.priority, reverse=True)
        self._unknown_policy: RulePolicy = unknown_policy if unknown_policy is not None else REVIEW

    def evaluate(self, action: Action) -> RulePolicy:
        explicit = self._match_explicit_rule(action.action_type)
        if explicit is not None:
            return explicit

        if action.action_type == "api.call":
            return AUTO if self._is_read_only_api_call(action) else REVIEW

        return DEFAULT_POLICIES.get(action.action_type, self._unknown_policy)

    def _match_explicit_rule(self, action_type: str) -> RulePolicy | None:
        for rule in self._rules:
            if fnmatchcase(action_type, rule.pattern):
                return rule.policy
        return None

    @staticmethod
    def _is_read_only_api_call(action: Action) -> bool:
        if not isinstance(action.params, dict):
            return False

        method = action.params.get("method")
        if isinstance(method, str) and method.upper() == "GET":
            return True

        read_only = action.params.get("read_only")
        return read_only is True


def rules_from_config(config: RunewallConfig) -> list[Rule]:
    """Convert config rules section into Rule objects for RulesEngine."""
    rules: list[Rule] = []
    rc = config.rules
    for field_name, action_type in _ACTION_TYPE_MAP.items():
        policy_str = getattr(rc, field_name)
        if policy_str is not None:
            rules.append(Rule(pattern=action_type, policy=_POLICY_MAP[policy_str]))
    return rules


def engine_from_config(config: RunewallConfig) -> RulesEngine:
    """Build a fully configured RulesEngine from a RunewallConfig."""
    rules = rules_from_config(config)
    unknown_policy = _POLICY_MAP.get(config.rules.unknown) if config.rules.unknown is not None else None
    return RulesEngine(rules=rules, unknown_policy=unknown_policy)


