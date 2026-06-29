"""Command line interface for RaProM."""

import argparse
import logging
import warnings

import numpy as np

from .correction import CorrectorFile
from .io import list_raw_files


def configure_logging(verbose=0, quiet=False, log_file=None):
    """Configure package logging for command line usage."""
    if quiet:
        level = logging.WARNING
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.INFO

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def add_logging_options(parser, default=0):
    parser.add_argument("-v", "--verbose", action="count", default=default, help="Increase logging verbosity; use twice for debug logs.")
    parser.add_argument("-q", "--quiet", action="store_true", default=False if default == 0 else argparse.SUPPRESS, help="Only show warnings and errors.")
    parser.add_argument("--log-file", default=None if default == 0 else argparse.SUPPRESS, help="Write logs to this file in addition to the console.")
    return parser


def build_parser():
    parser = argparse.ArgumentParser(prog="raprom", description="Process and correct MRR raw files.")
    add_logging_options(parser)
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="Convert .raw files in a folder to NetCDF.")
    add_logging_options(process, default=argparse.SUPPRESS)
    process.add_argument("path", help="Folder containing .raw files.")
    process.add_argument("-i", "--integration-time", type=int, required=True, help="Integration time in seconds, usually 60.")
    process.add_argument("--antenna-height", "-H", type=float, default=np.nan, help="Antenna height in meters.")
    process.add_argument("-M", "--adjust-m", type=float, default=1.0, help="Multiplicative calibration bias M.")
    process.add_argument("--no-correct", action="store_true", help="Skip raw-file correction before processing.")

    correct = subparsers.add_parser("correct", help="Correct .raw files in a folder.")
    add_logging_options(correct, default=argparse.SUPPRESS)
    correct.add_argument("path", help="Folder containing .raw files.")

    parser.set_defaults(command="process")
    return parser


def main(argv=None):
    if not warnings.filters:
        warnings.simplefilter("ignore")
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose, args.quiet, args.log_file)
    logger = logging.getLogger(__name__)

    if args.command == "correct":
        raw_files = list_raw_files(args.path)
        logger.info("Found %s raw file(s) in %s", len(raw_files), args.path)
        if raw_files:
            logger.info("Corrected files are written to the CorrectedRaw output folder; original raw files are left unchanged.")
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
