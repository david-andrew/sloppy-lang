#!/usr/bin/env python3
"""Render test on a real Mac over ssh: cross-build the games and render scenes of rendertest.py
for macOS here, copy them to the Mac, draw frame 60 of each there with its GPU, fetch the frames
and compare them with tests/render's references with rendertest.py's GPU limit.
usage: macrender.py --host user@mac [--renderer gl|glsoft|metal]... [--keep] [--jobs N] [name...]
  gl      Apple's hardware OpenGL (the default renderer on macOS today)
  glsoft  Apple's software OpenGL (SLOPPY_GL_SOFTWARE=1: what the CI runners have)
  metal   Metal (SLOPPY_METAL=1); a run that falls back to OpenGL fails
(all three without --renderer). The Mac needs nothing installed: the programs run as built, with
perl's alarm as the time limit (no Xcode tools there). Files go to ~/dev/tmp/sloppy-macrender on
the Mac and $TMPDIR/sloppy-macrender here; the frames are kept there (--keep: the Mac's too).
They run with no window (screenshot runs are headless on macOS; --env SLOPPY_HEADLESS=0 for a
window) and with SLOPPY_NO_AUDIO=1. The Macs this has run on
are people's own machines: use one only with its owner's OK."""
import argparse, concurrent.futures, multiprocessing, os, shlex, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pngutil import downsample, png_rows

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.join(root, "bin", "sloppy")
refdir = os.path.join(root, "tests", "render")
GPU_FRAME_LIMIT = 4.0          # as rendertest.py's: a whole frame on a GPU
RENDERERS = {"gl": "SLOPPY_METAL=0", "glsoft": "SLOPPY_METAL=0 SLOPPY_GL_SOFTWARE=1", "metal": "SLOPPY_METAL=1"}

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
ap.add_argument("--host", required=True, help="ssh destination, e.g. user@192.168.1.90")
ap.add_argument("--renderer", action="append", choices=sorted(RENDERERS), help="(repeatable; default: all)")
ap.add_argument("--keep", action="store_true", help="keep the programs and frames on the Mac")
ap.add_argument("--jobs", type=int, default=2, help="builds at once here")
ap.add_argument("--frames", default="60")
ap.add_argument("--timeout", type=int, default=120, help="seconds per run on the Mac")
ap.add_argument("--env", action="append", default=[], help="NAME=VALUE for every run on the Mac (repeatable)")
ap.add_argument("names", nargs="*")
a = ap.parse_args()
renderers = a.renderer or ["gl", "glsoft", "metal"]

games = {"cube": "examples/cube.jo", "rebound": "examples/rebound/rebound.jo", "dunes": "examples/dunes/dunes.jo", "aces": "examples/aces/aces.jo", "skybarons": "examples/skybarons/skybarons.jo",
         "new_game": "lib/new/game.jo", "new_arcade": "lib/new/arcade.jo", "new_pico": "lib/new/pico.jo", "new_platformer": "lib/new/platformer.jo", "new_3d": "lib/new/3d.jo", "new_character": "lib/new/character.jo", "new_story": "lib/new/story.jo"}
for f in sorted(os.listdir(refdir)):
    if f.endswith(".jo"): games[f[:-3]] = f"tests/render/{f}"
if a.names:
    bad = [n for n in a.names if n not in games]
    if bad: sys.exit(f"unknown: {' '.join(bad)} (names are rendertest.py's)")
    games = {k: v for k, v in games.items() if k in a.names}

out = os.path.join(tempfile.gettempdir(), "sloppy-macrender")
bins = os.path.join(out, "bin")
shutil.rmtree(out, ignore_errors=True)
os.makedirs(bins)
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))

def build(name):
    r = subprocess.run([sloppy, "build", "--release", "--target", "macos", os.path.join(root, games[name]), "-o", os.path.join(bins, name)],
                       env=env, capture_output=True, text=True)
    return name, r.returncode, r.stderr
failed = []
with concurrent.futures.ThreadPoolExecutor(max(1, a.jobs)) as ex:
    for name, rc, err in ex.map(build, games):
        if rc != 0:
            print(f"FAIL {name}: build failed\n{err}")
            failed.append(f"{name} (build)")
names = [n for n in games if os.path.exists(os.path.join(bins, n))]
print(f"built {len(names)} for macOS", flush=True)

