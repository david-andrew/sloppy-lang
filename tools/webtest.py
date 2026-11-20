#!/usr/bin/env python3
"""Web builds in a browser (Playwright's headless Chromium, when it is installed): typing into a text
field on a phone (touches and the phone's keyboard) and on a computer (mouse, keys, ctrl+V); text
from an input method, files dropped and picked, cursor shapes, redraw_on_input; two pages connected
through lib/invite.jo's screens; the audio clock and the times of presses; browser HTTP fetches.
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
aud = os.path.join(tmp, "audio_clock")
subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "audio_clock.jo"), "-o", aud, "--target", "wasm"], check=True, env=env)
r4 = subprocess.run(["node", os.path.join(root, "tools", "web_audio.mjs"), shell, aud + ".html", tmp], timeout=120)
shader_page = os.path.join(tmp, "uniform_budget")
subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "uniform_budget.jo"), "-o", shader_page, "--target", "wasm"], check=True, env=env)
r6 = subprocess.run(["node", os.path.join(root, "tools", "web_shaders.mjs"), shell, shader_page + ".html", tmp], timeout=120)
# render scenes drawn with WebGL against their references (tests/render: the draw state, depth
# targets, set_depth and reversed depth; a feedback loop the browser reports fails too)
sys.path.insert(0, os.path.join(root, "tools"))
from pngutil import downsample, png_rows
r7 = 0
for sc in ["draw_state", "depth_texture", "copy_depth", "scene_depth", "set_depth", "reversed_depth", "reversed_scene"]:
    pg = os.path.join(tmp, sc)
    subprocess.run([sloppy, "build", os.path.join(root, "tests", "render", sc + ".jo"), "-o", pg, "--target", "wasm"], check=True, env=env)
    shot = os.path.join(tmp, sc + "_web.png")
    rr = subprocess.run(["node", os.path.join(root, "tools", "web_render.mjs"), shell, pg + ".html", shot, "800", "450", tmp], timeout=120)
    if rr.returncode != 0 or not os.path.exists(shot):
        r7 = 1
        continue
    w, h, got = downsample(shot, 4)
    rw, rh, _, rows = png_rows(os.path.join(root, "tests", "render", sc + ".png"))
    want = b"".join(rows)
    if (w, h) != (rw, rh):
        print(f"FAIL {sc} (WebGL): size {w}x{h}, reference {rw}x{rh}")
        r7 = 1
        continue
    d = sum(abs(a - b) for a, b in zip(got, want)) / len(want)
    print(f"{'ok  ' if d <= 4.0 else 'FAIL'} {sc} (WebGL): mean abs difference {d:.3f}")
    if d > 4.0: r7 = 1
shutil.rmtree(tmp, ignore_errors=True)
r5 = subprocess.run([sys.executable, os.path.join(root, "tools", "webfetchcheck.py"), sloppy], env=env, timeout=120)
sys.exit(r.returncode or r2.returncode or r3.returncode or r4.returncode or r5.returncode or r6.returncode or r7)
