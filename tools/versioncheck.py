#!/usr/bin/env python3
"""The compiler's version (SLOPPY_VERSION in compiler/main.jo) and its library's (lib/VERSION) are
the same: a compiler refuses a library of another version, so they change together
(tools/bumpversion.py). Fails, saying both, when they differ; with bin/sloppy built, also unless
it refuses a library of another version, saying so.
usage: tools/versioncheck.py"""
import os, re, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def versions():
    m = re.search(r'^const SLOPPY_VERSION = "([^"]*)"', open(os.path.join(root, "compiler", "main.jo"), encoding="utf-8").read(), re.M)
    compiler = m.group(1) if m else None
    path = os.path.join(root, "lib", "VERSION")
    lib = open(path, encoding="utf-8").read().strip() if os.path.exists(path) else None
    return compiler, lib


if __name__ == "__main__":
    compiler, lib = versions()
    if compiler is None: sys.exit("no SLOPPY_VERSION in compiler/main.jo")
    if lib != compiler:
        sys.exit(f"compiler/main.jo says {compiler}, lib/VERSION says {lib}: they must be the same (tools/bumpversion.py {compiler} sets both)")
    exe = os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
    if os.path.exists(exe):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "VERSION"), "w").write("0.0.1\n")
            r = subprocess.run([exe, "check", os.path.join(root, "tests", "t", "hello.jo")], env=dict(os.environ, SLOPPY_LIB=d), capture_output=True, text=True)
            if r.returncode != 2 or "the compiler and its library must be the same version" not in r.stderr:
                sys.exit(f"bin/sloppy did not refuse a library of version 0.0.1 (exit {r.returncode}): {r.stderr.strip()[-300:]}")
    print(f"version {compiler}: compiler and library agree")
