
import sys
from clang import cindex

# pip install clan libclang
import sys, os
from clang import cindex

def walk(node, edges, current=None):
    if node.kind == cindex.CursorKind.FUNCTION_DECL and node.is_definition():
        current = node.spelling
        edges.setdefault(current, set())
    elif node.kind == cindex.CursorKind.CALL_EXPR and current:
        ref = node.referenced
        if ref is not None:
            edges[current].add(ref.spelling)
    for child in node.get_children():
        walk(child, edges, current)

def c_sources(root):
    if os.path.isfile(root):
        yield root; return
    for dirpath, _d, files in os.walk(root):
        for f in files:
            if f.endswith((".c", ".cc", ".cpp", ".cxx")):
                yield os.path.join(dirpath, f)

def main():
    root = sys.argv[1]
    args = ["-I.", "-Iinclude", "-DSOME_DEFINE"]   # <-- replace with your REAL build flags
    index, edges = cindex.Index.create(), {}
    for src in c_sources(root):
        try:
            tu = index.parse(src, args=args)
        except cindex.TranslationUnitLoadError:
            print(f"SKIP (unparseable): {src}", file=sys.stderr)
            continue
        for d in tu.diagnostics:                    # shows WHY files don't fully parse
            if d.severity >= cindex.Diagnostic.Error:
                print(f"  {src}: {d.spelling}", file=sys.stderr)
        walk(tu.cursor, edges)
    for caller in sorted(edges):
        for callee in sorted(edges[caller]):
            print(f"{caller} -> {callee}")

if __name__ == "__main__":
    main()