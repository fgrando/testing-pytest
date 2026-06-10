import sys
from clang import cindex
from pytest import Config          # pip install clang + a libclang shared lib

Config.set_library_path(r"C:\Users\fgrando\Downloads\testing-pytest")

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

edges, index = {}, cindex.Index.create()
for src in sys.argv[1:]:
    tu = index.parse(src, args=["-I.", "-Iinclude", "-DSOME_DEFINE"])
    walk(tu.cursor, edges)

for caller in sorted(edges):
    for callee in sorted(edges[caller]):
        print(f"{caller} -> {callee}")