#!/usr/bin/env python3
"""Shader text stability: a shader's generated GLSL (and SPIR-V, and Metal) must be the same bytes
from build to build while the shader's own code is the same, whatever changes elsewhere in the
program. Browsers key their compiled-program caches by the GLSL text, so a deploy that renumbered
every shader's names would make every player's next visit compile them all again.

Builds a program, then variants of it: unrelated code added before the shaders (a function, a
global, a struct: the compiler's global numbering of functions, locals and types moves), the code
moved down some lines, another shader added before them, and a change inside one shader. Each
shader is found by its name (the `// sloppy shader:` line) in the stages the compiler dumps
(SLOPPY_GLSL_DUMP, SLOPPY_SPIRV_DUMP, and SLOPPY_MSL_DUMP with --target macos). Unchanged shaders
must be byte-identical; the changed one must differ (and only its own stage).
usage: shaderstable.py [--keep]"""
import glob, os, re, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
env.pop("DISPLAY", None)
env.pop("WAYLAND_DISPLAY", None)

# The shaders under test cover what the GLSL translation names: structs (and a struct passed
# between the stages), helper functions and their uniform specializations, locals, loops,
# temporaries of compound assignments, nested arrays (SA_ structs), a GPU buffer reader, and a
# struct holding a Texture passed as its leaves.
SHADERS = """
struct StVertex:
    pos: vec3
    uv: vec2
struct StLight:
    color: vec4
    power: f32
struct StMat:
    tex: Texture
    gain: f32
struct StU:
    mvp: mat4
    key: StLight
    fill: StLight
    mat: StMat
    data: GpuBuffer[vec4]
    grid: f32[4]
struct StOut:
    pos: vec4
    uv: vec2
    light: StLight
st_light = (l: StLight, k: f32) -> vec4:
    acc = l.color * l.power
    loop i in [0..3):
        acc += vec4(f32(i) * k)
    acc
st_cells = (x: f32) -> f32:
    cells: f32[2][2] = [[x, 1.0], [2.0, x]]
    counts: i32[4] = [0, 0, 0, 0]
    j = i32(x) & 3
    counts[j] += 2
    cells[1][0] + f32(counts[j])
st_mat = (m: StMat, uv: vec2) -> vec4: sample(m.tex, uv) * m.gain
st_vs = (v: StVertex, u: StU) -> StOut:
    p = u.mvp * vec4(v.pos, 1)
    StOut(p, v.uv * st_cells(v.pos.x), StLight(u.data[0], u.grid[1]))
st_fs = (i: StOut, u: StU) -> vec4:
    c = st_light(u.key, 0.5) + st_light(u.fill, 0.25) + st_light(i.light, 1.0)
    c * st_mat(u.mat, i.uv) * st_cells(i.uv.y)
struct OtVertex:
    pos: vec2
struct OtOut:
    pos: vec4
    t: f32
struct OtU:
    tint: vec4
ot_wave = (x: f32) -> f32:
    s = 0.0
    loop i in [0..4):
        s += sin(x * f32(i))
    s
ot_vs = (v: OtVertex, u: OtU) -> OtOut: OtOut(vec4(v.pos, 0, 1), ot_wave(v.pos.x))
ot_fs = (i: OtOut, u: OtU) -> vec4: u.tint * ot_wave(i.t)
"""

MAIN = """
st = shader(st_vs, st_fs)
ot = shader(ot_vs, ot_fs)
print("{len(st.vs) + len(st.fs) + len(ot.vs) + len(ot.fs) > 0}")
"""

# unrelated code before the shaders: shifts every global number the compiler gives
NOISE = """
struct NoiseThing:
    a: int
    b: f32
noise_global = [1, 2, 3]
noise_fn = (x: int) -> int:
    y = x * 2
    z = y + noise_global[0]
    NoiseThing(z, 1.5).a
print("{noise_fn(4)}")
"""

# another shader, before the others, sharing a struct and a helper with them
EXTRA = """
struct ExVertex:
    pos: vec3
struct ExOut:
    pos: vec4
    w: f32
ex_vs = (v: ExVertex, u: OtU) -> ExOut: ExOut(vec4(v.pos, 1), ot_wave(v.pos.y))
ex_fs = (i: ExOut, u: OtU) -> vec4: u.tint * i.w
ex = shader(ex_vs, ex_fs)
print("{len(ex.vs) > 0}")
"""

