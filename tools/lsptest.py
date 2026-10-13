#!/usr/bin/env python3
"""Test the language server (sloppy lsp) the way an editor uses it.
usage: tools/lsptest.py [path/to/sloppy]        (default: bin/sloppy)"""
import json, os, pathlib, subprocess, sys, tempfile, urllib.parse

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
to_uri = lambda p: pathlib.Path(p).as_uri()
# (the same file: Windows URIs may differ in a drive letter's case and in how its colon is written)
same_uri = lambda a, b: a == b or os.name == "nt" and urllib.parse.unquote(a).lower() == urllib.parse.unquote(b).lower()


class Client:
    def __init__(self):
        self.p = subprocess.Popen([sloppy, "lsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")))
        self.id = 0
        self.notes = []
        self.versions = {}

    def send(self, obj):
        b = json.dumps(obj).encode()
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(b) + b)
        self.p.stdin.flush()

    def recv(self):
        h = b""
        while not h.endswith(b"\r\n\r\n"):
            c = self.p.stdout.read(1)
            if not c: raise EOFError("the server exited")
            h += c
        n = int([l for l in h.decode().split("\r\n") if l.lower().startswith("content-length")][0].split(":")[1])
        return json.loads(self.p.stdout.read(n))

    def request(self, method, params):
        self.id += 1
        self.send({"jsonrpc": "2.0", "id": self.id, "method": method, "params": params})
        while True:
            m = self.recv()
            if m.get("id") == self.id and "method" not in m:
                return m.get("result", m.get("error"))
            self.notes.append(m)

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def set_text(self, uri, text):
        v = self.versions.get(uri, 0) + 1
        self.versions[uri] = v
        if v == 1:
            self.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": "sloppy", "version": 1, "text": text}})
        else:
            self.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": v}, "contentChanges": [{"text": text}]})

    def diagnostics(self, uri):
        v = self.versions[uri]
        while True:
            for i, m in enumerate(self.notes):
                p = m.get("params", {})
                if m.get("method") == "textDocument/publishDiagnostics" and p["uri"] == uri and p.get("version") == v:
                    del self.notes[i]
                    return p["diagnostics"]
            self.notes.append(self.recv())


failures = 0
count = 0


def check(name, got, want):
    global failures, count
    count += 1
    if got != want:
        failures += 1
        print(f"FAIL {name}:\n  got:  {got!r}\n  want: {want!r}")


def lc(text, off):
    pre = text[:off]
    return {"line": pre.count("\n"), "character": off - (pre.rfind("\n") + 1)}


tmp = tempfile.mkdtemp(prefix="sloppy-lsptest-")
c = Client()
caps = c.request("initialize", {"capabilities": {}, "rootUri": to_uri(tmp)})["capabilities"]
check("capabilities", sorted(k for k, v in caps.items() if v), sorted(["textDocumentSync", "hoverProvider", "definitionProvider", "referencesProvider", "documentHighlightProvider", "documentSymbolProvider", "workspaceSymbolProvider", "documentFormattingProvider", "renameProvider", "completionProvider", "signatureHelpProvider", "inlayHintProvider", "semanticTokensProvider"]))
c.notify("initialized", {})

# ---- a program: names, types, declarations ----
prog = '''# A point in the plane
struct Point:
    x: f64      # across
    y: f64

enum Dir: left, right

# the distance between two points
dist = (a: Point, b: Point) -> f64:
    dx = a.x - b.x
    dy = a.y - b.y
    sqrt(dx * dx + dy * dy)

add = (a: int, b: int): a + b

twice = (f, x): f(f(x))

main = ():
    p = Point(1.0, 2.0)
    q = Point(x = 4.0, y = 6.0)
    d = dist(p, q)
    n = add(1, 2)
    t = twice((v: int): v * 2, 5)
    dir: Dir = .left
    xs = [1, 2, 3].map((v): v * 10)
    print(d, n, t, xs, p.dist(q), xs.len(), p.x, dir)
'''
path = os.path.join(tmp, "prog.jo")
open(path, "w", encoding="utf-8").write(prog)
uri = to_uri(path)
c.set_text(uri, prog)
check("no errors", c.diagnostics(uri), [])


