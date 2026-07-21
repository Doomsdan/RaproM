from __future__ import annotations

import bz2
import math
import threading

import pytest

from raprom.cancellation import ProcessingCancelled
from raprom.gui import (
    build_process_settings,
    find_raw_files,
    format_duration,
    load_gui_config_values,
    parse_optional_float,
    process_selected_path,
)


def test_parse_optional_float_accepts_empty_and_decimal_comma():
    assert math.isnan(parse_optional_float(""))
    assert parse_optional_float("1,25") == 1.25


def test_build_process_settings_accepts_raw_file(tmp_path):
    raw_file = tmp_path / "sample.raw"
    raw_file.write_text("", encoding="utf-8")
    output_dir = tmp_path / "out"

    settings = build_process_settings(str(raw_file), "60", "", "1.05", str(output_dir), True)

    assert settings.input_path == raw_file
    assert settings.integration_time == 60
    assert math.isnan(settings.antenna_height)
    assert settings.adjust_m == 1.05
    assert settings.output_dir == output_dir
    assert settings.correct is True


def test_build_process_settings_rejects_non_raw_file(tmp_path):
    text_file = tmp_path / "sample.txt"
    text_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Endung .raw"):
        build_process_settings(str(text_file), "60", "", "1.0", "", True)


def test_load_gui_config_values_from_station_yaml(tmp_path):
    config_path = tmp_path / "station.yaml"
    config_path.write_text(
        """
station:
  id: station-a
  paths:
    raw_data: D:/Mrrdata/station-a
    output: D:/Mrrdata/station-a/Processed
  instrument:
    antenna_height_m: 120.0
""".strip(),
        encoding="utf-8",
    )

    values = load_gui_config_values(config_path)

    assert values.input_path == "D:/Mrrdata/station-a"
    assert values.output_dir == "D:/Mrrdata/station-a/Processed"
    assert values.antenna_height == "120.0"
    assert values.integration_time == ""
    assert values.correct is None


def test_load_gui_config_values_prefers_process_block(tmp_path):
    config_path = tmp_path / "station.yaml"
    config_path.write_text(
        """
station:
  id: station-a
  paths:
    raw_data: D:/Mrrdata/station-a
    output: D:/Mrrdata/station-a/Processed
  instrument:
    antenna_height_m: 120.0

process:
  path: D:/Mrrdata/station-a/202501
  integration_time: 30
  antenna_height: 142.5
  output_dir: D:/Mrrdata/station-a/Processed/202501
  correct: false
  calibration:
    adjust_m: 1.05
""".strip(),
        encoding="utf-8",
    )

    values = load_gui_config_values(config_path)

    assert values.input_path == "D:/Mrrdata/station-a/202501"
    assert values.integration_time == "30"
    assert values.antenna_height == "142.5"
    assert values.adjust_m == "1.05"
    assert values.output_dir == "D:/Mrrdata/station-a/Processed/202501"
    assert values.correct is False


def test_process_selected_path_uses_single_file_processor(monkeypatch, tmp_path):
    raw_file = tmp_path / "sample.raw"
    raw_file.write_text("", encoding="utf-8")
    settings = build_process_settings(str(raw_file), "30", "120", "1.0", "", False)
    captured = {}

    def fake_process_raw_file(raw_path, integration_time, **kwargs):
        captured["raw_path"] = raw_path
        captured["integration_time"] = integration_time
        captured.update(kwargs)
        return "sample-processed.nc"

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (None, fake_process_raw_file))

    assert process_selected_path(settings) == ["sample-processed.nc"]
    assert captured["raw_path"] == raw_file
    assert captured["integration_time"] == 30
    assert captured["antenna_height"] == 120.0
    assert captured["correct"] is False


