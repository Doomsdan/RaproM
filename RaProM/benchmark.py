"""Benchmark and regression helpers for processing changes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
import time

import numpy as np
from netCDF4 import Dataset

from .netcdf import process_raw_file


@dataclass(frozen=True)
class BenchmarkRun:
    """Result for one processing benchmark run."""

    output_path: Path
    elapsed_seconds: float
    differences: tuple[str, ...]


def _attrs(dataset_or_variable):
    return {
        name: dataset_or_variable.getncattr(name)
        for name in dataset_or_variable.ncattrs()
    }


def _attrs_equal(left, right):
    if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
        return np.array_equal(np.asarray(left), np.asarray(right), equal_nan=True)
    return left == right


def _arrays_exactly_equal(left, right):
    left_array = np.ma.asarray(left)
    right_array = np.ma.asarray(right)

    if left_array.shape != right_array.shape:
        return False
    if left_array.dtype != right_array.dtype:
        return False
    if not np.array_equal(np.ma.getmaskarray(left_array), np.ma.getmaskarray(right_array)):
        return False

    left_data = np.asarray(left_array.filled(np.nan if np.issubdtype(left_array.dtype, np.floating) else 0))
    right_data = np.asarray(right_array.filled(np.nan if np.issubdtype(right_array.dtype, np.floating) else 0))

    if np.issubdtype(left_data.dtype, np.floating):
        equal = (left_data == right_data) | (np.isnan(left_data) & np.isnan(right_data))
        return bool(np.all(equal))
    return bool(np.array_equal(left_data, right_data))


def compare_netcdf(reference_path, candidate_path, *, compare_attrs=True):
    """Return exact differences between two NetCDF files.

    Floating point variables must match exactly, except NaNs are treated as
    equal when they appear in the same locations.
    """
    differences = []
    with Dataset(reference_path) as reference, Dataset(candidate_path) as candidate:
        reference_dimensions = {name: len(dim) for name, dim in reference.dimensions.items()}
        candidate_dimensions = {name: len(dim) for name, dim in candidate.dimensions.items()}
        if reference_dimensions != candidate_dimensions:
            differences.append(f"dimensions differ: {reference_dimensions!r} != {candidate_dimensions!r}")

        reference_variables = set(reference.variables)
        candidate_variables = set(candidate.variables)
        for name in sorted(reference_variables - candidate_variables):
            differences.append(f"missing variable in candidate: {name}")
        for name in sorted(candidate_variables - reference_variables):
            differences.append(f"extra variable in candidate: {name}")

        for name in sorted(reference_variables & candidate_variables):
            reference_variable = reference.variables[name]
            candidate_variable = candidate.variables[name]
            if reference_variable.dimensions != candidate_variable.dimensions:
                differences.append(
                    f"{name}: dimensions differ: {reference_variable.dimensions!r} != {candidate_variable.dimensions!r}"
                )
            if reference_variable.dtype != candidate_variable.dtype:
                differences.append(f"{name}: dtype differs: {reference_variable.dtype!r} != {candidate_variable.dtype!r}")
            if not _arrays_exactly_equal(reference_variable[:], candidate_variable[:]):
                differences.append(f"{name}: data differ")

            if compare_attrs:
                reference_attrs = _attrs(reference_variable)
                candidate_attrs = _attrs(candidate_variable)
                if reference_attrs.keys() != candidate_attrs.keys():
                    differences.append(f"{name}: attribute names differ")
                for attr_name in sorted(reference_attrs.keys() & candidate_attrs.keys()):
                    if not _attrs_equal(reference_attrs[attr_name], candidate_attrs[attr_name]):
                        differences.append(f"{name}: attribute {attr_name!r} differs")

        if compare_attrs:
            reference_attrs = _attrs(reference)
            candidate_attrs = _attrs(candidate)
            if reference_attrs.keys() != candidate_attrs.keys():
                differences.append("dataset attribute names differ")
            for attr_name in sorted(reference_attrs.keys() & candidate_attrs.keys()):
                if not _attrs_equal(reference_attrs[attr_name], candidate_attrs[attr_name]):
                    differences.append(f"dataset attribute {attr_name!r} differs")

    return differences


def benchmark_raw_file(
    raw_file,
    integration_time,
    *,
    antenna_height=np.nan,
    adjust_m=1.0,
    correct=False,
    reference_netcdf=None,
    repeats=1,
    output_dir=None,
):
    """Process a raw file repeatedly and optionally compare each output exactly."""
    runs = []
    if output_dir is None:
        temporary_directory = tempfile.TemporaryDirectory(prefix="raprom-benchmark-")
        benchmark_output_dir = Path(temporary_directory.name)
    else:
        temporary_directory = None
        benchmark_output_dir = Path(output_dir)
        benchmark_output_dir.mkdir(parents=True, exist_ok=True)

    try:
        for index in range(repeats):
            run_output_dir = benchmark_output_dir / f"run-{index + 1}"
            run_output_dir.mkdir(parents=True, exist_ok=True)
            started_at = time.perf_counter()
            output_path = Path(
                process_raw_file(
                    raw_file,
                    integration_time,
                    antenna_height=antenna_height,
                    adjust_m=adjust_m,
                    correct=correct,
                    output_dir=run_output_dir,
                )
            )
            elapsed_seconds = time.perf_counter() - started_at
            differences = ()
            if reference_netcdf is not None:
                differences = tuple(compare_netcdf(reference_netcdf, output_path))
            runs.append(BenchmarkRun(output_path, elapsed_seconds, differences))
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()

    return runs