def at(s, k=0, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = prog.index(s, i + 1)
    return {"textDocument": {"uri": uri}, "position": lc(prog, i + k)}


def hover(s, k=0, nth=0):
    h = c.request("textDocument/hover", at(s, k, nth))
    return h and h["contents"]["value"]


check("hover local", hover("dx * dx"), "```sloppy\n(variable) dx: f64\n```")
check("hover field", hover("a.x", 2), "```sloppy\n(field) x: f64\n```\n---\nacross")
check("hover function", hover("dist(p"), "```sloppy\ndist = (a: Point, b: Point) -> f64\n```\n---\nthe distance between two points")
check("hover inferred result", hover("add(1"), "```sloppy\nadd = (a: int, b: int) -> int\n```")
check("hover generic", hover("twice("), "```sloppy\ntwice = (f, x)\n# here: twice(f: (int) -> int, x: int) -> int\n```")
check("hover struct", hover("Point(1"), "```sloppy\nstruct Point:\n    x: f64\n    y: f64\n```\n---\nA point in the plane")
check("hover variant", hover(".left", 1), "```sloppy\n(variant) Dir.left\n```")
check("hover method call", hover("p.dist", 2), "```sloppy\ndist = (a: Point, b: Point) -> f64\n```\n---\nthe distance between two points")
check("hover named argument", hover("x = 4.0"), "```sloppy\n(field) x: f64\n```\n---\nacross")
check("hover builtin", hover("len()"), "```sloppy\n(builtin) len\n```")
check("hover lambda parameter", hover("v * 2"), "```sloppy\n(parameter) v: int\n```")
check("hover keyword", hover("loop" if "loop" in prog else "main = ", 7), None)


def where(r):
    if r is None: return None
    if isinstance(r, list): return [where(x) for x in r]
    return (os.path.basename(r["uri"]), r["range"]["start"]["line"], r["range"]["start"]["character"])


check("definition", where(c.request("textDocument/definition", at("dist(p"))), ("prog.jo", 8, 0))
check("definition of a field", where(c.request("textDocument/definition", at("a.x", 2))), ("prog.jo", 2, 4))
check("definition of a local", where(c.request("textDocument/definition", at("d, n, t"))), ("prog.jo", 20, 4))
d = where(c.request("textDocument/definition", at("map(")))
check("definition in the library", d and (d[0], d[1] > 0), ("array.jo", True))
refs = c.request("textDocument/references", dict(at("dist(p"), context={"includeDeclaration": True}))
check("references", sorted(where(refs)), [("prog.jo", 8, 0), ("prog.jo", 20, 8), ("prog.jo", 25, 25)])
hl = c.request("textDocument/documentHighlight", at("dx = "))
check("highlights", len(hl), 3)
ren = c.request("textDocument/rename", dict(at("dist(p"), newName="distance"))
check("rename", sorted((e["range"]["start"]["line"], e["newText"]) for e in ren["changes"][uri]), [(8, "distance"), (20, "distance"), (25, "distance")])
hints = c.request("textDocument/inlayHint", {"textDocument": {"uri": uri}, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 99, "character": 0}}})
check("inlay hints", sorted((h["position"]["line"], h["label"]) for h in hints), [(9, ": f64"), (10, ": f64"), (13, "-> int"), (15, "-> int"), (20, ": f64"), (21, ": int"), (22, ": int"), (24, ": int[]")])
legend = caps["semanticTokensProvider"]["legend"]


def semantic(u, text):
    """the semantic tokens of a document: (line, name, type, modifiers)"""
    data = c.request("textDocument/semanticTokens/full", {"textDocument": {"uri": u}})["data"]
    lines, out, line, ch = text.split("\n"), [], 0, 0
    for i in range(0, len(data), 5):
        dl, dc, n, t, m = data[i:i + 5]
        line, ch = line + dl, dc if dl else ch + dc
        out.append((line, lines[line][ch:ch + n], legend["tokenTypes"][t], ",".join(x for b, x in enumerate(legend["tokenModifiers"]) if m >> b & 1)))
    return out


