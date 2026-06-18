from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import tomllib
from typing import Any

from .db import project_state_dir


DEFAULT_CONFIG_TEXT = """[safety]
default_policy = "review"
max_snapshot_mb = 500

[retention]
snapshot_days = 30

[maps]
allow_execute = false

[auth]
github_token_env = "GITHUB_TOKEN"
"""


@dataclass(frozen=True)
class SafetyConfig:
    default_policy: str = "review"
    max_snapshot_mb: int = 500


@dataclass(frozen=True)
class RetentionConfig:
    snapshot_days: int = 30


@dataclass(frozen=True)
class MapsConfig:
    allow_execute: bool = False


@dataclass(frozen=True)
class AuthConfig:
    github_token_env: str = "GITHUB_TOKEN"
    vercel_token_env: str = "VERCEL_TOKEN"
    netlify_token_env: str = "NETLIFY_TOKEN"
    supabase_access_token_env: str = "SUPABASE_ACCESS_TOKEN"
    cloudflare_api_token_env: str = "CLOUDFLARE_API_TOKEN"


@dataclass(frozen=True)
class RunewallConfig:
    safety: SafetyConfig = SafetyConfig()
    retention: RetentionConfig = RetentionConfig()
    maps: MapsConfig = MapsConfig()
    auth: AuthConfig = AuthConfig()

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return asdict(self)


RESET_CONFIG_TEXT = """[safety]
default_policy = "review"
max_snapshot_mb = 500

[retention]
snapshot_days = 30

[maps]
allow_execute = false

[auth]
github_token_env = "GITHUB_TOKEN"
vercel_token_env = "VERCEL_TOKEN"
netlify_token_env = "NETLIFY_TOKEN"
supabase_access_token_env = "SUPABASE_ACCESS_TOKEN"
cloudflare_api_token_env = "CLOUDFLARE_API_TOKEN"
"""

_VALID_DEFAULT_POLICIES = {"auto", "review", "snapshot"}


