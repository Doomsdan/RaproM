from __future__ import annotations

import bz2
from pathlib import Path
import zipfile

import numpy as np
from netCDF4 import Dataset

import raprom.netcdf as netcdf


def raw_block(timestamp: str) -> list[str]:
    heights = " ".join(str(100 * index) for index in range(32))
    transfer = " ".join("1.0" for _ in range(32))
    values = " ".join(str(index + 1) for index in range(32))
    return [
        f"MRR {timestamp} UTC-05 DVS 6.10 DSN 0509106128 BW 37305 CC 1000 MDQ 100 57 57 TYP RAW",
        f"H {heights}",
        f"TF {transfer}",
        *[f"F{index:02d} {values}" for index in range(64)],
    ]


def write_raw(path: Path, blocks: list[list[str]]) -> None:
    lines = [line for block in blocks for line in block]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_process_raw_file_parses_raw_and_writes_expected_netcdf(monkeypatch, tmp_path):
    raw_path = tmp_path / "sample.raw"
    write_raw(raw_path, [raw_block("250101000000"), raw_block("250101000012")])

    def fake_scat_ext(diameter, _long_wavelength):
        return np.ones(len(diameter)), np.ones(len(diameter))

    def fake_process(matrix, heights, timestamp, diameters):
        assert matrix.shape == (31, 64)
        assert len(heights) == 31
        assert timestamp in {1735689610, 1735689620}
        assert len(diameters) == 31
        height_values = np.arange(31, dtype=float)
        drop_values = np.ones((31, 64), dtype=float)
        return (
            np.full(31, 10.0),
            drop_values,
            height_values + 20.0,
            height_values + 0.1,
            height_values + 0.2,
            np.full(31, np.nan),
            height_values + 1.0,
            height_values + 2.0,
            height_values + 3.0,
            height_values + 4.0,
            height_values + 5.0,
            drop_values,
            height_values + 6.0,
            np.full(31, np.nan),
            np.full(31, np.nan),
            height_values + 7.0,
            height_values + 8.0,
            np.ones(32),
            height_values + 9.0,
            height_values / 10.0 + 1.0,
            np.ones(32),
        )

    def fake_bb(_w, _ze, _heights):
        return 200.0, 300.0

    def fake_check_type(types, _bb_bot, _bb_top, _delta_h, nw, dm, lwc, rr, *_args):
        return types, nw, dm, lwc, rr

    def fake_rain_par(types, z, lwc, rr, nw, dm, _new_matrix, _diameters, dsd, nde, _heights, _w, _pia):
        return z, lwc, rr, nw, dm, dsd, nde, np.ones(32)

    monkeypatch.setattr(netcdf, "ScatExt", fake_scat_ext)
    monkeypatch.setattr(netcdf, "Process", fake_process)
    monkeypatch.setattr(netcdf, "BB", fake_bb)
    monkeypatch.setattr(netcdf, "CheckType", fake_check_type)
    monkeypatch.setattr(netcdf, "Rain_Par", fake_rain_par)

    output = Path(netcdf.process_raw_file(raw_path, integration_time=10, correct=False))

    assert output == tmp_path / "sample-processed.nc"
    with Dataset(output) as dataset:
        assert dataset.dimensions["Height"].size == 31
        assert dataset.dimensions["DropSize"].size == 64
        assert dataset.dimensions["PIA_Height"].size == 32
        np.testing.assert_allclose(dataset.variables["Height"][:3], [100.0, 200.0, 300.0])
        np.testing.assert_allclose(dataset.variables["Time"][:], [1735689610.0, 1735689620.0])
        np.testing.assert_allclose(dataset.variables["Type"][0, :3], [10.0, 10.0, 10.0])
        np.testing.assert_allclose(dataset.variables["RR"][0, :3], [0.2, 1.2, 2.2])
        assert dataset.variables["Type"].description.startswith("Predominant hydrometeor type")
        assert dataset.variables["RR"].units == "mm hr-1"
        assert "TyPrecipi" in dataset.variables


def test_process_raw_file_uses_output_dir(monkeypatch, tmp_path):
    raw_path = tmp_path / "sample.raw"
    output_dir = tmp_path / "processed"
    write_raw(raw_path, [raw_block("250101000000"), raw_block("250101000012")])

    monkeypatch.setattr(netcdf, "ScatExt", lambda diameter, _long_wavelength: (np.ones(len(diameter)), np.ones(len(diameter))))

    def fake_process(_matrix, _heights, _timestamp, _diameters):
        height_values = np.arange(31, dtype=float)
        drop_values = np.ones((31, 64), dtype=float)
        return (
            np.full(31, 10.0),
            drop_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            drop_values,
            height_values,
            height_values,
            height_values,
            height_values,
            height_values,
            np.ones(32),
            height_values,
            height_values,
            np.ones(32),
        )

    monkeypatch.setattr(netcdf, "Process", fake_process)
    monkeypatch.setattr(netcdf, "BB", lambda _w, _ze, _heights: (200.0, 300.0))
    monkeypatch.setattr(netcdf, "CheckType", lambda types, _bb_bot, _bb_top, _delta_h, nw, dm, lwc, rr, *_args: (types, nw, dm, lwc, rr))
    monkeypatch.setattr(netcdf, "Rain_Par", lambda types, z, lwc, rr, nw, dm, _new_matrix, _diameters, dsd, nde, _heights, _w, _pia: (z, lwc, rr, nw, dm, dsd, nde, np.ones(32)))

    output = Path(netcdf.process_raw_file(raw_path, integration_time=10, output_dir=output_dir, correct=False))

    assert output == output_dir / "sample-processed.nc"
    assert output.exists()


