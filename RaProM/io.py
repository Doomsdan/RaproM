"""Filesystem helpers for RaProM raw files."""

from pathlib import Path


def list_raw_files(root):
    """Return sorted ``.raw`` files below *root* (non-recursive)."""
    return sorted(Path(root).glob("*.raw"))


def ensure_directory(path):
    """Create *path* if needed and return it as a ``Path``."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
