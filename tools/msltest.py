#!/usr/bin/env python3
"""Metal test: build every program with shaders or compute functions (the examples, the render
scenes, the library's examples, the tests that use them) for macOS, keeping the Metal Shading
Language the compiler makes (SLOPPY_MSL_DUMP), and compile each with Apple's offline compiler
(xcrun metal, Metal 3).
usage: msltest.py   (skips, and passes, without xcrun's metal compiler: not on a Mac)"""
import glob, os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.join(root, "bin", "sloppy")
if not shutil.which("xcrun") or subprocess.run(["xcrun", "-sdk", "macosx", "-f", "metal"], capture_output=True).returncode != 0:
    print("xcrun metal not found: skipped")
    sys.exit(0)
programs = sorted(glob.glob(os.path.join(root, "examples", "*.jo")) + glob.glob(os.path.join(root, "examples", "*", "*.jo"))
                  + glob.glob(os.path.join(root, "tests", "render", "*.jo")) + glob.glob(os.path.join(root, "docs", "api", "*.jo"))
                  + [t for t in glob.glob(os.path.join(root, "tests", "t", "*.jo")) if any(w in open(t, encoding="utf-8").read() for w in ("compute(", "shader(", ".gpu"))])
out = tempfile.mkdtemp(prefix="sloppy-msl-")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
failed = 0
modules = 0
seen = set()
for src in programs:
    name = os.path.relpath(src, root)
    d = os.path.join(out, name.replace(os.sep, "_"))
    os.makedirs(d)
    r = subprocess.run([sloppy, "build", "--target", "macos", src, "-o", os.path.join(d, "prog")], env=dict(env, SLOPPY_MSL_DUMP=d), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {name}: build failed\n{r.stderr}")
        failed += 1
        continue
    for m in sorted(glob.glob(os.path.join(d, "*.metal"))):
        text = open(m, "rb").read()
        if text in seen: continue
        seen.add(text)
        modules += 1
        v = subprocess.run(["xcrun", "-sdk", "macosx", "metal", "-std=metal3.0", "-c", m, "-o", m + ".air"], capture_output=True, text=True)
        if v.returncode != 0:
            print(f"FAIL {name}: {os.path.basename(m)}\n{v.stdout}{v.stderr[:3000]}")
            failed += 1
shutil.rmtree(out, ignore_errors=True)
print(f"{modules} Metal sources from {len(programs)} programs, {failed} failed")
sys.exit(1 if failed else 0)
