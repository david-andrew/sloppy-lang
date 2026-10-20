#!/usr/bin/env python3
"""Run Sloppy test programs and compare output with .out files.
usage: runtests.py [--compiler sloppy0|sloppy|path] [--release] [--target native|wasm|windows|linux-arm64] [pattern]
(linux-arm64: run under qemu-aarch64, or SLOPPY_ARM64_RUN)
(on Windows itself: the compiler is bin/sloppy.exe, and programs are native Windows ones)"""
import os, re, shutil, subprocess, sys, glob, tempfile, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[1:]
compiler = "sloppy0"
release = False
target = "native"
pattern = ""
i = 0
while i < len(args):
    if args[i] == "--compiler": compiler = args[i + 1]; i += 2
    elif args[i] == "--release": release = True; i += 1
    elif args[i] == "--target": target = args[i + 1]; i += 2
    else: pattern = args[i]; i += 1

on_windows = os.name == "nt"
import ctypes.util
have_sqlite = on_windows or ctypes.util.find_library("sqlite3") is not None

# (a test in a container that ran out of time: stopping `podman exec` leaves the program running
# inside, for hours, so the container's own processes are stopped too)
def stop_container_run(target):
    if target == "windows" and not on_windows:
        subprocess.run(os.environ.get("SLOPPY_WINE", "podman exec sloppy-win /w/run.sh").split()[:3] + ["sh", "-c", "wineserver -k"], capture_output=True)
    elif target == "linux-arm64" and os.environ.get("SLOPPY_ARM64_RUN", "").startswith("podman exec"):
        c = os.environ["SLOPPY_ARM64_RUN"].split()[2]
        subprocess.run(["podman", "exec", c, "sh", "-c", "kill -9 $(ls /proc | grep -E '^[0-9]+$' | grep -v -x 1) 2>/dev/null"], capture_output=True)
# (a test with a .c file next to it calls C: the C is built into a library in the directory the
# test runs in, lib<name>.so (<name>.dll on Windows), with the target's C compiler. The command
# lists, or "" when there is no compiler for the target here)
def c_lib_commands(src, name, d):
    if on_windows:
        return [["gcc", "-shared", "-O1", "-o", os.path.join(d, name + ".dll"), src]] if shutil.which("gcc") else ""
    if target == "windows":
        if shutil.which("x86_64-w64-mingw32-gcc"):
            return [["x86_64-w64-mingw32-gcc", "-shared", "-O1", "-o", os.path.join(d, name + ".dll"), src]]
        # (Wine's container has one: the source copied where it sees it)
        shutil.copy(src, os.path.join(d, name + ".c"))
        wcc = os.environ.get("SLOPPY_WIN_CC", "podman exec sloppy-win x86_64-w64-mingw32-gcc").split()
        return [wcc + ["-shared", "-O1", "-o", f"/w/tests/{name}.dll", f"/w/tests/{name}.c"]]
    out = os.path.join(d, "lib" + name + ".so")
    if target == "linux-arm64":
        if shutil.which("aarch64-linux-gnu-gcc"): return [["aarch64-linux-gnu-gcc", "-shared", "-fPIC", "-O1", "-o", out, src]]
        # (clang makes the code, and bare-metal binutils' ld the library: the C uses no libc)
        if shutil.which("clang") and shutil.which("aarch64-elf-ld"):
            return [["clang", "--target=aarch64-linux-gnu", "-ffreestanding", "-fPIC", "-O1", "-c", src, "-o", out + ".o"],
                    ["aarch64-elf-ld", "-shared", "-o", out, out + ".o"]]
        return ""
    cc = os.environ.get("CC", "cc")
    return [[cc, "-shared", "-fPIC", "-O1", "-o", out, src]] if shutil.which(cc) else ""

