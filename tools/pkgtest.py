#!/usr/bin/env python3
"""Packages (compiler/pkg.jo), with git repositories made here standing in for others' (file://
URLs): sloppy add (a version, the newest version tag), sloppy.lock and its pins, sloppy update,
a package's own packages (each package's names its own; two versions of one package side by
side, a commit's shared), a tag, a package's other files, a directory as a package, the cache
(builds with the repositories gone), the errors, and sloppy test on a directory.
usage: tools/pkgtest.py [path/to/sloppy]"""
import os, re, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
tmp = tempfile.mkdtemp(prefix="sloppy-pkgtest-")
# (git never asks for a password here: no window, no prompt)
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), SLOPPY_PACKAGES=os.path.join(tmp, "cache"), GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="echo", SSH_ASKPASS="echo")
# (file:///C:/... on Windows)
url = lambda p: "file://" + ("/" if os.name == "nt" else "") + os.path.join(tmp, p).replace(os.sep, "/")
passed = failed = 0


def check(name, got, want, present=True):
    global passed, failed
    if (want in got) == present: passed += 1
    else:
        failed += 1
        print(f"FAIL {name}: wanted {want!r} {'in' if present else 'not in'}\n{got}")


def write(path, text):
    os.makedirs(os.path.dirname(os.path.join(tmp, path)), exist_ok=True)
    open(os.path.join(tmp, path), "w").write(text)


def read(path):
    return open(os.path.join(tmp, path)).read()


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=os.path.join(tmp, cwd), check=True, capture_output=True, text=True,
                          env=env).stdout.strip()


def repo(name, files, tag=None):
    for f, text in files.items(): write(f"repos/{name}/{f}", text)
    git(f"repos/{name}", "init", "-q", "-b", "main")
    git(f"repos/{name}", "add", ".")
    git(f"repos/{name}", "commit", "-qm", "first")
    if tag: git(f"repos/{name}", "tag", tag)


def commit(name, files, tag=None):
    for f, text in files.items(): write(f"repos/{name}/{f}", text)
    git(f"repos/{name}", "add", ".")
    git(f"repos/{name}", "commit", "-qm", "more")
    if tag: git(f"repos/{name}", "tag", tag)
    return git(f"repos/{name}", "rev-parse", "HEAD")


def sloppy_in(cwd, *args):
    r = subprocess.run([sloppy, *args], cwd=os.path.join(tmp, cwd), capture_output=True, text=True, env=env, timeout=120)
    return r.stdout + r.stderr


# ---- sloppy add, the lock, pins, the cache
repo("greet", {"greet.jo": 'greet = (n: str) -> str: "hello, {n}"\n'})
repo("sloppy-vecmath", {
    "vecmath.jo": f'build:\n    greet = package("{url("repos/greet")}")\n\nimport greet\n\nlength2 = (x: f64, y: f64) -> f64: x * x + y * y\nhello = () -> str: greet.greet("vecmath")\n',
    "extra.jo": "double = (x: f64) -> f64: 2.0 * x\n"}, tag="v1.0.0")
write("shared/shared.jo", "helper = () -> int: 42\n")
write("app/app.jo", 'build:\n    name = "App"\n    shared = package("../shared")\n\nimport vecmath\nimport shared\nimport \'vecmath/extra.jo\' as extra\n\n'
      'main = ():\n    print(vecmath.length2(3.0, 4.0), extra.double(2.5), shared.helper(), vecmath.hello())\n')

