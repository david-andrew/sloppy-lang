#!/usr/bin/env python3
"""Compile speed against an earlier commit: the instructions (tools/icount, exact unlike time) that
compiling bench/big.jo, the compiler and the games takes, with this commit's compiler and with
the earlier one's, on the same files. Fails when any is more than --limit percent (default 1) slower.
usage: tools/speedcheck.py [--base REV] [--limit PCT] [--release]   (default base: HEAD~1)"""
import argparse, os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--base", default="HEAD~1")
ap.add_argument("--limit", type=float, default=1.0)
ap.add_argument("--release", action="store_true", help="also time release builds")
args = ap.parse_args()

run = lambda *a, **k: subprocess.run(a, check=True, cwd=root, **k)
out = lambda *a: subprocess.run(a, check=True, cwd=root, capture_output=True, text=True).stdout.strip()
tmp = tempfile.mkdtemp(prefix="sloppy-speed-")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))

if not os.path.exists(os.path.join(root, "tools", "icount")):
    run("cc", "-O2", "-o", "tools/icount", "tools/icount.c")
if not os.path.exists(os.path.join(root, "bench", "big.jo")):
    run(sys.executable, "tools/genbench.py", "2000", "bench/big")

# the earlier compiler: its sources, built by this one (with its own library)
base = out("git", "rev-parse", "--short", args.base)
wt = os.path.join(tmp, "base")
run("git", "worktree", "add", "-q", "--detach", wt, base)
try:
    old = os.path.join(tmp, "sloppy-old")
    subprocess.run([os.path.join(root, "bin", "sloppy"), "build", os.path.join(wt, "compiler", "main.jo"), "-o", old],
                   check=True, env=dict(os.environ, SLOPPY_LIB=os.path.join(wt, "lib")))
finally:
    run("git", "worktree", "remove", "--force", wt)
new = os.path.join(root, "bin", "sloppy")


def icount(compiler, src, extra):
    r = subprocess.run([os.path.join(root, "tools", "icount"), compiler, "build", src, "-o", os.path.join(tmp, "out"), *extra],
                       cwd=root, env=env, capture_output=True, text=True)
    line = (r.stderr.strip().splitlines() or [""])[-1]
    if r.returncode != 0 or "G instructions" not in line:
        sys.exit(f"speedcheck: cannot count {os.path.basename(compiler)} build {src}: {r.stderr.strip()[-500:]}")
    return float(line.split()[0])


inputs = ["bench/big.jo", "compiler/main.jo", "examples/rebound/rebound.jo", "examples/breakwater/breakwater.jo"]
modes = [[]] + ([["--release"]] if args.release else [])
worst = 0.0
print(f"compile speed: {base} -> working tree (G instructions)")
for extra in modes:
    for src in inputs:
        a, b = icount(old, src, extra), icount(new, src, extra)
        pct = (b - a) / a * 100
        worst = max(worst, pct)
        flag = "  <- slower" if pct > args.limit else ""
        print(f"  {src + (' --release' if extra else ''):46} {a:7.3f} -> {b:7.3f}  {pct:+6.2f}%{flag}")
shutil.rmtree(tmp, ignore_errors=True)
if worst > args.limit:
    sys.exit(f"speedcheck: compiling is {worst:.2f}% slower than at {base} (the limit is {args.limit}%)")
