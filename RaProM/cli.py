"""Command line interface for RaProM."""

import argparse
import warnings

import numpy as np

from .correction import CorrectorFile
from .io import list_raw_files


def build_parser():
    parser = argparse.ArgumentParser(prog="raprom", description="Process and correct MRR raw files.")
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="Convert .raw files in a folder to NetCDF.")
    process.add_argument("path", help="Folder containing .raw files.")
    process.add_argument("-i", "--integration-time", type=int, required=True, help="Integration time in seconds, usually 60.")
    process.add_argument("--antenna-height", "-H", type=float, default=np.nan, help="Antenna height in meters.")
    process.add_argument("-M", "--adjust-m", type=float, default=1.0, help="Multiplicative calibration bias M.")
    process.add_argument("--no-correct", action="store_true", help="Skip raw-file correction before processing.")

    correct = subparsers.add_parser("correct", help="Correct .raw files in a folder.")
    correct.add_argument("path", help="Folder containing .raw files.")

    parser.set_defaults(command="process")
    return parser


def main(argv=None):
    if not warnings.filters:
        warnings.simplefilter("ignore")
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "correct":
        raw_files = list_raw_files(args.path)
        print('In this folder there are '+str(len(raw_files))+' raw files')
        if raw_files:
            print('Corrected files are written to the CorrectedRaw output folder; original raw files are left unchanged.\n')
        for raw_file in raw_files:
            CorrectorFile(str(raw_file))
        return 0

    from .netcdf import process_directory

    process_directory(
        args.path,
        args.integration_time,
        antenna_height=args.antenna_height,
        adjust_m=args.adjust_m,
        correct=not args.no_correct,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
