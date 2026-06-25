#!/usr/bin/env python3
"""Render buildboard.csv (pipe-delimited) into a self-contained green/red HTML board.

Input line format (header written by the Jenkins append step):
    timestamp|repo_url|revision|user|result|job

One row per (repo, revision); one column per job/pipeline. Each cell shows the
LATEST result for that (repo, revision, job). Per-revision overall tick is green
only if every job that reported for that revision passed.

Python 3.9+, standard library only. Run via:  python render_buildboard.py
"""
import argparse
import csv
import html
import sys
from collections import defaultdict
from datetime import datetime, timezone

DELIM = "|"
HEADER = ["timestamp", "repo_url", "revision", "user", "result", "job"]

# result -> (css class, glyph, rank)  ; higher rank = worse, used for "overall"
STATUS = {
    "SUCCESS":  ("ok",   "\u2713", 0),  # check
    "UNSTABLE": ("warn", "!",      1),
    "ABORTED":  ("skip", "\u2013", 2),  # en dash
    "FAILURE":  ("bad",  "\u2717", 3),  # ballot x
}
UNKNOWN = ("skip", "?", 2)


def parse_ts(s):
    """Parse the ISO 'Z' timestamp; fall back to a sortable string."""
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)


def rev_sort_key(rev):
    """SVN revisions are integers; sort those numerically, push others to the end."""
    try:
        return (0, int(rev))
    except (ValueError, TypeError):
        return (1, rev)


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter=DELIM)
        for raw in reader:
            if not raw:
                continue
            if raw[0].strip() == "timestamp":  # skip header line(s)
                continue
            rec = dict(zip(HEADER, (c.strip() for c in raw)))
            if len(raw) < len(HEADER):          # tolerate short lines
                for k in HEADER:
                    rec.setdefault(k, "")
            rec["result"] = rec.get("result", "").upper()
            rows.append(rec)
    return rows


def latest_cells(rows):
    """(repo, rev, job) -> winning record (most recent timestamp)."""
    best = {}
    for r in rows:
        key = (r["repo_url"], r["revision"], r["job"])
        if key not in best or parse_ts(r["timestamp"]) >= parse_ts(best[key]["timestamp"]):
            best[key] = r
    return best


def build_model(rows):
    cells = latest_cells(rows)
    repos = defaultdict(lambda: {"jobs": set(), "revs": set(), "cells": {}})
    for (repo, rev, job), rec in cells.items():
        b = repos[repo]
        b["jobs"].add(job)
        b["revs"].add(rev)
        b["cells"][(rev, job)] = rec
    return repos


def overall(rev, jobs, cells):
    """Worst status among jobs that reported for this revision."""
    seen = [cells[(rev, j)]["result"] for j in jobs if (rev, j) in cells]
    if not seen:
        return UNKNOWN
    worst = max(seen, key=lambda res: STATUS.get(res, UNKNOWN)[2])
    return STATUS.get(worst, UNKNOWN)


CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--txt:#e6edf3;--mut:#8b949e;
--ok:#2ea043;--bad:#da3633;--warn:#d29922;--skip:#484f58}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:18px;margin:0 0 2px}
.meta{color:var(--mut);font-size:12px;margin-bottom:18px}
.repo{font-size:13px;color:var(--mut);margin:22px 0 8px;font-weight:600;
word-break:break-all}
.filter{background:var(--panel);border:1px solid var(--line);color:var(--txt);
border-radius:6px;padding:6px 10px;font-size:13px;width:260px;margin-bottom:8px}
table{border-collapse:collapse;width:100%;background:var(--panel);
border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);
white-space:nowrap}
th{font-size:12px;color:var(--mut);font-weight:600;background:#11161d;
position:sticky;top:0}
td.rev{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-weight:600}
tr:last-child td{border-bottom:none}
.pill{display:inline-flex;align-items:center;justify-content:center;
width:22px;height:22px;border-radius:50%;font-weight:700;font-size:13px;color:#fff}
.ok{background:var(--ok)} .bad{background:var(--bad)}
.warn{background:var(--warn);color:#1a1a1a} .skip{background:var(--skip)}
.cell{color:var(--mut)}
.who{color:var(--mut);font-size:12px}
.legend{margin-top:16px;color:var(--mut);font-size:12px}
.legend .pill{width:18px;height:18px;font-size:11px;vertical-align:middle;margin:0 4px 0 12px}
"""

JS = """
function flt(q){q=q.toLowerCase();
document.querySelectorAll('tbody tr').forEach(function(r){
r.style.display=r.textContent.toLowerCase().indexOf(q)<0?'none':''});}
"""


def pill(status, title=""):
    cls, glyph, _ = status
    t = ' title="%s"' % html.escape(title) if title else ""
    return '<span class="pill %s"%s>%s</span>' % (cls, t, glyph)


def render(repos, title):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    total = sum(len(b["cells"]) for b in repos.values())
    out = []
    out.append("<!doctype html><meta charset='utf-8'>")
    out.append("<title>%s</title>" % html.escape(title))
    out.append("<style>%s</style>" % CSS)
    out.append("<div class='wrap'>")
    out.append("<h1>%s</h1>" % html.escape(title))
    out.append("<div class='meta'>generated %s &middot; %d records &middot; %d repo(s)</div>"
               % (now, total, len(repos)))
    out.append("<input class='filter' placeholder='filter revision / user / job\u2026' "
               "oninput='flt(this.value)'>")

    for repo in sorted(repos):
        b = repos[repo]
        jobs = sorted(b["jobs"])
        revs = sorted(b["revs"], key=rev_sort_key, reverse=True)
        out.append("<div class='repo'>%s</div>" % html.escape(repo))
        out.append("<table><thead><tr><th></th><th>revision</th>")
        for j in jobs:
            out.append("<th>%s</th>" % html.escape(j))
        out.append("<th>last build by</th><th>when</th></tr></thead><tbody>")

        for rev in revs:
            ov = overall(rev, jobs, b["cells"])
            # find most-recent record across this revision's cells for user/time
            recs = [b["cells"][(rev, j)] for j in jobs if (rev, j) in b["cells"]]
            latest = max(recs, key=lambda r: parse_ts(r["timestamp"]))
            out.append("<tr>")
            out.append("<td>%s</td>" % pill(ov))
            out.append("<td class='rev'>r%s</td>" % html.escape(rev))
            for j in jobs:
                rec = b["cells"].get((rev, j))
                if rec:
                    st = STATUS.get(rec["result"], UNKNOWN)
                    tip = "%s\n%s\n%s" % (rec["result"], rec["timestamp"], rec["user"])
                    out.append("<td class='cell'>%s</td>" % pill(st, tip))
                else:
                    out.append("<td class='cell'>%s</td>" % pill(UNKNOWN, "no build"))
            out.append("<td class='who'>%s</td>" % html.escape(latest["user"]))
            out.append("<td class='who'>%s</td>" % html.escape(latest["timestamp"]))
            out.append("</tr>")
        out.append("</tbody></table>")

    out.append("<div class='legend'>"
               "%s passed %s failed %s unstable %s no build / aborted</div>"
               % (pill(STATUS["SUCCESS"]), pill(STATUS["FAILURE"]),
                  pill(STATUS["UNSTABLE"]), pill(UNKNOWN)))
    out.append("<script>%s</script>" % JS)
    out.append("</div>")
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render buildboard.csv to HTML.")
    ap.add_argument("-i", "--input", default="buildboard.csv")
    ap.add_argument("-o", "--output", default="buildboard.html")
    ap.add_argument("-t", "--title", default="Build Board")
    a = ap.parse_args(argv)

    try:
        rows = load(a.input)
    except FileNotFoundError:
        print("input not found: %s" % a.input, file=sys.stderr)
        return 1

    htmldoc = render(build_model(rows), a.title)
    with open(a.output, "w", encoding="utf-8") as fh:
        fh.write(htmldoc)
    print("wrote %s (%d records)" % (a.output, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
