from __future__ import annotations

from fnmatch import fnmatchcase

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


class RulesEngine:
    """Evaluate actions against explicit rules and safe defaults."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules = sorted(rules or [], key=lambda rule: rule.priority, reverse=True)

    def evaluate(self, action: Action) -> RulePolicy:
        explicit = self._match_explicit_rule(action.action_type)
        if explicit is not None:
            return explicit

        if action.action_type == "api.call":
            return AUTO if self._is_read_only_api_call(action) else REVIEW

        return DEFAULT_POLICIES.get(action.action_type, REVIEW)

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
