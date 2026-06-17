from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.maps import MapValidationError, SiteMapRegistry


class SiteMapRegistryTests(unittest.TestCase):
    def test_registry_loads_github_json(self) -> None:
        registry = SiteMapRegistry()

        site_map = registry.load_map("github.json")

        self.assertEqual(site_map.site_name, "GitHub")
        self.assertEqual(site_map.base_url, "https://github.com")
        self.assertEqual(site_map.schema_version, "1.0.0")
        self.assertIn("create_issue", site_map.flows)

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


if __name__ == "__main__":
    unittest.main()
