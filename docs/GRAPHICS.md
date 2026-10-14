# Graphics and the GPU

A Sloppy game is written once and draws through whichever of four renderers the machine has.
This page explains which one runs where, how your shader code reaches each of them, what is the
same and what differs between them, and the three ways of computing on the GPU.

## The four renderers

| renderer | where | used when |
|---|---|---|
| **Vulkan** 1.3 | Linux, Windows | the driver has Vulkan 1.3 (current drivers for NVIDIA, AMD and Intel GPUs do) |
| **OpenGL** ES 3 | Linux, Windows | there is no usable Vulkan driver, or `SLOPPY_VULKAN=0` |
| **WebGL** 2 | the browser | a game built with `--target wasm` |
| **software** | everywhere | there is no GPU driver at all (a virtual machine, a server), or `SLOPPY_SOFTWARE=1` |

You do not choose in your program: the library picks the best one when the window opens, and
the same program runs on all four. The frame statistics overlay (`show_stats()`, or
`SLOPPY_STATS=1`) shows which is in use, e.g. `vulkan (NVIDIA GeForce GTX 1070)`, and
`soft_rendering()` tells the program when it is the software renderer (to draw fewer particles,
say).

**Why Vulkan first.** Vulkan lets the library work the way current GPUs work best, after Mason
Remaley's mr_gpu: every texture is in one bindless array, buffers are read by their address,
shaders fetch their own vertices, frames are recorded without render-pass objects, and each
frame's data goes into one block of upload memory. The CPU does less work per draw (Breakwater
spends 2.0 ms of CPU time per frame instead of 2.8 with OpenGL), and the GPU can decide what to
draw itself (`draw_indirect`, below).

**Why OpenGL stays.** Older drivers, some virtual machines and remote desktops have OpenGL but
no Vulkan 1.3, and the web has WebGL, which is OpenGL ES. The library's OpenGL path and its
Vulkan path draw the same frames: the render tests compare them pixel by pixel.

**Why a software renderer.** So a game always runs: on a server, in CI, in a VM without 3D
acceleration. It draws at half resolution by default (`SLOPPY_SOFT_SCALE=1` for full) and runs
your shader functions natively on the CPU.

## Shaders are Sloppy functions

A shader is a pair of ordinary functions: a vertex function and a fragment function.

```gdscript
struct V:                     # what each vertex holds
    pos: vec3
struct U:                     # the uniforms: one value for the whole draw
    mvp: mat4
    tint: vec4
struct O:                     # what the vertex function gives each fragment (pos first)
    pos: vec4
    shade: f32

vs = (v: V, u: U) -> O: O(u.mvp * vec4(v.pos, 1), v.pos.y)
fs = (i: O, u: U) -> vec4: vec4(u.tint.xyz * (0.6 + 0.4 * i.shade), 1)

sh = make_shader(shader(vs, fs))
m = mesh([V(vec3(-1, -1, 0)), V(vec3(1, -1, 0)), V(vec3(0, 1, 0))])
draw = ():
    clear()
    draw(sh, m, U(mat4(), vec4(1, 0.5, 0.2, 1)))
```

The compiler translates `shader(vs, fs)` three ways at compile time: to **SPIR-V** for Vulkan
(the compiler writes it itself, so no shader compiler or SDK is needed), to **GLSL ES 3.00** for
OpenGL and WebGL, and to native code, which the software renderer calls for each vertex and
pixel. Helper functions the shader calls are translated with it. A shader cannot allocate:
strings, growable arrays, maps and closures are compile errors in shader code; numbers, bools,
vectors, `mat4`, structs, fixed-size arrays (`f32[4]`, also `f32[4][4]`) and `Texture` are
fine.

**The same results everywhere.** Shader code follows the CPU's rules for numbers: integer
types wrap at their size, unsigned division, remainders, shifts, comparisons and `min`/`max`
are unsigned, `%` keeps the dividend's sign, float to integer conversions saturate, a compound
assignment computes its target once. The backends are checked against each other by
`tools/gpufuzz.py`, which draws random shader code with all three and requires identical pixels.

**What differs.** GPU arithmetic is 32-bit: in shader code an `int` (and `i64`, `u64`) wraps
at 32 bits and an `f64` is an `f32`. Use `i32`, `u32` and `f32` in shaders and the CPU (the
software renderer) gives the same answers. Functions such as `sin`, `exp` and `pow` may differ
in the last bits between GPUs, as they do in every graphics API.

**Effects on 2D drawing.** A fragment function of your own can run for everything 2D drawing
draws (sprites, shapes, text), as LÖVE's `setShader`: make it with the library's vertex
function, `fx = make_shader(shader(effect_vs, my_fs))`, then `use_effect(fx, params)` before
the drawing and `no_effect()` after (effects end with the frame). The fragment function takes a
`Pixel2D` (`pos`, `uv`, `color`) and an `Effect2D[P]` whose `params` are yours; `base_color(p, u)`
is the color the pixel would have had:

