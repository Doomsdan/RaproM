"""Filesystem helpers for RaProM raw files."""

from pathlib import Path
import bz2
import gzip
import logging
import shutil
import tarfile
import zipfile


logger = logging.getLogger(__name__)

SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".pytest_tmp",
    "__pycache__",
    "CorrectedRaw",
    "Moved",
}


def _is_in_skipped_directory(path):
    return any(part in SKIPPED_DIRECTORY_NAMES for part in path.parts)


def list_raw_files(root):
    """Return sorted ``.raw`` files below *root* and its subfolders."""
    return sorted(path for path in Path(root).rglob("*.raw") if not _is_in_skipped_directory(path.relative_to(root)))


def ensure_directory(path):
    """Create *path* if needed and return it as a ``Path``."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_member_path(root, member_name):
    destination = (root / member_name).resolve()
    root_resolved = root.resolve()
    if destination != root_resolved and root_resolved not in destination.parents:
        raise ValueError(f"Archive member would extract outside target folder: {member_name}")
    return destination


def _extract_zip(archive_path, root, should_extract=None):
    extracted = []
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            destination = _safe_member_path(root, member.filename)
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if destination.exists():
                logger.info("Skipping already extracted file: %s", destination)
                continue
            if should_extract is not None and not should_extract(destination):
                logger.info("Skipping archive member because output already exists: %s", destination)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Extracting %s from %s", destination, archive_path)
            with archive.open(member) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            extracted.append(destination)
    return extracted


def _extract_tar(archive_path, root, should_extract=None):
    extracted = []
    with tarfile.open(archive_path) as archive:
        for member in archive.getmembers():
            destination = _safe_member_path(root, member.name)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                logger.info("Skipping unsupported archive member: %s", member.name)
                continue
            if destination.exists():
                logger.info("Skipping already extracted file: %s", destination)
                continue
            if should_extract is not None and not should_extract(destination):
                logger.info("Skipping archive member because output already exists: %s", destination)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                continue
            logger.info("Extracting %s from %s", destination, archive_path)
            with source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
            extracted.append(destination)
    return extracted


def _extract_gzip(archive_path, root, should_extract=None):
    if archive_path.suffix.lower() != ".gz":
        return []
    destination = root / archive_path.stem
    if destination.exists():
        logger.info("Skipping already extracted file: %s", destination)
        return []
    if should_extract is not None and not should_extract(destination):
        logger.info("Skipping archive because output already exists: %s", destination)
        return []
    logger.info("Extracting %s from %s", destination, archive_path)
    with gzip.open(archive_path, "rb") as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)
    return [destination]


def _extract_bzip2(archive_path, root, should_extract=None):
    if archive_path.suffix.lower() != ".bz2":
        return []
    destination = root / archive_path.stem
    if destination.exists():
        logger.info("Skipping already extracted file: %s", destination)
        return []
    if should_extract is not None and not should_extract(destination):
        logger.info("Skipping archive because output already exists: %s", destination)
        return []
    logger.info("Extracting %s from %s", destination, archive_path)
    with bz2.open(archive_path, "rb") as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)
    return [destination]


def extract_archives(root, should_extract=None):
    """Extract supported archives below *root* without overwriting existing files."""
    root_path = Path(root)
    extracted = []
    for archive_path in sorted(root_path.rglob("*")):
        if not archive_path.is_file():
            continue
        if _is_in_skipped_directory(archive_path.relative_to(root_path)):
            continue
        extract_root = archive_path.parent
        suffixes = [suffix.lower() for suffix in archive_path.suffixes]
        try:
            if archive_path.suffix.lower() == ".zip":
                extracted.extend(_extract_zip(archive_path, extract_root, should_extract))
            elif archive_path.suffix.lower() == ".tar" or suffixes[-2:] in ([".tar", ".gz"], [".tar", ".bz2"], [".tar", ".xz"]):
                extracted.extend(_extract_tar(archive_path, extract_root, should_extract))
            elif archive_path.suffix.lower() == ".gz":
                extracted.extend(_extract_gzip(archive_path, extract_root, should_extract))
            elif archive_path.suffix.lower() == ".bz2":
                extracted.extend(_extract_bzip2(archive_path, extract_root, should_extract))
        except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
            logger.warning("Could not extract %s: %s", archive_path, exc)
    if extracted:
        logger.info("Extracted %s file(s) from archive(s) in %s", len(extracted), root_path)
    return extracted
