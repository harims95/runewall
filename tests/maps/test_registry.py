from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps import CommunityMapImportReport, CommunityMapInspectReport, CommunityMapValidationReport, ManifestValidationReport, MapValidationError, PackageImportReport, PackageInspectReport, SiteMapRegistry, TrustedKeyRecord
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

    def test_example_community_map_validates_and_has_no_secret_keys(self) -> None:
        registry = SiteMapRegistry()
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"

        report = registry.validate_community_map_file(example_path)

        self.assertTrue(report.ok)
        example_data = json.loads(example_path.read_text(encoding="utf-8"))
        rendered = json.dumps(example_data).lower()
        for forbidden in ("token", "api_key", "secret", "password", "private_key"):
            self.assertNotIn(forbidden, rendered)

    def test_import_community_map_file_copies_valid_file(self) -> None:
        registry = SiteMapRegistry()
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            report = registry.import_community_map_file(example_path, Path(temp_dir))

            imported_path = Path(temp_dir) / ".runewall" / "community-maps" / example_path.name
            imported_exists = imported_path.exists()

        self.assertIsInstance(report, CommunityMapImportReport)
        self.assertTrue(report.ok)
        self.assertTrue(imported_exists)
        self.assertEqual(report.destination, f".runewall/community-maps/{example_path.name}")

    def test_inspect_community_map_file_reports_metadata_for_valid_file(self) -> None:
        registry = SiteMapRegistry()
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"

        report = registry.inspect_community_map_file(example_path)

        self.assertIsInstance(report, CommunityMapInspectReport)
        self.assertTrue(report.ok)
        self.assertEqual(report.site, "github")
        self.assertEqual(report.flow, "create_issue")
        self.assertEqual(report.action_type, "map.dry_run")
        self.assertFalse(report.execute_enabled)
        self.assertFalse(report.contains_secrets)

    def test_inspect_community_map_file_detects_secret_like_fields(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text(
                '{"site":"github","flow":"create_issue","action_type":"map.dry_run","token":"abc"}',
                encoding="utf-8",
            )

            report = registry.inspect_community_map_file(map_path)

        self.assertFalse(report.ok)
        self.assertTrue(report.contains_secrets)
        self.assertFalse(report.execute_enabled)

    def test_list_community_map_files_returns_empty_when_missing(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            files = registry.list_community_map_files(Path(temp_dir))
        self.assertEqual(files, [])

    def test_validate_manifest_file_passes_for_example(self) -> None:
        registry = SiteMapRegistry()
        example_path = ROOT / "examples" / "community-maps" / "manifest.example.json"

        report = registry.validate_manifest_file(example_path)

        self.assertIsInstance(report, ManifestValidationReport)
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.name, "github-safe-issue-map")
        self.assertEqual(report.version, "0.1.0")
        self.assertEqual(report.author_name, "example-author")
        self.assertEqual(report.maps_count, 1)

    def test_validate_manifest_file_fails_for_missing_file(self) -> None:
        registry = SiteMapRegistry()
        report = registry.validate_manifest_file(Path("no-such-manifest.json"))
        self.assertFalse(report.ok)
        self.assertTrue(any("file not found" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_missing_name(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertTrue(any("name" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_secret_key_with_string_value(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {},
                    "token": "abc123",
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertTrue(any("secret-like field" in e for e in report.errors))

    def test_validate_manifest_file_passes_with_requires_tokens_false(self) -> None:
        import hashlib as _hashlib
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_content = b'{"site":"github","flow":"f","action_type":"map.dry_run"}'
            map_file = Path(temp_dir) / "x.json"
            map_file.write_bytes(map_content)
            checksum = "sha256-" + _hashlib.sha256(map_content).hexdigest()
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "requires_tokens": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {"x.json": checksum},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertTrue(report.ok, report.errors)
        self.assertTrue(report.checksums_verified)

    def test_validate_manifest_file_fails_for_execute_enabled_true(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": True},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertTrue(any("execute_enabled" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_community_execution_allowed_true(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": True},
                    "checksums": {},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertTrue(any("community_execution_allowed" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_missing_checksum(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_file = Path(temp_dir) / "mymap.json"
            map_file.write_text('{"site":"github","flow":"f","action_type":"map.dry_run"}', encoding="utf-8")
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "mymap.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertFalse(report.checksums_verified)
        self.assertTrue(any("missing checksum" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_wrong_checksum(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_file = Path(temp_dir) / "mymap.json"
            map_file.write_text('{"site":"github","flow":"f","action_type":"map.dry_run"}', encoding="utf-8")
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "mymap.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {"mymap.json": "sha256-wrong"},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertFalse(report.checksums_verified)
        self.assertTrue(any("checksum mismatch" in e for e in report.errors))

    def test_validate_manifest_file_fails_for_missing_map_file(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "nothere.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {"nothere.json": "sha256-abc"},
                }),
                encoding="utf-8",
            )
            report = registry.validate_manifest_file(path)
        self.assertFalse(report.ok)
        self.assertFalse(report.checksums_verified)
        self.assertTrue(any("map file not found" in e for e in report.errors))

    def test_inspect_package_directory_passes_for_example(self) -> None:
        registry = SiteMapRegistry()
        pkg = registry.inspect_package_directory(ROOT / "examples" / "community-maps")
        self.assertIsInstance(pkg, PackageInspectReport)
        self.assertTrue(pkg.ok)
        self.assertEqual(pkg.name, "github-safe-issue-map")
        self.assertEqual(pkg.maps_count, 1)
        self.assertTrue(pkg.checksums_verified)
        self.assertEqual(pkg.errors, [])
        self.assertEqual(pkg.validation_errors, [])

    def test_inspect_package_directory_fails_for_missing_directory(self) -> None:
        registry = SiteMapRegistry()
        pkg = registry.inspect_package_directory(Path("no-such-dir"))
        self.assertFalse(pkg.ok)
        self.assertTrue(any("directory not found" in e for e in pkg.errors))

    def test_inspect_package_directory_fails_for_no_manifest(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg = registry.inspect_package_directory(Path(temp_dir))
        self.assertFalse(pkg.ok)
        self.assertTrue(any("manifest" in e for e in pkg.errors))

    def test_inspect_package_directory_fails_for_wrong_checksum(self) -> None:
        import hashlib as _hashlib
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            map_content = b'{"site":"github","flow":"f","action_type":"map.dry_run"}'
            (Path(temp_dir) / "mymap.json").write_bytes(map_content)
            (Path(temp_dir) / "manifest.json").write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "mymap.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {"mymap.json": "sha256-wrong"},
                }),
                encoding="utf-8",
            )
            pkg = registry.inspect_package_directory(Path(temp_dir))
        self.assertFalse(pkg.ok)
        self.assertFalse(pkg.checksums_verified)
        self.assertTrue(any("checksum mismatch" in e for e in pkg.validation_errors))

    def test_import_package_directory_passes_for_example(self) -> None:
        registry = SiteMapRegistry()
        example_dir = ROOT / "examples" / "community-maps"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = registry.import_package_directory(example_dir, Path(temp_dir))
            imported_path = Path(temp_dir) / ".runewall" / "community-maps" / "github_create_issue.safe.json"
            file_exists = imported_path.exists()
        self.assertIsInstance(result, PackageImportReport)
        self.assertTrue(result.ok)
        self.assertTrue(result.validated)
        self.assertTrue(result.checksums_verified)
        self.assertFalse(result.execute_enabled)
        self.assertIn(".runewall/community-maps/github_create_issue.safe.json", result.imported_maps)
        self.assertTrue(file_exists)

    def test_import_package_directory_fails_for_missing_directory(self) -> None:
        registry = SiteMapRegistry()
        result = registry.import_package_directory(Path("no-such-dir"))
        self.assertFalse(result.ok)
        self.assertFalse(result.validated)
        self.assertTrue(any("directory not found" in e for e in result.errors))

    def test_import_package_directory_fails_for_no_manifest(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = registry.import_package_directory(Path(temp_dir))
        self.assertFalse(result.ok)
        self.assertFalse(result.validated)
        self.assertTrue(any("manifest" in e for e in result.errors))

    def test_import_package_directory_fails_for_wrong_checksum_and_imports_nothing(self) -> None:
        import hashlib as _hashlib
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as pkg_dir, tempfile.TemporaryDirectory() as root_dir:
            map_content = b'{"site":"github","flow":"f","action_type":"map.dry_run"}'
            (Path(pkg_dir) / "mymap.json").write_bytes(map_content)
            (Path(pkg_dir) / "manifest.json").write_text(
                json.dumps({
                    "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                    "author": {"name": "a"},
                    "maps": [{"path": "mymap.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                    "permissions": {"external_api_calls": False, "execute_enabled": False},
                    "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                    "checksums": {"mymap.json": "sha256-wrong"},
                }),
                encoding="utf-8",
            )
            result = registry.import_package_directory(Path(pkg_dir), Path(root_dir))
            imported_path = Path(root_dir) / ".runewall" / "community-maps" / "mymap.json"
            file_exists = imported_path.exists()
        self.assertFalse(result.ok)
        self.assertFalse(result.checksums_verified)
        self.assertFalse(file_exists)
        self.assertEqual(result.imported_maps, [])

    def test_import_package_directory_execute_enabled_false(self) -> None:
        registry = SiteMapRegistry()
        example_dir = ROOT / "examples" / "community-maps"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = registry.import_package_directory(example_dir, Path(temp_dir))
        self.assertFalse(result.execute_enabled)

    def test_list_trusted_keys_returns_empty_when_folder_missing(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            records, warnings = registry.list_trusted_keys(Path(temp_dir))
        self.assertEqual(records, [])
        self.assertEqual(warnings, [])

    def test_list_trusted_keys_returns_key_record(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            keys_dir = Path(temp_dir) / ".runewall" / "trusted-keys"
            keys_dir.mkdir(parents=True)
            (keys_dir / "example.json").write_text(
                json.dumps({
                    "key_id": "example-author-key",
                    "algorithm": "ed25519",
                    "public_key": "base64-placeholder",
                    "trusted_at": "2026-01-01T00:00:00Z",
                    "source": "local-file",
                    "status": "trusted",
                }),
                encoding="utf-8",
            )
            records, warnings = registry.list_trusted_keys(Path(temp_dir))
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], TrustedKeyRecord)
        self.assertEqual(records[0].key_id, "example-author-key")
        self.assertEqual(records[0].algorithm, "ed25519")
        self.assertEqual(records[0].status, "trusted")
        self.assertEqual(warnings, [])

    def test_list_trusted_keys_warns_for_invalid_record(self) -> None:
        registry = SiteMapRegistry()
        with tempfile.TemporaryDirectory() as temp_dir:
            keys_dir = Path(temp_dir) / ".runewall" / "trusted-keys"
            keys_dir.mkdir(parents=True)
            (keys_dir / "bad.json").write_text("not-json", encoding="utf-8")
            records, warnings = registry.list_trusted_keys(Path(temp_dir))
        self.assertEqual(records, [])
        self.assertTrue(any("bad.json" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