def test_find_raw_files_returns_sorted_raw_files(tmp_path):
    second = tmp_path / "b.raw"
    first = tmp_path / "a.raw"
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_raw = nested / "c.raw"
    ignored = tmp_path / "notes.txt"
    second.write_text("", encoding="utf-8")
    first.write_text("", encoding="utf-8")
    nested_raw.write_text("", encoding="utf-8")
    ignored.write_text("", encoding="utf-8")

    assert find_raw_files(tmp_path) == [first, second, nested_raw]


def test_process_selected_path_reports_file_progress(monkeypatch, tmp_path):
    raw_files = [tmp_path / "a.raw", tmp_path / "b.raw"]
    for raw_file in raw_files:
        raw_file.write_text("", encoding="utf-8")
    settings = build_process_settings(str(tmp_path), "30", "", "1.0", "", True)
    progress_events = []

    def fake_process_raw_file(raw_path, _integration_time, **_kwargs):
        return f"{raw_path.stem}-processed.nc"

    def fake_prepare_directory(_input_path, output_dir=None, correct=True):
        return raw_files, raw_files

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (fake_prepare_directory, fake_process_raw_file))

    outputs = process_selected_path(settings, progress_callback=progress_events.append)

    assert outputs == ["a-processed.nc", "b-processed.nc"]
    assert [(event.index, event.total, event.path.name) for event in progress_events] == [
        (1, 2, "a.raw"),
        (2, 2, "b.raw"),
    ]


def test_process_selected_path_stops_before_next_file(monkeypatch, tmp_path):
    raw_files = [tmp_path / "a.raw", tmp_path / "b.raw"]
    for raw_file in raw_files:
        raw_file.write_text("", encoding="utf-8")
    settings = build_process_settings(str(tmp_path), "30", "", "1.0", "", True)
    cancel_event = threading.Event()
    processed = []

    def fake_process_raw_file(raw_path, _integration_time, **_kwargs):
        processed.append(raw_path.name)
        cancel_event.set()
        return f"{raw_path.stem}-processed.nc"

    def fake_prepare_directory(_input_path, output_dir=None, correct=True):
        return raw_files, raw_files

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (fake_prepare_directory, fake_process_raw_file))

    with pytest.raises(ProcessingCancelled):
        process_selected_path(settings, cancel_event=cancel_event)

    assert processed == ["a.raw"]


def test_process_selected_path_stops_before_processing(monkeypatch, tmp_path):
    raw_file = tmp_path / "sample.raw"
    raw_file.write_text("", encoding="utf-8")
    settings = build_process_settings(str(raw_file), "30", "", "1.0", "", True)
    cancel_event = threading.Event()
    cancel_event.set()

    def fake_process_raw_file(*_args, **_kwargs):
        raise AssertionError("processing should not start after cancellation")

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (None, fake_process_raw_file))

    with pytest.raises(ProcessingCancelled):
        process_selected_path(settings, cancel_event=cancel_event)


def test_process_selected_path_prepares_folder_before_processing(monkeypatch, tmp_path):
    processed_raw = tmp_path / "0101.raw"
    processed_raw.write_text("", encoding="utf-8")
    (tmp_path / "0101-processed.nc").write_text("", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    with bz2.open(nested / "0102.raw.bz2", "wb") as archive:
        archive.write(b"MRR placeholder\n")

    settings = build_process_settings(str(tmp_path), "60", "", "1.0", "", False)
    processed = []

    def fake_process_raw_file(raw_path, _integration_time, **_kwargs):
        processed.append(raw_path.relative_to(tmp_path).as_posix())
        return f"{raw_path.stem}-processed.nc"

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (__import__("raprom.netcdf").netcdf.prepare_directory, fake_process_raw_file))

    outputs = process_selected_path(settings)

    assert processed == ["nested/0102.raw"]
    assert outputs == ["0102-processed.nc"]
    assert (nested / "0102.raw").exists()


def test_format_duration_uses_minutes_or_hours():
    assert format_duration(9) == "00:09"
    assert format_duration(125) == "02:05"
    assert format_duration(3661) == "01:01:01"