sem = semantic(uri, prog)
check("semantic tokens", [x for x in sem if x[0] in (1, 2, 5, 8, 9, 13, 20, 23)], [
    (1, "Point", "struct", "declaration"), (2, "x", "property", "declaration"), (5, "Dir", "enum", "declaration"),
    (5, "left", "enumMember", "declaration"), (5, "right", "enumMember", "declaration"),
    (8, "dist", "function", "declaration"), (8, "a", "parameter", "declaration"), (8, "Point", "struct", ""),
    (8, "b", "parameter", "declaration"), (8, "Point", "struct", ""),
    (9, "dx", "variable", "declaration"), (9, "a", "parameter", ""), (9, "x", "property", ""), (9, "b", "parameter", ""), (9, "x", "property", ""),
    (13, "add", "function", "declaration"), (13, "a", "parameter", "declaration"), (13, "b", "parameter", "declaration"), (13, "a", "parameter", ""), (13, "b", "parameter", ""),
    (20, "d", "variable", "declaration"), (20, "dist", "function", ""), (20, "p", "variable", ""), (20, "q", "variable", ""),
    (23, "dir", "variable", "declaration"), (23, "Dir", "enum", ""), (23, "left", "enumMember", "")])
sig = c.request("textDocument/signatureHelp", {"textDocument": {"uri": uri}, "position": lc(prog, prog.index("add(1, ") + 7)})
check("signature help", (sig["signatures"][0]["label"], sig["activeParameter"]), ("add = (a: int, b: int)", 1))
syms = c.request("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
check("symbols", [(s["name"], s["kind"], [k["name"] for k in s.get("children", [])]) for s in syms],
      [("Point", 23, ["x", "y"]), ("Dir", 10, ["left", "right"]), ("dist", 12, []), ("add", 12, []), ("twice", 12, []), ("main", 12, [])])
# workspace symbols: in the open file and in files on disk under the workspace's folder
os.makedirs(os.path.join(tmp, "more"), exist_ok=True)
open(os.path.join(tmp, "more", "extra.jo"), "w").write("struct Pointy:\n    px: int\n\nhelper = () -> int: 1\n")
ws = c.request("workspace/symbol", {"query": "poi"})
check("workspace symbols", sorted((w["name"], w["kind"], os.path.basename(urllib.parse.unquote(w["location"]["uri"]))) for w in ws),
      [("Point", 23, os.path.basename(path)), ("Pointy", 23, "extra.jo")])
# formatting: one edit of the whole text, none when it is laid out already or does not lex
fpath = os.path.join(tmp, "fmt.jo")
furi = to_uri(fpath)
c.set_text(furi, "f=(a:int)->int:\n  a+1\n")
fe = c.request("textDocument/formatting", {"textDocument": {"uri": furi}, "options": {"tabSize": 4, "insertSpaces": True}})
check("formatting", [e["newText"] for e in fe], ["f = (a: int) -> int:\n    a + 1\n"])
c.set_text(furi, "f = (a: int) -> int:\n    a + 1\n")
check("formatting: laid out already", c.request("textDocument/formatting", {"textDocument": {"uri": furi}, "options": {}}), [])
c.set_text(furi, "x = (1\n")
check("formatting: does not lex", c.request("textDocument/formatting", {"textDocument": {"uri": furi}, "options": {}}), [])
ws = c.request("workspace/symbol", {"query": "px"})
check("workspace symbols: members", [(w["name"], w.get("containerName"), w["location"]["range"]["start"]) for w in ws], [("px", "Pointy", {"line": 1, "character": 4})])

# ---- completion ----
cpath = os.path.join(tmp, "comp.jo")
curi = to_uri(cpath)
base = '''struct Ship:
    pos: vec2
    hp: int

enum Mode: idle, chase

ships: Ship[]
mode = Mode.idle

broken = (x: int) -> int:
    x + "no"

update = (dt: f64):
    loop s in ships:
        BODY
'''


def complete(body):
    src = base.replace("BODY", body)
    i = src.index("|")
    src = src.replace("|", "")
    c.set_text(curi, src)
    r = c.request("textDocument/completion", {"textDocument": {"uri": curi}, "position": lc(src, i)})
    return [x["label"] for x in r["items"]]


check("complete fields", complete("s.|")[:2], ["pos", "hp"])
check("complete in an unclosed call", complete("print(s.|")[:2], ["pos", "hp"])
check("complete in an unfinished if", complete("if s.|")[:2], ["pos", "hp"])
check("complete vector components", complete("s.pos.|")[:2], ["x", "y"])
check("complete variants", complete("mode = .|"), ["idle", "chase"])
check("complete enum type members", complete("mode = Mode.|"), ["idle", "chase"])
names = complete("sh|")
check("complete names", all(n in names for n in ["ships", "s", "dt", "Ship", "update", "print", "loop"]), True)
check("no internal names", any(n.startswith("__") for n in names), False)
check("complete array functions", all(n in complete("ships.|") for n in ["len", "push", "map", "filter"]), True)
check("nothing in comments", complete("x = 1  # s.|"), [])

# ---- errors ----
epath = os.path.join(tmp, "errs.jo")
euri = to_uri(epath)
c.set_text(euri, '''helper = (x: int) -> int:
    y = x +
    y

other = (s: str):
    n: int = s
    print(n)

third = (k: int) -> int:
    k.nope

use_helper = ():
    print(helper(3))
''')
check("several errors", [(d["range"]["start"]["line"], d["message"]) for d in c.diagnostics(euri)],
      [(1, "expected an expression here"), (5, "type mismatch: expected int, found str"), (9, "int has no field 'nope'")])
c.set_text(euri, "x = 1.5\ny = x + \"s\"\n")
check("operator error", [d["message"] for d in c.diagnostics(euri)], ["operator + is not defined for f64 and str"])
c.set_text(euri, "x = 1\n")
check("errors cleared", c.diagnostics(euri), [])
# (the build block's target decides which `when` branch is checked, as in a build)
c.set_text(euri, 'build:\n    target = windows\nwhen TARGET == "windows":\n    print(win_only)\nelse:\n    print(other_only)\n')
check("target from the build block", [d["message"] for d in c.diagnostics(euri)], ["unknown name 'win_only'"])
c.set_text(euri, 'build:\n    targte = wasm\n')
check("build block mistakes", [d["message"] for d in c.diagnostics(euri)], ["unknown build option 'targte' (the options are target, opt, output, name and icon)"])
c.set_text(euri, "x = 1\n")
c.diagnostics(euri)
# (errors found by lowering, reported once the editor is quiet)
c.set_text(euri, "total = 0\nxs = [1, 2, 3]\nys = parallel_map(xs, (x: int) -> int:\n    total += x\n    x)\nprint(ys)\n")
check("lowering: first the checker's", c.diagnostics(euri), [])
check("lowering: then lowering's", [(d["range"]["start"]["line"], d["message"][:39]) for d in c.diagnostics(euri)], [(3, "parallel_map runs this function on many")])

# ---- several files: use, errors in another file ----
open(os.path.join(tmp, "util.jo"), "w", encoding="utf-8").write("# doubles\ndouble = (x: int) -> int: x * 2\n")
mpath = os.path.join(tmp, "main.jo")
muri = to_uri(mpath)
msrc = "use 'util.jo'\nprint(double(21))\n"
c.set_text(muri, msrc)
check("multi-file: no errors", c.diagnostics(muri), [])
d = where(c.request("textDocument/definition", {"textDocument": {"uri": muri}, "position": lc(msrc, msrc.index("double"))}))
check("multi-file: definition", d, ("util.jo", 1, 0))
d = where(c.request("textDocument/definition", {"textDocument": {"uri": muri}, "position": lc(msrc, 6)}))
check("multi-file: use", d, ("util.jo", 0, 0))
refs = c.request("textDocument/references", {"textDocument": {"uri": muri}, "position": lc(msrc, msrc.index("double")), "context": {"includeDeclaration": True}})
check("multi-file: references", sorted(where(refs)), [("main.jo", 1, 6), ("util.jo", 1, 0)])
ren = c.request("textDocument/rename", {"textDocument": {"uri": muri}, "position": lc(msrc, msrc.index("double")), "newName": "twice"})
check("multi-file: rename", sorted((os.path.basename(u), len(es)) for u, es in ren["changes"].items()), [("main.jo", 1), ("util.jo", 1)])
# an error in the used file (not open): reported on that file
open(os.path.join(tmp, "util.jo"), "w", encoding="utf-8").write("double = (x: int) -> int: x.nope\n")
uuri = to_uri(os.path.join(tmp, "util.jo"))
c.set_text(muri, msrc + "\n")
check("multi-file: none in the main file", c.diagnostics(muri), [])
errs = [m["params"]["diagnostics"] for m in c.notes if m.get("method") == "textDocument/publishDiagnostics" and same_uri(m["params"]["uri"], uuri)]
check("multi-file: error in the used file", [[(d["range"]["start"]["line"], d["message"]) for d in e] for e in errs][-1:], [[(0, "int has no field 'nope'")]])
open(os.path.join(tmp, "util.jo"), "w", encoding="utf-8").write("double = (x: int) -> int: x * 2\n")
c.set_text(muri, msrc)
c.diagnostics(muri)
errs = [m["params"]["diagnostics"] for m in c.notes if m.get("method") == "textDocument/publishDiagnostics" and same_uri(m["params"]["uri"], uuri)]
check("multi-file: fixed", errs[-1:], [[]])

# ---- from m import names ----
open(os.path.join(tmp, "util.jo"), "w", encoding="utf-8").write("# doubles\ndouble = (x: int) -> int: x * 2\n_secret = 3\n")
fsrc = "from 'util.jo' import double as twice, _secret\nprint(twice(_secret))\n"
c.set_text(muri, fsrc)
check("from-import: no errors", c.diagnostics(muri), [])
d = where(c.request("textDocument/definition", {"textDocument": {"uri": muri}, "position": lc(fsrc, fsrc.index("twice("))}))
check("from-import: definition through an alias", d, ("util.jo", 1, 0))
d = where(c.request("textDocument/definition", {"textDocument": {"uri": muri}, "position": lc(fsrc, fsrc.index("double"))}))
check("from-import: definition of an imported name", d, ("util.jo", 1, 0))
csrc = "from 'util.jo' import d\n"
c.set_text(muri, csrc)
r = c.request("textDocument/completion", {"textDocument": {"uri": muri}, "position": lc(csrc, len(csrc) - 1)})
check("from-import: completion", sorted(x["label"] for x in r["items"]), ["_secret", "double"])
c.set_text(muri, msrc)
c.diagnostics(muri)

# ---- an unsaved edit of a file another open file uses ----
dpath = os.path.join(tmp, "dep.jo")
open(dpath, "w", encoding="utf-8").write("foo: int = 7\n")
duri = to_uri(dpath)
bpath = os.path.join(tmp, "user.jo")
bsrc = "use 'dep.jo'\nbar = foo\nprint(bar)\n"
open(bpath, "w", encoding="utf-8").write(bsrc)
buri = to_uri(bpath)
c.set_text(duri, "foo: int = 7\n")
c.set_text(buri, bsrc)
c.diagnostics(buri)
bar_at = {"textDocument": {"uri": buri}, "position": lc(bsrc, bsrc.index("bar ="))}
h = c.request("textDocument/hover", bar_at)
check("unsaved dependency: before", h and h["contents"]["value"], "```sloppy\n(global) bar: int\n```")
c.set_text(duri, 'foo: str = "s"\n')
h = c.request("textDocument/hover", bar_at)
check("unsaved dependency: after the edit", h and h["contents"]["value"], "```sloppy\n(global) bar: str\n```")

# ---- references across files, as a used file is opened, changed and closed ----
rdep = os.path.join(tmp, "rdep.jo")
open(rdep, "w", encoding="utf-8").write("foo = (x: int): x\nfoo(2)\n")
rdu = to_uri(rdep)
rsrc = "use 'rdep.jo'\nprint(foo(1))\n"
rpath = os.path.join(tmp, "ruser.jo")
open(rpath, "w", encoding="utf-8").write(rsrc)
ru = to_uri(rpath)
c.set_text(ru, rsrc)
c.diagnostics(ru)
rpos = {"textDocument": {"uri": ru}, "position": lc(rsrc, rsrc.index("foo(1")), "context": {"includeDeclaration": True}}
counts = [len(c.request("textDocument/references", rpos))]
c.set_text(rdu, "foo = (x: int): x\nfoo(2)\nfoo(3)\n")
counts.append(len(c.request("textDocument/references", rpos)))
c.notify("textDocument/didClose", {"textDocument": {"uri": rdu}})
counts.append(len(c.request("textDocument/references", rpos)))
check("references follow an opened, changed and closed file", counts, [3, 4, 3])

# ---- a file with errors is checked in rounds (leaving out what failed): hints and references once ----
epath = os.path.join(tmp, "errs.jo")
esrc = "f = (n: int) -> int:\n    a = n + 1\n    a\n\ng = () -> int:\n    x: int = \"no\"\n    x\n\nh = () -> int:\n    y: str = 5\n    0\n\nprint(f(2))\n"
open(epath, "w", encoding="utf-8").write(esrc)
eu = to_uri(epath)
c.set_text(eu, esrc)
check("file with errors: errors", len(c.diagnostics(eu)), 2)
eh = c.request("textDocument/inlayHint", {"textDocument": {"uri": eu}, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 99, "character": 0}}})
check("file with errors: each hint once", [(h["position"]["line"], h["label"]) for h in eh], [(1, ": int")])
erefs = c.request("textDocument/references", {"textDocument": {"uri": eu}, "position": lc(esrc, esrc.index("a\n\n")), "context": {"includeDeclaration": True}})
check("file with errors: each reference once", sorted(where(erefs)), [("errs.jo", 1, 4), ("errs.jo", 2, 4)])

