#!/usr/bin/env python3
"""Build the Sloppy playground: one self-contained web page with the compiler (compiled to
WebAssembly by itself), the standard library and examples. The page compiles and runs programs
on its own (open it from disk, or serve it anywhere).
usage: tools/playground.py [output.html]        (default: build/playground.html)"""
import base64, gzip, json, os, re, shutil, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "build", "playground.html")
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
sloppy = os.path.join(root, "bin", "sloppy")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))

# the compiler, as WebAssembly (it builds as a web page: take the module out of it)
tmp = os.path.join(root, "build", "playground-compiler")
subprocess.run([sloppy, "build", os.path.join(root, "compiler", "main.jo"), "--target", "wasm", "-o", tmp], check=True, env=env)
page = open(tmp + ".html").read()
wasm = base64.b64decode(re.search(r'const SLOPPY_WASM = "([^"]*)"', page).group(1))
os.remove(tmp + ".html")
gz = lambda b: base64.b64encode(gzip.compress(b, 9)).decode()

# the standard library, at /sloppy/lib
lib = {}
for d, _, names in os.walk(os.path.join(root, "lib")):
    for n in sorted(names):
        full = os.path.join(d, n)
        lib["/sloppy/lib/" + os.path.relpath(full, os.path.join(root, "lib"))] = base64.b64encode(open(full, "rb").read()).decode()

# examples: the playground's own, then the repository's games
examples = {}
exdir = os.path.join(root, "tools", "playground", "examples")
for n in sorted(os.listdir(exdir)):
    if n.endswith(".jo"):
        examples[re.sub(r"^\d+-", "", n[:-3])] = open(os.path.join(exdir, n)).read()
# (a game's other files, like its icon and models, go beside the program the playground compiles:
# in the page if they are small, else in files/<game>/ beside it, fetched when the game is chosen)
game_files = {}
for name, path in [("rebound (2D game)", "examples/rebound/rebound.jo"), ("breakwater (3D game)", "examples/breakwater/breakwater.jo"),
                   ("shapes (2D)", "examples/shapes.jo"), ("tiles (2D)", "examples/tiles.jo"),
                   ("cube (3D)", "examples/cube.jo"), ("scene (3D)", "examples/scene3d.jo"), ("dunes (3D game)", "examples/dunes/dunes.jo"),
                   ("lowline (3D game)", "examples/lowline/lowline.jo"),
                   ("arcade (sloppy new template)", "lib/new/arcade.jo"), ("firstperson (sloppy new template)", "lib/new/3d.jo")]:
    full = os.path.join(root, path)
    if not os.path.exists(full): continue
    examples[name] = open(full).read().replace("__TITLE__", name.split(" ")[0].title()).replace("__NAME__", name.split(" ")[0])
    if path.startswith("lib/"): continue
    d = os.path.dirname(full)
    if d == os.path.join(root, "examples"): continue
    names = [n for n in sorted(os.listdir(d)) if not n.endswith(".jo")]
    if not names: continue
    if sum(os.path.getsize(os.path.join(d, n)) for n in names) <= 200_000:
        game_files[name] = {"inline": {n: base64.b64encode(open(os.path.join(d, n), "rb").read()).decode() for n in names}}
    else:
        game = os.path.basename(d)
        to = os.path.join(os.path.dirname(os.path.abspath(out)), "files", game)
        os.makedirs(to, exist_ok=True)
        for n in names: shutil.copy(os.path.join(d, n), to)
        game_files[name] = {"fetch": "files/" + game + "/", "names": names}

html = open(os.path.join(root, "tools", "playground", "page.html")).read()
host = open(os.path.join(root, "tools", "playground", "host.js")).read()
html = html.replace('"/*SLOPPY_COMPILER*/"', json.dumps(gz(wasm)))
html = html.replace('"/*SLOPPY_LIB*/"', json.dumps(gz(json.dumps(lib).encode())))
html = html.replace("/*SLOPPY_EXAMPLES*/", json.dumps(examples).replace("</", "<\\/"))
html = html.replace("/*SLOPPY_GAME_FILES*/", json.dumps(game_files))
html = html.replace("/*SLOPPY_HOST*/", host)
html = html.replace("/*SLOPPY_HIGHLIGHT*/", open(os.path.join(root, "tools", "playground", "highlight.js")).read())
open(out, "w").write(html)
print(f"{out}: {len(html) // 1024} KB (compiler {len(wasm) // 1024} KB of WebAssembly)")
