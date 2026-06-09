#!/usr/bin/env python3
"""
Build a reproducible (byte-stable) zip archive on any host.

Why this is reproducible:
  - Stores files uncompressed (ZIP_STORED), so the output is INDEPENDENT of the
    zlib version linked into the Python interpreter.
  - Pins every per-entry field that would otherwise vary: timestamp, the
    "host OS" field, and external attributes.
  - Pins entry order (filesystem walk order is not deterministic).
  Result: same inputs + same epoch  ->  byte-identical archive, on Windows,
  Linux, or macOS, regardless of interpreter build.

Optionally embeds a SHA256SUMS manifest of the contents, so integrity rests on
the binaries rather than on the wrapper bytes.

Usage:
    make_release_zip.py OUT.zip ROOTDIR [--epoch N] [--no-manifest]

EPOCH precedence: --epoch  >  $SOURCE_DATE_EPOCH  >  SVN last-changed date of ROOTDIR.
"""

import argparse
import calendar
import hashlib
import os
import subprocess
import time
import zipfile

DOS_MIN_EPOCH = 315532800          # 1980-01-01T00:00:00Z: earliest a zip can store
MANIFEST_NAME = "SHA256SUMS"


def resolve_epoch(root):
    """Fixed timestamp for all entries, in Unix epoch seconds (UTC)."""
    env = os.environ.get("SOURCE_DATE_EPOCH")
    if env:
        return int(env)
    # SVN reports last-changed-date in UTC (trailing 'Z'); timegm treats it as UTC.
    iso = subprocess.check_output(
        ["svn", "info", "--show-item", "last-changed-date", root],
        text=True,
    ).strip()
    return calendar.timegm(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S"))


def collect_files(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()            # deterministic descent
        for name in filenames:
            files.append(os.path.join(dirpath, name))
    files.sort()
    return files


def arcname_for(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def build(out_path, root, epoch, with_manifest=True):
    epoch = max(int(epoch), DOS_MIN_EPOCH)
    date_time = time.gmtime(epoch)[:6]   # (Y, M, D, h, m, s) UTC -- never localtime

    # Collect (arcname, bytes) for every entry, including the manifest.
    entries = []
    manifest_lines = []
    for path in collect_files(root):
        arc = arcname_for(path, root)
        with open(path, "rb") as fh:
            data = fh.read()
        entries.append((arc, data))
        if with_manifest:
            manifest_lines.append(f"{hashlib.sha256(data).hexdigest()}  {arc}\n")

    if with_manifest:
        # sha256sum-style manifest: sorted, LF line endings, ASCII.
        manifest = "".join(sorted(manifest_lines)).encode("ascii")
        entries.append((MANIFEST_NAME, manifest))

    entries.sort(key=lambda e: e[0])     # deterministic entry order

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for arc, data in entries:
            zi = zipfile.ZipInfo(arc, date_time=date_time)
            zi.compress_type = zipfile.ZIP_STORED
            zi.create_system = 0         # force MS-DOS/FAT field on every host
            zi.external_attr = 0         # fixed attributes; do not inherit source perms
            zf.writestr(zi, data)        # we supply ALL metadata explicitly


def main(argv=None):
    p = argparse.ArgumentParser(description="Build a byte-reproducible zip archive.")
    p.add_argument("out", help="output .zip path")
    p.add_argument("root", help="directory whose contents are packaged")
    p.add_argument("--epoch", type=int, default=None,
                   help="fixed timestamp (Unix epoch); "
                        "defaults to $SOURCE_DATE_EPOCH or the SVN last-changed date")
    p.add_argument("--no-manifest", action="store_true",
                   help="do not embed a SHA256SUMS manifest")
    args = p.parse_args(argv)

    epoch = args.epoch if args.epoch is not None else resolve_epoch(args.root)
    build(args.out, args.root, epoch, with_manifest=not args.no_manifest)
    print(f"wrote {args.out}  (epoch={epoch}, manifest={not args.no_manifest})")


if __name__ == "__main__":
    main()

#build twice → certutil -hashfile out.zip SHA256   (compare the two hashes)
#or fc /b a.zip b.zip.