def doc(name, text, disk=True):
    """open a document (written to disk too) and wait for its errors"""
    p = os.path.join(tmp, name)
    if disk: open(p, "w", encoding="utf-8").write(text)
    u = to_uri(p)
    c.set_text(u, text)
    return u, c.diagnostics(u)


def tp(u, text, s, k=0, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(s, i + 1)
    return {"textDocument": {"uri": u}, "position": lc(text, i + k)}


def edits(ren):
    if "changes" not in ren: return ren.get("message")
    return sorted((os.path.basename(u), e["range"]["start"]["line"], e["range"]["start"]["character"], e["newText"]) for u, es in ren["changes"].items() for e in es)


# ---- renaming a name imported as another, or the original ----
open(os.path.join(tmp, "adep.jo"), "w", encoding="utf-8").write("double = (x: int): x * 2\n")
asrc = "from 'adep.jo' import double as twice\nprint(twice(2))\n"
au, _ = doc("auser.jo", asrc)
check("rename an alias", edits(c.request("textDocument/rename", dict(tp(au, asrc, "twice("), newName="triple"))),
      [("auser.jo", 0, 32, "triple"), ("auser.jo", 1, 6, "triple")])
check("rename the original of an alias", edits(c.request("textDocument/rename", dict(tp(au, asrc, "double"), newName="dbl"))),
      [("adep.jo", 0, 0, "dbl"), ("auser.jo", 0, 22, "dbl")])

# ---- references and rename from a used file reach the open files using it ----
bdsrc = "foo = (): 1\n"
bdu, _ = doc("bdep.jo", bdsrc)
bmsrc = "use 'bdep.jo'\nprint(foo())\n"
bmu, _ = doc("bmain.jo", bmsrc)
refs = c.request("textDocument/references", dict(tp(bdu, bdsrc, "foo"), context={"includeDeclaration": True}))
check("references from a used file", sorted(where(refs)), [("bdep.jo", 0, 0), ("bmain.jo", 1, 6)])
check("rename from a used file", edits(c.request("textDocument/rename", dict(tp(bdu, bdsrc, "foo"), newName="foo2"))),
      [("bdep.jo", 0, 0, "foo2"), ("bmain.jo", 1, 6, "foo2")])

# ---- rename: keywords and names that would change meaning ----
csrc = "foo = (): 1\nbar = 2\nf = ():\n    a = 1\n    b = 2\n    a + b\ng = ():\n    c = 3\n    c\nprint(foo() + bar, f(), g())\n"
cu, _ = doc("crename.jo", csrc)
ren = lambda s, nn: edits(c.request("textDocument/rename", dict(tp(cu, csrc, s), newName=nn)))
check("rename to a keyword", ren("foo", "loop"), "'loop' is a keyword")
check("rename to a declared name", ren("foo", "bar"), "'bar' is declared already (crename.jo:2)")
check("rename to a used name", ren("foo", "print"), "'print' names something used already (crename.jo:10)")
check("rename a local to another of its function's", ren("a = 1", "b"), "'b' is declared already (crename.jo:5)")
check("rename a local to another function's", ren("a = 1", "c"), [("crename.jo", 3, 4, "c"), ("crename.jo", 5, 4, "c")])

# ---- names that are not ASCII ----
usrc = "数量 = 3\nprint(数量)\n"
uu, _ = doc("unicode.jo", usrc)
refs = c.request("textDocument/references", dict(tp(uu, usrc, "数量)"), context={"includeDeclaration": True}))
check("non-ASCII: references", sorted((r["range"]["start"]["line"], r["range"]["end"]["character"] - r["range"]["start"]["character"]) for r in refs), [(0, 2), (1, 2)])
h = c.request("textDocument/hover", tp(uu, usrc, "数量)", 1))
check("non-ASCII: hover on the second character", h and h["contents"]["value"], "```sloppy\n(global) 数量: int\n```")
check("non-ASCII: rename", edits(c.request("textDocument/rename", dict(tp(uu, usrc, "数量)"), newName="计数"))), [("unicode.jo", 0, 0, "计数"), ("unicode.jo", 1, 6, "计数")])
usrc2 = "数量 = 3\nprint(数"
c.set_text(uu, usrc2)
r = c.request("textDocument/completion", {"textDocument": {"uri": uu}, "position": lc(usrc2, len(usrc2))})
check("non-ASCII: completion", "数量" in [x["label"] for x in r["items"]], True)

# ---- closing a document keeps the errors another open document has ----
edu, _ = doc("edep.jo", "foo = (): missing\n")
eusrc = "use 'edep.jo'\nprint(foo())\n"
euu, _ = doc("euser.jo", eusrc)
c.notify("textDocument/didClose", {"textDocument": {"uri": euu}})
c.request("textDocument/hover", tp(edu, "foo", "foo"))
errs = [m["params"]["diagnostics"] for m in c.notes if m.get("method") == "textDocument/publishDiagnostics" and m["params"]["uri"] == edu]
check("closing a user keeps a used file's errors", [[d["message"] for d in e] for e in errs][-1:], [["unknown name 'missing'"]])

# ---- files changed on disk ----
open(os.path.join(tmp, "wdep.jo"), "w", encoding="utf-8").write("val: int = 1\n")
wsrc = "use 'wdep.jo'\nx = val\nprint(x)\n"
wu, errs = doc("wuser.jo", wsrc)
open(os.path.join(tmp, "wdep.jo"), "w", encoding="utf-8").write('val: str = "s"\n')
c.notify("workspace/didChangeWatchedFiles", {"changes": [{"uri": to_uri(os.path.join(tmp, "wdep.jo")), "type": 2}]})
h = c.request("textDocument/hover", tp(wu, wsrc, "x ="))
check("a used file changed on disk", (errs, h and h["contents"]["value"]), ([], "```sloppy\n(global) x: str\n```"))

# ---- completion in strings ----
def complete_in(text):
    i = text.index("|")
    text = text.replace("|", "")
    gu = to_uri(os.path.join(tmp, "strs.jo"))
    c.set_text(gu, text)
    r = c.request("textDocument/completion", {"textDocument": {"uri": gu}, "position": lc(text, i)})
    return "sx" in [x["label"] for x in r["items"]]


check("completion in strings", [complete_in('sx = 1\nt = """\nab s|\n"""\n'), complete_in('sx = 1\nt = "a\nb s|"\n'), complete_in('sx = 1\nt = r"{s|}"\n'),
                                complete_in('sx = 1\nt = "{{s|"\n'), complete_in("sx = 1\nt = '{s|}'\n"), complete_in('sx = 1\nt = "{s|}"\n'), complete_in('sx = 1\nt = """a\n"""\nprint(s|)\n')],
      [False, False, False, False, True, True, True])

# ---- signature help: strings, module calls ----
open(os.path.join(tmp, "hmod.jo"), "w", encoding="utf-8").write("g = (a: int, b: int) -> int: a + b\n")
hsrc = 'import \'hmod.jo\'\nf = (x: str, y: int): print(x, y)\nk = (x: str = ",", y: int = 0): print(x, y)\nf(",", 2)\nf("(", 2)\nprint(hmod.g(1, 2))\nk()\n'
hu, _ = doc("sighelp.jo", hsrc)
sh = lambda s, k: c.request("textDocument/signatureHelp", tp(hu, hsrc, s, k))
s1, s2, s3, s4 = sh('f(",", 2', 6), sh('f("(", 2', 6), sh("g(1, 2", 5), sh("k()", 2)
check("signature help: strings and module calls", [s and s["activeParameter"] for s in (s1, s2, s3)] + [s4 and len(s4["signatures"][0]["parameters"])], [1, 1, 1, 2])

# ---- function headers with strings and braces ----
isrc = 'f = (x: int) -> {str: int}: {"x": x}\ng = (s: str = ")"): s + "!"\nh = (s: str = "("): s\nprint(f(1), g(), h())\n'
iu, _ = doc("headers.jo", isrc)
hv = lambda s: (c.request("textDocument/hover", tp(iu, isrc, s)) or {}).get("contents", {}).get("value", "").split("\n")[1]
check("hover headers with strings and braces", [hv("f("), hv("h(")], ["f = (x: int) -> {str: int}", 'h = (s: str = "(")'])
ih = c.request("textDocument/inlayHint", {"textDocument": {"uri": iu}, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 99, "character": 0}}})
check("result hint after a string default", [(h["position"]["line"], h["position"]["character"], h["label"]) for h in ih if h["position"]["line"] == 1], [(1, 18, "-> str")])

