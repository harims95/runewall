from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
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


_VALID_RISK_LEVELS = {"low", "medium", "high"}


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