def variants():
    base = SHADERS + MAIN
    yield "base", base, set()
    yield "noise before", NOISE + base, set()
    yield "moved down", "\n# a comment\n\n\n" + base, set()
    # (the extra shader's helpers are translated first: the numbering the others get must not move)
    shaders_then = SHADERS.replace("ot_vs = ", EXTRA.split("ex = shader")[0] + "ot_vs = ")
    yield "shader added before", shaders_then + "\nex = shader(ex_vs, ex_fs)\nprint(\"{len(ex.vs) > 0}\")\n" + MAIN, set()
    # (a change inside st_fs: its fragment stage differs; its vertex stage and the other shader do not)
    yield "st_fs changed", (SHADERS + MAIN).replace("st_light(u.fill, 0.25)", "st_light(u.fill, 0.75)"), {("st_vs+st_fs", "frag")}

def build(src, d, macos):
    os.makedirs(d)
    path = os.path.join(d, "prog.jo")
    open(path, "w").write(src)
    denv = dict(env, SLOPPY_GLSL_DUMP=d)
    cmd = [sloppy, "build"]
    if macos:
        cmd += ["--target", "macos"]
        denv["SLOPPY_MSL_DUMP"] = d
    else:
        denv["SLOPPY_SPIRV_DUMP"] = d
    r = subprocess.run(cmd + [path, "-o", os.path.join(d, "prog")], env=denv, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAIL build ({'macos' if macos else 'linux'}):\n{r.stderr}\n--- program ---\n{src}")
    # each shader by its stages' names; the n-th SPIR-V or Metal pair is the n-th GLSL one
    out = {}
    n = 0
    while os.path.exists(os.path.join(d, f"{n}.vert")):
        stages = {st: open(os.path.join(d, f"{n}.{st}"), "rb").read() for st in ("vert", "frag")}
        names = [re.search(rb"// sloppy shader: (\w+)", stages[st]).group(1).decode() for st in ("vert", "frag")]
        key = "+".join(names)
        for st in ("vert", "frag"):
            out[(key, "glsl " + st)] = stages[st]
            if macos:
                mp = os.path.join(d, f"{n}.{'vs' if st == 'vert' else 'fs'}.metal")
                if os.path.exists(mp): out[(key, "metal " + st)] = open(mp, "rb").read()
            else:
                sp = os.path.join(d, f"{n}.{st}.spv")
                if os.path.exists(sp): out[(key, "spirv " + st)] = open(sp, "rb").read()
        n += 1
    return out

def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="sloppy-shaderstable-")
    failed = 0
    checks = 0
    try:
        for macos in (False, True):
            results = []
            for i, (name, src, changed) in enumerate(variants()):
                results.append((name, build(src, os.path.join(tmp, f"{'mac' if macos else 'linux'}{i}"), macos), changed))
            base = results[0][1]
            for key in ("st_vs+st_fs", "ot_vs+ot_fs"):
                if not any(k[0] == key for k in base):
                    print(f"FAIL: shader {key} not found in the dumps")
                    failed += 1
            # no build-dependent text in the GLSL: no source places, no paths
            for (key, what), text in base.items():
                if what.startswith("glsl") and re.search(rb"\.jo\b|:\d+:\d+", text):
                    print(f"FAIL: {key} {what} names a source file or place")
                    failed += 1
            for name, out, changed in results[1:]:
                for (key, what), text in base.items():
                    stage = what.split()[1]
                    other = out.get((key, what))
                    checks += 1
                    if other is None:
                        print(f"FAIL {name}: {key} {what} missing")
                        failed += 1
                    elif (key, stage) in changed:
                        if other == text:
                            print(f"FAIL {name}: {key} {what} did not change with its code")
                            failed += 1
                    elif other != text:
                        print(f"FAIL {name}: {key} {what} changed although its code did not")
                        failed += 1
    finally:
        if keep: print(f"kept {tmp}")
        else: shutil.rmtree(tmp, ignore_errors=True)
    print(f"shader text stability: {checks} comparisons, {failed} failed")
    sys.exit(1 if failed else 0)

main()
