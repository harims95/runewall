from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main
from runewall.core.config import config_path, load_config


class ConfigTests(unittest.TestCase):
    def test_init_creates_config_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            path = Path(temp_dir) / ".runewall" / "config.toml"
            self.assertEqual(exit_code, 0)
            self.assertTrue(path.exists())
            self.assertIn('default_policy = "review"', path.read_text(encoding="utf-8"))

    def test_existing_config_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            root = Path(temp_dir)
            path = config_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[safety]\ndefault_policy = \"auto\"\n", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "[safety]\ndefault_policy = \"auto\"\n")

    def test_load_config_returns_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_config(Path(temp_dir))

            self.assertEqual(config.safety.default_policy, "review")
            self.assertEqual(config.safety.max_snapshot_mb, 500)
            self.assertEqual(config.retention.snapshot_days, 30)
            self.assertFalse(config.maps.allow_execute)
            self.assertEqual(config.auth.github_token_env, "GITHUB_TOKEN")


if __name__ == "__main__":
    unittest.main()
