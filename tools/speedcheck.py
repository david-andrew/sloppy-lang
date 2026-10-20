#!/usr/bin/env python3
"""Compile speed against an earlier commit: the instructions (tools/icount, exact unlike time) that
compiling bench/big.jo, the compiler and the games takes, with this commit's compiler and with
the earlier one's, on the same files and library; then the library's own share, this compiler
with the earlier library and with this one (code every program or every game compiles: a frame
loop that calls more). Fails when any is more than --limit percent (default 1) slower.
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
# (one process: the counters see the compiler's process only, not code-generation workers)
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), SLOPPY_EMIT_WORKERS="1")

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
    # (with its own library; when this compiler needs runtime functions that one lacks, with this one's)
    r = subprocess.run([os.path.join(root, "bin", "sloppy"), "build", os.path.join(wt, "compiler", "main.jo"), "-o", old],
                       env=dict(os.environ, SLOPPY_LIB=os.path.join(wt, "lib")), capture_output=True, text=True)
    if r.returncode != 0:
        r = subprocess.run([os.path.join(root, "bin", "sloppy"), "build", os.path.join(wt, "compiler", "main.jo"), "-o", old],
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), capture_output=True, text=True)
        if r.returncode == 0: print("(the earlier compiler built with this commit's library)")
    if r.returncode != 0:
        # (its sources take what this compiler no longer does: made from its own C bootstrap)
        print("(the earlier compiler made from its own bootstrap)")
        wenv = dict(os.environ, SLOPPY_LIB=os.path.join(wt, "lib"))
        subprocess.run(["make", "-s", "-C", os.path.join(wt, "stage0")], check=True)
        s1 = os.path.join(tmp, "sloppy-old1")
        subprocess.run([os.path.join(wt, "stage0", "sloppy0"), os.path.join(wt, "compiler", "main.jo"), "-o", s1], check=True, env=wenv)
        subprocess.run([s1, "build", os.path.join(wt, "compiler", "main.jo"), "-o", old], check=True, env=wenv)
    # (its library kept: when this commit's library has what it cannot read, new syntax, it
    # compiles with its own)
    old_lib = os.path.join(tmp, "base-lib")
    shutil.copytree(os.path.join(wt, "lib"), old_lib)
    # (and its own copy of the inputs: when this commit's are in syntax it cannot read, it
    # compiles those, nearly the same)
    old_src = os.path.join(tmp, "base-src")
    for d in ["bench", "compiler", "examples/rebound", "examples/breakwater"]:
        if os.path.isdir(os.path.join(wt, d)): shutil.copytree(os.path.join(wt, d), os.path.join(old_src, d))
finally:
    run("git", "worktree", "remove", "--force", wt)
new = os.path.join(root, "bin", "sloppy")


# instructions in G: tools/icount (the CPU's counters), else valgrind's count (virtual machines,
# CI's among them, often have no counters; slower, but as exact)
counter = None


def icount(compiler, src, extra, lib=None):
    global counter
    env = dict(globals()["env"], SLOPPY_LIB=lib) if lib else globals()["env"]
    cmd = [compiler, "build", src, "-o", os.path.join(tmp, "out"), *extra]
    if counter is None:
        r = subprocess.run([os.path.join(root, "tools", "icount"), *cmd], cwd=root, env=env, capture_output=True, text=True)
        counter = "valgrind" if "perf_event_open" in r.stderr else "icount"
        if counter == "valgrind": print("(no instruction counters here: counting with valgrind)")
    if counter == "icount":
        r = subprocess.run([os.path.join(root, "tools", "icount"), *cmd], cwd=root, env=env, capture_output=True, text=True)
        line = (r.stderr.strip().splitlines() or [""])[-1]
        if r.returncode == 0 and "G instructions" in line: return float(line.split()[0])
    else:
        r = subprocess.run(["valgrind", "--tool=cachegrind", "--cache-sim=no", "--cachegrind-out-file=/dev/null", *cmd],
                           cwd=root, env=env, capture_output=True, text=True)
        refs = [l for l in r.stderr.splitlines() if "I refs:" in l or "I   refs:" in l]
        if r.returncode == 0 and refs: return int(refs[-1].split(":")[1].replace(",", "")) / 1e9
    if compiler == old and not lib:
        print(f"(the earlier compiler cannot read this commit's library: {src} measured with its own)")
        return icount(compiler, src, extra, old_lib)
    if compiler == old and not src.startswith(old_src) and os.path.exists(os.path.join(old_src, src)):
        print(f"(the earlier compiler cannot read this commit's {src}: its own copy measured)")
        return icount(compiler, os.path.join(old_src, src), extra, old_lib)
    sys.exit(f"speedcheck: cannot count {os.path.basename(compiler)} build {src}: {r.stderr.strip()[-500:]}")


inputs = ["bench/big.jo", "compiler/main.jo", "examples/rebound/rebound.jo", "examples/breakwater/breakwater.jo"]
modes = [[]] + ([["--release"]] if args.release else [])
worst = 0.0
print(f"compile speed: {base} -> working tree (G instructions)")
for extra in modes:
    for src in inputs:
        a = icount(old, src, extra)
        b = icount(new, src, extra)
        pct = (b - a) / a * 100
        worst = max(worst, pct)
        flag = "  <- slower" if pct > args.limit else ""
        print(f"  {src + (' --release' if extra else ''):46} {a:7.3f} -> {b:7.3f}  {pct:+6.2f}%{flag}")

# the library: the same compiler, the earlier library and this one, on programs that use little
# of it, where what the library makes every program compile shows most
with open(os.path.join(tmp, "hello.jo"), "w") as f: f.write('print("hi")\n')
with open(os.path.join(tmp, "game.jo"), "w") as f: f.write('window("t", 320, 200)\ndraw = ():\n    clear(BLACK)\n    rect(1, 2, 3, 4, RED)\n    text("hi", vec2(3, 3), 12, WHITE)\n')
# (files new in this library stand empty in the earlier one: this compiler may read them by name,
# and what they hold was not in it)
cmp_lib = os.path.join(tmp, "base-lib-cmp")
shutil.copytree(old_lib, cmp_lib)
for d, _, fs in os.walk(os.path.join(root, "lib")):
    for fn in fs:
        rel = os.path.relpath(os.path.join(d, fn), os.path.join(root, "lib"))
        if fn.endswith(".jo") and not os.path.exists(os.path.join(cmp_lib, rel)):
            os.makedirs(os.path.dirname(os.path.join(cmp_lib, rel)), exist_ok=True)
            open(os.path.join(cmp_lib, rel), "w").close()
print(f"library: {base}'s -> the working tree's, compiled by this compiler")
for src in [os.path.join(tmp, "hello.jo"), os.path.join(tmp, "game.jo"), "examples/rebound/rebound.jo", "examples/breakwater/breakwater.jo"]:
    cmd = [os.path.join(root, "tools", "icount"), new, "build", src, "-o", os.path.join(tmp, "out")]
    got = []
    for lib in [cmp_lib, os.path.join(root, "lib")]:
        if counter == "valgrind": break
        r = subprocess.run(cmd, cwd=root, env=dict(env, SLOPPY_LIB=lib), capture_output=True, text=True)
        line = (r.stderr.strip().splitlines() or [""])[-1]
        if r.returncode != 0 or "G instructions" not in line: break
        got.append(float(line.split()[0]))
    name = os.path.basename(src) if src.startswith(tmp) else src
    if len(got) < 2:
        print(f"  {name:46} (not measured: this compiler cannot build it with the earlier library)")
        continue
    pct = (got[1] - got[0]) / got[0] * 100
    worst = max(worst, pct)
    flag = "  <- slower" if pct > args.limit else ""
    print(f"  {name:46} {got[0]:7.3f} -> {got[1]:7.3f}  {pct:+6.2f}%{flag}")
shutil.rmtree(tmp, ignore_errors=True)
if worst > args.limit:
    sys.exit(f"speedcheck: compiling is {worst:.2f}% slower than at {base} (the limit is {args.limit}%)")
