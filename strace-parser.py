#!/usr/bin/env python3.9
"""Extract executables spawned during a `make` run from a Cygwin strace log.

    strace -o build-trace.txt make <targets>
    python3.9 parse_strace.py build-trace.txt
    python3.9 parse_strace.py build-trace.txt --funcs   # tune SPAWN_MARKERS
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

# Cygwin strace line: "<relus> <totus> [thread] <prog> <pid> <func>: <rest>"
LINE_RE = re.compile(
    r"^\s*\d+\s+\d+\s+\[[^\]]*\]\s+\S+\s+\d+\s+(?P<func>[^:]+):\s*(?P<rest>.*)$"
)

# Trace functions that carry a spawn/exec. VERIFY with --funcs, then adjust.
SPAWN_MARKERS = ("spawn", "exec")

# C:\cygwin64\bin\gcc.exe  style
WIN_EXE_RE = re.compile(r"[A-Za-z]:[\\/][^\s,;)\"']*?\.exe", re.IGNORECASE)
# /usr/bin/gcc  or  /cygdrive/c/.../foo.exe  style
POSIX_RE = re.compile(r"/(?:cygdrive/[A-Za-z]/)?[^\s,;)\"']+")


def cygdrive_to_win(p: str) -> str:
    m = re.match(r"/cygdrive/([A-Za-z])/(.*)", p)
    if m:
        return f"{m.group(1).upper()}:\\" + m.group(2).replace("/", "\\")
    return p


def extract_paths(rest):
    found = [m.group(0) for m in WIN_EXE_RE.finditer(rest)]
    for m in POSIX_RE.finditer(rest):           # remove this loop if too noisy
        tok = m.group(0)
        if tok.endswith(".exe") or "/bin/" in tok or "/usr/" in tok:
            found.append(tok)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--funcs", action="store_true",
                    help="list trace function names + counts, then exit")
    args = ap.parse_args()

    func_counter = Counter()
    binaries = Counter()        # path -> number of spawns
    unmatched = 0
    samples = []

    with open(args.logfile, encoding="latin-1", errors="replace") as fh:
        for line in fh:
            m = LINE_RE.match(line)
            if not m:
                unmatched += 1
                if line.strip() and len(samples) < 3:
                    samples.append(line.rstrip())
                continue
            func = m.group("func").strip()
            func_counter[func] += 1
            if args.funcs:
                continue
            if not any(mark in func.lower() for mark in SPAWN_MARKERS):
                continue
            for p in extract_paths(m.group("rest")):
                binaries[cygdrive_to_win(p)] += 1

    if args.funcs:
        print(f"# lines not matching LINE_RE: {unmatched}")
        for s in samples:
            print(f"#   sample: {s}")
        for func, n in func_counter.most_common():
            print(f"{n:7d}  {func}")
        return 0

    if not binaries:
        print("No spawns matched. Run --funcs: if LINE_RE doesn't match your "
              "lines, fix the prefix regex; otherwise adjust SPAWN_MARKERS.",
              file=sys.stderr)
        return 1

    for path, n in sorted(binaries.items()):
        print(f"{n:5d}  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())