# one shell script on the Mac runs them all, one after another (one GPU)
remote = "dev/tmp/sloppy-macrender"
lines = ["set -u", f"cd ~/{remote}", "rm -rf frames; mkdir -p frames"]
extra = " ".join(shlex.quote(e) for e in a.env)
for r in renderers:
    lines.append(f"mkdir -p frames/{r}")
    for n in names:
        lines.append(f"rm -rf saved; {RENDERERS[r]} {extra} SLOPPY_NO_AUDIO=1 SLOPPY_FRAMES={a.frames} SLOPPY_SCALE=1 SLOPPY_SAVE_DIR=$PWD/saved "
                     f"SLOPPY_SCREENSHOT=frames/{r}/{n}.png perl -e 'alarm {a.timeout}; exec @ARGV' ./bin/{n} >frames/{r}/{n}.log 2>&1; echo $? >frames/{r}/{n}.rc")
with open(os.path.join(out, "run.sh"), "w") as f: f.write("\n".join(lines) + "\n")

def ssh(cmd, **kw): return subprocess.run(["ssh", "-o", "BatchMode=yes", a.host, cmd], **kw)
# (tar both ways: bsdtar is part of macOS)
r = subprocess.run(f"tar -C {shlex.quote(out)} -cf - bin run.sh | ssh -o BatchMode=yes {shlex.quote(a.host)} "
                   f"'rm -rf ~/{remote} && mkdir -p ~/{remote} && tar -C ~/{remote} -xf -'", shell=True)
if r.returncode != 0: sys.exit("copying to the Mac failed")
print(f"running {len(names)} x {len(renderers)} on {a.host}", flush=True)
r = ssh(f"/bin/bash ~/{remote}/run.sh")
if r.returncode != 0: print(f"(the run script exited with {r.returncode})")
r = subprocess.run(f"ssh -o BatchMode=yes {shlex.quote(a.host)} 'tar -C ~/{remote} -cf - frames' | tar -C {shlex.quote(out)} -xf -", shell=True)
if r.returncode != 0: sys.exit("fetching the frames failed")
if not a.keep: ssh(f"rm -rf ~/{remote}")

# (the comparisons, which take a second or two each, on --jobs processes)
def compare(job):
    r, n = job
    base = os.path.join(out, "frames", r, n)
    log = open(base + ".log", errors="replace").read() if os.path.exists(base + ".log") else ""
    rc = open(base + ".rc").read().strip() if os.path.exists(base + ".rc") else "?"
    if r != "metal" and "# not with OpenGL" in open(os.path.join(root, games[n]), encoding="utf-8").read(2000):
        return None, f"skip {n} ({r}): not with OpenGL"
    if rc != "0" or not os.path.exists(base + ".png"): return False, f"FAIL {n} ({r}): render failed (exit {rc})\n{log[-2000:]}"
    if r == "metal" and "using OpenGL" in log: return False, f"FAIL {n} ({r}): not drawn with Metal\n{log[-1000:]}"
    rw, rh, bpp, rows = png_rows(os.path.join(refdir, n + ".png"))
    want = b"".join(rows)
    w, h, got = downsample(base + ".png", 4)
    if (w, h) != (rw, rh): return False, f"FAIL {n} ({r}): size {w}x{h}, reference {rw}x{rh}"
    d = sum(abs(x - y) for x, y in zip(got, want)) / len(want)
    return d <= GPU_FRAME_LIMIT, f"{'ok  ' if d <= GPU_FRAME_LIMIT else 'FAIL'} {n} ({r}): mean abs difference {d:.3f}"
runs = 0
jobs = [(r, n) for r in renderers for n in names]
# (fork: the workers start with what is loaded here, not by running this script again)
with concurrent.futures.ProcessPoolExecutor(max(1, a.jobs), mp_context=multiprocessing.get_context("fork")) as ex:
    for (r, n), (ok, text) in zip(jobs, ex.map(compare, jobs)):
        print(text, flush=True)
        if ok is None: continue
        runs += 1
        if not ok: failed.append(f"{n} ({r})")
print(f"frames in {os.path.join(out, 'frames')}")
print(f"{runs - len(failed)} passed, {len(failed)} failed" + (": " + ", ".join(failed) if failed else ""))
sys.exit(1 if failed else 0)