# ---- document symbols ----
jsrc = 'a = (1, 2)\nf=(x: int): x\ng = (\n    x: int,\n    y: int\n):\n    x + y\ns = """\nfake = (): 1\n"""\ntest "é😀":\n    pass\n'
ju, _ = doc("syms.jo", jsrc)
js = c.request("textDocument/documentSymbol", {"textDocument": {"uri": ju}})
check("symbols: kinds, extents, strings, UTF-16", [(s["name"], s["kind"], s["range"]["end"]["line"], s["selectionRange"]["end"]["character"]) for s in js],
      [("a", 13, 0, 1), ("f", 12, 1, 1), ("g", 12, 6, 1), ("s", 13, 9, 1), ('test "é😀"', 24, 11, 10)])

# ---- a UNC path ----
unc = "file://server/share/unc.jo"
c.set_text(unc, 'x: int = "no"\n')
check("UNC path", [d["message"] for d in c.diagnostics(unc)], ["type mismatch: expected int, found str"])
c.set_text(unc, "use 'dep.jo'\n")
d = c.request("textDocument/definition", {"textDocument": {"uri": unc}, "position": {"line": 0, "character": 6}})
check("UNC path: a used file's URI", d and d["uri"], "file://server/share/dep.jo")

# ---- a generic function's hints: only where its instances agree ----
lsrc = 'twice = (x):\n    y = x + x\n    y\none = (x):\n    z = x\n    z\nprint(twice(1), twice("s"), one(1))\n'
lu, _ = doc("generic.jo", lsrc)
lh = c.request("textDocument/inlayHint", {"textDocument": {"uri": lu}, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 99, "character": 0}}})
check("generic hints", sorted((h["position"]["line"], h["label"]) for h in lh), [(3, "-> int"), (4, ": int")])

