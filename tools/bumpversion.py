#!/usr/bin/env python3
"""A new version: SLOPPY_VERSION in compiler/main.jo and lib/VERSION set to it together (a compiler
refuses a library of another version), and CHANGELOG.md's "## Unreleased" entries put under a
heading of their own, with an empty "## Unreleased" above. Then rebuild (tools/bootstrap.sh),
commit, and tag vX.Y.Z (.github/workflows/release.yml publishes it).
usage: tools/bumpversion.py X.Y.Z"""
import os, re, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]): sys.exit(__doc__.split("usage: ")[1])
v = sys.argv[1]
main = os.path.join(root, "compiler", "main.jo")
src = open(main, encoding="utf-8").read()
src, n = re.subn(r'^const SLOPPY_VERSION = "[^"]*"', f'const SLOPPY_VERSION = "{v}"', src, count=1, flags=re.M)
if n != 1: sys.exit("no SLOPPY_VERSION in compiler/main.jo")
open(main, "w", encoding="utf-8").write(src)
open(os.path.join(root, "lib", "VERSION"), "w", encoding="utf-8").write(v + "\n")
log = os.path.join(root, "CHANGELOG.md")
text = open(log, encoding="utf-8").read()
if f"\n## {v}\n" not in text:
    if "\n## Unreleased\n" in text: text = text.replace("\n## Unreleased\n", f"\n## Unreleased\n\n## {v}\n", 1)
    else: text = text.replace("\n## ", f"\n## Unreleased\n\n## {v}\n\n## ", 1)
    open(log, "w", encoding="utf-8").write(text)
print(f"version {v}: compiler/main.jo, lib/VERSION and CHANGELOG.md; now tools/bootstrap.sh, commit, tag v{v}")
