"""Command line interface for RaProM."""

import argparse
import logging
import warnings

import numpy as np

from .config import load_process_config, merge_process_config
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


def add_config_option(parser, default=None):
    parser.add_argument("-c", "--config", default=default, help="Load process options from a TOML/YAML config file.")
    return parser


def build_parser():
    parser = argparse.ArgumentParser(prog="raprom", description="Process and correct MRR raw files.")
    add_logging_options(parser)
    add_config_option(parser)
    subparsers = parser.add_subparsers(dest="command")

    process = subparsers.add_parser("process", help="Convert .raw files in a folder to NetCDF.")
    add_logging_options(process, default=argparse.SUPPRESS)
    add_config_option(process, default=argparse.SUPPRESS)
    process.add_argument("path", nargs="?", default=None, help="Folder containing .raw files.")
    process.add_argument("-i", "--integration-time", type=int, default=None, help="Integration time in seconds, usually 60.")
    process.add_argument("--antenna-height", "-H", type=float, default=None, help="Antenna height in meters.")
    process.add_argument("-M", "--adjust-m", type=float, default=None, help="Multiplicative calibration bias M.")
    process.add_argument("-o", "--output-dir", default=None, help="Folder for generated NetCDF files.")
    process.add_argument("--no-correct", action="store_false", dest="correct", default=None, help="Skip raw-file correction before processing.")

    correct = subparsers.add_parser("correct", help="Correct .raw files in a folder.")
    add_logging_options(correct, default=argparse.SUPPRESS)
    correct.add_argument("path", help="Folder containing .raw files.")

    benchmark = subparsers.add_parser("benchmark", help="Process one .raw file and optionally compare it to a reference NetCDF.")
    add_logging_options(benchmark, default=argparse.SUPPRESS)
    benchmark.add_argument("raw_file", help="Raw file to process.")
    benchmark.add_argument("-i", "--integration-time", type=int, required=True, help="Integration time in seconds, usually 60.")
    benchmark.add_argument("--reference", default=None, help="Reference NetCDF file that must match exactly.")
    benchmark.add_argument("--repeats", type=int, default=1, help="Number of processing runs.")
    benchmark.add_argument("--antenna-height", "-H", type=float, default=np.nan, help="Antenna height in meters.")
    benchmark.add_argument("-M", "--adjust-m", type=float, default=1.0, help="Multiplicative calibration bias M.")
    benchmark.add_argument("-o", "--output-dir", default=None, help="Folder for benchmark outputs.")
    benchmark.add_argument("--correct", action="store_true", default=False, help="Correct raw file before processing.")

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

    if args.command == "benchmark":
        from .benchmark import benchmark_raw_file

        runs = benchmark_raw_file(
            args.raw_file,
            args.integration_time,
            antenna_height=args.antenna_height,
            adjust_m=args.adjust_m,
            correct=args.correct,
            reference_netcdf=args.reference,
            repeats=args.repeats,
            output_dir=args.output_dir,
        )
        for index, run in enumerate(runs, start=1):
            logger.info("Benchmark run %s: %.3f s -> %s", index, run.elapsed_seconds, run.output_path)
            if run.differences:
                for difference in run.differences:
                    logger.error("Reference mismatch: %s", difference)
                return 1
        return 0

    from .netcdf import process_directory

    try:
        process_config = merge_process_config(
            load_process_config(args.config),
            {
                "path": getattr(args, "path", None),
                "integration_time": getattr(args, "integration_time", None),
                "antenna_height": getattr(args, "antenna_height", None),
                "adjust_m": getattr(args, "adjust_m", None),
                "output_dir": getattr(args, "output_dir", None),
                "correct": getattr(args, "correct", None),
            },
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    if not process_config.path:
        parser.error("process requires a path argument or process.path in the config file.")
    if process_config.integration_time is None:
        parser.error("process requires --integration-time or process.integration_time in the config file.")

    process_directory(
        process_config.path,
        process_config.integration_time,
        antenna_height=process_config.antenna_height,
        adjust_m=process_config.adjust_m,
        correct=process_config.correct,
        output_dir=process_config.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
