from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps import CommunityMapValidationReport, MapValidationError, SiteMapRegistry
from runewall.maps.registry import FlowNotFoundError, SiteMapNotFoundError, SiteMap, lint_map


class SiteMapRegistryTests(unittest.TestCase):
    def test_registry_loads_github_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("github.json")

        self.assertEqual(site_map.site_name, "GitHub")
        self.assertEqual(site_map.base_url, "https://github.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("create_issue", site_map.flows)

    def test_registry_loads_vercel_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("vercel.json")

        self.assertEqual(site_map.site_name, "Vercel")
        self.assertEqual(site_map.base_url, "https://vercel.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("list_projects", site_map.flows)

    def test_registry_loads_netlify_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("netlify.json")

        self.assertEqual(site_map.site_name, "Netlify")
        self.assertEqual(site_map.base_url, "https://app.netlify.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("list_sites", site_map.flows)

    def test_registry_loads_cloudflare_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("cloudflare.json")

        self.assertEqual(site_map.site_name, "Cloudflare")
        self.assertEqual(site_map.base_url, "https://dash.cloudflare.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("list_zones", site_map.flows)

    def test_invalid_map_raises_clear_error(self) -> None:
        registry = SiteMapRegistry()

        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid.json"
            invalid_path.write_text('{"site": {"name": "Broken"}}', encoding="utf-8")

            with self.assertRaises(MapValidationError) as context:
                registry.load_file(invalid_path)

        self.assertEqual(
            str(context.exception),
            f"{invalid_path}: missing required field 'schema_version'",
        )

    def test_registry_loads_category_and_tags_for_github(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("github.json")

        self.assertEqual(site_map.category, "development")
        self.assertEqual(site_map.tags, ["code", "issues"])

    def test_registry_loads_category_and_tags_for_slack(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("slack.json")

        self.assertEqual(site_map.category, "communication")
        self.assertEqual(site_map.tags, ["team", "chat"])

    def test_registry_returns_empty_category_and_tags_when_missing(self) -> None:
        registry = SiteMapRegistry()

        with tempfile.TemporaryDirectory() as temp_dir:
            no_meta_path = Path(temp_dir) / "nometa.json"
            no_meta_path.write_text(
                '{"schema_version":"1.0.0","site":{"name":"NoMeta","base_url":"https://example.com","map_version":"0.1.0"},"flows":{}}',
                encoding="utf-8",
            )
            site_map = registry.load_file(no_meta_path)

        self.assertEqual(site_map.category, "")
        self.assertEqual(site_map.tags, [])

    def test_search_maps_deploy_returns_vercel_and_netlify(self) -> None:
        registry = SiteMapRegistry()

        results = registry.search_maps("deploy")

        names = {sm.site_name for sm in results}
        self.assertIn("Vercel", names)
        self.assertIn("Netlify", names)

    def test_search_maps_chat_returns_slack_and_discord(self) -> None:
        registry = SiteMapRegistry()

        results = registry.search_maps("chat")

        names = {sm.site_name for sm in results}
        self.assertIn("Slack", names)
        self.assertIn("Discord", names)

    def test_search_maps_no_match_returns_empty(self) -> None:
        registry = SiteMapRegistry()

        results = registry.search_maps("xyznotfound")

        self.assertEqual(results, [])

    def test_lint_map_detects_invalid_risk_level_as_error(self) -> None:
        site_map = SiteMap(
            schema_version="1.0.0",
            site_name="Test",
            base_url="https://test.com",
            map_version="0.1.0",
            flows={"bad_flow": {"risk_level": "critical", "reversible": False}},
            raw={"site": {"tags": ["t"]}, "_filename": "test.json"},
            category="test",
            tags=["t"],
        )

        _warnings, errors = lint_map(site_map)

        self.assertTrue(any("invalid risk_level" in e for e in errors))

    def test_lint_map_detects_tags_not_list_as_error(self) -> None:
        site_map = SiteMap(
            schema_version="1.0.0",
            site_name="Test",
            base_url="https://test.com",
            map_version="0.1.0",
            flows={},
            raw={"site": {"tags": "not-a-list"}, "_filename": "test.json"},
            category="test",
            tags=[],
        )

        _warnings, errors = lint_map(site_map)

        self.assertIn("tags is not a list", errors)

    def test_load_site_by_key_returns_github(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_site("github")

        self.assertIsNotNone(site_map)
        assert site_map is not None
        self.assertEqual(site_map.site_name, "GitHub")

    def test_bundled_maps_path_is_absolute_and_exists(self) -> None:
        registry = SiteMapRegistry()

        maps_path = registry.bundled_maps_path()

        self.assertTrue(maps_path.is_absolute())
        self.assertTrue(maps_path.is_dir())
        self.assertIn("maps/sites", maps_path.as_posix())

    def test_require_site_raises_clear_error_for_unknown_site(self) -> None:
        registry = SiteMapRegistry()

        with self.assertRaises(SiteMapNotFoundError) as context:
            registry.require_site("unknown")

        self.assertEqual(str(context.exception), "Site map not found: unknown")

    def test_require_flow_raises_clear_error_for_unknown_flow(self) -> None:
        registry = SiteMapRegistry()
        site_map = registry.require_site("github")

        with self.assertRaises(FlowNotFoundError) as context:
            registry.require_flow(site_map, "unknown_flow")

        self.assertEqual(str(context.exception), "Flow not found for GitHub: unknown_flow")

    def test_registry_loads_linear_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("linear.json")

        self.assertEqual(site_map.site_name, "Linear")
        self.assertEqual(site_map.base_url, "https://linear.app")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("create_issue", site_map.flows)

    def test_registry_loads_supabase_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("supabase.json")

        self.assertEqual(site_map.site_name, "Supabase")
        self.assertEqual(site_map.base_url, "https://supabase.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("list_projects", site_map.flows)

    def test_registry_loads_slack_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("slack.json")

        self.assertEqual(site_map.site_name, "Slack")
        self.assertEqual(site_map.base_url, "https://slack.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("send_message", site_map.flows)

    def test_registry_loads_discord_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("discord.json")

        self.assertEqual(site_map.site_name, "Discord")
        self.assertEqual(site_map.base_url, "https://discord.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("send_message", site_map.flows)

    def test_validate_bundled_maps_passes_with_github_vercel_netlify_cloudflare_and_linear(self) -> None:
        registry = SiteMapRegistry()

        results = registry.validate_bundled_maps()

        by_key = {result.site_key: result for result in results}

        for key in ("github", "vercel", "netlify", "cloudflare", "linear", "supabase", "slack", "discord"):
            self.assertIn(key, by_key)
            self.assertTrue(by_key[key].ok)
            self.assertIsNone(by_key[key].error)

    def test_validate_community_map_file_passes_for_valid_local_map(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text(
                '{"site":"github","flow":"create_issue","action_type":"map.dry_run"}',
                encoding="utf-8",
            )

            report = registry.validate_community_map_file(map_path)

        self.assertIsInstance(report, CommunityMapValidationReport)
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_validate_community_map_file_fails_for_secret_like_fields(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text(
                '{"site":"github","flow":"create_issue","action_type":"map.dry_run","token":"abc"}',
                encoding="utf-8",
            )

            report = registry.validate_community_map_file(map_path)

        self.assertFalse(report.ok)
        self.assertTrue(any("secret-like field" in error for error in report.errors))

    def test_validate_community_map_file_fails_for_enabled_execution(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text(
                '{"site":"github","flow":"create_issue","action_type":"map.dry_run","allow_execute":true}',
                encoding="utf-8",
            )

            report = registry.validate_community_map_file(map_path)

        self.assertFalse(report.ok)
        self.assertIn("community maps cannot enable execution", report.errors)


if __name__ == "__main__":
    unittest.main()
