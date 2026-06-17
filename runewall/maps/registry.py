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


@dataclass(frozen=True)
class MapValidationResult:
    site_key: str
    site_name: str | None
    ok: bool
    error: str | None = None


class SiteMapRegistry:
    """Loads bundled JSON site maps from runewall.maps.sites."""

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
        return SiteMap(
            schema_version=schema_version,
            site_name=site_name,
            base_url=base_url,
            map_version=map_version,
            flows=flows,
            raw={**data, "_filename": source},
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