tmp = os.path.join(tempfile.gettempdir(), "sloppy-tests")
sloppy_bin = os.path.join(root, "bin", "sloppy.exe" if on_windows else "sloppy")
tests = sorted(glob.glob(os.path.join(root, "tests", "t", "*.jo")))
tests = [t for t in tests if pattern in os.path.basename(t)]
passed = failed = 0
os.makedirs(tmp, exist_ok=True)
os.environ["SLOPPY_SEED"] = "12345"         # (random() starts from the clock; tests print the same each time)
import shutil
shutil.rmtree(os.path.join(tmp, "saved-data"), ignore_errors=True)     # (save_data: tests start with nothing saved)
for t in tests:
    name = os.path.basename(t)[:-3]
    exp_path = t[:-3] + ".out"
    expected = open(exp_path, encoding="utf-8").read() if os.path.exists(exp_path) else None
    exe = os.path.join(tmp, name)
    if target == "windows":
        # (run under Wine: SLOPPY_WINE_DIR is shared with the container SLOPPY_WINE runs in)
        exe = os.path.join(os.environ.get("SLOPPY_WINE_DIR", "/tmp/winshare"), "tests", name)
        os.makedirs(os.path.dirname(exe), exist_ok=True)
    head = open(t, encoding="utf-8").read(2000)
    if compiler == "sloppy0" and "# requires: sloppy" in head:
        continue
    if target == "wasm" and "# requires: native" in head:
        continue
    # (`# requires: unix`: signals, a shell's commands)
    if (target in ("wasm", "windows") or on_windows) and "# requires: unix" in head:
        continue
    # (`# known: macos hangs, ...`: a failure on macOS that is being looked into, told, not run)
    if sys.platform == "darwin" and target == "native" and "# known: macos" in head:
        print(f"SKIP {name}: known to fail on macOS ({head.split('# known: macos', 1)[1].splitlines()[0].strip(' ,')})")
        continue
    # (`# requires: sqlite`: the system's SQLite, which a machine may not have; Wine has none)
    if "# requires: sqlite" in head and (target not in ("native",) or not have_sqlite):
        print(f"SKIP {name}: no SQLite here")
        continue
    # (name.in, when there is one, is the test's standard input; Wine's container is not given it)
    stdin_data = open(t[:-3] + ".in", encoding="utf-8").read() if os.path.exists(t[:-3] + ".in") else ""
    if stdin_data and target == "windows":
        continue
    run_dir = None
    if os.path.exists(t[:-3] + ".c") and target != "wasm":
        cmds = c_lib_commands(t[:-3] + ".c", name, os.path.dirname(exe))
        if not cmds:
            print(f"SKIP {name}: no C compiler for {target} here")
            continue
        r = None
        for c in cmds:
            r = subprocess.run(c, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
            if r.returncode != 0: break
        if r.returncode != 0:
            print(f"FAIL {name}: its C does not build\n{r.stdout}{r.stderr}")
            failed += 1
            continue
        run_dir = os.path.dirname(exe)
    if compiler == "sloppy0":
        cmd = [os.path.join(root, "stage0", "sloppy0"), t, "-o", exe]
    else:
        sloppy = sloppy_bin if compiler == "sloppy" else os.path.abspath(compiler)
        cmd = [sloppy, "build", t, "-o", exe] + (["--target", target] if target != "native" else []) + (["--release"] if release else [])
        env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
    except subprocess.TimeoutExpired:
        print(f"FAIL {name}: the compiler took over 60 s")
        failed += 1
        continue
    if r.returncode != 0:
        print(f"FAIL {name}: compile error\n{r.stderr}")
        failed += 1
        continue
    # (`# no warnings` at the top: code a warning must not be given for)
    if "# no warnings" in head and "warning: " in r.stderr:
        print(f"FAIL {name}: a warning where none is wanted\n{r.stderr}")
        failed += 1
        continue
    if target == "wasm":
        run = ["node", os.path.join(root, "tools", "runwasm.js"), exe + ".html"]
    elif target == "windows":
        run = os.environ.get("SLOPPY_WINE", "podman exec sloppy-win /w/run.sh").split() + ["tests/" + name + ".exe"]
    elif target == "linux-arm64":
        run = os.environ.get("SLOPPY_ARM64_RUN", "qemu-aarch64-static").split() + [exe]
        # (a container is given standard input only with -i)
        if stdin_data and run[:2] == ["podman", "exec"] and "-i" not in run: run.insert(2, "-i")
    elif on_windows:
        run = [exe + ".exe"]
    else:
        run = [exe]
    try:
        # (`# env: NAME=value` lines at the top: set for the run, a headless game's SLOPPY_SCREENSHOT say)
        test_env = dict(os.environ, SLOPPY_SAVE_DIR=os.path.join(tmp, "saved-data"))
        # (no display: a game in a test draws with no window, not one on the desktop)
        test_env.pop("DISPLAY", None)
        test_env.pop("WAYLAND_DISPLAY", None)
        for l in head.splitlines():
            if l.startswith("# env: ") and "=" in l:
                k, v = l[7:].split("=", 1)
                test_env[k.strip()] = v.strip().replace("$TMP", tmp)
                # (a container's program is not given this one's environment: Wine's, in /w)
                if run[:2] == ["podman", "exec"]:
                    cv = v.strip().replace("$TMP", "/w/tests" if target == "windows" else tmp)
                    run[2:2] = ["-e", f"{k.strip()}={cv}"]
                    if "-e" in run and "LANG=C.UTF-8" not in run: run[2:2] = ["-e", "LANG=C.UTF-8"]     # (é as UTF-8, not two Latin-1 letters)
        # (a test with a C library runs where it is: `@lib("./libname.so")`)
        if run_dir and run[:2] == ["podman", "exec"] and target != "windows": run[2:2] = ["-w", run_dir]
        r = subprocess.run(run, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, input=stdin_data,
                           env=test_env, cwd=run_dir)
    except subprocess.TimeoutExpired as e:
        print(f"FAIL {name}: timed out")
        # (what it said before: where it stopped)
        for what, out in (("stdout", e.stdout), ("stderr", e.stderr)):
            if isinstance(out, bytes): out = out.decode("utf-8", "replace")
            if out:
                print(f"   {what}, the last lines:")
                for l in out.splitlines()[-8:]: print(f"   | {l}")
        failed += 1
        stop_container_run(target)
        continue
    out = r.stdout
    if r.returncode != 0 and not name.startswith("panic"):
        # (the backtrace after a panic differs with --release and is not there on the web;
        # tests/backtrace checks it)
        err = "".join(l for l in r.stderr.splitlines(True) if not l.startswith(("    in ", "    called from ", "    ...", "    (the ")))
        out += f"[exit {r.returncode}] {err}"
    if expected is None:
        print(f"NEW  {name}:\n{out}")
        failed += 1
    elif out != expected:
        print(f"FAIL {name}")
        el, ol = expected.splitlines(), out.splitlines()
        for k in range(max(len(el), len(ol))):
            e = el[k] if k < len(el) else "<missing>"
            o = ol[k] if k < len(ol) else "<missing>"
            if e != o:
                print(f"   line {k+1}: expected {e!r}\n   line {k+1}:      got {o!r}")
                break
        failed += 1
    else:
        passed += 1
# backtraces after a panic: tests/backtrace/*.jo, all of stderr against .out (native debug builds)
if compiler != "sloppy0" and target in ("native", "windows") and not release:
    sloppy = sloppy_bin if compiler == "sloppy" else os.path.abspath(compiler)
    for t in sorted(glob.glob(os.path.join(root, "tests", "backtrace", "*.jo"))):
        name = "backtrace/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        exe = os.path.join(tmp, "bt_" + os.path.basename(t)[:-3])
        run = [exe + ".exe"] if on_windows else [exe]
        if target == "windows":
            exe = os.path.join(os.environ.get("SLOPPY_WINE_DIR", "/tmp/winshare"), "tests", "bt_" + os.path.basename(t)[:-3])
            run = os.environ.get("SLOPPY_WINE", "podman exec sloppy-win /w/run.sh").split() + ["tests/" + os.path.basename(exe) + ".exe"]
        subprocess.run([sloppy, "build", t, "-o", exe] + (["--target", target] if target != "native" else []), capture_output=True, env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")))
        r = subprocess.run(run, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        # (how deep a recursion gets before the stack runs out depends on the machine)
        out = re.sub(r"\([\d,]+ times\)", "(N times)", r.stdout + r.stderr)
        out = re.sub(r"\d[\d,]* calls deep", "N calls deep", out)
        exp_path = t[:-3] + ".out"
        if not os.path.exists(exp_path):
            print(f"NEW  {name}:\n{out}")
            failed += 1
        elif out != open(exp_path, encoding="utf-8").read():
            print(f"FAIL {name}:\n{out}")
            failed += 1
        else: passed += 1
# `test` blocks in tests/unit, run with `sloppy test` (native, self-hosted compiler only)
if compiler != "sloppy0" and target == "native":
    sloppy = sloppy_bin if compiler == "sloppy" else os.path.abspath(compiler)
    for t in sorted(glob.glob(os.path.join(root, "tests", "unit", "*.jo"))):
        name = "unit/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        r = subprocess.run([sloppy, "test", t], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        if r.returncode == 0 and re.search(r"\d+ tests? passed", r.stdout): passed += 1
        else:
            print(f"FAIL {name}\n{r.stdout}{r.stderr}")
            failed += 1
    # failing tests are reported and the rest still run (each in a process of its own)
    if os.name != "nt" and pattern in "unit/failing":
        t = os.path.join(root, "tests", "unit_failing", "mixed.jo")
        r = subprocess.run([sloppy, "test", t], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        want = ["test adds ... ok", "test fails ... FAILED", "test panics ... FAILED", "in the last test", "test quits early ... FAILED",
                "called exit(0) before its end", "2 passed, 3 failed"]
        if r.returncode == 1 and all(w in r.stdout + r.stderr for w in want): passed += 1
        else:
            print(f"FAIL unit/failing (exit {r.returncode})\n{r.stdout}{r.stderr}")
            failed += 1
        # (sloppy test file.jo words: only the tests with one of the words in their names)
        r = subprocess.run([sloppy, "test", t, "adds", "runs"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        r2 = subprocess.run([sloppy, "test", t, "nothing"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        if r.returncode == 0 and "2 tests passed (3 not run" in r.stdout and "fails" not in r.stdout and r2.returncode == 1 and "no test's name has 'nothing'" in r2.stderr: passed += 1
        else:
            print(f"FAIL unit/filter (exit {r.returncode}, {r2.returncode})\n{r.stdout}{r.stderr}{r2.stdout}{r2.stderr}")
            failed += 1
    # (sloppy test on a game that calls window(...) at its top: the tests run with no display)
    if pattern in "unit/window":
        t = os.path.join(root, "tests", "unit_window", "game.jo")
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        r = subprocess.run([sloppy, "test", t], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(env, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        if r.returncode == 0 and "1 test passed" in r.stdout: passed += 1
        else:
            print(f"FAIL unit/window (exit {r.returncode})\n{r.stdout}{r.stderr}")
            failed += 1
    # the tutorials' programs (docs/TUTORIAL*.md: code blocks starting "# step") must build
    for tf in sorted(glob.glob(os.path.join(root, "docs", "TUTORIAL*.md"))):
        tname = os.path.basename(tf)[:-3].lower()
        tut = open(tf, encoding="utf-8").read()
        for k, code in enumerate(re.findall(r"```gdscript\n(# step.*?)```", tut, re.S)):
            name = f"{tname}/step{k + 1}"
            if pattern not in name: continue
            src = os.path.join(tmp, f"{tname}_step{k + 1}.jo")
            open(src, "w", encoding="utf-8").write(code)
            r = subprocess.run([sloppy, "build", src, "-o", os.path.join(tmp, "tutorial_step")], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
            if r.returncode == 0: passed += 1
            else:
                print(f"FAIL {name}: does not build\n{r.stderr}")
                failed += 1
    # sloppy fmt: tests/fmt/*.jo laid out must be their .out (which stays as it is), and the
    # compiler, the library and the examples must be laid out so already
    for t in sorted(glob.glob(os.path.join(root, "tests", "fmt", "*.jo"))):
        name = "fmt/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        want = open(t[:-3] + ".out", encoding="utf-8").read()
        env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
        got = subprocess.run([sloppy, "fmt", "-"], stdin=open(t, "rb"), capture_output=True, env=env, timeout=60).stdout.decode()
        again = subprocess.run([sloppy, "fmt", "-"], input=want.encode(), capture_output=True, env=env, timeout=60).stdout.decode()
        if got == want and again == want: passed += 1
        else:
            print(f"FAIL {name}:\n{got}")
            failed += 1
    if pattern in "fmt/repository":
        r = subprocess.run([sloppy, "fmt", "--check", "compiler", "lib", "examples", "docs/api"], capture_output=True, text=True, cwd=root,
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=120)
        if r.returncode == 0: passed += 1
        else:
            print(f"FAIL fmt/repository: not laid out by sloppy fmt (run it on these):\n{r.stdout}{r.stderr}")
            failed += 1
    # `sloppy new`: each template, made into a project, must build (and the program's tests pass)
    for kind in ["game", "arcade", "pico", "platformer", "3d", "story", "online", "program", "tui", "server"]:
        name = "new/" + kind
        if pattern not in name: continue
        d = os.path.join(tmp, "new_" + kind)
        shutil.rmtree(d, ignore_errors=True)
        env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
        r = subprocess.run([sloppy, "new", d, kind], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=60)
        src = os.path.join(d, "new_" + kind + ".jo")
        if r.returncode == 0:
            cmd = [sloppy, "test", src] if kind in ("program", "tui", "server") else [sloppy, "build", src, "-o", os.path.join(tmp, "new_project")]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=60)
        if r.returncode == 0: passed += 1
        else:
            print(f"FAIL {name}\n{r.stdout}{r.stderr}")
            failed += 1
    # the library page's examples (docs/api/*.jo) must build, and docs/API.md be what tools/apidoc.py makes now
    for src in sorted(glob.glob(os.path.join(root, "docs", "api", "*.jo"))):
        name = "api/" + os.path.basename(src)[:-3]
        if pattern not in name: continue
        r = subprocess.run([sloppy, "build", src, "-o", os.path.join(tmp, "api_example")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        if r.returncode == 0: passed += 1
        else:
            print(f"FAIL {name}: does not build\n{r.stderr}")
            failed += 1
    if pattern in "api/API.md":
        sys.path.insert(0, os.path.join(root, "tools"))
        import apidoc
        if apidoc.markdown(apidoc.collect()) == open(os.path.join(root, "docs", "API.md"), encoding="utf-8").read(): passed += 1
        else:
            print("FAIL api/API.md: out of date (run tools/apidoc.py)")
            failed += 1
    # programs the compiler must reject: tests/errors/*.jo start with `# error: <part of the message>`
    for t in sorted(glob.glob(os.path.join(root, "tests", "errors", "*.jo"))):
        name = "errors/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        want = open(t, encoding="utf-8").readline().split("# error:", 1)[-1].strip()
        r = subprocess.run([sloppy, "build", t, "-o", os.path.join(tmp, "error_case")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        # (a diagnostic: exit status 1 with an error at a place, never the compiler crashing)
        crashed = r.returncode != 1 or "panic:" in r.stderr or "internal compiler error" in r.stderr
        if not crashed and want in r.stderr: passed += 1
        else:
            print(f"FAIL {name}: expected an error containing {want!r}\n{r.stderr}")
            failed += 1
    # code made on several processors is the same as code made on one (compiler/par.jo)
    if pattern in "parallel/emit" and os.name != "nt" and target == "native" and not release:
        same = True
        for flags in [[], ["--release"], ["-g"]]:
            outs = []
            for envs in [{"SLOPPY_EMIT_WORKERS": "1"}, {"SLOPPY_EMIT_FORCE": "1"}]:
                o = os.path.join(tmp, "par_" + str(len(outs)))
                # (the compiler itself: a large program that is always there)
                r = subprocess.run([sloppy, "build", os.path.join(root, "compiler", "main.jo"), "-o", o] + flags, capture_output=True,
                                   text=True, env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), **envs), timeout=300)
                outs.append(open(o, "rb").read() if r.returncode == 0 and os.path.exists(o) else b"")
                if not outs[-1]: print(f"FAIL parallel/emit: {flags} {envs} did not build\n{r.stderr}")
            if not outs[0] or not outs[1]: same = False
            elif outs[0] != outs[1]:
                print(f"FAIL parallel/emit: {flags} differs from one processor's code")
                same = False
        if same: passed += 1
        else: failed += 1
    # programs that build with a warning: tests/warnings/*.jo start with `# warning: <part of it>`
    for t in sorted(glob.glob(os.path.join(root, "tests", "warnings", "*.jo"))):
        name = "warnings/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        want = open(t, encoding="utf-8").readline().split("# warning:", 1)[-1].strip()
        r = subprocess.run([sloppy, "build", t, "-o", os.path.join(tmp, "warning_case")], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60)
        if r.returncode == 0 and "warning: " + want in r.stderr: passed += 1
        else:
            print(f"FAIL {name}: expected a warning containing {want!r}\n{r.stderr}")
            failed += 1
    # the interactive prompt: tests/repl/*.in typed at `sloppy` (stdout and stderr) against .out
    repl_tests = sorted(glob.glob(os.path.join(root, "tests", "repl", "*.in")))
    for t in repl_tests:
        name = "repl/" + os.path.basename(t)[:-3]
        if pattern not in name: continue
        exp_path = t[:-3] + ".out"
        r = subprocess.run([sloppy], stdin=open(t), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")), timeout=60, cwd=os.path.dirname(t))
        out = re.sub(r"\d[\d,]* calls deep", "N calls deep", r.stdout) + (f"[exit {r.returncode}]\n" if r.returncode != 0 else "")
        if not os.path.exists(exp_path):
            print(f"NEW  {name}:\n{out}")
            failed += 1
        elif out != open(exp_path, encoding="utf-8").read():
            print(f"FAIL {name}:\n{out}")
            failed += 1
        else: passed += 1
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
