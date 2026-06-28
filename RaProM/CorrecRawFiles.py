"""Compatibility wrapper for raw-file correction."""

from raprom.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["correct", *(__import__("sys").argv[1:] or [input("Insert the path where the raw are --for instance d:\\Mrrdata/\n")])]))