out = sloppy_in("app", "add", url("repos/sloppy-vecmath"))
check("sloppy add: the newest version tag", out, "added vecmath v1.0.0 to app.jo: import vecmath")
check("sloppy add: the build block", read("app/app.jo"), f'vecmath = package("{url("repos/sloppy-vecmath")}", "v1.0.0")')
lock = read("app/sloppy.lock")
check("the lock: the package", lock, f"\nvecmath {url('repos/sloppy-vecmath')} v1.0.0 ")
check("the lock: its package, as vecmath names it", lock, f"\nvecmath/greet {url('repos/greet')} - ")
check("a program with packages", sloppy_in("app", "app.jo"), "25.0 5.0 42 hello, vecmath")
# a new commit of greet's default branch: the pin holds until sloppy update
old = git("repos/greet", "rev-parse", "HEAD")
new = commit("greet", {"greet.jo": 'greet = (n: str) -> str: "hi, {n}"\n'})
check("pinned", sloppy_in("app", "app.jo"), "hello, vecmath")
out = sloppy_in("app", "update")
check("sloppy update: a branch", out, f"vecmath/greet: the default branch {old[:7]} -> {new[:7]}")
check("sloppy update: a tag stays", out, "vecmath: v1.0.0 (a tag; there is no newer version)")
check("updated", sloppy_in("app", "app.jo"), "hi, vecmath")
# the cache: the repositories gone
os.rename(os.path.join(tmp, "repos"), os.path.join(tmp, "repos_gone"))
check("offline, from the cache", sloppy_in("app", "app.jo"), "25.0 5.0 42 hi, vecmath")
os.rename(os.path.join(tmp, "repos_gone"), os.path.join(tmp, "repos"))
# a newer tag: said by sloppy update, not taken
commit("sloppy-vecmath", {"extra.jo": "double = (x: f64) -> f64: 3.0 * x\n"}, tag="v1.1.0")
out = sloppy_in("app", "update", "vecmath")
check("sloppy update name: newer tags", out, "vecmath: v1.0.0 (a tag, which stays; newer: v1.1.0")
check("sloppy update name: only that one (and its own)", out, "vecmath/greet: the default branch at")
check("still v1.0.0", sloppy_in("app", "app.jo"), "25.0 5.0 42")
check("sloppy update: a name that is not there", sloppy_in("app", "update", "nope"), "has no git package 'nope' (its git packages: vecmath, greet)")

# sloppy add with a version: after the URL, or URL@version; and as a name
write("add/a.jo", "print(1)\n")
check("sloppy add URL version", sloppy_in("add", "add", url("repos/sloppy-vecmath"), "v1.0.0", "as", "vm"), "added vm v1.0.0 to a.jo: import vm")
check("... in the build block", read("add/a.jo"), f'vm = package("{url("repos/sloppy-vecmath")}", "v1.0.0")')
check("sloppy add URL@version", sloppy_in("add", "add", url("repos/greet") + "@main"), "added greet main to a.jo")
out = sloppy_in("add", "add", url("repos/sloppy-vecmath"), "v9", "as", "vm2")
check("sloppy add: a version that is not there", out, "has no 'v9'")
check("... its tags", out, "its tags: v1.1.0, v1.0.0")
check("... and nothing written", read("add/a.jo"), "vm2", present=False)
check("sloppy add: two versions", sloppy_in("add", "add", url("repos/sloppy-vecmath"), "v1.0.0", "v1.1.0"), "sloppy add takes one version")
check("sloppy add: a name that is not one", sloppy_in("add", "add", url("repos/greet"), "as", "1x"), "'1x' is not a name")
check("sloppy add: a directory has no versions", sloppy_in("add", "add", "../shared", "v1"), "a directory has no versions")

# ---- a tag, under another name: the main file is still the package's own (vecmath.jo)
write("t/a.jo", f'build:\n    vm = package("{url("repos/sloppy-vecmath")}", "v1.0.0")\n\nimport vm\nimport \'vm/extra.jo\' as ex\n\nmain = (): print(vm.length2(1.0, 1.0), ex.double(1.0))\n')
check("a tag, the main file by the package's name", sloppy_in("t", "a.jo"), "2.0 2.0")

# ---- each package's names are its own: a and b both name a util, each its own
write("ns/liba/util.jo", 'whoami = () -> str: "A\'s util"\n')
write("ns/libb/util.jo", 'whoami = () -> str: "B\'s util"\n')
write("ns/depa/depa.jo", 'build:\n    util = package("../liba")\nimport util\na_says = () -> str: util.whoami()\n')
write("ns/depb/depb.jo", 'build:\n    util = package("../libb")\nimport util\nb_says = () -> str: util.whoami()\n')
write("ns/app/main.jo", 'build:\n    depa = package("../depa")\n    depb = package("../depb")\n    util = package("../liba")\nimport depa\nimport depb\nprint(depa.a_says(), "/", depb.b_says())\n')
check("per-package names", sloppy_in("ns/app", "main.jo"), "A's util / B's util")
# (the program's big does not change what a package's `import big` means: the library's)
write("ns/big/big.jo", 'whoami = () -> str: "package big"\n')
write("ns/usesbig/usesbig.jo", 'import big\nhuge = () -> str: "{big.Big(1.5, 3)}"\n')
write("ns/app/std.jo", 'build:\n    big = package("../big")\n    usesbig = package("../usesbig")\nimport usesbig\nimport big\nprint(usesbig.huge(), big.whoami())\n')
check("a program's package does not hide a library module in another package", sloppy_in("ns/app", "std.jo"), "1.50K package big")

