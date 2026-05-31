"""
Render the row-vs-previous-row diff table as HTML inside a Tkinter window.

Requires tkinterweb (it embeds a real HTML/CSS engine, so tables and the
ins/del background colors actually render):

    pip install tkinterweb

Run:
    python diff_tk.py      (or:  py diff_tk.py  on Windows)
"""
import html
import re
import tkinter as tk
from difflib import SequenceMatcher

try:
    from tkinterweb import HtmlFrame
except ImportError:
    raise SystemExit("This script needs tkinterweb. Install it with:\n    pip install tkinterweb")

_WORD = re.compile(r"\S+|\s+")


def html_diff(old: str, new: str, by: str = "char") -> str:
    """Inline HTML diff of two strings: removed text in <del>, added in <ins>."""
    a = list(old) if by == "char" else _WORD.findall(old)
    b = list(new) if by == "char" else _WORD.findall(new)
    parts = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            parts.append(html.escape("".join(a[i1:i2])))
        else:
            if i1 != i2:
                parts.append(f"<del>{html.escape(''.join(a[i1:i2]))}</del>")
            if j1 != j2:
                parts.append(f"<ins>{html.escape(''.join(b[j1:j2]))}</ins>")
    return "".join(parts)


CSS = """
<style>
  body  { font-family: 'Segoe UI', sans-serif; background: #ffffff; margin: 12px; }
  table { border-collapse: collapse; font-size: 14px; }
  th, td { border: 1px solid #cccccc; padding: 6px 10px; text-align: left; }
  thead th { background: #f0f0f0; }
  ins { background: #e6ffed; color: #036a1e; text-decoration: none; }
  del { background: #ffeef0; color: #b31515; }
</style>
"""

# diff granularity per column: short codes -> char, prose -> word
COL_MODE = ["char", "char", "char", "word"]


def build_table_html(table) -> str:
    """Build the entire HTML document: each data row diffed against the row above it."""
    header, data = table[0], table[1:]
    rows = ["<tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in header) + "</tr>"]
    # first data row: nothing before it, render plain
    rows.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in data[0]) + "</tr>")
    prev = data[0]
    for row in data[1:]:
        cells = [
            html_diff(p, c, by=COL_MODE[i] if i < len(COL_MODE) else "char")
            for i, (p, c) in enumerate(zip(prev, row))
        ]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        prev = row
    return CSS + "<table>" + "".join(rows) + "</table>"


TABLE = [
    ["version", "status", "owner", "notes"],
    ["v1.0", "draft",  "alice", "initial draft"],
    ["v1.1", "draft",  "alice", "initial layout"],
    ["v1.2", "review", "bob",   "initial layout"],
    ["v2.0", "review", "bob",   "major rewrite of intro"],
]


def main():
    document = build_table_html(TABLE)
    root = tk.Tk()
    root.title("Row diff viewer")
    root.geometry("680x340")
    frame = HtmlFrame(root)
    frame.load_html(document)
    frame.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()