# ---- keywords and hover docs past attributes ----
check("keyword completion", all(k in complete("le|") for k in ["let", "from", "soa", "type", "loop"]), True)
nsrc = "# adds one\n@cabi\ninc = (x: int) -> int: x + 1\nprint(inc(1))\n"
nu, _ = doc("attrs.jo", nsrc)
h = c.request("textDocument/hover", tp(nu, nsrc, "inc(1"))
check("hover doc above an attribute", h and h["contents"]["value"], "```sloppy\ninc = (x: int) -> int\n```\n---\nadds one")

# ---- a library file ----
lpath = os.path.join(root, "lib", "game", "stats.jo")
luri = to_uri(lpath)
lsrc = open(lpath, encoding="utf-8").read()
c.set_text(luri, lsrc)
check("library file: no errors", c.diagnostics(luri), [])
h = c.request("textDocument/hover", {"textDocument": {"uri": luri}, "position": lc(lsrc, lsrc.index("__stats_summary(120)"))})
check("library file: hover", h and h["contents"]["value"].split("\n")[1], "__stats_summary = (count: int) -> (str, str, str)")

c.request("shutdown", None)
c.notify("exit", None)
c.p.wait(timeout=5)
check("exit status", c.p.returncode, 0)
print(f"{count - failures} passed, {failures} failed")
sys.exit(1 if failures else 0)
