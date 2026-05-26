import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .io import read_lines

_DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(\S+)")


def parse_c_defines(path: Path, prefix: str = "") -> dict[str, str]:
    """Extract `#define NAME VALUE` pairs from a C header.

    If `prefix` is given, only defines whose name starts with it are returned.
    """
    out = {}
    for line in read_lines(path):
        m = _DEFINE_RE.match(line)
        if m and m.group(1).startswith(prefix):
            out[m.group(1)] = m.group(2)
    return out


def parse_xml_entries(path: Path, tag: str = "entry") -> dict[str, str]:
    """Return {name: value} for every <tag name="..." value="..."/> element."""
    root = ET.parse(path).getroot()
    return {e.attrib["name"]: e.attrib["value"] for e in root.iter(tag)}
