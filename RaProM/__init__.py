"""RaProM: processing tools for MRR2 radar raw data."""

import logging

__all__ = ["CorrectorFile", "process_directory", "process_raw_file"]

logging.getLogger(__name__).addHandler(logging.NullHandler())


def __getattr__(name):
    if name == "CorrectorFile":
        from .correction import CorrectorFile

        return CorrectorFile
    if name in {"process_directory", "process_raw_file"}:
        from .netcdf import process_directory, process_raw_file

        return {"process_directory": process_directory, "process_raw_file": process_raw_file}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
