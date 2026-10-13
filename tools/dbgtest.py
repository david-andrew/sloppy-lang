#!/usr/bin/env python3
"""Debuggers on Sloppy programs built with `sloppy build -g`: each tests/debug/<name>.jo is built,
run under gdb (and lldb, if installed) with lib/debug's printers, stopped at the line marked
`# stop` (or where it panics, when no line is marked), and what they show of the variables (gdb:
info locals and bt; lldb: frame variable and bt) must contain each line of <name>.expect for that
debugger ("gdb: ..." or "lldb: ...").
usage: tools/dbgtest.py [path/to/sloppy]"""
import os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
tmp = tempfile.mkdtemp(prefix="sloppy-dbgtest-")
debuggers = [d for d in ("gdb", "lldb") if shutil.which(d)]
if not debuggers: sys.exit("dbgtest: neither gdb nor lldb is installed")
passed = failed = 0
for name in sorted(f[:-3] for f in os.listdir(os.path.join(root, "tests", "debug")) if f.endswith(".jo")):
    src = os.path.join(root, "tests", "debug", name + ".jo")
    exe = os.path.join(tmp, name)
    r = subprocess.run([sloppy, "build", "-g", src, "-o", exe], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL {name}: does not build\n{r.stderr}")
        failed += 1
        continue
    lines = open(src).read().split("\n")
    stop = next((i + 1 for i, l in enumerate(lines) if l.rstrip().endswith("# stop")), 0)
    where = f"{name}.jo:{stop}" if stop else "__panic"
    expect = [l.split(": ", 1) for l in open(os.path.join(root, "tests", "debug", name + ".expect")).read().splitlines() if ": " in l]
    for dbg in debuggers:
        if dbg == "gdb":
            cmd = ["gdb", "-q", "-batch", "-nx", "-x", os.path.join(root, "lib", "debug", "sloppy_gdb.py"),
                   "-ex", f"break {where}", "-ex", "run", "-ex", "info locals", "-ex", "bt", exe]
        else:
            bp = f"breakpoint set -f {name}.jo -l {stop}" if stop else "breakpoint set -n __panic"
            cmd = ["lldb", "-b", "--no-lldbinit", "-o", f"command script import {os.path.join(root, 'lib', 'debug', 'sloppy_lldb.py')}",
                   "-o", bp, "-o", "run", "-o", "frame variable -P 1", "-o", "bt", exe]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, cwd=tmp).stdout
        except subprocess.TimeoutExpired:
            out = "(timeout)"
        missing = [want for d, want in expect if d == dbg and want not in out]
        if missing:
            print(f"FAIL {name} ({dbg}): missing {missing}\n{out[-3000:]}")
            failed += 1
        else:
            passed += 1
shutil.rmtree(tmp, ignore_errors=True)
print(f"{passed} passed, {failed} failed ({', '.join(debuggers)})")
sys.exit(1 if failed else 0)
