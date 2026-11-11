#!/usr/bin/env python3
"""Browser HTTP client checks: tasks (JSPI), frame polling, options and streamed progress.
Uses the same headless Chromium/CDP mechanism as webtest.py, with a local server on 9700-9799.
usage: tools/webfetchcheck.py [path/to/sloppy]
"""
import os, pathlib, shutil, subprocess, sys, tempfile

root = pathlib.Path(__file__).resolve().parent.parent
sloppy = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "bin/sloppy"
shells = sorted(pathlib.Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))
if not shells or not shutil.which("node"):
    print("(no headless Chromium or node: browser fetch checks skipped)")
    sys.exit(0)
env = dict(os.environ, SLOPPY_LIB=str(root / "lib"), DISPLAY="", WAYLAND_DISPLAY="")
with tempfile.TemporaryDirectory(prefix="sloppy-webfetch-") as work:
    for name in ("fetch_tasks", "fetch_poll"):
        subprocess.run([str(sloppy), "build", str(root / f"tests/web/{name}.jo"), "--target", "wasm", "-o", f"{work}/{name}.html"], check=True, env=env)
    sys.exit(subprocess.run(["node", str(root / "tools/web_fetch.mjs"), str(shells[-1]), work], env=env, timeout=60).returncode)