# ---- two versions of one package, side by side; one commit shared
repo("mathx", {"mathx.jo": 'VERSION = "1.0.0"\nstruct Vec:\n    x: int\nclampi = (x: int, lo: int, hi: int) -> int: min(max(x, lo), hi)\nvec = (x: int) -> Vec: Vec(x)\n'}, tag="v1.0.0")
commit("mathx", {"mathx.jo": 'VERSION = "2.0.0"\nstruct Vec:\n    x: int\nclamp_int = (x: int, lo: int, hi: int) -> int: min(max(x, lo), hi)\nvec = (x: int) -> Vec: Vec(x)\n'}, tag="v2.0.0")
repo("sloppy-grids", {"grids.jo": f'build:\n    mathx = package("{url("repos/mathx")}", "v1.0.0")\nimport mathx\nseen = () -> str: mathx.VERSION + " " + str(mathx.clampi(9, 0, 3))\ntake = (v: mathx.Vec) -> int: v.x\n'}, tag="v1.0.0")
repo("inis", {"inis.jo": f'build:\n    mathx = package("{url("repos/mathx")}", "v2.0.0")\nimport mathx\nseen = () -> str: mathx.VERSION + " " + str(mathx.clamp_int(9, 0, 4))\nmake = () -> mathx.Vec: mathx.vec(5)\n'}, tag="v1.0.0")
repo("tables", {"tables.jo": f'build:\n    m2 = package("{url("repos/mathx")}", "v2.0.0")\nimport m2\nwidth = (v: m2.Vec) -> int: v.x * 2\n'}, tag="v1.0.0")
write("dia/main.jo", f'build:\n    grids = package("{url("repos/sloppy-grids")}", "v1.0.0")\n    inis = package("{url("repos/inis")}", "v1.0.0")\n    tables = package("{url("repos/tables")}", "v1.0.0")\n'
      'import grids\nimport inis\nimport tables\nprint(grids.seen(), "/", inis.seen(), "/", tables.width(inis.make()))\n')
out = sloppy_in("dia", "main.jo")
check("two versions of one package", out, "1.0.0 3 / 2.0.0 4 / 10")
check("... v2.0.0 fetched once, for inis and tables", str(out.count("repos/mathx at")), "2")
lock = read("dia/sloppy.lock")
check("... the lock: grids' mathx", lock, f"grids/mathx {url('repos/mathx')} v1.0.0 ")
check("... the lock: inis' mathx", lock, f"inis/mathx {url('repos/mathx')} v2.0.0 ")
write("dia/mix.jo", f'build:\n    grids = package("{url("repos/sloppy-grids")}", "v1.0.0")\n    inis = package("{url("repos/inis")}", "v1.0.0")\nimport grids\nimport inis\nprint(grids.take(inis.make()))\n')
check("two versions' types are two types", sloppy_in("dia", "mix.jo"), "expects mathx.Vec (v1.0.0), found mathx.Vec (v2.0.0)")
# (an error in a package's file: which package)
commit("inis", {"inis.jo": f'build:\n    mathx = package("{url("repos/mathx")}", "v2.0.0")\nimport mathx\nseen = () -> str: mathx.clampi(1, 2, 3)\n'}, tag="v1.0.1")
write("dia/bad.jo", f'build:\n    inis = package("{url("repos/inis")}", "v1.0.1")\nimport inis\nprint(inis.seen())\n')
out = sloppy_in("dia", "bad.jo")
check("an error in a package: the package and its version", out, "in package inis (v1.0.1, ")
check("... and the error", out, "unknown function 'clampi'")

# ---- a directory beside the program with a package's name
write("shadow/pathgrid/grid.jo", "local = 1\n")
write("shadow/main.jo", f'build:\n    pathgrid = package("{url("repos/greet")}")\nimport \'pathgrid/greet.jo\' as g\nprint(g.greet("x"))\n')
write("shadow/pathgrid/greet.jo", "local = 1\n")
check("a directory with a package's name", sloppy_in("shadow", "main.jo"), "could be package pathgrid's greet.jo (")

