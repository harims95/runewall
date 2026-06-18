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
from runewall.core.config import config_path, load_config, set_config_value


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

    def test_load_config_reads_custom_snapshot_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = config_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[safety]\nmax_snapshot_mb = 1\n", encoding="utf-8")

            config = load_config(root)

            self.assertEqual(config.safety.max_snapshot_mb, 1)

    def test_load_config_reads_allow_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = config_path(root)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")

            config = load_config(root)

            self.assertTrue(config.maps.allow_execute)


class ConfigSetTests(unittest.TestCase):
    def test_set_maps_allow_execute_true_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("maps.allow_execute", "true", root=root)
            self.assertTrue(load_config(root).maps.allow_execute)

    def test_set_maps_allow_execute_false_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("maps.allow_execute", "true", root=root)
            set_config_value("maps.allow_execute", "false", root=root)
            self.assertFalse(load_config(root).maps.allow_execute)

    def test_set_safety_max_snapshot_mb_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("safety.max_snapshot_mb", "100", root=root)
            self.assertEqual(load_config(root).safety.max_snapshot_mb, 100)

    def test_set_creates_config_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertFalse(config_path(root).exists())
            set_config_value("maps.allow_execute", "true", root=root)
            self.assertTrue(config_path(root).exists())
            self.assertTrue(load_config(root).maps.allow_execute)

    def test_set_auth_vercel_token_env_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("auth.vercel_token_env", "MY_VERCEL_TOKEN", root=root)
            self.assertEqual(load_config(root).auth.vercel_token_env, "MY_VERCEL_TOKEN")

    def test_set_auth_netlify_token_env_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("auth.netlify_token_env", "MY_NETLIFY_TOKEN", root=root)
            self.assertEqual(load_config(root).auth.netlify_token_env, "MY_NETLIFY_TOKEN")

    def test_set_auth_supabase_access_token_env_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("auth.supabase_access_token_env", "MY_SUPABASE_TOKEN", root=root)
            self.assertEqual(load_config(root).auth.supabase_access_token_env, "MY_SUPABASE_TOKEN")

    def test_set_auth_cloudflare_api_token_env_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            set_config_value("auth.cloudflare_api_token_env", "MY_CF_TOKEN", root=root)
            self.assertEqual(load_config(root).auth.cloudflare_api_token_env, "MY_CF_TOKEN")

    def test_set_unknown_key_raises_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                set_config_value("maps.unknown_key", "true", root=Path(temp_dir))
        self.assertIn("Unknown config key: maps.unknown_key", str(context.exception))

    def test_set_invalid_boolean_raises_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                set_config_value("maps.allow_execute", "yes", root=Path(temp_dir))
        self.assertIn("Invalid boolean for maps.allow_execute", str(context.exception))
        self.assertIn("Use true or false", str(context.exception))

    def test_set_invalid_integer_raises_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                set_config_value("safety.max_snapshot_mb", "abc", root=Path(temp_dir))
        self.assertIn("Invalid integer for safety.max_snapshot_mb", str(context.exception))


if __name__ == "__main__":
    unittest.main()
