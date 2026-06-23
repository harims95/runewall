from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
import shutil
from typing import Any


class MapValidationError(ValueError):
    """Raised when a site map is missing required fields."""


class SiteMapNotFoundError(LookupError):
    """Raised when a bundled site map cannot be found."""


class FlowNotFoundError(LookupError):
    """Raised when a flow does not exist in a site map."""


@dataclass(frozen=True)
class SiteMap:
    schema_version: str
    site_name: str
    base_url: str
    map_version: str
    flows: dict[str, Any]
    raw: dict[str, Any]
    category: str
    tags: list[str]


@dataclass(frozen=True)
class MapValidationResult:
    site_key: str
    site_name: str | None
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class CommunityMapValidationReport:
    ok: bool
    path: str
    errors: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class CommunityMapImportReport:
    ok: bool
    source: str
    destination: str | None
    validated: bool
    execute_enabled: bool
    errors: list[str]


@dataclass(frozen=True)
class CommunityMapInspectReport:
    ok: bool
    path: str
    site: str | None
    flow: str | None
    action_type: str | None
    validation_ok: bool
    errors: list[str]
    warnings: list[str]
    execute_enabled: bool
    contains_secrets: bool


@dataclass(frozen=True)
class ManifestValidationReport:
    ok: bool
    path: str
    errors: list[str]
    warnings: list[str]
    name: str | None = None
    version: str | None = None
    author_name: str | None = None
    maps_count: int = 0
    checksums_verified: bool = False


_VALID_RISK_LEVELS = {"low", "medium", "high"}
_COMMUNITY_SECRET_KEYS = ("token", "api_key", "secret", "password", "private_key")
_MANIFEST_REQUIRED_STR = ("manifest_version", "name", "version", "description")
_MANIFEST_REQUIRED_DICT = ("author", "permissions", "safety", "checksums")
_MANIFEST_MAP_REQUIRED = ("path", "site", "flow", "action_type")


def lint_map(site_map: SiteMap) -> tuple[list[str], list[str]]:
    """Return (warnings, errors) for quality issues in a site map."""
    warnings: list[str] = []
    errors: list[str] = []

    raw_tags = site_map.raw.get("site", {}).get("tags")
    if raw_tags is not None and not isinstance(raw_tags, list):
        errors.append("tags is not a list")
    elif not site_map.tags:
        warnings.append("map tags are empty")

    if not site_map.category:
        warnings.append("category is missing")

    for flow_name, flow_data in site_map.flows.items():
        description = str(flow_data.get("description", ""))
        risk_level = str(flow_data.get("risk_level", ""))
        reversible = bool(flow_data.get("reversible", False))
        requires_auth = bool(flow_data.get("requires_auth", False))
        api_path = flow_data.get("api_path")

        if not description.strip():
            warnings.append(f"{flow_name}: description is empty")

        if risk_level not in _VALID_RISK_LEVELS:
            errors.append(f"{flow_name}: invalid risk_level: {risk_level!r}")

        if requires_auth and api_path is None:
            warnings.append(f"{flow_name}: requires_auth true but api_path is missing")

        if risk_level == "high" and not reversible:
            warnings.append(f"{flow_name}: risk_level {risk_level} but reversible is false")

        if api_path is not None:
            if not isinstance(api_path, dict) or not api_path.get("method") or not api_path.get("url"):
                warnings.append(f"{flow_name}: api_path exists but method or url is missing")

    return warnings, errors


