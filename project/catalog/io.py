from pathlib import Path


def read_text(path: Path) -> str:
    """Return the full text content of a file (UTF-8)."""
    return Path(path).read_text(encoding="utf-8")


def read_lines(path: Path) -> list[str]:
    """Return the file content split into lines (newline stripped)."""
    return read_text(path).splitlines()
