#!/usr/bin/env python3
"""Web builds in a browser (Playwright's headless Chromium, when it is installed): typing into a text
field on a phone (touches and the phone's keyboard) and on a computer (mouse, keys, ctrl+V); text
from an input method, files dropped and picked, cursor shapes, redraw_on_input; two pages connected
through lib/invite.jo's screens.
usage: tools/webtest.py [path/to/sloppy]"""
import os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
shell = None
pw = os.path.expanduser("~/.cache/ms-playwright")
if os.path.isdir(pw):
    for d in sorted(os.listdir(pw)):
        if d.startswith("chromium_headless_shell"):
            for sub in os.listdir(os.path.join(pw, d)):
                p = os.path.join(pw, d, sub, "chrome-headless-shell")
                if os.path.exists(p): shell = p
if not shell or not shutil.which("node"):
    print("(no browser or no node: nothing tried)")
    sys.exit(0)
tmp = tempfile.mkdtemp(prefix="sloppy-webtest-")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
page = os.path.join(tmp, "text_field")
subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "text_field.jo"), "-o", page, "--target", "wasm"], check=True, env=env)
r = subprocess.run(["node", os.path.join(root, "tools", "web_input.mjs"), shell, page + ".html", tmp], timeout=120)
desk = os.path.join(tmp, "desktop")
subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "desktop.jo"), "-o", desk, "--target", "wasm"], check=True, env=env)
r3 = subprocess.run(["node", os.path.join(root, "tools", "web_desktop.mjs"), shell, desk + ".html", tmp], timeout=120)
inv = os.path.join(tmp, "invite_ui")
subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "invite_ui.jo"), "-o", inv, "--target", "wasm"], check=True, env=env)
r2 = subprocess.run(["node", os.path.join(root, "tools", "web_invite.mjs"), shell, inv + ".html", tmp], timeout=120)
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(r.returncode or r2.returncode or r3.returncode)
