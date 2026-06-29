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


def test_benchmark_command_fails_on_reference_drift(monkeypatch, tmp_path):
    captured = {}

    class FakeRun:
        elapsed_seconds = 1.25
        output_path = tmp_path / "candidate.nc"
        differences = ("RR: data differ",)

    def fake_benchmark_raw_file(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return [FakeRun()]

    monkeypatch.setattr("raprom.benchmark.benchmark_raw_file", fake_benchmark_raw_file)

    assert cli.main(["benchmark", "sample.raw", "-i", "60", "--reference", "reference.nc"]) == 1
    assert captured["args"] == ("sample.raw", 60)
    assert captured["kwargs"]["reference_netcdf"] == "reference.nc"
