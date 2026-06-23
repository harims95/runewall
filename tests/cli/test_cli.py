from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import EMPTY_LOG_MESSAGE, main
from runewall.core.config import config_path
from runewall.core.log import ActionLog
from runewall.core.models import Action
from runewall.core.snapshot import SnapshotEngine
from runewall.maps import SiteMapRegistry


class CliTests(unittest.TestCase):
    def test_top_level_help_exits_zero_and_mentions_local_first(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as error:
                main(["--help"])
        self.assertEqual(error.exception.code, 0)
        rendered = output.getvalue()
        self.assertIn("Runewall is a local-first safety/runtime layer for AI agents.", rendered)
        self.assertIn("mcp      inspect planned MCP tool surface", rendered)
        self.assertIn("policy   explain, test, list, and audit safety policies", rendered)

    def test_mcp_tools_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["mcp", "tools"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("MCP tools", rendered)
        self.assertIn("runewall.policy_test", rendered)
        self.assertIn("runewall.release_check", rendered)

    def test_mcp_tools_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["mcp", "tools", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertIn("runewall.policy_test", data["initial_tools"])
        self.assertIn("runewall.dry_run", data["initial_tools"])
        self.assertIn("runewall.release_check", data["initial_tools"])

    def test_mcp_status_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["mcp", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("MCP status", rendered)
        self.assertIn("* stdio --once supported", rendered)
        self.assertIn("* tools/call", rendered)
        self.assertIn("* runewall.dry_run", rendered)

    def test_mcp_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["mcp", "status", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertIn("initialize", data["mcp"]["methods"])
        self.assertIn("tools/list", data["mcp"]["methods"])
        self.assertIn("tools/call", data["mcp"]["methods"])
        self.assertIn("runewall.dry_run", data["mcp"]["supported_tools"])
        self.assertFalse(data["mcp"]["safety"]["execute_exposed"])

    def test_sdk_status_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["sdk", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Python SDK status", rendered)
        self.assertIn("* dry_run", rendered)
        self.assertIn("* execute", rendered)

    def test_sdk_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["sdk", "status", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertIn("dry_run", data["sdk"]["available_functions"])
        self.assertFalse(data["sdk"]["safety"]["execute_exposed"])

    def test_community_maps_status_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community maps status", rendered)
        self.assertIn("- runewall maps community validate <path>", rendered)
        self.assertIn("- runewall maps community inspect <path>", rendered)
        self.assertIn("- runewall maps community import <path>", rendered)
        self.assertIn("- local files only", rendered)
        self.assertIn("- execute disabled for community maps", rendered)

    def test_community_maps_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "status", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertIn("available_commands", data["community_maps"])
        self.assertIn("runewall maps community inspect <path>", data["community_maps"]["available_commands"])
        self.assertFalse(data["community_maps"]["safety"]["execute_enabled_for_community_maps"])

    def test_community_maps_validate_valid_local_sample_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text('{"site":"github","flow":"create_issue","action_type":"map.dry_run"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "validate", str(map_path)])
        self.assertEqual(exit_code, 0)
        self.assertIn("Community map validation: OK", output.getvalue())

    def test_community_maps_validate_valid_local_sample_json_returns_ok_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text('{"site":"github","flow":"create_issue","action_type":"map.dry_run"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "validate", str(map_path), "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["errors"], [])

    def test_community_maps_validate_missing_file_returns_clear_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "validate", "missing-community-map.json", "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("file not found" in error for error in data["errors"]))

    def test_community_maps_validate_secret_like_fields_return_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for key in ("token", "api_key", "secret", "password", "private_key"):
                map_path = Path(temp_dir) / f"{key}.json"
                map_path.write_text(
                    json.dumps({"site": "github", "flow": "create_issue", "action_type": "map.dry_run", key: "value"}),
                    encoding="utf-8",
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "validate", str(map_path), "--json"])
                self.assertEqual(exit_code, 1)
                import json as _json
                data = _json.loads(output.getvalue())
                self.assertFalse(data["ok"])

    def test_community_maps_validate_missing_site_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text('{"flow":"create_issue","action_type":"map.dry_run"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "validate", str(map_path), "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("site" in error for error in data["errors"]))

    def test_community_maps_validate_missing_flow_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text('{"site":"github","action_type":"map.dry_run"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "validate", str(map_path), "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("flow" in error for error in data["errors"]))

    def test_community_maps_import_valid_example_succeeds(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "import", str(example_path)])
            finally:
                os.chdir(original_cwd)
            imported_path = Path(temp_dir) / ".runewall" / "community-maps" / example_path.name
            imported_exists = imported_path.exists()
        self.assertEqual(exit_code, 0)
        self.assertIn("Community map import: OK", output.getvalue())
        self.assertTrue(imported_exists)

    def test_community_maps_import_valid_example_json_returns_ok_true(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "import", str(example_path), "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["validated"])
        self.assertFalse(data["execute_enabled"])
        self.assertIn(".runewall/community-maps/", data["destination"])
        self.assertNotIn("\\", data["destination"])

    def test_community_maps_import_invalid_map_fails_and_does_not_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_map_path = Path(temp_dir) / "invalid-map.json"
            invalid_map_path.write_text('{"site":"github","action_type":"map.dry_run","token":"x"}', encoding="utf-8")
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "import", str(invalid_map_path), "--json"])
            finally:
                os.chdir(original_cwd)
            imported_path = Path(temp_dir) / ".runewall" / "community-maps" / invalid_map_path.name
            imported_exists = imported_path.exists()
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["validated"])
        self.assertFalse(imported_exists)

    def test_community_maps_inspect_valid_example_exits_zero(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "inspect", str(example_path)])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map inspect", rendered)
        self.assertIn("Site: github", rendered)
        self.assertIn("Flow: create_issue", rendered)
        self.assertIn("Execute enabled: false", rendered)

    def test_community_maps_inspect_valid_example_json_returns_ok_true(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "inspect", str(example_path), "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertFalse(data["safety"]["execute_enabled"])

    def test_community_maps_inspect_missing_file_returns_clear_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "inspect", "missing-community-map.json", "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("file not found" in error for error in data["validation"]["errors"]))

    def test_community_maps_inspect_secret_like_fields_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "community-map.json"
            map_path.write_text(
                '{"site":"github","flow":"create_issue","action_type":"map.dry_run","token":"abc"}',
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "inspect", str(map_path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(data["safety"]["contains_secrets"])
        self.assertFalse(data["safety"]["execute_enabled"])

    def test_community_maps_list_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)

    def test_community_maps_list_json_returns_ok_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["community_maps"], [])

    def test_community_maps_list_includes_imported_map_after_import(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "github_create_issue.safe.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["maps", "community", "import", str(example_path), "--json"])
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertIn(example_path.name, data["community_maps"])

    def test_manifest_validate_example_exits_zero(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "manifest.example.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "manifest", "validate", str(example_path)])
        self.assertEqual(exit_code, 0)
        self.assertIn("Community map manifest validation: OK", output.getvalue())

    def test_manifest_validate_example_json_returns_ok_true(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "manifest.example.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "manifest", "validate", str(example_path), "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["errors"], [])
        self.assertFalse(data["signing"]["implemented"])
        self.assertTrue(data["checksums"]["implemented"])
        self.assertTrue(data["checksums"]["verified"])

    def test_manifest_inspect_example_exits_zero(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "manifest.example.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "manifest", "inspect", str(example_path)])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map manifest inspect", rendered)
        self.assertIn("Name: github-safe-issue-map", rendered)
        self.assertIn("Version: 0.1.0", rendered)
        self.assertIn("Author: example-author", rendered)
        self.assertIn("Maps: 1", rendered)
        self.assertIn("Validation: OK", rendered)
        self.assertIn("Checksums: verified", rendered)

    def test_manifest_inspect_example_json_returns_ok_true(self) -> None:
        example_path = ROOT / "examples" / "community-maps" / "manifest.example.json"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "manifest", "inspect", str(example_path), "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "github-safe-issue-map")
        self.assertEqual(data["maps_count"], 1)
        self.assertTrue(data["validation"]["ok"])
        self.assertFalse(data["signing"]["implemented"])
        self.assertTrue(data["checksums"]["implemented"])
        self.assertTrue(data["checksums"]["verified"])

    def test_manifest_validate_missing_file_returns_failure(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "manifest", "validate", "no-such-manifest.json", "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("file not found" in e for e in data["errors"]))

    def test_manifest_validate_missing_name_returns_failure(self) -> None:
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("name" in e for e in data["errors"]))

    def test_manifest_validate_secret_key_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for key in ("token", "secret", "password", "private_key"):
                path = Path(temp_dir) / f"{key}.json"
                path.write_text(
                    json.dumps({
                        "manifest_version": "0.1", "name": "n", "version": "0.1.0", "description": "d",
                        "author": {"name": "a"},
                        "maps": [{"path": "x.json", "site": "github", "flow": "f", "action_type": "map.dry_run"}],
                        "permissions": {"external_api_calls": False, "execute_enabled": False},
                        "safety": {"secrets_in_files": False, "dry_run_first": True, "community_execution_allowed": False},
                        "checksums": {},
                        key: "abc123",
                    }),
                    encoding="utf-8",
                )
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
                self.assertEqual(exit_code, 1, f"expected failure for key={key}")
                data = json.loads(output.getvalue())
                self.assertFalse(data["ok"])

    def test_manifest_validate_execute_enabled_true_returns_failure(self) -> None:
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("execute_enabled" in e for e in data["errors"]))

    def test_manifest_validate_community_execution_allowed_true_returns_failure(self) -> None:
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("community_execution_allowed" in e for e in data["errors"]))

    def test_manifest_validate_missing_checksum_returns_failure(self) -> None:
        import hashlib as _hashlib
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("missing checksum" in e for e in data["errors"]))

    def test_manifest_validate_wrong_checksum_returns_failure(self) -> None:
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("checksum mismatch" in e for e in data["errors"]))

    def test_manifest_validate_missing_map_file_returns_failure(self) -> None:
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "manifest", "validate", str(path), "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("map file not found" in e for e in data["errors"]))

    def test_package_inspect_example_exits_zero(self) -> None:
        example_dir = ROOT / "examples" / "community-maps"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "package", "inspect", str(example_dir)])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map package inspect", rendered)
        self.assertIn("Name: github-safe-issue-map", rendered)
        self.assertIn("Validation: OK", rendered)
        self.assertIn("Checksums: OK", rendered)
        self.assertIn("Signing: not implemented", rendered)
        self.assertIn("Execute enabled: false", rendered)

    def test_package_inspect_example_json_returns_ok_true(self) -> None:
        example_dir = ROOT / "examples" / "community-maps"
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "package", "inspect", str(example_dir), "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "github-safe-issue-map")
        self.assertEqual(data["maps_count"], 1)
        self.assertTrue(data["checksums"]["verified"])
        self.assertTrue(data["checksums"]["implemented"])
        self.assertFalse(data["signing"]["implemented"])
        self.assertFalse(data["safety"]["execute_enabled"])
        self.assertFalse(data["safety"]["remote_downloads"])
        self.assertFalse(data["safety"]["external_api_calls"])

    def test_package_inspect_missing_directory_returns_failure(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "package", "inspect", "no-such-dir", "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("directory not found" in e for e in data["errors"]))

    def test_package_inspect_directory_without_manifest_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "package", "inspect", temp_dir, "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("manifest" in e for e in data["errors"]))

    def test_package_inspect_wrong_checksum_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "mymap.json").write_text(
                '{"site":"github","flow":"f","action_type":"map.dry_run"}', encoding="utf-8"
            )
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
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "package", "inspect", temp_dir, "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["checksums"]["verified"])
        self.assertTrue(any("checksum mismatch" in e for e in data["errors"]))

    def test_package_import_example_exits_zero(self) -> None:
        example_dir = ROOT / "examples" / "community-maps"
        original_cwd = Path.cwd()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "package", "import", str(example_dir)])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Community map package import: OK", output.getvalue())
        self.assertIn(".runewall/community-maps/github_create_issue.safe.json", output.getvalue())

    def test_package_import_example_json_returns_ok_true(self) -> None:
        example_dir = ROOT / "examples" / "community-maps"
        original_cwd = Path.cwd()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "package", "import", str(example_dir), "--json"])
                imported_path = Path(temp_dir) / ".runewall" / "community-maps" / "github_create_issue.safe.json"
                file_exists = imported_path.exists()
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["validated"])
        self.assertTrue(data["checksums"]["verified"])
        self.assertFalse(data["execute_enabled"])
        self.assertFalse(data["signing"]["implemented"])
        self.assertIn(".runewall/community-maps/github_create_issue.safe.json", data["imported_maps"])
        self.assertTrue(file_exists)

    def test_package_import_missing_directory_fails(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "package", "import", "no-such-dir", "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("directory not found" in e for e in data["errors"]))

    def test_package_import_directory_without_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["maps", "community", "package", "import", temp_dir, "--json"])
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any("manifest" in e for e in data["errors"]))

    def test_package_import_wrong_checksum_fails_and_imports_nothing(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as pkg_dir, tempfile.TemporaryDirectory() as root_dir:
            (Path(pkg_dir) / "mymap.json").write_text(
                '{"site":"github","flow":"f","action_type":"map.dry_run"}', encoding="utf-8"
            )
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
            try:
                os.chdir(root_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "package", "import", pkg_dir, "--json"])
                imported_path = Path(root_dir) / ".runewall" / "community-maps" / "mymap.json"
                file_exists = imported_path.exists()
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["checksums"]["verified"])
        self.assertEqual(data["imported_maps"], [])
        self.assertFalse(file_exists)

    def test_community_signing_status_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "signing", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map signing status", rendered)
        self.assertIn("- manifest checksum verification", rendered)
        self.assertIn("- signature verification", rendered)
        self.assertIn("- signing does not imply execution", rendered)

    def test_community_signing_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "signing", "status", "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["signing"]["implemented"])
        self.assertTrue(data["signing"]["checksum_verification"])
        self.assertFalse(data["signing"]["safety"]["signing_implies_execution"])
        self.assertFalse(data["signing"]["safety"]["community_execution_enabled"])

    def test_community_keys_status_exits_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "keys", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map trusted keys status", rendered)
        self.assertIn("- local explicit trust only", rendered)
        self.assertIn("- .runewall/trusted-keys/", rendered)
        self.assertIn("- key store status", rendered)
        self.assertIn("- signing does not imply execution", rendered)

    def test_community_keys_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "community", "keys", "status", "--json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["trusted_keys"]["storage"], ".runewall/trusted-keys/")
        self.assertTrue(data["trusted_keys"]["safety"]["trust_must_be_explicit"])
        self.assertFalse(data["trusted_keys"]["safety"]["private_keys_stored"])
        self.assertFalse(data["trusted_keys"]["safety"]["community_execution_enabled"])

    def test_keys_list_exits_zero_when_folder_missing(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("No trusted keys found.", output.getvalue())

    def test_keys_list_json_exits_zero_and_returns_empty(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["trusted_keys"], [])

    def test_keys_list_shows_key_record(self) -> None:
        original_cwd = Path.cwd()
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
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("example-author-key", rendered)
        self.assertIn("Algorithm: ed25519", rendered)
        self.assertNotIn("base64-placeholder", rendered)

    def test_keys_list_json_includes_key_id_and_omits_public_key(self) -> None:
        original_cwd = Path.cwd()
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
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(len(data["trusted_keys"]), 1)
        self.assertEqual(data["trusted_keys"][0]["key_id"], "example-author-key")
        self.assertNotIn("public_key", data["trusted_keys"][0])

    def test_keys_list_invalid_record_creates_warning(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            keys_dir = Path(temp_dir) / ".runewall" / "trusted-keys"
            keys_dir.mkdir(parents=True)
            (keys_dir / "bad.json").write_text("not-valid-json", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["trusted_keys"], [])
        self.assertIn("warnings", data)
        self.assertTrue(any("bad.json" in w for w in data["warnings"]))

    def _write_test_key(self, keys_dir: Path, key_id: str = "example-author-key") -> None:
        keys_dir.mkdir(parents=True, exist_ok=True)
        (keys_dir / f"{key_id}.json").write_text(
            json.dumps({
                "key_id": key_id, "algorithm": "ed25519",
                "public_key": "base64-placeholder",
                "trusted_at": "2026-01-01T00:00:00Z",
                "source": "local-file", "status": "trusted",
            }),
            encoding="utf-8",
        )

    def test_keys_inspect_exits_zero_for_valid_key(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_test_key(Path(temp_dir) / ".runewall" / "trusted-keys")
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "inspect", "example-author-key"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Community map trusted key inspect", rendered)
        self.assertIn("Key ID: example-author-key", rendered)
        self.assertIn("Algorithm: ed25519", rendered)
        self.assertNotIn("base64-placeholder", rendered)

    def test_keys_inspect_json_returns_ok_true(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_test_key(Path(temp_dir) / ".runewall" / "trusted-keys")
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "inspect", "example-author-key", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["key"]["key_id"], "example-author-key")
        self.assertNotIn("public_key", data["key"])
        self.assertFalse(data["safety"]["private_key_included"])
        self.assertFalse(data["safety"]["community_execution_enabled"])

    def test_keys_inspect_unknown_key_returns_not_found(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "inspect", "no-such-key", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_code"], "key_not_found")

    def test_keys_inspect_invalid_record_does_not_crash(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            keys_dir = Path(temp_dir) / ".runewall" / "trusted-keys"
            keys_dir.mkdir(parents=True)
            (keys_dir / "bad.json").write_text("not-valid-json", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "inspect", "example-author-key", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_code"], "key_not_found")

    _EXAMPLE_KEY = ROOT / "examples" / "community-maps" / "keys" / "example-author-key.json"

    def test_keys_trust_example_key_exits_zero(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY)])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Community map trusted key: OK", output.getvalue())
        self.assertIn("Key ID: example-author-key", output.getvalue())

    def test_keys_trust_example_key_json_and_stored_file(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY), "--json"])
                stored_path = Path(temp_dir) / ".runewall" / "trusted-keys" / "example-author-key.json"
                stored_data = json.loads(stored_path.read_text(encoding="utf-8"))
                file_exists = stored_path.exists()
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["key_id"], "example-author-key")
        self.assertFalse(data["signature_verification_enabled"])
        self.assertFalse(data["community_execution_enabled"])
        self.assertTrue(file_exists)
        self.assertEqual(stored_data["status"], "trusted")
        self.assertIn("trusted_at", stored_data)
        self.assertNotIn("private_key", stored_data)

    def test_keys_trust_existing_key_without_force_fails(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY)])
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY), "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_code"], "key_already_exists")

    def test_keys_trust_with_force_succeeds(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY)])
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY), "--force", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_keys_trust_private_key_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            key_file = Path(temp_dir) / "bad-key.json"
            key_file.write_text(
                json.dumps({"key_id": "k", "algorithm": "ed25519", "public_key": "x", "private_key": "secret"}),
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(key_file), "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        data = json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_code"], "private_key_not_allowed")

    def test_keys_trust_unsupported_algorithm_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            key_file = Path(temp_dir) / "rsa-key.json"
            key_file.write_text(
                json.dumps({"key_id": "k", "algorithm": "rsa", "public_key": "x"}),
                encoding="utf-8",
            )
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "trust", str(key_file), "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(output.getvalue())["error_code"], "unsupported_algorithm")

    def test_keys_list_shows_trusted_key_after_trust(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY)])
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        key_ids = [k["key_id"] for k in data["trusted_keys"]]
        self.assertIn("example-author-key", key_ids)

    def test_keys_inspect_shows_trusted_key_after_trust(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                main(["maps", "community", "keys", "trust", str(self._EXAMPLE_KEY)])
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["maps", "community", "keys", "inspect", "example-author-key", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        data = json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["key"]["key_id"], "example-author-key")
        self.assertEqual(data["key"]["status"], "trusted")

    def test_mcp_serve_handles_two_newline_delimited_requests(self) -> None:
        output = io.StringIO()
        request_stream = (
            '{"jsonrpc":"2.0","id":101,"method":"initialize","params":{}}\n'
            '\n'
            '{"jsonrpc":"2.0","id":102,"method":"tools/list","params":{}}\n'
        )
        with patch("sys.stdin", io.StringIO(request_stream)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve"])
        self.assertEqual(exit_code, 0)
        import json as _json
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        first = _json.loads(lines[0])
        second = _json.loads(lines[1])
        self.assertEqual(first["id"], 101)
        self.assertEqual(first["result"]["serverInfo"]["name"], "runewall")
        self.assertEqual(second["id"], 102)
        names = [tool["name"] for tool in second["result"]["tools"]]
        self.assertIn("runewall.dry_run", names)

    def test_mcp_serve_invalid_json_returns_parse_error_and_continues(self) -> None:
        output = io.StringIO()
        request_stream = (
            '{invalid json\n'
            '{"jsonrpc":"2.0","id":103,"method":"tools/list","params":{}}\n'
        )
        with patch("sys.stdin", io.StringIO(request_stream)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve"])
        self.assertEqual(exit_code, 0)
        import json as _json
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        first = _json.loads(lines[0])
        second = _json.loads(lines[1])
        self.assertIsNone(first["id"])
        self.assertEqual(first["error"]["code"], -32700)
        self.assertEqual(second["id"], 103)
        self.assertIn("tools", second["result"])

    def test_mcp_serve_once_handles_initialize(self) -> None:
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}')):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(data["result"]["serverInfo"]["name"], "runewall")
        self.assertEqual(data["result"]["serverInfo"]["version"], "0.6.0")

    def test_mcp_serve_once_handles_tools_list(self) -> None:
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 2)
        names = [tool["name"] for tool in data["result"]["tools"]]
        self.assertIn("runewall.policy_test", names)
        self.assertIn("runewall.dry_run", names)
        self.assertIn("runewall.release_check", names)

    def test_mcp_serve_once_handles_tools_call_policy_test(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":3,"method":"tools/call",'
            '"params":{"name":"runewall.policy_test","arguments":{"action_type":"map.execute"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 3)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        self.assertIn("map.execute", data["result"]["content"][0]["text"])
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_policy_audit(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":4,"method":"tools/call",'
            '"params":{"name":"runewall.policy_audit","arguments":{}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 4)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        audit = _json.loads(data["result"]["content"][0]["text"])
        self.assertIn("level", audit)
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_release_check(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":5,"method":"tools/call",'
            '"params":{"name":"runewall.release_check","arguments":{}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 5)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        release_check = _json.loads(data["result"]["content"][0]["text"])
        self.assertIn("level", release_check)
        self.assertIn("checks", release_check)
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_doctor(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":6,"method":"tools/call",'
            '"params":{"name":"runewall.doctor","arguments":{}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 6)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        doctor = _json.loads(data["result"]["content"][0]["text"])
        self.assertIn("summary", doctor)
        self.assertIn("policy_audit", doctor)
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_maps_list(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":7,"method":"tools/call",'
            '"params":{"name":"runewall.maps_list","arguments":{}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 7)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        maps_list = _json.loads(data["result"]["content"][0]["text"])
        self.assertIn("maps", maps_list)
        self.assertTrue(any(site["key"] == "github" for site in maps_list["maps"]))
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_maps_show(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":8,"method":"tools/call",'
            '"params":{"name":"runewall.maps_show","arguments":{"site":"github","flow":"create_issue"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 8)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        maps_show = _json.loads(data["result"]["content"][0]["text"])
        self.assertEqual(maps_show["key"], "github")
        self.assertEqual(maps_show["flows"][0]["name"], "create_issue")
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_handles_tools_call_dry_run(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":9,"method":"tools/call",'
            '"params":{"name":"runewall.dry_run","arguments":{"site":"github","flow":"create_issue","inputs":{"repo":"user/repo","title":"Bug"}}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 9)
        self.assertEqual(data["result"]["content"][0]["type"], "text")
        dry_run = _json.loads(data["result"]["content"][0]["text"])
        self.assertEqual(dry_run["site"], "github")
        self.assertEqual(dry_run["flow"], "create_issue")
        self.assertTrue(dry_run["dry_run"])
        self.assertIn("create_issue", data["result"]["content"][0]["text"])
        self.assertFalse(data["result"]["isError"])

    def test_mcp_serve_once_tools_call_maps_show_missing_site_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":10,"method":"tools/call",'
            '"params":{"name":"runewall.maps_show","arguments":{"flow":"create_issue"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 10)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Missing required argument: site")

    def test_mcp_serve_once_tools_call_maps_show_missing_flow_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":11,"method":"tools/call",'
            '"params":{"name":"runewall.maps_show","arguments":{"site":"github"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 11)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Missing required argument: flow")

    def test_mcp_serve_once_tools_call_maps_show_unknown_map_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":12,"method":"tools/call",'
            '"params":{"name":"runewall.maps_show","arguments":{"site":"unknown","flow":"missing"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 12)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Map not found")

    def test_mcp_serve_once_tools_call_dry_run_missing_site_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":13,"method":"tools/call",'
            '"params":{"name":"runewall.dry_run","arguments":{"flow":"create_issue","inputs":{}}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 13)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Missing required argument: site")

    def test_mcp_serve_once_tools_call_dry_run_missing_flow_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":14,"method":"tools/call",'
            '"params":{"name":"runewall.dry_run","arguments":{"site":"github","inputs":{}}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 14)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Missing required argument: flow")

    def test_mcp_serve_once_tools_call_dry_run_unknown_map_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":15,"method":"tools/call",'
            '"params":{"name":"runewall.dry_run","arguments":{"site":"unknown","flow":"missing","inputs":{}}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 15)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Map not found")

    def test_mcp_serve_once_tools_call_missing_action_type_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":16,"method":"tools/call",'
            '"params":{"name":"runewall.policy_test","arguments":{}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 16)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Missing required argument: action_type")

    def test_mcp_serve_once_tools_call_unknown_tool_returns_invalid_params(self) -> None:
        output = io.StringIO()
        request = (
            '{"jsonrpc":"2.0","id":17,"method":"tools/call",'
            '"params":{"name":"runewall.unknown","arguments":{"action_type":"map.execute"}}}'
        )
        with patch("sys.stdin", io.StringIO(request)):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 17)
        self.assertEqual(data["error"]["code"], -32602)
        self.assertEqual(data["error"]["message"], "Unknown tool")

    def test_mcp_serve_once_unknown_method_returns_method_not_found(self) -> None:
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":18,"method":"unknown","params":{}}')):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 18)
        self.assertEqual(data["error"]["code"], -32601)
        self.assertEqual(data["error"]["message"], "Method not found")

    def test_mcp_serve_once_invalid_json_returns_parse_error(self) -> None:
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("{invalid json")):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIsNone(data["id"])
        self.assertEqual(data["error"]["code"], -32700)

    def test_mcp_serve_once_missing_method_returns_invalid_request(self) -> None:
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"jsonrpc":"2.0","id":19,"params":{}}')):
            with redirect_stdout(output):
                exit_code = main(["mcp", "serve", "--once"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["id"], 19)
        self.assertEqual(data["error"]["code"], -32600)

    def test_policy_help_exits_zero_and_mentions_audit(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as error:
                main(["policy", "--help"])
        self.assertEqual(error.exception.code, 0)
        rendered = output.getvalue()
        self.assertIn("Explain, test, list, and audit Runewall safety policies.", rendered)
        self.assertIn("audit", rendered)

    def test_release_help_exits_zero_and_mentions_check(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as error:
                main(["release", "--help"])
        self.assertEqual(error.exception.code, 0)
        rendered = output.getvalue()
        self.assertIn("Run local release readiness checks.", rendered)
        self.assertIn("check", rendered)
        self.assertIn("json-check", rendered)
        self.assertIn("examples", rendered)
        self.assertIn("status", rendered)

    def test_maps_help_exits_zero_and_mentions_lint(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as error:
                main(["maps", "--help"])
        self.assertEqual(error.exception.code, 0)
        rendered = output.getvalue()
        self.assertIn("Inspect bundled action maps.", rendered)
        self.assertIn("lint", rendered)

    def test_version_prints_human_readable_output(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["version"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue().strip()
        self.assertEqual(rendered, "Runewall 0.6.0")
        self.assertNotIn("{", rendered)

    def test_version_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["version", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["name"], "runewall")
        self.assertEqual(data["version"], "0.6.0")

    def test_version_json_matches_human_version(self) -> None:
        human_output = io.StringIO()
        json_output = io.StringIO()
        with redirect_stdout(human_output):
            main(["version"])
        with redirect_stdout(json_output):
            main(["version", "--json"])
        import json as _json
        data = _json.loads(json_output.getvalue())
        self.assertIn(data["version"], human_output.getvalue())

    def test_init_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "runewall.db").exists())
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())
            self.assertIn("Initialized Runewall at", output.getvalue())

    def test_init_json_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["init", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["initialized"])
        self.assertIn("database_path", data)
        self.assertIn("config_path", data)

    def test_init_json_creates_database_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["init", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertTrue((Path(temp_dir) / ".runewall" / "runewall.db").exists())
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())

    def test_init_json_does_not_overwrite_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            try:
                os.chdir(temp_dir)
                main(["init"])
                config_file.write_text("[custom]\nvalue = true\n", encoding="utf-8")
                main(["init", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(
                config_file.read_text(encoding="utf-8"),
                "[custom]\nvalue = true\n",
            )

    def test_init_json_idempotent_returns_ok_when_already_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["init", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["initialized"])

    def test_init_human_output_unchanged_after_json_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["init"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIn("Initialized Runewall at", output.getvalue())
        self.assertNotIn("{", output.getvalue())

    def test_config_path_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "path"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue().strip()
        self.assertEqual(exit_code, 0)
        self.assertEqual(rendered, str(config_path(Path(temp_dir)).resolve()))

    def test_config_show_does_not_print_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                "\n".join(
                    [
                        "[safety]",
                        'default_policy = "review"',
                        "",
                        "[auth]",
                        'github_token_env = "GITHUB_TOKEN"',
                        'github_token = "super-secret-token"',
                    ]
                ),
                encoding="utf-8",
            )
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "show"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("[auth]", rendered)
        self.assertIn('github_token_env = "GITHUB_TOKEN"', rendered)
        self.assertIn('github_token = "***REDACTED***"', rendered)
        self.assertNotIn("super-secret-token", rendered)

    def test_log_command_with_empty_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["log"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), EMPTY_LOG_MESSAGE)

    def test_maps_list_prints_github_vercel_netlify_and_cloudflare(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "list"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("site_name\tbase_url\tflows", rendered)
        self.assertIn("GitHub", rendered)
        self.assertIn("https://github.com", rendered)
        self.assertIn("Vercel", rendered)
        self.assertIn("https://vercel.com", rendered)
        self.assertIn("Netlify", rendered)
        self.assertIn("https://app.netlify.com", rendered)
        self.assertIn("Cloudflare", rendered)
        self.assertIn("https://dash.cloudflare.com", rendered)

    def test_maps_path_prints_absolute_bundled_maps_path(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "path"])

        rendered = output.getvalue().strip()
        normalized = rendered.replace("\\", "/")
        self.assertEqual(exit_code, 0)
        self.assertTrue(Path(rendered).is_absolute())
        self.assertIn("maps/sites", normalized)

    def test_maps_show_github_prints_create_issue(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Base URL: https://github.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- create_issue", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: True", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: repo, title", rendered)

    def test_maps_show_vercel_prints_list_projects(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "vercel"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Vercel", rendered)
        self.assertIn("Base URL: https://vercel.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_projects", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_show_netlify_prints_list_sites(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "netlify"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Netlify", rendered)
        self.assertIn("Base URL: https://app.netlify.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_sites", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_show_cloudflare_prints_list_zones(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "cloudflare"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Cloudflare", rendered)
        self.assertIn("Base URL: https://dash.cloudflare.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_zones", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_list_includes_linear(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Linear", rendered)
        self.assertIn("https://linear.app", rendered)

    def test_maps_show_linear_prints_create_issue(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "linear"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Linear", rendered)
        self.assertIn("Base URL: https://linear.app", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- create_issue", rendered)
        self.assertIn("risk_level: medium", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: team_id, title", rendered)

    def test_maps_validate_includes_linear_ok(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("linear (Linear)\tOK", rendered)

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_linear_create_issue(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "linear", "create_issue", "--dry-run",
                        "--input", "team_id=team123",
                        "--input", "title=Bug report",
                    ])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Linear", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Risk level: medium", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("- team_id=team123", rendered)
        self.assertIn("- title=Bug report", rendered)
        self.assertIn("Missing inputs: none", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_json_for_linear_create_issue(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "linear", "create_issue", "--dry-run", "--json",
                "--input", "team_id=team123",
                "--input", "title=Bug report",
            ])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "linear")
        self.assertEqual(data["flow"], "create_issue")
        self.assertEqual(data["risk_level"], "medium")
        self.assertFalse(data["reversible"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertEqual(data["api_path"], {"method": "POST", "url": "/graphql"})
        self.assertEqual(data["policy"], "auto")
        self.assertEqual(data["decision"], "allow")
        self.assertEqual(data["policy_source"], "config_rule")
        self.assertEqual(data["policy_reason"], 'rules.map_dry_run = "auto"')

    def test_maps_list_includes_supabase(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Supabase", rendered)
        self.assertIn("https://supabase.com", rendered)

    def test_maps_show_supabase_prints_list_projects(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "supabase"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Supabase", rendered)
        self.assertIn("Base URL: https://supabase.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- list_projects", rendered)
        self.assertIn("risk_level: low", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: none", rendered)

    def test_maps_validate_includes_supabase_ok(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("supabase (Supabase)\tOK", rendered)

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_supabase_list_projects(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "supabase", "list_projects", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Supabase", rendered)
        self.assertIn("Flow name: list_projects", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /v1/projects", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_json_for_supabase_list_projects(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["act", "supabase", "list_projects", "--dry-run", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "supabase")
        self.assertEqual(data["flow"], "list_projects")
        self.assertEqual(data["risk_level"], "low")
        self.assertFalse(data["reversible"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertEqual(data["api_path"], {"method": "GET", "url": "/v1/projects"})

    def test_maps_list_includes_slack(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Slack", rendered)
        self.assertIn("https://slack.com", rendered)

    def test_maps_show_slack_prints_send_message(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "slack"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Slack", rendered)
        self.assertIn("Base URL: https://slack.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- send_message", rendered)
        self.assertIn("risk_level: medium", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: channel, text", rendered)

    def test_maps_validate_includes_slack_ok(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("slack (Slack)\tOK", rendered)

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_slack_send_message(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "slack", "send_message", "--dry-run",
                        "--input", "channel=C123",
                        "--input", "text=Hello",
                    ])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Slack", rendered)
        self.assertIn("Flow name: send_message", rendered)
        self.assertIn("Risk level: medium", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("- channel=C123", rendered)
        self.assertIn("- text=Hello", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: POST /api/chat.postMessage", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_json_for_slack_send_message(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "slack", "send_message", "--dry-run", "--json",
                "--input", "channel=C123",
                "--input", "text=Hello",
            ])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "slack")
        self.assertEqual(data["flow"], "send_message")
        self.assertEqual(data["risk_level"], "medium")
        self.assertFalse(data["reversible"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertEqual(data["api_path"], {"method": "POST", "url": "/api/chat.postMessage"})

    def test_act_dry_run_slack_missing_text_fails_clearly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "slack", "send_message", "--dry-run",
                "--input", "channel=C123",
            ])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("Missing inputs: text", rendered)
        self.assertIn("Missing required inputs: text", rendered)

    def test_maps_list_includes_discord(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Discord", rendered)
        self.assertIn("https://discord.com", rendered)

    def test_maps_show_discord_prints_send_message(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "discord"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Discord", rendered)
        self.assertIn("Base URL: https://discord.com", rendered)
        self.assertIn("Map version: 0.1.0", rendered)
        self.assertIn("Schema version: 1.0.0", rendered)
        self.assertIn("- send_message", rendered)
        self.assertIn("risk_level: medium", rendered)
        self.assertIn("reversible: False", rendered)
        self.assertIn("requires_auth: True", rendered)
        self.assertIn("required inputs: channel_id, content", rendered)

    def test_maps_validate_includes_discord_ok(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("discord (Discord)\tOK", rendered)

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_discord_send_message(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "discord", "send_message", "--dry-run",
                        "--input", "channel_id=123",
                        "--input", "content=Hello",
                    ])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Discord", rendered)
        self.assertIn("Flow name: send_message", rendered)
        self.assertIn("Risk level: medium", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("- channel_id=123", rendered)
        self.assertIn("- content=Hello", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: POST /api/v10/channels/{channel_id}/messages", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_json_for_discord_send_message(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "discord", "send_message", "--dry-run", "--json",
                "--input", "channel_id=123",
                "--input", "content=Hello",
            ])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "discord")
        self.assertEqual(data["flow"], "send_message")
        self.assertEqual(data["risk_level"], "medium")
        self.assertFalse(data["reversible"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertEqual(data["api_path"], {"method": "POST", "url": "/api/v10/channels/{channel_id}/messages"})

    def test_act_dry_run_discord_missing_content_fails_clearly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "discord", "send_message", "--dry-run",
                "--input", "channel_id=123",
            ])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("Missing inputs: content", rendered)
        self.assertIn("Missing required inputs: content", rendered)

    def test_maps_show_unknown_site_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "show", "unknown"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Site map not found: unknown")

    @patch.object(SiteMapRegistry, "bundled_maps_path")
    def test_maps_path_missing_directory_fails_clearly(self, mocked_path) -> None:
        mocked_path.return_value = Path("missing-maps-dir")
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "path"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Bundled maps directory not found: missing-maps-dir")

    def test_maps_validate_prints_ok_for_github_vercel_netlify_and_cloudflare(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("github (GitHub)\tOK", rendered)
        self.assertIn("vercel (Vercel)\tOK", rendered)
        self.assertIn("netlify (Netlify)\tOK", rendered)
        self.assertIn("cloudflare (Cloudflare)\tOK", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_prints_dependency_checks(self, mocked_find_spec) -> None:
        def fake_find_spec(name: str) -> object | None:
            if name in {"httpx", "bs4"}:
                return object()
            return None

        mocked_find_spec.side_effect = fake_find_spec
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Dependency httpx: OK", rendered)
        self.assertIn("Dependency bs4: OK", rendered)
        self.assertIn("Bundled maps:", rendered)
        self.assertIn("Summary: WARN", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "super-secret-token"}, clear=True)
    def test_doctor_does_not_print_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["doctor"])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("GITHUB_TOKEN: set", rendered)
        self.assertNotIn("super-secret-token", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_handles_missing_runewall_cleanly(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Runewall DB: missing", rendered)
        self.assertIn("Summary: WARN", rendered)

    def test_doctor_shows_config_present_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Config: present", rendered)

    def test_doctor_shows_config_missing_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Config: missing", rendered)

    def test_doctor_shows_map_execution_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: disabled", rendered)

    def test_doctor_includes_policy_audit_ok_for_safe_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy audit: OK", output.getvalue())

    def test_doctor_shows_map_execution_enabled_when_config_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: ENABLED", rendered)

    def test_doctor_summary_is_warn_when_map_execution_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Map execution: ENABLED", rendered)
            self.assertIn("Summary: WARN", rendered)
            self.assertIn("Policy audit: WARN", rendered)
            self.assertIn("- maps.allow_execute is true; real external execution is enabled.", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_prints_valid_json(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("python", data)
        self.assertIn("database", data)
        self.assertIn("config", data)
        self.assertIn("dependencies", data)
        self.assertIn("auth", data)
        self.assertIn("maps", data)
        self.assertIn("summary", data)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "super-secret-token"}, clear=True)
    def test_doctor_json_does_not_print_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["doctor", "--json"])
        self.assertEqual(exit_code, 0)
        self.assertNotIn("super-secret-token", output.getvalue())
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["github_token"], "present")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_shows_config_present_after_init(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["config"]["present"])

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_shows_config_missing_before_init(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["config"]["present"])

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_shows_map_execution_disabled_by_default(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["config"]["map_execution"], "disabled")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_policy_audit_ok_for_safe_profile(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["policy_audit"]["level"], "OK")
        self.assertEqual(data["policy_audit"]["warnings"], [])

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_shows_warn_when_map_execution_enabled(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["config"]["map_execution"], "ENABLED")
        self.assertEqual(data["summary"], "WARN")
        self.assertEqual(data["policy_audit"]["level"], "WARN")
        self.assertEqual(
            data["policy_audit"]["warnings"],
            [{"key": "maps.allow_execute", "message": "real external execution is enabled"}],
        )

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_policy_audit_invalid_updates_summary(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text("[safety]\nmax_snapshot_mb = 0\n", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["policy_audit"]["level"], "INVALID")
        self.assertEqual(data["policy_audit"]["warnings"], [])
        self.assertEqual(data["policy_audit"]["errors"], [{"key": "safety.max_snapshot_mb", "message": "must be a positive integer"}])
        self.assertEqual(data["summary"], "FAIL")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_normal_human_output_unchanged(self, mocked_find_spec) -> None:
        def fake_find_spec(name: str) -> object | None:
            if name in {"httpx", "bs4"}:
                return object()
            return None

        mocked_find_spec.side_effect = fake_find_spec
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Python:", rendered)
        self.assertIn("Runewall DB:", rendered)
        self.assertIn("Config:", rendered)
        self.assertIn("Summary:", rendered)
        self.assertNotIn("{", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_shows_vercel_token_missing(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("VERCEL_TOKEN: missing", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"VERCEL_TOKEN": "secret-vercel-token"}, clear=True)
    def test_doctor_shows_vercel_token_present(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["doctor"])
        self.assertEqual(exit_code, 0)
        self.assertIn("VERCEL_TOKEN: set", output.getvalue())
        self.assertNotIn("secret-vercel-token", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_vercel_token(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("vercel_token", data["auth"])
        self.assertEqual(data["auth"]["vercel_token"], "missing")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"VERCEL_TOKEN": "secret-vercel-token"}, clear=True)
    def test_doctor_json_does_not_print_vercel_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor", "--json"])
        self.assertNotIn("secret-vercel-token", output.getvalue())
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["vercel_token"], "present")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_shows_netlify_token_missing(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor"])
            finally:
                os.chdir(original_cwd)
        self.assertIn("NETLIFY_TOKEN: missing", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"NETLIFY_TOKEN": "secret-netlify-token"}, clear=True)
    def test_doctor_shows_netlify_token_present(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor"])
        self.assertIn("NETLIFY_TOKEN: set", output.getvalue())
        self.assertNotIn("secret-netlify-token", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_netlify_token(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("netlify_token", data["auth"])
        self.assertEqual(data["auth"]["netlify_token"], "missing")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"NETLIFY_TOKEN": "secret-netlify-token"}, clear=True)
    def test_doctor_json_does_not_print_netlify_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor", "--json"])
        self.assertNotIn("secret-netlify-token", output.getvalue())
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["netlify_token"], "present")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_shows_supabase_token_missing(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor"])
            finally:
                os.chdir(original_cwd)
        self.assertIn("SUPABASE_ACCESS_TOKEN: missing", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"SUPABASE_ACCESS_TOKEN": "secret-supabase-token"}, clear=True)
    def test_doctor_shows_supabase_token_present(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor"])
        self.assertIn("SUPABASE_ACCESS_TOKEN: set", output.getvalue())
        self.assertNotIn("secret-supabase-token", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_supabase_access_token(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("supabase_access_token", data["auth"])
        self.assertEqual(data["auth"]["supabase_access_token"], "missing")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"SUPABASE_ACCESS_TOKEN": "secret-supabase-token"}, clear=True)
    def test_doctor_json_does_not_print_supabase_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor", "--json"])
        self.assertNotIn("secret-supabase-token", output.getvalue())
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["supabase_access_token"], "present")

    def test_maps_stats_json_includes_supabase_in_real_execution_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("supabase", data["real_execution_maps"])

    def test_maps_stats_json_does_not_include_supabase_in_dry_run_only(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertNotIn("supabase", data["dry_run_only_maps"])

    def test_maps_stats_human_includes_supabase_in_real_execution(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats"])
        self.assertIn("supabase", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_shows_cloudflare_token_missing(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor"])
            finally:
                os.chdir(original_cwd)
        self.assertIn("CLOUDFLARE_API_TOKEN: missing", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "secret-cf-token"}, clear=True)
    def test_doctor_shows_cloudflare_token_present(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor"])
        self.assertIn("CLOUDFLARE_API_TOKEN: set", output.getvalue())
        self.assertNotIn("secret-cf-token", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_cloudflare_api_token(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("cloudflare_api_token", data["auth"])
        self.assertEqual(data["auth"]["cloudflare_api_token"], "missing")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "secret-cf-token"}, clear=True)
    def test_doctor_json_does_not_print_cloudflare_token_value(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        output = io.StringIO()
        with redirect_stdout(output):
            main(["doctor", "--json"])
        self.assertNotIn("secret-cf-token", output.getvalue())
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["cloudflare_api_token"], "present")

    def test_maps_stats_json_includes_cloudflare_in_real_execution_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("cloudflare", data["real_execution_maps"])

    def test_maps_stats_json_does_not_include_cloudflare_in_dry_run_only(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertNotIn("cloudflare", data["dry_run_only_maps"])

    def test_maps_stats_human_includes_cloudflare_in_real_execution(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats"])
        self.assertIn("cloudflare", output.getvalue())
        self.assertIn("Real execution:", output.getvalue())

    def test_maps_stats_includes_netlify_in_real_execution(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats"])
        self.assertIn("netlify", output.getvalue())
        self.assertIn("Real execution:", output.getvalue())

    def test_maps_stats_json_includes_netlify_in_real_execution_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("netlify", data["real_execution_maps"])

    def test_maps_stats_json_does_not_include_netlify_in_dry_run_only(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertNotIn("netlify", data["dry_run_only_maps"])

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_github_create_issue(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                            "--input",
                            "body=Details",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: True", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("- repo=user/repo", rendered)
        self.assertIn("- title=Bug report", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_vercel_list_projects(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "vercel", "list_projects", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Vercel", rendered)
        self.assertIn("Flow name: list_projects", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /v9/projects", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_netlify_list_sites(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "netlify", "list_sites", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Netlify", rendered)
        self.assertIn("Flow name: list_sites", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /api/v1/sites", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    @patch("runewall.cli.main.execute_map_action")
    def test_act_dry_run_for_cloudflare_list_zones(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["act", "cloudflare", "list_zones", "--dry-run"])
            finally:
                os.chdir(original_cwd)

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Site name: Cloudflare", rendered)
        self.assertIn("Flow name: list_zones", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Reversible: False", rendered)
        self.assertIn("Requires auth: True", rendered)
        self.assertIn("Provided inputs:", rendered)
        self.assertIn("- none", rendered)
        self.assertIn("Missing inputs: none", rendered)
        self.assertIn("API path: GET /client/v4/zones", rendered)
        self.assertIn("Runewall is not initialized; dry run was not logged.", rendered)
        mocked_execute.assert_not_called()

    def test_act_dry_run_missing_required_input_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(
                [
                    "act",
                    "github",
                    "create_issue",
                    "--dry-run",
                    "--input",
                    "repo=user/repo",
                ]
            )

        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("Missing inputs: title", rendered)
        self.assertIn("Missing required inputs: title", rendered)

    def test_act_dry_run_with_init_logs_map_dry_run_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.target, "github:create_issue")
        self.assertEqual(action.status, "success")
        self.assertEqual(
            action.params,
            {"site": "github", "flow": "create_issue", "inputs": {"repo": "user/repo", "title": "Bug report"}},
        )
        self.assertEqual(
            action.result,
            {"risk_level": "low", "reversible": True, "requires_auth": True, "executed": False},
        )
        self.assertNotIn("Runewall is not initialized; dry run was not logged.", output.getvalue())

    def test_act_execute_is_blocked_by_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "failed")
        self.assertEqual(
            action.result,
            {"error": "Map execution is disabled by config. Set [maps] allow_execute = true to enable."},
        )
        self.assertEqual(
            output.getvalue().strip(),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    def test_act_dry_run_failed_logs_failed_if_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--dry-run",
                            "--input",
                            "repo=user/repo",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.status, "failed")
        self.assertEqual(
            action.result,
            {"error": "Missing required inputs: title"},
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_is_blocked_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            output.getvalue().strip(),
            "Map execution is disabled by config. Set [maps] allow_execute = true to enable.",
        )

    def test_act_dry_run_unknown_site_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["act", "unknown", "create_issue", "--dry-run"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Site map not found: unknown")

    def test_act_dry_run_unknown_flow_fails_clearly(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["act", "github", "unknown_flow", "--dry-run"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Flow not found for GitHub: unknown_flow")

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_allowed_reaches_existing_token_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                config_file = Path.cwd() / ".runewall" / "config.toml"
                config_file.write_text(
                    config_file.read_text(encoding="utf-8").replace("allow_execute = false", "allow_execute = true"),
                    encoding="utf-8",
                )
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "failed")
        self.assertEqual(action.result, {"error": "GITHUB_TOKEN is required to execute github:create_issue."})
        self.assertNotIn("GITHUB_TOKEN", str(action.params))
        self.assertEqual(output.getvalue().strip(), "GITHUB_TOKEN is required to execute github:create_issue.")

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_success_logs_map_execute_without_token(self, mocked_execute) -> None:
        mocked_execute.return_value = {
            "issue_url": "https://github.com/user/repo/issues/1",
            "issue_number": 1,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                config_file = Path.cwd() / ".runewall" / "config.toml"
                config_file.write_text(
                    config_file.read_text(encoding="utf-8").replace("allow_execute = false", "allow_execute = true"),
                    encoding="utf-8",
                )
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "github",
                            "create_issue",
                            "--execute",
                            "--input",
                            "repo=user/repo",
                            "--input",
                            "title=Bug report",
                            "--input",
                            "body=Details",
                        ]
                    )
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.execute")
        self.assertEqual(action.status, "success")
        self.assertEqual(
            action.result,
            {"issue_url": "https://github.com/user/repo/issues/1", "issue_number": 1},
        )
        self.assertNotIn("secret-token", str(action.params))
        self.assertNotIn("secret-token", str(action.result))
        self.assertIn("Created GitHub issue for user/repo.", output.getvalue())

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=True)
    def test_act_execute_unsupported_site_flow_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "act",
                            "linear",
                            "create_issue",
                            "--execute",
                            "--input", "team_id=t",
                            "--input", "title=Bug",
                        ]
                    )
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertEqual(output.getvalue().strip(), "Execution is not supported for linear:create_issue.")

    def test_status_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output.getvalue().strip(),
                "Runewall is not initialized. Run `runewall init` first.",
            )

    def test_pending_before_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output.getvalue().strip(),
                "Runewall is not initialized. Run `runewall init` first.",
            )

    def test_pending_after_init_with_no_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "No pending actions.")

    def test_pending_shows_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                log.add_action(Action(action_type="file.write", target="done.txt", status="success"))
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("id\ttimestamp\taction_type\ttarget\tstatus", rendered)
            self.assertIn("file.delete", rendered)
            self.assertIn("old.txt", rendered)
            self.assertIn("pending", rendered)
            self.assertNotIn("done.txt", rendered)

    def test_status_after_init_with_no_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Database:", rendered)
            self.assertIn("Total actions: 0", rendered)
            self.assertIn("Success actions: 0", rendered)
            self.assertIn("Failed actions: 0", rendered)
            self.assertIn("Rolled back actions: 0", rendered)
            self.assertIn("Latest action: none", rendered)

    def test_status_after_at_least_one_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(
                    Action(
                        action_type="file.write",
                        target="demo.txt",
                        status="success",
                    )
                )
                with redirect_stdout(output):
                    exit_code = main(["status"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Total actions: 1", rendered)
            self.assertIn("Success actions: 1", rendered)
            self.assertIn("Failed actions: 0", rendered)
            self.assertIn("Rolled back actions: 0", rendered)
            self.assertIn("Latest action:", rendered)
            self.assertIn("file.write", rendered)
            self.assertIn("demo.txt", rendered)

    def test_approve_changes_pending_to_approved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt"))
                with redirect_stdout(output):
                    exit_code = main(["approve", action.id])
                updated = log.get_action(action.id)
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "approved")
            self.assertIn(f"Approved action {action.id}.", output.getvalue())

    def test_reject_changes_pending_to_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt"))
                with redirect_stdout(output):
                    exit_code = main(["reject", action.id])
                updated = log.get_action(action.id)
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIsNotNone(updated)
            assert updated is not None
            self.assertEqual(updated.status, "rejected")
            self.assertIn(f"Rejected action {action.id}.", output.getvalue())

    def test_approving_non_existent_action_gives_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["approve", "missing-id"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), "Action not found: missing-id")

    def test_rejecting_non_existent_action_gives_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["reject", "missing-id"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), "Action not found: missing-id")

    def test_execute_non_approved_action_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                with redirect_stdout(output):
                    exit_code = main(["execute", action.id])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            self.assertEqual(output.getvalue().strip(), f"Action {action.id} is not approved.")

    def test_approve_json_success_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                with redirect_stdout(output):
                    exit_code = main(["approve", action.id, "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_id"], action.id)
        self.assertEqual(data["status"], "approved")

    def test_reject_json_success_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                with redirect_stdout(output):
                    exit_code = main(["reject", action.id, "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_id"], action.id)
        self.assertEqual(data["status"], "rejected")

    def test_execute_json_success_for_approved_file_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                target_file = Path(temp_dir) / "to_delete.txt"
                target_file.write_text("content", encoding="utf-8")
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(
                    action_type="file.delete",
                    target=str(target_file),
                    status="approved",
                ))
                with redirect_stdout(output):
                    exit_code = main(["execute", action.id, "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_id"], action.id)
        self.assertEqual(data["status"], "success")

    def test_rollback_json_success_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                root = Path(temp_dir)
                target = root / "notes.txt"
                target.write_text("before", encoding="utf-8")
                log = ActionLog(root=root)
                action = log.add_action(Action(action_type="file.write", target="notes.txt", status="approved"))
                log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))
                target.write_text("after", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["rollback", action.id, "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_id"], action.id)
        self.assertEqual(data["status"], "rolled_back")

    def test_rollback_last_json_success_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                root = Path(temp_dir)
                target = root / "last.txt"
                target.write_text("before", encoding="utf-8")
                log = ActionLog(root=root)
                action = log.add_action(Action(action_type="file.write", target="last.txt", status="approved"))
                log.add_snapshot(SnapshotEngine(root=root).create_snapshot(action))
                target.write_text("after", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["rollback", "--last", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_id"], action.id)
        self.assertEqual(data["status"], "rolled_back")

    def test_approve_json_missing_action_prints_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["approve", "missing-id", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["action_id"], "missing-id")
        self.assertIn("not found", data["error"].lower())

    def test_human_approval_output_unchanged_after_json_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                action = log.add_action(Action(action_type="file.delete", target="old.txt", status="pending"))
                approve_output = io.StringIO()
                with redirect_stdout(approve_output):
                    exit_code_approve = main(["approve", action.id])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code_approve, 0)
        self.assertIn(f"Approved action {action.id}.", approve_output.getvalue())
        self.assertNotIn("{", approve_output.getvalue())

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Main Heading", "Section Heading"],
            "text": "Hello world from Runewall. " * 20,
        },
    )
    def test_read_command_prints_structured_preview(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
            finally:
                os.chdir(original_cwd)

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIn("Title: Example Page", rendered)
            self.assertIn("Headings:", rendered)
            self.assertIn("- Main Heading", rendered)
            self.assertIn("- Section Heading", rendered)
            self.assertIn("Text preview:", rendered)
            self.assertIn("Hello world from Runewall.", rendered)
            self.assertIn("Runewall is not initialized; read action was not logged.", rendered)

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Main Heading"],
            "text": "Hello world from Runewall.",
        },
    )
    def test_read_with_init_logs_web_read_success(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "web.read")
            self.assertEqual(action.target, "https://example.com")
            self.assertEqual(action.status, "success")
            self.assertEqual(action.params, {"mode": "universal_read"})
            self.assertEqual(action.result, {"title": "Example Page", "heading_count": 1, "text_length": 26})
            self.assertNotIn("Runewall is not initialized; read action was not logged.", output.getvalue())

    def test_config_validate_default_config_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("OK", output.getvalue())

    def test_config_validate_json_default_config_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "validate", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["errors"], [])

    def test_config_validate_invalid_max_snapshot_mb_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[safety]\nmax_snapshot_mb = -1\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["config", "validate", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any(e["key"] == "safety.max_snapshot_mb" for e in data["errors"]))

    def test_config_validate_invalid_snapshot_days_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[retention]\nsnapshot_days = 0\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["config", "validate", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any(e["key"] == "retention.snapshot_days" for e in data["errors"]))

    def test_config_validate_invalid_allow_execute_type_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text('[maps]\nallow_execute = "yes"\n', encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["config", "validate", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any(e["key"] == "maps.allow_execute" for e in data["errors"]))

    def test_config_reset_writes_default_safe_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["config", "reset"])
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
            finally:
                os.chdir(original_cwd)
            self.assertTrue(config_file.exists())
            content = config_file.read_text(encoding="utf-8")
            self.assertIn("allow_execute = false", content)
            self.assertIn("GITHUB_TOKEN", content)
            self.assertIn("CLOUDFLARE_API_TOKEN", content)

    def test_config_reset_keeps_allow_execute_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                main(["config", "reset"])
            finally:
                os.chdir(original_cwd)
            from runewall.core.config import load_config
            self.assertFalse(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_reset_json_returns_ok_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "reset", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["reset"])
        self.assertIn("path", data)

    def test_config_reset_does_not_delete_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "reset"])
                db_path = Path(temp_dir) / ".runewall" / "runewall.db"
            finally:
                os.chdir(original_cwd)
            self.assertTrue(db_path.exists())

    def test_config_set_maps_allow_execute_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "Updated config: maps.allow_execute = true")
            from runewall.core.config import load_config
            self.assertTrue(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_set_safety_max_snapshot_mb(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "100"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "Updated config: safety.max_snapshot_mb = 100")
            from runewall.core.config import load_config
            self.assertEqual(load_config(Path(temp_dir)).safety.max_snapshot_mb, 100)

    def test_config_set_creates_config_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())
            from runewall.core.config import load_config
            self.assertTrue(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_set_unknown_key_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.unknown_key", "true"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Unknown config key: maps.unknown_key", output.getvalue())

    def test_config_set_invalid_boolean_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "yes"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid boolean for maps.allow_execute", output.getvalue())
        self.assertIn("Use true or false", output.getvalue())

    def test_config_set_invalid_integer_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "abc"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Invalid integer for safety.max_snapshot_mb", output.getvalue())

    def test_config_set_json_boolean_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["key"], "maps.allow_execute")
        self.assertIs(data["value"], True)
        self.assertIn("config_path", data)

    def test_config_set_json_integer_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "100", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["key"], "safety.max_snapshot_mb")
        self.assertEqual(data["value"], 100)
        self.assertIsInstance(data["value"], int)

    def test_config_set_json_creates_config_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(temp_dir) / ".runewall" / "config.toml").exists())
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["ok"])

    def test_config_set_json_unknown_key_prints_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "unknown.key", "value", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["key"], "unknown.key")
        self.assertIn("Unknown config key", data["error"])

    def test_config_set_json_invalid_boolean_prints_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "yes", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["key"], "maps.allow_execute")
        self.assertIn("Invalid boolean", data["error"])

    def test_config_set_json_invalid_integer_prints_json_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "safety.max_snapshot_mb", "abc", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["key"], "safety.max_snapshot_mb")
        self.assertIn("Invalid integer", data["error"])

    def test_config_set_human_output_unchanged_after_json_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "maps.allow_execute", "true"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "Updated config: maps.allow_execute = true")
        self.assertNotIn("{", output.getvalue())

    def test_config_path_json_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "path", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("path", data)
        self.assertIn("exists", data)

    def test_config_path_json_exists_true_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "path", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["exists"])
        self.assertIn(".runewall", data["path"])

    def test_config_show_json_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "show", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("config", data)
        cfg = data["config"]
        self.assertIn("safety", cfg)
        self.assertIn("retention", cfg)
        self.assertIn("maps", cfg)
        self.assertIn("auth", cfg)

    def test_config_show_json_safe_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "show", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["exists"])
        self.assertIn("config", data)
        self.assertFalse(data["config"]["maps"]["allow_execute"])
        self.assertNotIn("super-secret", output.getvalue())

    def test_config_show_json_reflects_allow_execute_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "show", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["config"]["maps"]["allow_execute"])

    def test_config_show_json_does_not_print_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                "[auth]\ngithub_token = \"super-secret-token\"\n",
                encoding="utf-8",
            )
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "show", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertNotIn("super-secret-token", output.getvalue())

    def test_config_normal_human_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                path_output = io.StringIO()
                with redirect_stdout(path_output):
                    exit_code_path = main(["config", "path"])
                show_output = io.StringIO()
                with redirect_stdout(show_output):
                    exit_code_show = main(["config", "show"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code_path, 0)
        self.assertIn(".runewall", path_output.getvalue())
        self.assertNotIn("{", path_output.getvalue())
        self.assertEqual(exit_code_show, 0)
        self.assertIn("[safety]", show_output.getvalue())
        self.assertIn("[maps]", show_output.getvalue())

    @patch("runewall.cli.main.read_url", side_effect=RuntimeError("network down"))
    def test_failed_read_logs_failed_if_db_exists(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 1)
            mocked_read.assert_called_once_with("https://example.com")
            self.assertIsNotNone(action)
            assert action is not None
            self.assertEqual(action.action_type, "web.read")
            self.assertEqual(action.status, "failed")
            self.assertEqual(action.result, {"error": "network down"})
            self.assertEqual(output.getvalue().strip(), "Read failed: network down")


    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Heading One", "Heading Two"],
            "text": "Some text content.",
        },
    )
    def test_read_json_success_prints_valid_json(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["url"], "https://example.com")
        self.assertEqual(data["title"], "Example Page")
        self.assertEqual(data["headings"], ["Heading One", "Heading Two"])
        self.assertEqual(data["text"], "Some text content.")
        self.assertFalse(data["logged"])

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": [],
            "text": "Some text.",
        },
    )
    def test_read_json_with_init_includes_logged_true_and_logs_action(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com", "--json"])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["logged"])
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "web.read")
        self.assertEqual(action.status, "success")

    @patch("runewall.cli.main.read_url", side_effect=RuntimeError("network down"))
    def test_read_json_failure_prints_valid_json_and_exits_nonzero(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["url"], "https://example.com")
        self.assertIn("network down", data["error"])

    @patch(
        "runewall.cli.main.read_url",
        return_value={
            "url": "https://example.com",
            "title": "Example Page",
            "headings": ["Heading"],
            "text": "Text content.",
        },
    )
    def test_read_human_output_unchanged_after_json_added(self, mocked_read) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["read", "https://example.com"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Title: Example Page", rendered)
        self.assertIn("- Heading", rendered)
        self.assertIn("Text preview:", rendered)
        self.assertNotIn("{", rendered)

    def test_cleanup_snapshots_with_no_snapshots_dir_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip(), "No snapshots directory found.")

    def test_cleanup_snapshots_reports_deleted_count(self) -> None:
        import os as _os
        import time as _time

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                snapshots_dir = Path.cwd() / ".runewall" / "snapshots"
                snapshots_dir.mkdir(parents=True, exist_ok=True)
                old_snap = snapshots_dir / "old_snap"
                old_snap.mkdir()
                old_time = _time.time() - 31 * 86400
                _os.utime(old_snap, (old_time, old_time))
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIn("Deleted 1 old snapshot(s).", output.getvalue())


    def test_cleanup_snapshots_json_no_dir_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["snapshots_directory_exists"])
        self.assertEqual(data["deleted_count"], 0)
        self.assertNotIn("retention_days", data)

    def test_cleanup_snapshots_json_includes_retention_days_when_dir_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                snapshots_dir = Path.cwd() / ".runewall" / "snapshots"
                snapshots_dir.mkdir(parents=True, exist_ok=True)
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["snapshots_directory_exists"])
        self.assertIn("retention_days", data)
        self.assertEqual(data["retention_days"], 30)

    def test_cleanup_snapshots_json_reports_deleted_count(self) -> None:
        import os as _os
        import time as _time

        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                snapshots_dir = Path.cwd() / ".runewall" / "snapshots"
                snapshots_dir.mkdir(parents=True, exist_ok=True)
                old_snap = snapshots_dir / "old_snap"
                old_snap.mkdir()
                old_time = _time.time() - 31 * 86400
                _os.utime(old_snap, (old_time, old_time))
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["snapshots_directory_exists"])
        self.assertEqual(data["deleted_count"], 1)
        self.assertEqual(data["retention_days"], 30)

    def test_cleanup_snapshots_human_output_unchanged_after_json_added(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["cleanup", "snapshots"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "No snapshots directory found.")

    def test_status_json_before_init_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["status", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertFalse(data["initialized"])
            self.assertIn("database_path", data)

    def test_status_json_after_init_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["status", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertIn("total_actions", data)
            self.assertIn("success_count", data)
            self.assertIn("failed_count", data)
            self.assertIn("rolled_back_count", data)
            self.assertIn("pending_count", data)
            self.assertIn("latest_action", data)

    def test_log_json_empty_db_prints_empty_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["log", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertEqual(data, [])

    def test_log_json_after_action_includes_action_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(
                    action_type="file.write",
                    target="demo.txt",
                    status="success",
                    params={"mode": "overwrite"},
                    result={"bytes": 42},
                ))
                with redirect_stdout(output):
                    exit_code = main(["log", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertEqual(len(data), 1)
            entry = data[0]
            self.assertEqual(entry["action_type"], "file.write")
            self.assertEqual(entry["target"], "demo.txt")
            self.assertEqual(entry["status"], "success")
            self.assertEqual(entry["params"], {"mode": "overwrite"})
            self.assertEqual(entry["result"], {"bytes": 42})
            self.assertIn("id", entry)
            self.assertIn("timestamp", entry)

    def test_normal_status_and_log_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code_status = main(["status"])
                status_out = output.getvalue()
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code_log = main(["log"])
                log_out = output.getvalue()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code_status, 0)
            self.assertIn("Database:", status_out)
            self.assertIn("Total actions:", status_out)
            self.assertEqual(exit_code_log, 0)
            self.assertIn(EMPTY_LOG_MESSAGE, log_out)


    def test_pending_json_before_init_prints_initialized_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertFalse(data["initialized"])
            self.assertEqual(data["pending"], [])

    def test_pending_json_after_init_with_no_pending_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertEqual(data["pending"], [])

    def test_pending_json_with_pending_action_includes_action_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                log = ActionLog(root=Path.cwd())
                log.add_action(Action(
                    action_type="file.delete",
                    target="old.txt",
                    status="pending",
                    params={"reason": "cleanup"},
                    result=None,
                ))
                log.add_action(Action(
                    action_type="file.write",
                    target="done.txt",
                    status="success",
                ))
                with redirect_stdout(output):
                    exit_code = main(["pending", "--json"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            import json as _json
            data = _json.loads(output.getvalue())
            self.assertTrue(data["initialized"])
            self.assertEqual(len(data["pending"]), 1)
            entry = data["pending"][0]
            self.assertEqual(entry["action_type"], "file.delete")
            self.assertEqual(entry["target"], "old.txt")
            self.assertEqual(entry["status"], "pending")
            self.assertEqual(entry["params"], {"reason": "cleanup"})
            self.assertIn("id", entry)
            self.assertIn("timestamp", entry)

    def test_normal_pending_human_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["pending"])
            finally:
                os.chdir(original_cwd)

            self.assertEqual(exit_code, 0)
            self.assertIn("No pending actions.", output.getvalue())


    def test_act_dry_run_json_success_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run", "--json",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
                "--input", "body=Details",
            ])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertEqual(data["risk_level"], "low")
        self.assertTrue(data["reversible"])
        self.assertTrue(data["requires_auth"])
        self.assertEqual(data["missing_inputs"], [])
        self.assertIn("provided_inputs", data)
        self.assertIn("ui_steps_count", data)
        self.assertEqual(data["policy"], "auto")
        self.assertEqual(data["decision"], "allow")
        self.assertEqual(data["policy_source"], "config_rule")
        self.assertEqual(data["policy_reason"], 'rules.map_dry_run = "auto"')

    def test_act_dry_run_human_output_includes_policy_details(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
            ])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: auto", rendered)
        self.assertIn("Decision: allow", rendered)
        self.assertIn("Source: config rule", rendered)

    def test_act_dry_run_json_safe_profile_includes_auto_allow_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--dry-run", "--json",
                        "--input", "repo=user/repo",
                        "--input", "title=Bug",
                    ])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["policy"], "auto")
        self.assertEqual(data["decision"], "allow")

    def test_act_dry_run_json_rules_map_dry_run_block_returns_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.map_dry_run", "block"])
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--dry-run", "--json",
                        "--input", "repo=user/repo",
                        "--input", "title=Bug",
                    ])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["policy"], "block")
        self.assertEqual(data["decision"], "blocked")
        self.assertEqual(data["policy_source"], "config_rule")
        self.assertEqual(data["policy_reason"], 'rules.map_dry_run = "block"')

    def test_act_dry_run_json_missing_input_prints_json_error_and_exits_nonzero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run", "--json",
                "--input", "repo=user/repo",
            ])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertIn("Missing required inputs", data["error"])

    def test_act_dry_run_json_with_init_logs_action(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--dry-run", "--json",
                        "--input", "repo=user/repo",
                        "--input", "title=Bug",
                    ])
                action = ActionLog.open_existing(root=Path.cwd()).get_last_action()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action.action_type, "map.dry_run")
        self.assertEqual(action.status, "success")
        import json as _json
        _json.loads(output.getvalue())

    def test_execute_json_error_code_execution_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["act", "github", "create_issue", "--execute", "--json",
                          "--input", "repo=u/r", "--input", "title=t"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "EXECUTION_DISABLED")
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')

    @patch.dict("os.environ", {}, clear=True)
    def test_execute_json_error_code_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    main(["act", "vercel", "list_projects", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "MISSING_TOKEN")
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')

    def test_execute_json_error_code_unsupported_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    main(["act", "linear", "create_issue", "--execute", "--json",
                          "--input", "team_id=t", "--input", "title=Bug"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "UNSUPPORTED_EXECUTION")
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')

    @patch.dict("os.environ", {"VERCEL_TOKEN": "tok"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_execute_json_error_code_api_error(self, mocked_execute) -> None:
        from runewall.maps.executor import MapExecutionError
        mocked_execute.side_effect = MapExecutionError("API error", error_code="API_ERROR")
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    main(["act", "vercel", "list_projects", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "API_ERROR")
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')
        self.assertNotIn("tok", output.getvalue())

    def test_execute_json_error_code_unknown_site(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["act", "unknown_site", "create_issue", "--execute", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "UNKNOWN_SITE")

    def test_execute_json_error_code_unknown_flow(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["act", "github", "unknown_flow", "--execute", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "UNKNOWN_FLOW")

    def test_execute_json_error_code_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    main(["act", "github", "create_issue", "--execute", "--json",
                          "--input", "repo=u/r"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["error_code"], "INVALID_INPUT")

    def test_act_execute_json_blocked_by_config_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--execute", "--json",
                        "--input", "repo=user/repo",
                        "--input", "title=Bug",
                    ])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "create_issue")
        self.assertIn("allow_execute", data["error"])

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_json_missing_token_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "vercel", "list_projects", "--execute", "--json",
                    ])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "vercel")
        self.assertIn("VERCEL_TOKEN", data["error"])

    @patch.dict("os.environ", {"VERCEL_TOKEN": "secret-vercel-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_vercel_success(self, mocked_execute) -> None:
        mocked_execute.return_value = {"project_count": 2, "projects": [{"id": "p1", "name": "app"}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "vercel", "list_projects", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["executed"])
        self.assertEqual(data["site"], "vercel")
        self.assertEqual(data["result"]["project_count"], 2)
        self.assertNotIn("secret-vercel-token", output.getvalue())

    @patch.dict("os.environ", {"NETLIFY_TOKEN": "secret-netlify-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_netlify_success(self, mocked_execute) -> None:
        mocked_execute.return_value = {"site_count": 1, "sites": [{"id": "s1", "name": "site"}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "netlify", "list_sites", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["executed"])
        self.assertEqual(data["result"]["site_count"], 1)
        self.assertNotIn("secret-netlify-token", output.getvalue())

    @patch.dict("os.environ", {"SUPABASE_ACCESS_TOKEN": "secret-supabase-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_supabase_success(self, mocked_execute) -> None:
        mocked_execute.return_value = {"project_count": 3, "projects": []}
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "supabase", "list_projects", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["executed"])
        self.assertEqual(data["result"]["project_count"], 3)
        self.assertNotIn("secret-supabase-token", output.getvalue())

    @patch.dict("os.environ", {}, clear=True)
    def test_act_execute_cloudflare_json_missing_token_returns_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "cloudflare", "list_zones", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["error_code"], "MISSING_TOKEN")
        self.assertEqual(data["site"], "cloudflare")

    @patch.dict("os.environ", {"CLOUDFLARE_API_TOKEN": "secret-cf-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_cloudflare_success(self, mocked_execute) -> None:
        mocked_execute.return_value = {"zone_count": 2, "zones": [{"id": "z1", "name": "example.com"}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "cloudflare", "list_zones", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["executed"])
        self.assertEqual(data["result"]["zone_count"], 2)
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')
        self.assertNotIn("secret-cf-token", output.getvalue())

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-github-token"}, clear=True)
    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_github_success(self, mocked_execute) -> None:
        mocked_execute.return_value = {"issue_url": "https://github.com/u/r/issues/1", "issue_number": 1}
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main([
                        "act", "github", "create_issue", "--execute", "--json",
                        "--input", "repo=u/r", "--input", "title=Bug",
                    ])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertTrue(data["executed"])
        self.assertIn("issue_url", data["result"])
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["decision"], "review_required")
        self.assertEqual(data["policy_source"], "default_rule")
        self.assertEqual(data["policy_reason"], 'built-in default for "map.execute"')
        self.assertNotIn("secret-github-token", output.getvalue())

    @patch("runewall.cli.main.execute_map_action")
    def test_act_execute_json_policy_block_prevents_external_call(self, mocked_execute) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text('[maps]\nallow_execute = true\n\n[rules]\nmap_execute = "block"\n', encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "vercel", "list_projects", "--execute", "--json"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        mocked_execute.assert_not_called()
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["error_code"], "POLICY_BLOCKED")
        self.assertEqual(data["policy"], "block")
        self.assertEqual(data["decision"], "blocked")
        self.assertEqual(data["policy_source"], "config_rule")
        self.assertEqual(data["policy_reason"], 'rules.map_execute = "block"')

    def test_act_execute_human_policy_block_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text('[maps]\nallow_execute = true\n\n[rules]\nmap_execute = "block"\n', encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "vercel", "list_projects", "--execute"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        self.assertIn("Map execution blocked by policy: map.execute", output.getvalue())

    def test_act_execute_json_unsupported_map_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("[maps]\nallow_execute = true\n", encoding="utf-8")
                with redirect_stdout(output):
                    exit_code = main(["act", "linear", "create_issue", "--execute", "--json",
                                      "--input", "team_id=t", "--input", "title=Bug"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "linear")
        self.assertIn("not supported", data["error"].lower())

    def test_act_dry_run_human_output_unchanged_after_json_added(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main([
                "act", "github", "create_issue", "--dry-run",
                "--input", "repo=user/repo",
                "--input", "title=Bug",
            ])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Site name: GitHub", rendered)
        self.assertIn("Flow name: create_issue", rendered)
        self.assertIn("Risk level: low", rendered)
        self.assertIn("Missing inputs: none", rendered)

    def test_act_dry_run_json_unknown_site_prints_valid_json_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["act", "unknown_site", "create_issue", "--dry-run", "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "unknown_site")
        self.assertEqual(data["flow"], "create_issue")
        self.assertIn("Unknown site", data["error"])

    def test_act_dry_run_json_unknown_flow_prints_valid_json_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["act", "github", "unknown_flow", "--dry-run", "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertFalse(data["executed"])
        self.assertEqual(data["site"], "github")
        self.assertEqual(data["flow"], "unknown_flow")
        self.assertIn("Unknown flow", data["error"])

    def test_act_dry_run_human_error_output_unchanged_for_unknown_site_and_flow(self) -> None:
        site_output = io.StringIO()
        with redirect_stdout(site_output):
            exit_code_site = main(["act", "unknown_site", "create_issue", "--dry-run"])
        self.assertEqual(exit_code_site, 1)
        self.assertEqual(site_output.getvalue().strip(), "Site map not found: unknown_site")

        flow_output = io.StringIO()
        with redirect_stdout(flow_output):
            exit_code_flow = main(["act", "github", "unknown_flow", "--dry-run"])
        self.assertEqual(exit_code_flow, 1)
        self.assertEqual(flow_output.getvalue().strip(), "Flow not found for GitHub: unknown_flow")

    def test_maps_list_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("maps", data)
        self.assertIsInstance(data["maps"], list)

    def test_maps_list_json_includes_all_bundled_sites(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "list", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        keys = {entry["key"] for entry in data["maps"]}
        self.assertIn("github", keys)
        self.assertIn("vercel", keys)
        self.assertIn("netlify", keys)
        self.assertIn("cloudflare", keys)
        for entry in data["maps"]:
            self.assertIn("site_name", entry)
            self.assertIn("base_url", entry)
            self.assertIn("flow_count", entry)
            self.assertIn("flows", entry)

    def test_maps_show_json_github_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["key"], "github")
        self.assertEqual(data["site_name"], "GitHub")
        self.assertIn("base_url", data)
        self.assertIn("map_version", data)
        self.assertIn("schema_version", data)
        self.assertIn("flows", data)

    def test_maps_show_json_github_includes_create_issue(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "show", "github", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        flow_names = [f["name"] for f in data["flows"]]
        self.assertIn("create_issue", flow_names)
        flow = next(f for f in data["flows"] if f["name"] == "create_issue")
        self.assertEqual(flow["risk_level"], "low")
        self.assertTrue(flow["reversible"])
        self.assertTrue(flow["requires_auth"])
        self.assertIn("repo", flow["required_inputs"])
        self.assertIn("title", flow["required_inputs"])

    def test_maps_validate_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("ok", data)
        self.assertIn("results", data)
        self.assertIsInstance(data["results"], list)

    def test_maps_validate_json_returns_ok_true_for_bundled_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        for result in data["results"]:
            self.assertTrue(result["ok"])
            self.assertIsNone(result["error"])
            self.assertIn("key", result)
            self.assertIn("site_name", result)

    def test_maps_normal_human_output_unchanged_after_json_added(self) -> None:
        list_output = io.StringIO()
        with redirect_stdout(list_output):
            exit_code_list = main(["maps", "list"])
        self.assertEqual(exit_code_list, 0)
        self.assertIn("site_name\tbase_url\tflows", list_output.getvalue())
        self.assertIn("GitHub", list_output.getvalue())

        show_output = io.StringIO()
        with redirect_stdout(show_output):
            exit_code_show = main(["maps", "show", "github"])
        self.assertEqual(exit_code_show, 0)
        self.assertIn("Site name: GitHub", show_output.getvalue())

        validate_output = io.StringIO()
        with redirect_stdout(validate_output):
            exit_code_validate = main(["maps", "validate"])
        self.assertEqual(exit_code_validate, 0)
        self.assertIn("github (GitHub)\tOK", validate_output.getvalue())


    def test_maps_list_json_includes_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "list", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        github_entry = next(e for e in data["maps"] if e["key"] == "github")
        self.assertEqual(github_entry["category"], "development")
        self.assertEqual(github_entry["tags"], ["code", "issues"])
        for entry in data["maps"]:
            self.assertIn("category", entry)
            self.assertIn("tags", entry)

    def test_maps_show_json_github_includes_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["category"], "development")
        self.assertEqual(data["tags"], ["code", "issues"])

    def test_maps_show_human_includes_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "show", "github"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Category: development", rendered)
        self.assertIn("Tags: code, issues", rendered)

    def test_maps_validate_still_passes_with_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        self.assertEqual(exit_code, 0)
        self.assertIn("github (GitHub)\tOK", output.getvalue())
        self.assertIn("slack (Slack)\tOK", output.getvalue())

    def test_maps_lint_exits_zero_with_no_warnings_or_errors(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint"])
        self.assertEqual(exit_code, 0)

    def test_maps_lint_json_includes_strict_false(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "lint", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["strict"])
        self.assertTrue(data["ok"])

    def test_maps_lint_strict_exits_zero_when_maps_are_clean(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint", "--strict"])
        self.assertEqual(exit_code, 0)
        self.assertIn("strict mode", output.getvalue())

    @patch("runewall.cli.main.lint_map", return_value=(["some warning"], []))
    def test_maps_lint_normal_exits_zero_when_only_warnings(self, _mocked) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint"])
        self.assertEqual(exit_code, 0)

    @patch("runewall.cli.main.lint_map", return_value=(["some warning"], []))
    def test_maps_lint_strict_exits_nonzero_when_warnings_exist(self, _mocked) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint", "--strict"])
        self.assertEqual(exit_code, 1)

    def test_maps_lint_strict_json_includes_strict_true(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "lint", "--strict", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["strict"])
        self.assertTrue(data["ok"])

    @patch("runewall.cli.main.lint_map", return_value=(["some warning"], []))
    def test_maps_lint_strict_json_ok_false_when_warnings_exist(self, _mocked) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "lint", "--strict", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["strict"])
        self.assertFalse(data["ok"])
        self.assertGreater(data["warning_count"], 0)

    def test_maps_lint_runs_successfully_on_bundled_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Map lint results", output.getvalue())

    def test_maps_lint_shows_all_bundled_maps_ok(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "lint"])
        rendered = output.getvalue()
        self.assertIn("github", rendered)
        self.assertNotIn("description is empty", rendered)
        for key in ("cloudflare", "github", "netlify", "vercel", "slack", "discord", "linear", "supabase"):
            self.assertIn(f"{key}: OK", rendered)

    def test_maps_lint_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "lint", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("ok", data)
        self.assertIn("warning_count", data)
        self.assertIn("error_count", data)
        self.assertIn("results", data)

    def test_maps_lint_json_includes_warning_and_error_counts(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "lint", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["error_count"], 0)
        self.assertEqual(data["warning_count"], 0)
        github_result = next(r for r in data["results"] if r["key"] == "github")
        self.assertIsInstance(github_result["warnings"], list)
        self.assertIsInstance(github_result["errors"], list)
        self.assertEqual(github_result["warnings"], [])
        self.assertEqual(github_result["errors"], [])

    def test_maps_validate_still_works_alongside_lint(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "validate"])
        self.assertEqual(exit_code, 0)
        self.assertIn("github (GitHub)\tOK", output.getvalue())

    def test_maps_export_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "export", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("maps", data)
        self.assertIsInstance(data["maps"], list)

    def test_maps_export_json_includes_all_bundled_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "export", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        keys = {entry["key"] for entry in data["maps"]}
        for expected in ("github", "vercel", "netlify", "cloudflare", "slack", "discord", "linear", "supabase"):
            self.assertIn(expected, keys)

    def test_maps_export_json_includes_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "export", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        github = next(e for e in data["maps"] if e["key"] == "github")
        self.assertEqual(github["category"], "development")
        self.assertEqual(github["tags"], ["code", "issues"])
        for entry in data["maps"]:
            self.assertIn("category", entry)
            self.assertIn("tags", entry)

    def test_maps_export_json_includes_flows(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "export", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        github = next(e for e in data["maps"] if e["key"] == "github")
        self.assertIsInstance(github["flows"], list)
        self.assertEqual(len(github["flows"]), 1)
        flow = github["flows"][0]
        self.assertEqual(flow["name"], "create_issue")
        self.assertIn("risk_level", flow)
        self.assertIn("reversible", flow)
        self.assertIn("requires_auth", flow)
        self.assertIn("required_inputs", flow)
        self.assertIn("api_path", flow)

    def test_maps_export_without_json_prints_guidance(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "export"])
        self.assertEqual(exit_code, 0)
        self.assertIn("runewall maps export --json", output.getvalue())
        self.assertNotIn("{", output.getvalue())

    def test_maps_stats_prints_total_maps_and_flows(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "stats"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Total maps:", rendered)
        self.assertIn("Total flows:", rendered)
        self.assertIn("Real execution:", rendered)
        self.assertIn("Dry-run only:", rendered)

    def test_maps_stats_includes_categories(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "stats"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Categories:", rendered)
        self.assertIn("communication:", rendered)
        self.assertIn("deployment:", rendered)

    def test_maps_stats_json_prints_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "stats", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("total_maps", data)
        self.assertIn("total_flows", data)
        self.assertIn("categories", data)
        self.assertIn("real_execution_maps", data)
        self.assertIn("dry_run_only_maps", data)

    def test_maps_stats_json_includes_total_maps_and_flows(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertGreaterEqual(data["total_maps"], 8)
        self.assertGreaterEqual(data["total_flows"], 8)
        self.assertIsInstance(data["categories"], dict)

    def test_maps_stats_json_includes_github_in_real_execution(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("github", data["real_execution_maps"])
        self.assertNotIn("github", data["dry_run_only_maps"])

    def test_maps_stats_json_includes_dry_run_only_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            main(["maps", "stats", "--json"])
        import json as _json
        data = _json.loads(output.getvalue())
        for key in ("slack", "discord", "linear"):
            self.assertIn(key, data["dry_run_only_maps"])
            self.assertNotIn(key, data["real_execution_maps"])
        for key in ("vercel", "netlify", "supabase", "cloudflare"):
            self.assertIn(key, data["real_execution_maps"])
            self.assertNotIn(key, data["dry_run_only_maps"])
        self.assertNotIn("vercel", data["dry_run_only_maps"])

    def test_maps_list_human_still_works_with_category_and_tags(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("site_name\tbase_url\tflows", rendered)
        self.assertIn("GitHub", rendered)
        self.assertIn("Slack", rendered)


    def test_maps_list_category_deployment_returns_vercel_and_netlify(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list", "--category", "deployment"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Vercel", rendered)
        self.assertIn("Netlify", rendered)
        self.assertNotIn("GitHub", rendered)
        self.assertNotIn("Slack", rendered)

    def test_maps_list_tag_chat_returns_slack_and_discord(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list", "--tag", "chat"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Slack", rendered)
        self.assertIn("Discord", rendered)
        self.assertNotIn("GitHub", rendered)
        self.assertNotIn("Vercel", rendered)

    def test_maps_list_category_deployment_json_returns_only_deployment_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "list", "--category", "deployment", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        keys = {e["key"] for e in data["maps"]}
        self.assertIn("vercel", keys)
        self.assertIn("netlify", keys)
        self.assertNotIn("github", keys)
        for entry in data["maps"]:
            self.assertEqual(entry["category"], "deployment")

    def test_maps_search_deploy_returns_deployment_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "search", "deploy"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Vercel", rendered)
        self.assertIn("Netlify", rendered)
        self.assertNotIn("GitHub", rendered)

    def test_maps_search_chat_returns_communication_maps(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "search", "chat"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Slack", rendered)
        self.assertIn("Discord", rendered)
        self.assertNotIn("GitHub", rendered)

    def test_maps_search_unknown_returns_no_maps_message(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "search", "xyznotfound"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(output.getvalue().strip(), "No maps found.")

    def test_maps_search_unknown_json_returns_count_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "search", "xyznotfound", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["query"], "xyznotfound")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["maps"], [])

    def test_maps_search_deploy_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["maps", "search", "deploy", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["query"], "deploy")
        self.assertGreater(data["count"], 0)
        keys = {e["key"] for e in data["maps"]}
        self.assertIn("vercel", keys)
        self.assertIn("netlify", keys)


    def test_config_set_auth_vercel_token_env_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["config", "set", "auth.vercel_token_env", "MY_VERCEL_TOKEN"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)

    def test_config_set_auth_netlify_token_env_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                exit_code = main(["config", "set", "auth.netlify_token_env", "MY_NETLIFY_TOKEN"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)

    def test_config_set_auth_supabase_access_token_env_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                exit_code = main(["config", "set", "auth.supabase_access_token_env", "MY_SUPABASE_TOKEN"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)

    def test_config_set_auth_cloudflare_api_token_env_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                exit_code = main(["config", "set", "auth.cloudflare_api_token_env", "MY_CF_TOKEN"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)

    def test_config_set_rules_file_write_review_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["config", "set", "rules.file_write", "review"])
            finally:
                os.chdir(original_cwd)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.rules.file_write, "review")
        self.assertEqual(exit_code, 0)

    def test_config_set_rules_file_delete_block_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["config", "set", "rules.file_delete", "block"])
            finally:
                os.chdir(original_cwd)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.rules.file_delete, "block")
        self.assertEqual(exit_code, 0)

    def test_config_set_rules_creates_rules_section_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["config", "set", "rules.file_write", "review"])
            finally:
                os.chdir(original_cwd)
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            content = config_file.read_text(encoding="utf-8")
            self.assertIn("[rules]", content)
            self.assertIn('file_write = "review"', content)
        self.assertEqual(exit_code, 0)

    def test_config_set_invalid_rule_value_fails_clearly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["config", "set", "rules.file_write", "danger"])
        self.assertEqual(exit_code, 1)
        self.assertIn(
            "Invalid value for rules.file_write. Must be one of: auto, snapshot, review, block",
            output.getvalue(),
        )

    def test_config_set_invalid_rule_value_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["config", "set", "rules.file_write", "danger", "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["key"], "rules.file_write")
        self.assertEqual(
            data["error"],
            "Invalid value for rules.file_write. Must be one of: auto, snapshot, review, block",
        )

    def test_config_set_unknown_rule_key_fails(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["config", "set", "rules.delete_everything", "auto"])
        self.assertEqual(exit_code, 1)
        self.assertIn("Unknown config key: rules.delete_everything", output.getvalue())

    def test_config_show_includes_custom_vercel_token_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "auth.vercel_token_env", "MY_VERCEL_TOKEN"])
                with redirect_stdout(output):
                    exit_code = main(["config", "show"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("MY_VERCEL_TOKEN", output.getvalue())

    def test_config_validate_passes_with_custom_auth_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "auth.vercel_token_env", "MY_VERCEL_TOKEN"])
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_profile_safe_writes_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "profile", "safe"])
            finally:
                os.chdir(original_cwd)
            self.assertEqual(exit_code, 0)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.safety.default_policy, "review")
            self.assertFalse(cfg.maps.allow_execute)
            self.assertIn("Applied config profile: safe", output.getvalue())
            self.assertIn("Path:", output.getvalue())

    def test_config_profile_dev_writes_snapshot_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["config", "profile", "dev"])
            finally:
                os.chdir(original_cwd)
            self.assertEqual(exit_code, 0)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.safety.default_policy, "snapshot")
            self.assertFalse(cfg.maps.allow_execute)

    def test_config_profile_agent_writes_valid_guarded_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                exit_code = main(["config", "profile", "agent"])
            finally:
                os.chdir(original_cwd)
            self.assertEqual(exit_code, 0)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.safety.default_policy, "review")
            self.assertFalse(cfg.maps.allow_execute)

    def test_config_profile_safe_json_returns_ok_true(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["config", "profile", "safe", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["profile"], "safe")
        self.assertTrue(data["applied"])
        self.assertIn("path", data)

    def test_config_profile_unknown_fails_clearly(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["config", "profile", "risky"])
        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("Unknown config profile: risky", rendered)
        self.assertIn("Known profiles:", rendered)
        self.assertIn("safe", rendered)
        self.assertIn("dev", rendered)
        self.assertIn("agent", rendered)

    def test_config_profile_unknown_json_returns_error(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["config", "profile", "risky", "--json"])
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["profile"], "risky")
        self.assertIn("Unknown config profile: risky", data["error"])
        self.assertIn("safe", data["known_profiles"])
        self.assertIn("dev", data["known_profiles"])
        self.assertIn("agent", data["known_profiles"])

    def test_config_validate_passes_after_safe_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_validate_passes_after_dev_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "dev"])
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_validate_passes_after_agent_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "agent"])
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_profile_does_not_delete_db(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "profile", "safe"])
                db_path = Path(temp_dir) / ".runewall" / "runewall.db"
            finally:
                os.chdir(original_cwd)
            self.assertTrue(db_path.exists())

    def test_config_validate_passes_with_valid_rules_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(
                    '[rules]\nfile_write = "review"\nunknown = "block"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_validate_passes_after_valid_rule_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.file_write", "review"])
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Config: OK", output.getvalue())

    def test_config_validate_rejects_invalid_rule_policy_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(
                    '[rules]\nfile_write = "danger"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("INVALID", rendered)
        self.assertIn("rules.file_write", rendered)

    def test_config_validate_rejects_unknown_rule_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(
                    '[rules]\ndelete_everything = "auto"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["config", "validate"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("INVALID", rendered)
        self.assertIn("rules.delete_everything", rendered)

    def test_config_validate_json_returns_structured_errors_for_invalid_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_file = Path(temp_dir) / ".runewall" / "config.toml"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(
                    '[rules]\nfile_write = "danger"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["config", "validate", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertTrue(any(e["key"] == "rules.file_write" for e in data["errors"]))

    def test_config_profile_safe_keeps_maps_allow_execute_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
            finally:
                os.chdir(original_cwd)
            from runewall.core.config import load_config
            self.assertFalse(load_config(Path(temp_dir)).maps.allow_execute)

    def test_config_profile_agent_makes_file_write_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "agent"])
            finally:
                os.chdir(original_cwd)
            from runewall.core.config import load_config
            cfg = load_config(Path(temp_dir))
            self.assertEqual(cfg.rules.file_write, "review")
            self.assertFalse(cfg.maps.allow_execute)

    def test_policy_explain_file_write_from_config_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[rules]\nfile_write = "snapshot"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.write"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Action: file.write", rendered)
        self.assertIn("Policy: snapshot", rendered)
        self.assertIn("Source: config rule", rendered)
        self.assertIn('Reason: rules.file_write = "snapshot"', rendered)

    def test_policy_explain_file_delete_from_config_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[rules]\nfile_delete = "block"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.delete"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: block", rendered)
        self.assertIn("Source: config rule", rendered)
        self.assertIn('Reason: rules.file_delete = "block"', rendered)

    def test_policy_explain_web_read_from_config_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[rules]\nweb_read = "auto"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "web.read"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: auto", rendered)
        self.assertIn("Source: config rule", rendered)
        self.assertIn('Reason: rules.web_read = "auto"', rendered)

    def test_policy_explain_unknown_action_uses_rules_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[rules]\nunknown = "review"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "unknown.action", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_type"], "unknown.action")
        self.assertEqual(data["policy"], "review")
        self.assertEqual(data["source"], "config_rule")
        self.assertEqual(data["reason"], 'rules.unknown = "review"')

    def test_policy_explain_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["policy", "explain", "map.execute", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_type"], "map.execute")
        self.assertEqual(data["policy"], "review")

    def test_policy_explain_after_agent_profile_file_write_is_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "agent"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: review", output.getvalue())
        self.assertIn("Source: config rule", output.getvalue())

    def test_policy_explain_after_safe_profile_file_write_is_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: snapshot", output.getvalue())
        self.assertIn("Source: config rule", output.getvalue())

    def test_policy_explain_reflects_updated_rules_file_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.file_write", "review"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: review", output.getvalue())
        self.assertIn('Reason: rules.file_write = "review"', output.getvalue())

    def test_policy_test_is_accepted_by_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Action: file.write", output.getvalue())

    def test_policy_test_file_write_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.write"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: snapshot", rendered)
        self.assertIn("Decision: snapshot_required", rendered)
        self.assertIn("Source: default rule", rendered)

    def test_policy_test_file_write_json_returns_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.write", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["action_type"], "file.write")
        self.assertEqual(data["policy"], "snapshot")
        self.assertEqual(data["decision"], "snapshot_required")

    def test_policy_test_after_safe_profile_gives_snapshot_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Decision: snapshot_required", output.getvalue())

    def test_policy_test_after_agent_profile_gives_review_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "agent"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.write"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Decision: review_required", output.getvalue())

    def test_policy_test_rules_file_delete_block_gives_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.file_delete", "block"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "test", "file.delete"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: block", rendered)
        self.assertIn("Decision: blocked", rendered)

    def test_policy_audit_exists_as_cli_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy audit: OK", output.getvalue())

    def test_policy_audit_safe_profile_returns_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy audit: OK", rendered)
        self.assertIn("No risky policy settings found.", rendered)

    def test_policy_audit_maps_allow_execute_true_returns_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "maps.allow_execute", "true"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        self.assertIn("maps.allow_execute is true; real external execution is enabled.", output.getvalue())

    def test_policy_audit_rules_map_execute_auto_returns_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.map_execute", "auto"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        self.assertIn("rules.map_execute is auto; map execution can proceed without review.", output.getvalue())

    def test_policy_audit_rules_file_delete_auto_returns_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.file_delete", "auto"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        self.assertIn("rules.file_delete is auto; file deletes can proceed without review.", output.getvalue())

    def test_policy_audit_rules_unknown_auto_returns_warn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.unknown", "auto"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        self.assertIn("rules.unknown is auto; unknown actions can proceed without review.", output.getvalue())

    def test_policy_audit_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["policy", "audit", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["level"], "OK")
        self.assertEqual(data["warnings"], [])

    def test_policy_audit_invalid_config_returns_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text("[safety]\nmax_snapshot_mb = 0\n", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "audit", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["level"], "INVALID")
        self.assertEqual(data["warnings"], [])
        self.assertEqual(data["errors"], [{"key": "safety.max_snapshot_mb", "message": "must be a positive integer"}])

    def test_policy_audit_does_not_modify_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_text = '[rules]\nfile_delete = "auto"\n'
            config_file.write_text(config_text, encoding="utf-8")
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["policy", "audit"])
                self.assertEqual(config_file.read_text(encoding="utf-8"), config_text)
            finally:
                os.chdir(original_cwd)

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_release_check_exists_as_top_level_command(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["release", "check"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Release check: OK", output.getvalue())

    def test_release_json_check_exists(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "json-check"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("JSON contract check: OK", rendered)

    def test_release_json_check_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "json-check", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["level"], "OK")
        self.assertEqual(data["missing_fields"], [])
        self.assertEqual(data["missing_error_codes"], [])
        self.assertEqual(data["path"], "docs/agent-json-schema.md")

    def test_release_json_check_reports_ok_when_docs_include_required_fields_and_codes(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "json-check"])
        self.assertEqual(exit_code, 0)
        self.assertIn(
            "docs/agent-json-schema.md includes required agent JSON fields and error codes.",
            output.getvalue(),
        )

    def test_release_json_check_warns_when_agent_json_schema_doc_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["release", "json-check", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["level"], "WARN")
        self.assertEqual(data["missing_fields"], [])
        self.assertEqual(data["missing_error_codes"], [])
        self.assertEqual(data["path"], "docs/agent-json-schema.md")
        self.assertEqual(data["message"], "docs/agent-json-schema.md is missing.")

    def test_release_examples_exists(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "examples"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Release examples", rendered)

    def test_release_examples_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "examples", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(
            data["examples"],
            [
                "runewall config profile safe",
                "runewall config validate",
                "runewall policy audit",
                "runewall maps lint --strict",
                "runewall doctor",
                "runewall release check",
                "runewall release json-check",
                "python -m pytest tests -v",
            ],
        )

    def test_release_examples_include_release_check(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "examples"])
        self.assertEqual(exit_code, 0)
        self.assertIn("- runewall release check", output.getvalue())

    def test_release_examples_include_release_json_check(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "examples"])
        self.assertEqual(exit_code, 0)
        self.assertIn("- runewall release json-check", output.getvalue())

    def test_release_status_exists(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "status"])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("Release status", rendered)
        self.assertIn("Recommended final check:", rendered)

    def test_release_status_json_returns_valid_json(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "status", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(
            data["readiness"],
            {
                "config": "ready",
                "policy": "ready",
                "maps": "ready",
                "json_contract": "ready",
                "doctor": "ready",
                "tests_manual": "python -m pytest tests -v",
            },
        )
        self.assertNotIn("Release status", output.getvalue())

    def test_release_status_json_includes_recommended_commands(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "status", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(
            data["recommended_commands"],
            [
                "runewall release check",
                "runewall release json-check",
                "python -m pytest tests -v",
            ],
        )
        self.assertIn("runewall release check", data["recommended_commands"])
        self.assertNotIn("runewall releasecheck", data["recommended_commands"])

    def test_release_status_human_output_includes_release_check(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["release", "status"])
        self.assertEqual(exit_code, 0)
        self.assertIn("runewall release check", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_release_check_json_returns_valid_json(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                output.truncate(0)
                output.seek(0)
                with redirect_stdout(output):
                    exit_code = main(["release", "check", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["level"], "OK")
        self.assertIn("checks", data)
        self.assertEqual(data["checks"]["config"]["level"], "OK")
        self.assertEqual(data["checks"]["policy_audit"]["level"], "OK")
        self.assertEqual(data["checks"]["maps_lint"]["level"], "OK")
        self.assertEqual(data["checks"]["doctor_basics"]["level"], "OK")

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_safe_profile_release_check_returns_ok(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["release", "check"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("Release check: OK", output.getvalue())

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_maps_allow_execute_true_makes_release_check_warn(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["init"])
                main(["config", "set", "maps.allow_execute", "true"])
                with redirect_stdout(output):
                    exit_code = main(["release", "check"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        rendered = output.getvalue()
        self.assertIn("Release check: WARN", rendered)
        self.assertIn("Policy audit: WARN", rendered)
        self.assertIn("- maps.allow_execute is true; real external execution is enabled.", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_invalid_config_makes_release_check_fail(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text("[safety]\nmax_snapshot_mb = 0\n", encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["release", "check", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 1)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertFalse(data["ok"])
        self.assertEqual(data["level"], "FAIL")
        self.assertEqual(data["checks"]["config"]["level"], "INVALID")

    @patch("runewall.cli.main.importlib.util.find_spec")
    def test_release_check_does_not_modify_config(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_text = '[rules]\nfile_delete = "auto"\n'
            config_file.write_text(config_text, encoding="utf-8")
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["release", "check"])
                self.assertEqual(config_file.read_text(encoding="utf-8"), config_text)
            finally:
                os.chdir(original_cwd)

    def test_policy_explain_without_rules_still_explains_default_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[safety]\ndefault_policy = "review"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "explain", "file.write"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy: snapshot", rendered)
        self.assertIn("Source: default rule", rendered)

    def test_policy_list_works_in_human_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "list"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Policy rules", rendered)
        self.assertIn("file.read: auto", rendered)
        self.assertIn("file.write: snapshot", rendered)
        self.assertIn("file.create: snapshot", rendered)
        self.assertIn("file.delete: review", rendered)
        self.assertIn("web.read: auto", rendered)
        self.assertIn("map.dry_run: auto", rendered)
        self.assertIn("map.execute: review", rendered)
        self.assertIn("unknown: review", rendered)

    def test_policy_list_json_returns_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertTrue(data["ok"])
        self.assertEqual(data["policies"]["file.write"]["policy"], "snapshot")
        self.assertEqual(data["policies"]["file.write"]["source"], "default_rule")
        self.assertEqual(data["policies"]["map.execute"]["policy"], "review")

    def test_policy_list_after_safe_profile_shows_file_write_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "safe"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("file.write: snapshot", output.getvalue())

    def test_policy_list_after_agent_profile_shows_file_write_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "profile", "agent"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("file.write: review", output.getvalue())

    def test_policy_list_json_map_execute_shows_review(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["policy", "list", "--json"])
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["policies"]["map.execute"]["policy"], "review")

    def test_policy_list_json_unknown_uses_configured_unknown_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[rules]\nunknown = "block"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "list", "--json"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["policies"]["unknown"]["policy"], "block")
        self.assertEqual(data["policies"]["unknown"]["source"], "config_rule")
        self.assertEqual(data["policies"]["unknown"]["reason"], 'rules.unknown = "block"')

    def test_policy_list_reflects_updated_rules_file_delete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                main(["config", "set", "rules.file_delete", "block"])
                with redirect_stdout(output):
                    exit_code = main(["policy", "list"])
            finally:
                os.chdir(original_cwd)
        self.assertEqual(exit_code, 0)
        self.assertIn("file.delete: block", output.getvalue())

    def test_policy_list_without_rules_lists_default_policies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            config_file = Path(temp_dir) / ".runewall" / "config.toml"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text('[safety]\ndefault_policy = "review"\n', encoding="utf-8")
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    exit_code = main(["policy", "list"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("file.write: snapshot", rendered)
        self.assertIn("unknown: review", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_custom_vercel_token_env_changes_human_label(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_dir = Path(temp_dir) / ".runewall"
                config_dir.mkdir()
                (config_dir / "config.toml").write_text(
                    '[auth]\nvercel_token_env = "MY_VERCEL_TOKEN"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("MY_VERCEL_TOKEN: missing", rendered)
        self.assertNotIn("\nVERCEL_TOKEN: missing", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {"MY_VERCEL_TOKEN": "secret-custom-tok"}, clear=True)
    def test_doctor_custom_vercel_token_env_checks_custom_env_var(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_dir = Path(temp_dir) / ".runewall"
                config_dir.mkdir()
                (config_dir / "config.toml").write_text(
                    '[auth]\nvercel_token_env = "MY_VERCEL_TOKEN"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    exit_code = main(["doctor"])
            finally:
                os.chdir(original_cwd)
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("MY_VERCEL_TOKEN: set", rendered)
        self.assertNotIn("secret-custom-tok", rendered)

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_includes_configured_env_name(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                config_dir = Path(temp_dir) / ".runewall"
                config_dir.mkdir()
                (config_dir / "config.toml").write_text(
                    '[auth]\nvercel_token_env = "MY_VERCEL_TOKEN"\n',
                    encoding="utf-8",
                )
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["vercel"]["env"], "MY_VERCEL_TOKEN")
        self.assertEqual(data["auth"]["vercel"]["status"], "missing")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_default_includes_structured_auth_with_env_names(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["auth"]["github"]["env"], "GITHUB_TOKEN")
        self.assertEqual(data["auth"]["vercel"]["env"], "VERCEL_TOKEN")
        self.assertEqual(data["auth"]["netlify"]["env"], "NETLIFY_TOKEN")
        self.assertEqual(data["auth"]["supabase"]["env"], "SUPABASE_ACCESS_TOKEN")
        self.assertEqual(data["auth"]["cloudflare"]["env"], "CLOUDFLARE_API_TOKEN")

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_old_flat_auth_keys_still_present(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertIn("github_token", data["auth"])
        self.assertIn("vercel_token", data["auth"])
        self.assertIn("netlify_token", data["auth"])
        self.assertIn("supabase_access_token", data["auth"])
        self.assertIn("cloudflare_api_token", data["auth"])

    @patch("runewall.cli.main.importlib.util.find_spec")
    @patch.dict("os.environ", {}, clear=True)
    def test_doctor_json_summary_warn_when_tokens_missing(self, mocked_find_spec) -> None:
        mocked_find_spec.return_value = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            output = io.StringIO()
            try:
                os.chdir(temp_dir)
                with redirect_stdout(output):
                    main(["doctor", "--json"])
            finally:
                os.chdir(original_cwd)
        import json as _json
        data = _json.loads(output.getvalue())
        self.assertEqual(data["summary"], "WARN")


if __name__ == "__main__":
    unittest.main()
