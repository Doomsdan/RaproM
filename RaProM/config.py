"""Configuration loading for RaProM."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class ProcessConfig:
    """Configuration values for ``raprom process``."""

    path: str | None = None
    integration_time: int | None = None
    antenna_height: float = np.nan
    adjust_m: float = 1.0
    output_dir: str | None = None
    correct: bool = True


def load_process_config(config_path: str | Path | None) -> ProcessConfig:
    """Load process configuration from a TOML, YAML, or YML file."""
    if config_path is None:
        return ProcessConfig()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = _load_mapping(path)
    process_data = data.get("process", data)
    if not isinstance(process_data, dict):
        raise ValueError("Process config must be a mapping.")

    return ProcessConfig(**_normalize_process_config(process_data))


def merge_process_config(config: ProcessConfig, overrides: dict[str, Any]) -> ProcessConfig:
    """Return a config with explicit command-line overrides applied."""
    values = {field.name: getattr(config, field.name) for field in fields(ProcessConfig)}
    values.update({key: value for key, value in overrides.items() if value is not None})
    return ProcessConfig(**values)


def _load_mapping(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".toml":
        try:
            import tomllib
        except ModuleNotFoundError:  # pragma: no cover - used on Python 3.10
            import tomli as tomllib

        with path.open("rb") as handle:
            data = tomllib.load(handle)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError("YAML config files require PyYAML. Use TOML or install PyYAML.") from exc

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    else:
        raise ValueError("Config files must use .toml, .yaml, or .yml.")

    if not isinstance(data, dict):
        raise ValueError("Config file must contain a mapping.")
    return data


def _normalize_process_config(data: dict[str, Any]) -> dict[str, Any]:
    config = dict(data)

    if "radar_height" in config and "antenna_height" not in config:
        config["antenna_height"] = config.pop("radar_height")

    calibration = config.pop("calibration", None)
    if isinstance(calibration, dict) and "adjust_m" in calibration and "adjust_m" not in config:
        config["adjust_m"] = calibration["adjust_m"]

    if "no_correct" in config and "correct" not in config:
        config["correct"] = not bool(config.pop("no_correct"))

    allowed = {field.name for field in fields(ProcessConfig)}
    unknown = sorted(set(config) - allowed)
    if unknown:
        raise ValueError(f"Unknown process config option(s): {', '.join(unknown)}")

    return config
