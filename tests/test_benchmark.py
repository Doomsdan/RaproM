from __future__ import annotations

import numpy as np
from netCDF4 import Dataset

from raprom.benchmark import compare_netcdf


def write_dataset(path, values):
    with Dataset(path, mode="w", format="NETCDF4") as dataset:
        dataset.description = "reference"
        dataset.createDimension("time", 2)
        variable = dataset.createVariable("RR", "f8", ("time",))
        variable.units = "mm hr-1"
        variable[:] = values


def test_compare_netcdf_accepts_exact_match_with_nan(tmp_path):
    reference = tmp_path / "reference.nc"
    candidate = tmp_path / "candidate.nc"
    values = np.array([1.0, np.nan])
    write_dataset(reference, values)
    write_dataset(candidate, values)

    assert compare_netcdf(reference, candidate) == []


def test_compare_netcdf_reports_data_drift(tmp_path):
    reference = tmp_path / "reference.nc"
    candidate = tmp_path / "candidate.nc"
    write_dataset(reference, np.array([1.0, np.nan]))
    write_dataset(candidate, np.array([1.0, 2.0]))

    assert compare_netcdf(reference, candidate) == ["RR: data differ"]


def test_compare_netcdf_reports_attribute_drift(tmp_path):
    reference = tmp_path / "reference.nc"
    candidate = tmp_path / "candidate.nc"
    write_dataset(reference, np.array([1.0, 2.0]))
    write_dataset(candidate, np.array([1.0, 2.0]))
    with Dataset(candidate, mode="a") as dataset:
        dataset.variables["RR"].units = "changed"

    assert compare_netcdf(reference, candidate) == ["RR: attribute 'units' differs"]
