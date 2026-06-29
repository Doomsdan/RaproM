from __future__ import annotations

from pathlib import Path

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
