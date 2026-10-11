#!/usr/bin/env python3
"""Draw every program with a window through OpenGL and through Vulkan and compare the frames:
the examples, the library's examples (docs/api) and the tutorials' steps. Prints the mean
absolute difference of each (0..255, at a quarter of the size) and writes both frames and
an HTML page that shows them side by side to build/vkcompare/.
usage: vkcompare.py [--frames N] [name...]   (needs a display and a GPU)"""
import glob, html, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pngutil import downsample

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.join(root, "bin", "sloppy")
out = os.path.join(root, "build", "vkcompare")
os.makedirs(out, exist_ok=True)
args = sys.argv[1:]
frames = "60"
if "--frames" in args:
    i = args.index("--frames")
    frames = args[i + 1]
    del args[i:i + 2]

programs = {}
for f in sorted(glob.glob(os.path.join(root, "examples", "*.jo")) + glob.glob(os.path.join(root, "examples", "*", "*.jo")) + glob.glob(os.path.join(root, "docs", "api", "*.jo"))):
    src = open(f, encoding="utf-8").read()
    if re.search(r"^draw\s*=", src, re.M):
        programs[os.path.relpath(f, root).replace(os.sep, "_")[:-3]] = f
tmp = tempfile.mkdtemp(prefix="sloppy-vkcompare-")
for tut in sorted(glob.glob(os.path.join(root, "docs", "TUTORIAL*.md"))):
    tname = os.path.basename(tut)[:-3].lower()
    for k, code in enumerate(re.findall(r"```gdscript\n(# step.*?)```", open(tut, encoding="utf-8").read(), re.S)):
        src = os.path.join(tmp, f"{tname}_step{k + 1}.jo")
        open(src, "w", encoding="utf-8").write(code)
        programs[f"{tname}_step{k + 1}"] = src
if args: programs = {k: v for k, v in programs.items() if any(a in k for a in args)}

rows = []
for name, src in programs.items():
    exe = os.path.join(tmp, name)
    r = subprocess.run([sloppy, "build", src, "-o", exe], capture_output=True, text=True, cwd=os.path.dirname(src))
    if r.returncode != 0:
        print(f"build failed {name}: {r.stderr[:300]}")
        continue
    shots = {}
    for label, vk in (("gl", "0"), ("vk", "1")):
        png = os.path.join(out, f"{name}_{label}.png")
        if os.path.exists(png): os.remove(png)
        env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), SLOPPY_FRAMES=frames, SLOPPY_SCREENSHOT=png,
                   SLOPPY_WINDOW="960x540", SLOPPY_SCALE="1", SLOPPY_VULKAN=vk)
        r = subprocess.run([exe], env=env, capture_output=True, text=True, timeout=120, cwd=os.path.dirname(src))
        if r.returncode != 0 or not os.path.exists(png):
            print(f"{label} failed {name}: {r.stderr[-500:]}")
            break
        if vk == "1" and "using OpenGL" in r.stderr: print(f"note {name}: {r.stderr.strip()[:200]}")
        shots[label] = downsample(png, 4)
    if len(shots) < 2: continue
    (w, h, a), (w2, h2, b) = shots["gl"], shots["vk"]
    d = 255.0 if (w, h) != (w2, h2) else sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    rows.append((d, name))
    print(f"{d:7.3f}  {name}", flush=True)

rows.sort(reverse=True)
page = ["<!doctype html><meta charset=utf-8><title>OpenGL and Vulkan</title><style>body{font:14px sans-serif;background:#222;color:#ddd}img{width:480px}td{vertical-align:top}</style><table>"]
for d, name in rows:
    page.append(f"<tr><td>{html.escape(name)}<br>{d:.3f}</td><td><img src='{name}_gl.png'><br>OpenGL</td><td><img src='{name}_vk.png'><br>Vulkan</td></tr>")
open(os.path.join(out, "index.html"), "w").write("\n".join(page) + "</table>")
print(f"{len(rows)} programs; build/vkcompare/index.html")
