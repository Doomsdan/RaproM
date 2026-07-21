from __future__ import annotations

import math

import pytest

from raprom.config import load_process_config, load_station_config, merge_process_config


def test_load_process_config_from_toml(tmp_path):
    config_path = tmp_path / "raprom.toml"
    config_path.write_text(
        """
[process]
path = "D:/Mrrdata"
integration_time = 60
radar_height = 120.0
output_dir = "D:/Mrrdata/Processed"

[process.calibration]
adjust_m = 1.05
""".strip(),
        encoding="utf-8",
    )

    config = load_process_config(config_path)

    assert config.path == "D:/Mrrdata"
    assert config.integration_time == 60
    assert config.antenna_height == 120.0
    assert config.adjust_m == 1.05
    assert config.output_dir == "D:/Mrrdata/Processed"


def test_merge_process_config_keeps_defaults_and_applies_overrides():
    config = load_process_config(None)
    merged = merge_process_config(config, {"integration_time": 30, "adjust_m": None})

    assert merged.integration_time == 30
    assert merged.adjust_m == 1.0
    assert math.isnan(merged.antenna_height)


def test_unknown_process_config_option_is_rejected(tmp_path):
    config_path = tmp_path / "raprom.toml"
    config_path.write_text("[process]\nunknown = true\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown process config"):
        load_process_config(config_path)


def test_load_station_config_from_yaml(tmp_path):
    config_path = tmp_path / "station.yaml"
    config_path.write_text(
        """
station:
  id: station-a
  name: Station A
  timezone: Europe/Berlin
  location:
    latitude: 50.123
    longitude: 8.456
    altitude_m: 142.5
  instrument:
    serial_number: "0509106128"
    antenna_height_m: 120.0
  paths:
    raw_data: D:/Mrrdata/station-a
    output: D:/Mrrdata/station-a/Processed
""".strip(),
        encoding="utf-8",
    )

    config = load_station_config(config_path)

    assert config.id == "station-a"
    assert config.name == "Station A"
    assert config.latitude == 50.123
    assert config.longitude == 8.456
    assert config.altitude == 142.5
    assert config.antenna_height == 120.0
    assert config.timezone == "Europe/Berlin"
    assert config.mrr_serial_number == "0509106128"
    assert config.raw_data_path == "D:/Mrrdata/station-a"
    assert config.output_dir == "D:/Mrrdata/station-a/Processed"


def test_station_yaml_can_also_contain_process_config(tmp_path):
    config_path = tmp_path / "station.yaml"
    config_path.write_text(
        """
station:
  id: station-a

process:
  path: D:/Mrrdata/station-a
  integration_time: 60
  antenna_height: 120.0
""".strip(),
        encoding="utf-8",
    )

    config = load_process_config(config_path)

    assert config.path == "D:/Mrrdata/station-a"
    assert config.integration_time == 60
    assert config.antenna_height == 120.0


def test_station_config_requires_id(tmp_path):
    config_path = tmp_path / "station.yaml"
    config_path.write_text("station:\n  name: Missing ID\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires station.id"):
        load_station_config(config_path)
