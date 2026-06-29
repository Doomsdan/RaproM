from __future__ import annotations

import math

import raprom.cli as cli


def test_main_uses_config_without_explicit_process_subcommand(monkeypatch, tmp_path):
    config_path = tmp_path / "raprom.toml"
    config_path.write_text(
        """
[process]
path = "D:/Mrrdata"
integration_time = 60
output_dir = "D:/Mrrdata/Processed"
""".strip(),
        encoding="utf-8",
    )

    captured = {}

    def fake_process_directory(root, integration_time, **kwargs):
        captured["root"] = root
        captured["integration_time"] = integration_time
        captured.update(kwargs)
        return []

    monkeypatch.setattr("raprom.netcdf.process_directory", fake_process_directory)

    assert cli.main(["--config", str(config_path)]) == 0
    assert captured["root"] == "D:/Mrrdata"
    assert captured["integration_time"] == 60
    assert math.isnan(captured["antenna_height"])
    assert captured["adjust_m"] == 1.0
    assert captured["correct"] is True
    assert captured["output_dir"] == "D:/Mrrdata/Processed"