class SiteMapRegistry:
    """Loads bundled JSON site maps from runewall.maps.sites."""

    def bundled_maps_path(self) -> Path:
        return Path(__file__).resolve().parent / "sites"

    def community_maps_path(self, root: Path | None = None) -> Path:
        return (root or Path.cwd()) / ".runewall" / "community-maps"

    def list_maps(self) -> list[SiteMap]:
        maps: list[SiteMap] = []
        sites_root = resources.files("runewall.maps").joinpath("sites")
        for entry in sorted(sites_root.iterdir(), key=lambda item: item.name):
            if entry.is_file() and entry.name.endswith(".json"):
                maps.append(self.load_map(entry.name))
        return maps

    def validate_bundled_maps(self) -> list[MapValidationResult]:
        results: list[MapValidationResult] = []
        sites_root = resources.files("runewall.maps").joinpath("sites")
        for entry in sorted(sites_root.iterdir(), key=lambda item: item.name):
            if not entry.is_file() or not entry.name.endswith(".json"):
                continue
            site_key = entry.name.removesuffix(".json")
            try:
                site_map = self.load_map(entry.name)
            except MapValidationError as error:
                results.append(
                    MapValidationResult(
                        site_key=site_key,
                        site_name=None,
                        ok=False,
                        error=str(error),
                    )
                )
                continue
            results.append(
                MapValidationResult(
                    site_key=site_key,
                    site_name=site_map.site_name,
                    ok=True,
                )
            )
        return results

    def load_site(self, site_key: str) -> SiteMap | None:
        normalized_key = site_key.strip().lower()
        for site_map in self.list_maps():
            filename_key = site_map.raw.get("_filename", "").removesuffix(".json").lower()
            name_key = site_map.site_name.lower()
            if normalized_key in {filename_key, name_key}:
                return site_map
        return None

    def require_site(self, site_key: str) -> SiteMap:
        site_map = self.load_site(site_key)
        if site_map is None:
            raise SiteMapNotFoundError(f"Site map not found: {site_key}")
        return site_map

    def get_flow(self, site_map: SiteMap, flow_name: str) -> dict[str, Any] | None:
        return site_map.flows.get(flow_name)

    def require_flow(self, site_map: SiteMap, flow_name: str) -> dict[str, Any]:
        flow = self.get_flow(site_map, flow_name)
        if flow is None:
            raise FlowNotFoundError(f"Flow not found for {site_map.site_name}: {flow_name}")
        return flow

    def search_maps(self, query: str) -> list[SiteMap]:
        q = query.strip().lower()
        results = []
        for site_map in self.list_maps():
            key = site_map.raw.get("_filename", "").removesuffix(".json").lower()
            flow_names = [name.lower() for name in site_map.flows]
            flow_descriptions = [
                str(fd.get("description", "")).lower()
                for fd in site_map.flows.values()
            ]
            if (
                q in key
                or q in site_map.site_name.lower()
                or q in site_map.category.lower()
                or any(q in tag.lower() for tag in site_map.tags)
                or any(q in fn for fn in flow_names)
                or any(q in fd for fd in flow_descriptions)
            ):
                results.append(site_map)
        return results

    def load_map(self, filename: str) -> SiteMap:
        map_resource = resources.files("runewall.maps").joinpath("sites", filename)
        with map_resource.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return self._build_site_map(data, source=filename)

    def load_file(self, path: Path) -> SiteMap:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return self._build_site_map(data, source=str(path))

    def validate_community_map_file(self, path: Path) -> CommunityMapValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        resolved_path = str(path)

        if not path.exists():
            return CommunityMapValidationReport(ok=False, path=resolved_path, errors=[f"file not found: {resolved_path}"], warnings=warnings)
        if not path.is_file():
            return CommunityMapValidationReport(ok=False, path=resolved_path, errors=[f"not a file: {resolved_path}"], warnings=warnings)

        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as error:
            return CommunityMapValidationReport(ok=False, path=resolved_path, errors=[f"invalid JSON: {error.msg}"], warnings=warnings)

        if not isinstance(data, dict):
            return CommunityMapValidationReport(ok=False, path=resolved_path, errors=["community map must be a JSON object"], warnings=warnings)

        if not isinstance(data.get("site"), str) or not str(data.get("site", "")).strip():
            errors.append("missing required field 'site'")
        if not isinstance(data.get("flow"), str) or not str(data.get("flow", "")).strip():
            errors.append("missing required field 'flow'")
        if not isinstance(data.get("action_type"), str) or not str(data.get("action_type", "")).strip():
            errors.append("missing required field 'action_type'")

        for secret_key in self._find_matching_keys(data, _COMMUNITY_SECRET_KEYS):
            errors.append(f"secret-like field is not allowed: {secret_key}")

        if self._has_enabled_execution(data):
            errors.append("community maps cannot enable execution")

        return CommunityMapValidationReport(ok=not errors, path=resolved_path, errors=errors, warnings=warnings)

    def inspect_community_map_file(self, path: Path) -> CommunityMapInspectReport:
        validation = self.validate_community_map_file(path)
        data = self._load_community_map_data(path)
        site = data.get("site") if isinstance(data.get("site"), str) and str(data.get("site", "")).strip() else None
        flow = data.get("flow") if isinstance(data.get("flow"), str) and str(data.get("flow", "")).strip() else None
        action_type = data.get("action_type") if isinstance(data.get("action_type"), str) and str(data.get("action_type", "")).strip() else None
        contains_secrets = bool(data) and bool(self._find_matching_keys(data, _COMMUNITY_SECRET_KEYS))
        return CommunityMapInspectReport(
            ok=validation.ok,
            path=validation.path,
            site=site,
            flow=flow,
            action_type=action_type,
            validation_ok=validation.ok,
            errors=validation.errors,
            warnings=validation.warnings,
            execute_enabled=False,
            contains_secrets=contains_secrets,
        )

    def import_community_map_file(self, path: Path, root: Path | None = None) -> CommunityMapImportReport:
        report = self.validate_community_map_file(path)
        if not report.ok:
            return CommunityMapImportReport(
                ok=False,
                source=report.path,
                destination=None,
                validated=False,
                execute_enabled=False,
                errors=report.errors,
            )

        destination_dir = self.community_maps_path(root)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_path = destination_dir / path.name
        shutil.copy2(path, destination_path)
        relative_destination = Path(".runewall") / "community-maps" / path.name
        return CommunityMapImportReport(
            ok=True,
            source=report.path,
            destination=relative_destination.as_posix(),
            validated=True,
            execute_enabled=False,
            errors=[],
        )

    def list_community_map_files(self, root: Path | None = None) -> list[Path]:
        directory = self.community_maps_path(root)
        if not directory.is_dir():
            return []
        return sorted(
            [entry for entry in directory.iterdir() if entry.is_file()],
            key=lambda entry: entry.name,
        )

    def validate_manifest_file(self, path: Path) -> ManifestValidationReport:
        errors: list[str] = []
        resolved_path = str(path)

        if not path.exists():
            return ManifestValidationReport(ok=False, path=resolved_path, errors=[f"file not found: {resolved_path}"], warnings=[])
        if not path.is_file():
            return ManifestValidationReport(ok=False, path=resolved_path, errors=[f"not a file: {resolved_path}"], warnings=[])

        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            return ManifestValidationReport(ok=False, path=resolved_path, errors=[f"invalid JSON: {exc.msg}"], warnings=[])

        if not isinstance(data, dict):
            return ManifestValidationReport(ok=False, path=resolved_path, errors=["manifest must be a JSON object"], warnings=[])

        name = data.get("name") if isinstance(data.get("name"), str) and str(data.get("name", "")).strip() else None
        version = data.get("version") if isinstance(data.get("version"), str) and str(data.get("version", "")).strip() else None
        author_obj = data.get("author") if isinstance(data.get("author"), dict) else None
        author_name = str(author_obj["name"]) if author_obj and isinstance(author_obj.get("name"), str) and str(author_obj["name"]).strip() else None
        maps_list = data.get("maps") if isinstance(data.get("maps"), list) else None
        maps_count = len(maps_list) if maps_list is not None else 0

        for field in _MANIFEST_REQUIRED_STR:
            if not isinstance(data.get(field), str) or not str(data.get(field, "")).strip():
                errors.append(f"missing required field '{field}'")
        for field in _MANIFEST_REQUIRED_DICT:
            if not isinstance(data.get(field), dict):
                errors.append(f"missing required field '{field}'")
        if not isinstance(data.get("maps"), list):
            errors.append("missing required field 'maps'")

        if author_obj is not None and (not isinstance(author_obj.get("name"), str) or not str(author_obj.get("name", "")).strip()):
            errors.append("author.name is required")

        if maps_list is not None:
            if not maps_list:
                errors.append("maps must not be empty")
            for i, entry in enumerate(maps_list):
                if not isinstance(entry, dict):
                    errors.append(f"maps[{i}] must be an object")
                    continue
                for field in _MANIFEST_MAP_REQUIRED:
                    if not isinstance(entry.get(field), str) or not str(entry.get(field, "")).strip():
                        errors.append(f"maps[{i}] missing required field '{field}'")

        perms = data.get("permissions")
        if isinstance(perms, dict):
            if perms.get("external_api_calls") is not False:
                errors.append("permissions.external_api_calls must be false")
            if perms.get("execute_enabled") is not False:
                errors.append("permissions.execute_enabled must be false")

        safety_obj = data.get("safety")
        if isinstance(safety_obj, dict):
            if safety_obj.get("secrets_in_files") is not False:
                errors.append("safety.secrets_in_files must be false")
            if safety_obj.get("dry_run_first") is not True:
                errors.append("safety.dry_run_first must be true")
            if safety_obj.get("community_execution_allowed") is not False:
                errors.append("safety.community_execution_allowed must be false")

        for secret_key in self._find_manifest_secret_keys(data):
            errors.append(f"secret-like field is not allowed: {secret_key}")

        checksums_verified = self._verify_manifest_checksums(
            path.parent, maps_list or [], data.get("checksums"), errors
        )

        return ManifestValidationReport(
            ok=not errors,
            path=resolved_path,
            errors=errors,
            warnings=[],
            name=name,
            version=version,
            author_name=author_name,
            maps_count=maps_count,
            checksums_verified=checksums_verified,
        )

    def inspect_manifest_file(self, path: Path) -> ManifestValidationReport:
        return self.validate_manifest_file(path)

    def _load_community_map_data(self, path: Path) -> dict[str, Any]:
        if not path.exists() or not path.is_file():
            return {}
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _build_site_map(self, data: dict[str, Any], *, source: str) -> SiteMap:
        schema_version = self._require_str(data, "schema_version", source=source)
        site = self._require_dict(data, "site", source=source)
        site_name = self._require_str(site, "name", source=source)
        base_url = self._require_str(site, "base_url", source=source)
        map_version = self._require_str(site, "map_version", source=source)
        flows = self._require_dict(data, "flows", source=source)
        category = str(site.get("category", ""))
        tags = [str(t) for t in site.get("tags", []) if isinstance(t, str)]
        return SiteMap(
            schema_version=schema_version,
            site_name=site_name,
            base_url=base_url,
            map_version=map_version,
            flows=flows,
            raw={**data, "_filename": source},
            category=category,
            tags=tags,
        )

    def _require_dict(self, data: dict[str, Any], key: str, *, source: str) -> dict[str, Any]:
        value = data.get(key)
        if not isinstance(value, dict):
            raise MapValidationError(f"{source}: missing required field '{key}'")
        return value

    def _require_str(self, data: dict[str, Any], key: str, *, source: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise MapValidationError(f"{source}: missing required field '{key}'")
        return value

    def _find_matching_keys(self, data: Any, patterns: tuple[str, ...], *, prefix: str = "") -> list[str]:
        matches: list[str] = []
        if isinstance(data, dict):
            for key, value in data.items():
                key_text = str(key)
                key_path = f"{prefix}.{key_text}" if prefix else key_text
                lowered = key_text.lower()
                if any(pattern in lowered for pattern in patterns):
                    matches.append(key_path)
                matches.extend(self._find_matching_keys(value, patterns, prefix=key_path))
        elif isinstance(data, list):
            for index, item in enumerate(data):
                item_prefix = f"{prefix}[{index}]"
                matches.extend(self._find_matching_keys(item, patterns, prefix=item_prefix))
        return matches

    def _verify_manifest_checksums(
        self,
        manifest_dir: Path,
        maps_list: list[Any],
        checksums: Any,
        errors: list[str],
    ) -> bool:
        if not isinstance(checksums, dict):
            return False
        all_ok = True
        for entry in maps_list:
            if not isinstance(entry, dict):
                continue
            map_path_str = entry.get("path")
            if not isinstance(map_path_str, str) or not map_path_str.strip():
                continue
            if map_path_str not in checksums:
                errors.append(f"missing checksum for {map_path_str}")
                all_ok = False
                continue
            map_file = manifest_dir / map_path_str
            if not map_file.exists() or not map_file.is_file():
                errors.append(f"map file not found: {map_path_str}")
                all_ok = False
                continue
            actual = "sha256-" + hashlib.sha256(map_file.read_bytes()).hexdigest()
            expected = checksums[map_path_str]
            if actual != expected:
                errors.append(f"checksum mismatch for {map_path_str}")
                all_ok = False
        return all_ok

    def _find_manifest_secret_keys(self, data: Any, *, prefix: str = "") -> list[str]:
        """Return key paths matching secret patterns where the value is a non-empty string."""
        matches: list[str] = []
        if isinstance(data, dict):
            for key, value in data.items():
                key_text = str(key)
                key_path = f"{prefix}.{key_text}" if prefix else key_text
                if any(p in key_text.lower() for p in _COMMUNITY_SECRET_KEYS) and isinstance(value, str) and value.strip():
                    matches.append(key_path)
                matches.extend(self._find_manifest_secret_keys(value, prefix=key_path))
        elif isinstance(data, list):
            for index, item in enumerate(data):
                matches.extend(self._find_manifest_secret_keys(item, prefix=f"{prefix}[{index}]"))
        return matches

    def _has_enabled_execution(self, data: Any) -> bool:
        if isinstance(data, dict):
            for key, value in data.items():
                key_text = str(key).lower()
                if key_text in {"execute", "allow_execute", "execution_enabled"} and value is True:
                    return True
                if self._has_enabled_execution(value):
                    return True
        elif isinstance(data, list):
            return any(self._has_enabled_execution(item) for item in data)
        return False
