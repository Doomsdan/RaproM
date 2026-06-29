from __future__ import annotations

import math

import pytest

from raprom.gui import build_process_settings, find_raw_files, format_duration, parse_optional_float, process_selected_path


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
    ignored = tmp_path / "notes.txt"
    second.write_text("", encoding="utf-8")
    first.write_text("", encoding="utf-8")
    ignored.write_text("", encoding="utf-8")

    assert find_raw_files(tmp_path) == [first, second]


def test_process_selected_path_reports_file_progress(monkeypatch, tmp_path):
    raw_files = [tmp_path / "a.raw", tmp_path / "b.raw"]
    for raw_file in raw_files:
        raw_file.write_text("", encoding="utf-8")
    settings = build_process_settings(str(tmp_path), "30", "", "1.0", "", True)
    progress_events = []

    def fake_process_raw_file(raw_path, _integration_time, **_kwargs):
        return f"{raw_path.stem}-processed.nc"

    monkeypatch.setattr("raprom.gui._get_processors", lambda: (None, fake_process_raw_file))

    outputs = process_selected_path(settings, progress_callback=progress_events.append)

    assert outputs == ["a-processed.nc", "b-processed.nc"]
    assert [(event.index, event.total, event.path.name) for event in progress_events] == [
        (1, 2, "a.raw"),
        (2, 2, "b.raw"),
    ]


def test_format_duration_uses_minutes_or_hours():
    assert format_duration(9) == "00:09"
    assert format_duration(125) == "02:05"
    assert format_duration(3661) == "01:01:01"
