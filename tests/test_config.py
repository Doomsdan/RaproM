from __future__ import annotations

import math

import pytest

from raprom.config import load_process_config, merge_process_config


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