```gdscript
gray_fs = (p: Pixel2D, u: Effect2D[f32]) -> vec4:
    c = base_color(p, u)
    g = dot(c.xyz, vec3(0.3, 0.59, 0.11))
    vec4(mix(c.xyz, vec3(g, g, g), u.params), c.w)
gray = make_shader(shader(effect_vs, gray_fs))
...
use_effect(gray, f32(1.0))
sprite(enemy, pos)
no_effect()
```

## Computing on the GPU

There are three levels, from the simplest to the most control. All three also run without a
GPU (on the CPU's cores, or in the browser), so a program never needs a fallback of its own.

**GPU arrays** are for numeric work written as array expressions. `gpu(xs)` uploads, a dotted
expression becomes one GPU program, and `cpu(g)` downloads:

```gdscript
g = gpu(rand(4_000_000))
h = sin.(g) .* 0.5 .+ g           # one GPU program, made at compile time
print(sum(h), max(h))             # reductions run on the GPU too
```

**GPU buffers and compute functions** keep your own structs on the GPU and change them there.
A compute function is written like a shader and runs once per element:

```gdscript
struct Bug:
    pos: vec2
    vel: vec2
struct Step:
    bugs: GpuBuffer[Bug]
    dt: f32

step = (id: int, u: Step): u.bugs[id].pos += u.bugs[id].vel * u.dt

bugs = gpu_buffer(start_bugs)       # upload (start_bugs: a Bug[] made on the CPU)
stepper = compute(step)
update = (dt: f64): dispatch(stepper, len(bugs), Step(bugs, f32(dt)))
```

Shaders read buffers among their uniforms (`u.bugs[instance_id()]`), so thousands of objects
can be moved and drawn without coming back to the CPU. A compute function over a grid takes
`id: ivec2` or `id: ivec3` (`dispatch(k, ivec2(w, h), params)`). Atomics (`atomic_add`,
`atomic_min`...) let many invocations change one element. `draw_indirect` draws as many
instances as a compute function decided, and `draw_indirect_count` takes the number of draws
from a buffer too: culling and spawning can happen entirely on the GPU. Barriers between
dispatches and draws are automatic.

**Subgroup operations** combine values across the invocations a GPU runs together
(`subgroup_add`, `subgroup_exclusive_add`, `subgroup_min`, `subgroup_elect`,
`subgroup_broadcast_first`...). A subgroup is 32 invocations on NVIDIA, 64 on some AMD GPUs and
1 on the CPU, so code written for any size (the usual case: one atomic per subgroup instead of
one per element) gives the same results everywhere.

Where these run: through Vulkan, buffers are GPU memory and compute functions are compute
programs (SPIR-V, made by the compiler). With OpenGL, WebGL or the software renderer, buffers
are CPU memory and compute functions run on all CPU cores; shaders still read the buffers.
`gpu_compute()` tells which.

## Switches and troubleshooting

| setting | effect |
|---|---|
| `SLOPPY_VULKAN=0` | use OpenGL even where Vulkan works (`=1`: Vulkan, also for tests without a window) |
| `SLOPPY_SOFTWARE=1` | use the software renderer; `SLOPPY_SOFT_SCALE=1` draws it at full resolution |
| `SLOPPY_NO_GPU=1` | GPU arrays and compute functions run on the CPU |
| `SLOPPY_VK_DEVICE=n` | use the nth Vulkan device (e.g. Mesa's software driver, for testing) |
| `SLOPPY_VK_VALIDATE=1` | turn on the Khronos validation layer, where it is installed |
| `SLOPPY_VK_PIPELINE_CACHE=0` | do not keep pipelines between runs |
| `SLOPPY_STATS=1` | show frame times and the renderer in use (`?stats` on a web page) |

- **Which renderer did I get, and why not Vulkan?** `SLOPPY_VK_VALIDATE=1` prints the Vulkan
  device chosen; a game that falls back to OpenGL prints why Vulkan could not be used (no
  Vulkan 1.3 driver, a missing feature) when `SLOPPY_VULKAN=1` asks for it.
- **The first run of a game starts slower than later ones.** With Vulkan, the driver builds a
  pipeline for each shader and state the first time they are drawn; the library keeps them in
  `~/.cache/sloppy` (`%LOCALAPPDATA%\sloppy` on Windows), so later runs start drawing at once.
- **A shader compiles but draws differently on one renderer.** That is a bug in Sloppy: please
  report it with the program. `SLOPPY_VULKAN=0` and `SLOPPY_SOFTWARE=1` let you compare the
  three on one machine.
