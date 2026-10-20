#!/usr/bin/env python3
"""The guides' code blocks (```gdscript in docs/*.md, but API.md and the tutorials, which runtests
builds) checked with `sloppy check`. Most blocks are parts of programs, which name what they
leave out: what that gives is let pass (unknown names, `...` standing for more, indentation of a
piece of a block, files beside the program). Any other error is an example the language moved
away from (a `global x` it now needs, a function renamed).
usage: tools/doccheck.py [sloppy]     (default bin/sloppy)"""
import glob, os, re, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy")
PASS = re.compile(r"unknown (name|function|type|module)|cannot find (module|')|is never|expected an expression here|"
                  r"spread with `\.\.\.`|unexpected indentation|cannot read the JavaScript|is already defined|"
                  r"overloaded or generic function '.*' as a value|is a function and is not called here")
docs = [d for d in sorted(glob.glob(os.path.join(root, "docs", "*.md")))
        if not os.path.basename(d).startswith(("API", "TUTORIAL"))]
tmp = tempfile.mkdtemp()
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
bad = 0
n = 0
for doc in docs:
    src = open(doc, encoding="utf-8").read()
    for m in re.finditer(r"```gdscript\n(.*?)```", src, re.S):
        code = m.group(1)
        if "package(" in code: continue          # (no network here)
        line = src[:m.start()].count("\n") + 2
        f = os.path.join(tmp, f"block_{line}.jo")
        open(f, "w", encoding="utf-8").write(code)
        n += 1
        r = subprocess.run([sloppy, "check", f], capture_output=True, text=True, env=env, timeout=120)
        errs = [l.split(": error: ", 1)[1] for l in r.stderr.splitlines() if ": error: " in l]
        if errs and not PASS.search(errs[0]):
            bad += 1
            print(f"FAIL {os.path.relpath(doc, root)}:{line}: {errs[0]}")
print(f"{n - bad} passed, {bad} failed")
sys.exit(1 if bad else 0)
