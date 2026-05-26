import filecmp
from pathlib import Path


def files_equal(a: Path, b: Path) -> bool:
    """True if two files are byte-identical."""
    return filecmp.cmp(a, b, shallow=False)


def files_differ(a: Path, b: Path) -> bool:
    """True if two files are not byte-identical."""
    return not files_equal(a, b)
