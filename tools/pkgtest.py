#!/usr/bin/env python3
"""Packages (compiler/pkg.jo), with git repositories made here standing in for others' (file://
URLs): sloppy add, sloppy.lock and its pins, a package's own packages, a tag, a package's other
files, a directory as a package, the cache (builds with the repositories gone), and the errors.
usage: tools/pkgtest.py [path/to/sloppy]"""
import os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
tmp = tempfile.mkdtemp(prefix="sloppy-pkgtest-")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), SLOPPY_PACKAGES=os.path.join(tmp, "cache"))
# (file:///C:/... on Windows)
url = lambda p: "file://" + ("/" if os.name == "nt" else "") + os.path.join(tmp, p).replace(os.sep, "/")
passed = failed = 0


def check(name, got, want):
    global passed, failed
    if want in got: passed += 1
    else:
        failed += 1
        print(f"FAIL {name}: wanted {want!r} in\n{got}")


def write(path, text):
    os.makedirs(os.path.dirname(os.path.join(tmp, path)), exist_ok=True)
    open(os.path.join(tmp, path), "w").write(text)


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=os.path.join(tmp, cwd), check=True, capture_output=True)


def repo(name, files, tag=None):
    for f, text in files.items(): write(f"repos/{name}/{f}", text)
    git(f"repos/{name}", "init", "-q", "-b", "main")
    git(f"repos/{name}", "add", ".")
    git(f"repos/{name}", "commit", "-qm", "first")
    if tag: git(f"repos/{name}", "tag", tag)


def sloppy_in(cwd, *args):
    r = subprocess.run([sloppy, *args], cwd=os.path.join(tmp, cwd), capture_output=True, text=True, env=env, timeout=120)
    return r.stdout + r.stderr


repo("greet", {"greet.jo": 'greet = (n: str) -> str: "hello, {n}"\n'})
repo("sloppy-vecmath", {
    "vecmath.jo": f'build:\n    greet = package("{url("repos/greet")}")\n\nimport greet\n\nlength2 = (x: f64, y: f64) -> f64: x * x + y * y\nhello = () -> str: greet.greet("vecmath")\n',
    "extra.jo": "double = (x: f64) -> f64: 2.0 * x\n"}, tag="v1")
write("shared/shared.jo", "helper = () -> int: 42\n")
write("app/app.jo", 'build:\n    name = "App"\n    shared = package("../shared")\n\nimport vecmath\nimport shared\nimport \'vecmath/extra.jo\' as extra\n\n'
      'main = ():\n    print(vecmath.length2(3.0, 4.0), extra.double(2.5), shared.helper(), vecmath.hello())\n')

out = sloppy_in("app", "add", url("repos/sloppy-vecmath"))
check("sloppy add", out, "added vecmath to app.jo: import vecmath")
check("sloppy add: the build block", open(os.path.join(tmp, "app/app.jo")).read(), f'vecmath = package("{url("repos/sloppy-vecmath")}")')
lock = open(os.path.join(tmp, "app/sloppy.lock")).read()
check("the lock: the package", lock, f"vecmath {url('repos/sloppy-vecmath')} - ")
check("the lock: its package", lock, f"greet {url('repos/greet')} - ")
check("a program with packages", sloppy_in("app", "app.jo"), "25.0 5.0 42 hello, vecmath")
# a new commit: the pin holds until its line goes
write("repos/sloppy-vecmath/vecmath.jo", open(os.path.join(tmp, "repos/sloppy-vecmath/vecmath.jo")).read().replace("x * x + y * y", "x * x + y * y + 1000.0"))
git("repos/sloppy-vecmath", "commit", "-qam", "second")
check("pinned", sloppy_in("app", "app.jo"), "25.0 5.0 42")
open(os.path.join(tmp, "app/sloppy.lock"), "w").write("".join(l for l in lock.splitlines(True) if not l.startswith("vecmath ")))
check("unpinned: the newest commit", sloppy_in("app", "app.jo"), "1025.0 5.0 42")
# the cache: the repositories gone
os.rename(os.path.join(tmp, "repos"), os.path.join(tmp, "repos_gone"))
check("offline, from the cache", sloppy_in("app", "app.jo"), "1025.0 5.0 42")
os.rename(os.path.join(tmp, "repos_gone"), os.path.join(tmp, "repos"))
# a tag, under another name, its file imported
write("t/a.jo", f'build:\n    vm = package("{url("repos/sloppy-vecmath")}", "v1")\n\nimport \'vm/vecmath.jo\' as vm\n\nmain = (): print(vm.length2(1.0, 1.0))\n')
check("a tag", sloppy_in("t", "a.jo"), "2.0")
# errors
write("t/b.jo", f'build:\n    vm = package("{url("repos/sloppy-vecmath")}", "nope")\n\nimport vm\nmain = (): print(1)\n')
check("a tag that is not there", sloppy_in("t", "b.jo"), "has no 'nope'")
write("t/c.jo", 'build:\n    x = package("../no-such-dir")\n\nimport x\nmain = (): print(1)\n')
check("a directory that is not there", sloppy_in("t", "c.jo"), "there is no directory")
write("t/e.jo", 'build:\n    z = package(3)\n\nmain = (): print(1)\n')
check("package() of a number", sloppy_in("t", "e.jo"), "package() takes strings in quotes")
write("t/f.jo", 'build:\n    z = package("--upload-pack=touch pwned")\n\nimport z\nmain = (): print(1)\n')
check("an option for git, not a URL", sloppy_in("t", "f.jo"), "is not a directory or a git URL")
write("t/g.jo", 'build:\n    z = package("https://example.com/x", "--upload-pack=touch pwned")\n\nimport z\nmain = (): print(1)\n')
check("an option for git as the ref", sloppy_in("t", "g.jo"), "is not a git URL")
check("... and nothing run", str(os.path.exists(os.path.join(tmp, "t", "pwned"))), "False")
shutil.rmtree(tmp, ignore_errors=True)
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
