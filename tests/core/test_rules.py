from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.core.models import Action, Rule
from runewall.core.rules import AUTO, BLOCK, REVIEW, SNAPSHOT, RulesEngine


class RulesEngineTests(unittest.TestCase):
    def test_file_read_returns_auto(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="file.read", target="notes.txt"))

        self.assertEqual(policy, AUTO)

    def test_file_write_returns_snapshot(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="file.write", target="notes.txt"))

        self.assertEqual(policy, SNAPSHOT)

    def test_file_delete_returns_review(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="file.delete", target="notes.txt"))

        self.assertEqual(policy, REVIEW)

    def test_shell_exec_returns_review(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="shell.exec", target="rm -rf /tmp"))

        self.assertEqual(policy, REVIEW)

    def test_email_send_returns_review(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="email.send", target="user@example.com"))

        self.assertEqual(policy, REVIEW)

    def test_api_call_get_returns_auto(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(
            Action(
                action_type="api.call",
                target="https://example.com/items",
                params={"method": "GET"},
            )
        )

        self.assertEqual(policy, AUTO)

    def test_unknown_action_returns_review(self) -> None:
        engine = RulesEngine()

        policy = engine.evaluate(Action(action_type="calendar.invite", target="team-sync"))

        self.assertEqual(policy, REVIEW)

    def test_explicit_block_rule_overrides_default(self) -> None:
        engine = RulesEngine(rules=[Rule(pattern="file.write", policy=BLOCK, priority=10)])

        policy = engine.evaluate(Action(action_type="file.write", target="notes.txt"))

        self.assertEqual(policy, BLOCK)


class RulesFromConfigTests(unittest.TestCase):
    def test_default_behavior_unchanged_without_rules_config(self) -> None:
        from runewall.core.config import RunewallConfig
        from runewall.core.rules import engine_from_config
        engine = engine_from_config(RunewallConfig())
        self.assertEqual(engine.evaluate(Action(action_type="file.write", target="f")), SNAPSHOT)
        self.assertEqual(engine.evaluate(Action(action_type="file.delete", target="f")), REVIEW)
        self.assertEqual(engine.evaluate(Action(action_type="calendar.invite", target="t")), REVIEW)

    def test_file_write_review_overrides_default_snapshot(self) -> None:
        from runewall.core.config import RulesConfig, RunewallConfig
        from runewall.core.rules import engine_from_config
        engine = engine_from_config(RunewallConfig(rules=RulesConfig(file_write="review")))
        self.assertEqual(engine.evaluate(Action(action_type="file.write", target="f")), REVIEW)

    def test_file_delete_block_blocks_delete(self) -> None:
        from runewall.core.config import RulesConfig, RunewallConfig
        from runewall.core.rules import engine_from_config
        engine = engine_from_config(RunewallConfig(rules=RulesConfig(file_delete="block")))
        self.assertEqual(engine.evaluate(Action(action_type="file.delete", target="f")), BLOCK)

    def test_unknown_block_blocks_unknown_actions(self) -> None:
        from runewall.core.config import RulesConfig, RunewallConfig
        from runewall.core.rules import engine_from_config
        engine = engine_from_config(RunewallConfig(rules=RulesConfig(unknown="block")))
        self.assertEqual(engine.evaluate(Action(action_type="calendar.invite", target="t")), BLOCK)
        self.assertEqual(engine.evaluate(Action(action_type="sms.send", target="t")), BLOCK)

    def test_unknown_block_does_not_affect_default_policy_actions(self) -> None:
        from runewall.core.config import RulesConfig, RunewallConfig
        from runewall.core.rules import engine_from_config
        engine = engine_from_config(RunewallConfig(rules=RulesConfig(unknown="block")))
        self.assertEqual(engine.evaluate(Action(action_type="file.write", target="f")), SNAPSHOT)
        self.assertEqual(engine.evaluate(Action(action_type="file.delete", target="f")), REVIEW)

    def test_rules_from_config_returns_empty_list_without_rules(self) -> None:
        from runewall.core.config import RunewallConfig
        from runewall.core.rules import rules_from_config
        self.assertEqual(rules_from_config(RunewallConfig()), [])


if __name__ == "__main__":
    unittest.main()
