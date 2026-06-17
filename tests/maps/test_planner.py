from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps.planner import DryRunPlanner, dry_run_result, missing_inputs_error, render_plan


class DryRunPlannerTests(unittest.TestCase):
    def test_valid_dry_run_for_github_create_issue(self) -> None:
        planner = DryRunPlanner()

        plan = planner.build_plan(
            "github",
            "create_issue",
            {"repo": "user/repo", "title": "Bug report", "body": "Details"},
        )

        self.assertEqual(plan.site_name, "GitHub")
        self.assertEqual(plan.flow_name, "create_issue")
        self.assertEqual(plan.risk_level, "low")
        self.assertTrue(plan.reversible)
        self.assertTrue(plan.requires_auth)
        self.assertEqual(plan.missing_inputs, [])
        rendered = render_plan(plan)
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- repo=user/repo", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertEqual(
            dry_run_result(plan),
            {
                "risk_level": "low",
                "reversible": True,
                "requires_auth": True,
                "executed": False,
            },
        )

    def test_missing_required_input_fails_clearly(self) -> None:
        planner = DryRunPlanner()

        plan = planner.build_plan("github", "create_issue", {"repo": "user/repo"})

        self.assertEqual(plan.missing_inputs, ["title"])
        self.assertEqual(missing_inputs_error(plan), "Missing required inputs: title")


if __name__ == "__main__":
    unittest.main()