# ---- errors
write("t/b.jo", f'build:\n    vm = package("{url("repos/sloppy-vecmath")}", "nope")\n\nimport vm\nmain = (): print(1)\n')
out = sloppy_in("t", "b.jo")
check("a tag that is not there", out, "has no 'nope'")
check("... its branches and tags", out, "its branches: main; its tags: v1.1.0, v1.0.0. Name one as package(")
check("... at the build block's line", out, "b.jo:2:5: error:")
check("... the import as a note", out, "b.jo:4:1: note: imported here")
# (a commit by its first characters: one on no branch's or tag's tip too)
write("t/h.jo", f'build:\n    g = package("{url("repos/greet")}", "{old[:9]}")\nimport g\nprint(g.greet("old"))\n')
check("a commit's first characters", sloppy_in("t", "h.jo"), "hello, old")
write("t/i.jo", f'build:\n    g = package("{url("repos/greet")}", "abcdef12")\nimport g\nprint(1)\n')
check("a commit that is not there", sloppy_in("t", "i.jo"), "has no commit starting with abcdef12 (or more than one does: a commit is 40 characters, or the first 7 or more of them)")
write("t/j.jo", f'build:\n    g = package("{url("repos/no-such-repo")}")\nimport g\nprint(1)\n')
out = sloppy_in("t", "j.jo")
check("no repository at a file:// URL", out, "there is no git repository at ")
check("... and no GitHub hint", out, "GitHub", present=False)
# (a repository whose HEAD names a branch it does not have)
git("", "init", "-q", "--bare", "-b", "master", "repos/nohead.git")
git("repos/greet", "push", "-q", url("repos/nohead.git"), "main")
write("t/k.jo", f'build:\n    g = package("{url("repos/nohead.git")}")\nimport g\nprint(1)\n')
check("no default branch", sloppy_in("t", "k.jo"), "has no default branch (its HEAD names a branch that is not there); its branches: main. Name one as package(")
write("t/l.jo", f'build:\n    g = package("../repos/nohead.git")\nimport g\nprint(1)\n')
check("a bare repository as a directory", sloppy_in("t", "l.jo"), "is a git repository's own files (a bare repository): name it by its URL, package(\"file://")
write("t/c.jo", 'build:\n    x = package("../no-such-dir")\n\nimport x\nmain = (): print(1)\n')
check("a directory that is not there", sloppy_in("t", "c.jo"), "there is no directory")
write("empty/README.md", "nothing\n")
write("t/m.jo", 'build:\n    empty = package("../empty")\nimport empty\nprint(1)\n')
check("a package with no .jo files", sloppy_in("t", "m.jo"), "package 'empty' (../empty) has no .jo files")
write("multi/one.jo", "a = 1\n")
write("multi/two.jo", "b = 2\n")
write("t/n.jo", 'build:\n    many = package("../multi")\nimport many\nprint(1)\n')
check("a package with no main file", sloppy_in("t", "n.jo"), "its files there are one.jo, two.jo; import one of them, as import 'many/one.jo' as one")
repo("outside", {"outside.jo": 'build:\n    helper = package("../helper")\nimport helper\nt = () -> int: 1\n'})
write("t/o.jo", f'build:\n    outside = package("{url("repos/outside")}")\nimport outside\nprint(outside.t())\n')
check("a git package's directory package outside it", sloppy_in("t", "o.jo"), "a git package's directory packages must be inside its repository")
write("t/e.jo", 'build:\n    z = package(3)\n\nmain = (): print(1)\n')
check("package() of a number", sloppy_in("t", "e.jo"), "package() takes strings in quotes")
write("t/f.jo", 'build:\n    z = package("--upload-pack=touch pwned")\n\nimport z\nmain = (): print(1)\n')
check("an option for git, not a URL", sloppy_in("t", "f.jo"), "is not a directory or a git URL")
write("t/g.jo", 'build:\n    z = package("https://example.com/x", "--upload-pack=touch pwned")\n\nimport z\nmain = (): print(1)\n')
check("an option for git as the ref", sloppy_in("t", "g.jo"), "is not a git URL")
check("... and nothing run", str(os.path.exists(os.path.join(tmp, "t", "pwned"))), "False")

# ---- sloppy test on a directory: the tests of each file, one count
write("tests/geo.jo", "area = (w: int, h: int) -> int: w * h\n\ntest \"area\":\n    assert(area(2, 3) == 6)\n")
write("tests/app.jo", "import 'geo.jo'\nprint(geo.area(1, 1))\n\ntest \"one\":\n    assert(geo.area(1, 1) == 1)\n\ntest \"two\":\n    assert(geo.area(1, 2) == 2)\n")
write("tests/sub/more.jo", "test \"more\":\n    assert(1 + 1 == 2)\n")
write("tests/none.jo", "x = 1\n")
out = sloppy_in("tests", "test")
check("sloppy test: a directory", out, "4 tests passed in 3 files")
check("sloppy test .", sloppy_in("tests", "test", "."), "4 tests passed in 3 files")
check("sloppy test dir words", sloppy_in("", "test", "tests", "area"), "1 test passed in 1 file")
write("tests/sub/bad.jo", "test \"bad\":\n    assert(1 == 2)\n")
check("sloppy test: a failure", sloppy_in("tests", "test"), "4 passed, 1 failed in 4 files (failed: sub/bad.jo)")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
