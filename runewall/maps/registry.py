from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any


class MapValidationError(ValueError):
    """Raised when a site map is missing required fields."""


@dataclass(frozen=True)
class SiteMap:
    schema_version: str
    site_name: str
    base_url: str
    map_version: str
    flows: dict[str, Any]
    raw: dict[str, Any]


class SiteMapRegistry:
    """Loads bundled JSON site maps from runewall.maps.sites."""

    def list_maps(self) -> list[SiteMap]:
        maps: list[SiteMap] = []
        sites_root = resources.files("runewall.maps").joinpath("sites")
        for entry in sorted(sites_root.iterdir(), key=lambda item: item.name):
            if entry.is_file() and entry.name.endswith(".json"):
                maps.append(self.load_map(entry.name))
        return maps

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
            raw=data,
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