def test_process_directory_extracts_archives_once_and_processes_new_raw(monkeypatch, tmp_path):
    archive_path = tmp_path / "raw-data.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("archived.raw", "MRR placeholder\n")

    calls = []

    def fake_process_raw_file(raw_file, integration_time, antenna_height, adjust_m, correct, output_dir):
        calls.append(Path(raw_file).name)
        output = Path(raw_file).with_name(f"{Path(raw_file).stem}-processed.nc")
        output.write_text("processed", encoding="utf-8")
        return str(output)

    monkeypatch.setattr(netcdf, "process_raw_file", fake_process_raw_file)

    outputs = netcdf.process_directory(tmp_path, integration_time=60, correct=False)

    assert calls == ["archived.raw"]
    assert outputs == [str(tmp_path / "archived-processed.nc")]
    assert (tmp_path / "archived.raw").read_text(encoding="utf-8") == "MRR placeholder\n"

    (tmp_path / "archived.raw").write_text("keep existing file\n", encoding="utf-8")
    calls.clear()

    outputs = netcdf.process_directory(tmp_path, integration_time=60, correct=False)

    assert calls == []
    assert outputs == []
    assert (tmp_path / "archived.raw").read_text(encoding="utf-8") == "keep existing file\n"


def test_process_directory_skips_corrected_output_candidate(monkeypatch, tmp_path):
    raw_path = tmp_path / "sample.raw"
    raw_path.write_text("MRR placeholder\n", encoding="utf-8")
    corrected_output = tmp_path / "CorrectedRaw" / "sample-corrected-processed.nc"
    corrected_output.parent.mkdir()
    corrected_output.write_text("processed", encoding="utf-8")

    def fail_process_raw_file(*_args, **_kwargs):
        raise AssertionError("processed an already completed raw file")

    monkeypatch.setattr(netcdf, "process_raw_file", fail_process_raw_file)

    assert netcdf.process_directory(tmp_path, integration_time=60, correct=True) == []


def test_process_directory_recurses_into_subfolders(monkeypatch, tmp_path):
    nested = tmp_path / "station-a" / "202501"
    nested.mkdir(parents=True)
    raw_path = nested / "nested.raw"
    raw_path.write_text("MRR placeholder\n", encoding="utf-8")

    archive_dir = tmp_path / "station-b"
    archive_dir.mkdir()
    with zipfile.ZipFile(archive_dir / "raw-data.zip", "w") as archive:
        archive.writestr("archived.raw", "MRR archived\n")

    calls = []

    def fake_process_raw_file(raw_file, integration_time, antenna_height, adjust_m, correct, output_dir):
        raw_file = Path(raw_file)
        calls.append(raw_file.relative_to(tmp_path).as_posix())
        output = raw_file.with_name(f"{raw_file.stem}-processed.nc")
        output.write_text("processed", encoding="utf-8")
        return str(output)

    monkeypatch.setattr(netcdf, "process_raw_file", fake_process_raw_file)

    outputs = netcdf.process_directory(tmp_path, integration_time=60, correct=False)

    assert calls == ["station-a/202501/nested.raw", "station-b/archived.raw"]
    assert outputs == [
        str(nested / "nested-processed.nc"),
        str(archive_dir / "archived-processed.nc"),
    ]
    assert (archive_dir / "archived.raw").exists()


def test_process_directory_extracts_bz2_raw_files(monkeypatch, tmp_path):
    nested = tmp_path / "station-a"
    nested.mkdir()
    with bz2.open(nested / "sample.raw.bz2", "wb") as archive:
        archive.write(b"MRR bz2 placeholder\n")

    calls = []

    def fake_process_raw_file(raw_file, integration_time, antenna_height, adjust_m, correct, output_dir):
        raw_file = Path(raw_file)
        calls.append(raw_file.relative_to(tmp_path).as_posix())
        output = raw_file.with_name(f"{raw_file.stem}-processed.nc")
        output.write_text("processed", encoding="utf-8")
        return str(output)

    monkeypatch.setattr(netcdf, "process_raw_file", fake_process_raw_file)

    outputs = netcdf.process_directory(tmp_path, integration_time=60, correct=False)

    assert calls == ["station-a/sample.raw"]
    assert outputs == [str(nested / "sample-processed.nc")]
    assert (nested / "sample.raw").read_text(encoding="utf-8") == "MRR bz2 placeholder\n"


def test_process_directory_does_not_extract_bz2_when_output_exists(monkeypatch, tmp_path):
    with bz2.open(tmp_path / "sample.raw.bz2", "wb") as archive:
        archive.write(b"MRR bz2 placeholder\n")
    (tmp_path / "sample-processed.nc").write_text("processed", encoding="utf-8")

    def fail_process_raw_file(*_args, **_kwargs):
        raise AssertionError("processed an already completed compressed raw file")

    monkeypatch.setattr(netcdf, "process_raw_file", fail_process_raw_file)

    assert netcdf.process_directory(tmp_path, integration_time=60, correct=False) == []
    assert not (tmp_path / "sample.raw").exists()


def test_process_directory_ignores_generated_corrected_raw_folder(monkeypatch, tmp_path):
    corrected = tmp_path / "CorrectedRaw"
    corrected.mkdir()
    (corrected / "sample-corrected.raw").write_text("generated", encoding="utf-8")

    def fail_process_raw_file(*_args, **_kwargs):
        raise AssertionError("processed generated corrected raw file")

    monkeypatch.setattr(netcdf, "process_raw_file", fail_process_raw_file)

    assert netcdf.process_directory(tmp_path, integration_time=60) == []
