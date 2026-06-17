from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps import MapValidationError, SiteMapRegistry
from runewall.maps.registry import FlowNotFoundError, SiteMapNotFoundError


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

    def test_load_site_by_key_returns_github(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_site("github")

        self.assertIsNotNone(site_map)
        assert site_map is not None
        self.assertEqual(site_map.site_name, "GitHub")

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

    def test_validate_bundled_maps_passes_with_github_and_vercel(self) -> None:
        registry = SiteMapRegistry()

        results = registry.validate_bundled_maps()

        by_key = {result.site_key: result for result in results}

        self.assertEqual(set(by_key), {"github", "vercel"})
        self.assertEqual(by_key["github"].site_name, "GitHub")
        self.assertTrue(by_key["github"].ok)
        self.assertIsNone(by_key["github"].error)
        self.assertEqual(by_key["vercel"].site_name, "Vercel")
        self.assertTrue(by_key["vercel"].ok)
        self.assertIsNone(by_key["vercel"].error)


if __name__ == "__main__":
    unittest.main()