def validate_config_data(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    safety = data.get("safety", {})
    if isinstance(safety, dict):
        dp = safety.get("default_policy")
        if dp is not None and dp not in _VALID_DEFAULT_POLICIES:
            errors.append({"key": "safety.default_policy", "message": f"must be one of: auto, review, snapshot (got {dp!r})"})
        msm = safety.get("max_snapshot_mb")
        if msm is not None and (not isinstance(msm, int) or isinstance(msm, bool) or msm <= 0):
            errors.append({"key": "safety.max_snapshot_mb", "message": "must be a positive integer"})

    retention = data.get("retention", {})
    if isinstance(retention, dict):
        sd = retention.get("snapshot_days")
        if sd is not None and (not isinstance(sd, int) or isinstance(sd, bool) or sd <= 0):
            errors.append({"key": "retention.snapshot_days", "message": "must be a positive integer"})

    maps_section = data.get("maps", {})
    if isinstance(maps_section, dict):
        ae = maps_section.get("allow_execute")
        if ae is not None and not isinstance(ae, bool):
            errors.append({"key": "maps.allow_execute", "message": "must be a boolean"})

    auth = data.get("auth", {})
    if isinstance(auth, dict):
        for env_key in ("github_token_env", "vercel_token_env", "netlify_token_env", "supabase_access_token_env", "cloudflare_api_token_env"):
            val = auth.get(env_key)
            if val is not None and not isinstance(val, str):
                errors.append({"key": f"auth.{env_key}", "message": "must be a string"})

    return errors


KNOWN_CONFIG_KEYS: dict[str, type] = {
    "safety.default_policy": str,
    "safety.max_snapshot_mb": int,
    "retention.snapshot_days": int,
    "maps.allow_execute": bool,
    "auth.github_token_env": str,
}


def config_path(root: Path | None = None) -> Path:
    return project_state_dir(root) / "config.toml"


def ensure_config(root: Path | None = None) -> Path:
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")
    return path


def set_config_value(key: str, raw_value: str, root: Path | None = None) -> None:
    if key not in KNOWN_CONFIG_KEYS:
        raise ValueError(
            f"Unknown config key: {key}. Known keys: {', '.join(sorted(KNOWN_CONFIG_KEYS))}"
        )

    expected_type = KNOWN_CONFIG_KEYS[key]
    parsed: Any

    if expected_type is bool:
        if raw_value.lower() == "true":
            parsed = True
        elif raw_value.lower() == "false":
            parsed = False
        else:
            raise ValueError(
                f"Invalid boolean for {key}: {raw_value!r}. Use true or false."
            )
    elif expected_type is int:
        try:
            parsed = int(raw_value)
        except ValueError:
            raise ValueError(f"Invalid integer for {key}: {raw_value!r}.")
    else:
        parsed = raw_value

    ensure_config(root)
    data = load_config_data(root)
    section, field = key.split(".", 1)
    if section not in data or not isinstance(data[section], dict):
        data[section] = {}
    data[section][field] = parsed
    config_path(root).write_text(_format_config_for_file(data) + "\n", encoding="utf-8")


def load_config(root: Path | None = None) -> RunewallConfig:
    raw_data = load_config_data(root)
    return RunewallConfig(
        safety=_load_safety(raw_data.get("safety")),
        retention=_load_retention(raw_data.get("retention")),
        maps=_load_maps(raw_data.get("maps")),
        auth=_load_auth(raw_data.get("auth")),
    )


def load_config_data(root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = config_path(root)
    if not path.exists():
        return RunewallConfig().to_dict()

    with path.open("rb") as handle:
        raw_data = tomllib.load(handle)

    merged = RunewallConfig().to_dict()
    for section_name, section_values in raw_data.items():
        if not isinstance(section_values, dict):
            continue
        current = merged.get(section_name, {})
        if isinstance(current, dict):
            current.update(section_values)
            merged[section_name] = current
        else:
            merged[section_name] = dict(section_values)
    return merged


def safe_config_dict(config: RunewallConfig) -> dict[str, dict[str, Any]]:
    return _redact_mapping(config.to_dict())


def format_config(config: RunewallConfig) -> str:
    return format_config_data(config.to_dict())


def format_config_data(data: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for section_name, section_values in _redact_mapping(data).items():
        lines.append(f"[{section_name}]")
        for key, value in section_values.items():
            lines.append(f"{key} = {_format_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _load_safety(data: Any) -> SafetyConfig:
    section = data if isinstance(data, dict) else {}
    return SafetyConfig(
        default_policy=_as_str(section.get("default_policy"), "review"),
        max_snapshot_mb=_as_int(section.get("max_snapshot_mb"), 500),
    )


def _load_retention(data: Any) -> RetentionConfig:
    section = data if isinstance(data, dict) else {}
    return RetentionConfig(
        snapshot_days=_as_int(section.get("snapshot_days"), 30),
    )


def _load_maps(data: Any) -> MapsConfig:
    section = data if isinstance(data, dict) else {}
    return MapsConfig(
        allow_execute=_as_bool(section.get("allow_execute"), False),
    )


def _load_auth(data: Any) -> AuthConfig:
    section = data if isinstance(data, dict) else {}
    return AuthConfig(
        github_token_env=_as_str(section.get("github_token_env"), "GITHUB_TOKEN"),
        vercel_token_env=_as_str(section.get("vercel_token_env"), "VERCEL_TOKEN"),
        netlify_token_env=_as_str(section.get("netlify_token_env"), "NETLIFY_TOKEN"),
        supabase_access_token_env=_as_str(section.get("supabase_access_token_env"), "SUPABASE_ACCESS_TOKEN"),
        cloudflare_api_token_env=_as_str(section.get("cloudflare_api_token_env"), "CLOUDFLARE_API_TOKEN"),
    )


def _as_str(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value.strip() else default


def _as_int(value: Any, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


def _as_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _format_config_for_file(data: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for section_name, section_values in data.items():
        lines.append(f"[{section_name}]")
        for field_key, value in section_values.items():
            lines.append(f"{field_key} = {_format_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            redacted[key] = _redact_mapping(value)
        elif _is_secret_key(key):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    if lowered.endswith("_env"):
        return False
    return any(token in lowered for token in ("token", "secret", "password"))


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return f'"{value}"'
