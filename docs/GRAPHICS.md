# Graphics and the GPU

A Sloppy game is written once and draws through whichever of five renderers the machine has.
This page explains which one runs where, how your shader code reaches each of them, what is the
same and what differs between them, and the three ways of computing on the GPU.

## Portable WebGL2 shader limits

WebGL2 guarantees 256 vertex and 224 fragment uniform vectors, 15 varying vectors,
16 vertex attributes, and 16 texture units per stage (32 combined). A desktop GPU may
allow much more. Uniform packing follows GLSL ES Appendix A, not uniform-buffer
`std140` layout. `python3 tools/webglbudget.py` compiles library and example shaders
for the web and checks a conservative bound: each scalar/vector takes a whole row,
arrays include every element, and matrices take one row per column. The Linux CI test
job runs this audit.

GLSL uniforms are independent fields, declared only in stages that read them.
Read-only struct arguments to shader helpers are specialized to those fields;
copying an entire struct still reads every field. The native byte layout and the
64-joint skin palette are unchanged. GL/WebGL creates skeletal programs when the
first skinned mesh is loaded. Compile/link errors include both entry points and
sources, stage and program logs, conservative resource counts, and GPU limits.

## The five renderers

| renderer | where | used when |
|---|---|---|
| **Metal** 3 | macOS | the machine supports Metal 3 |
| **Vulkan** 1.3 | Linux, Windows | the driver has Vulkan 1.3 (current drivers for NVIDIA, AMD and Intel GPUs do) |
| **OpenGL** ES 3 | Linux, Windows | there is no usable Vulkan driver, or `SLOPPY_VULKAN=0` |
| **WebGL** 2 | the browser | a game built with `--target wasm` |
| **software** | everywhere | there is no GPU driver at all (a virtual machine, a server), or `SLOPPY_SOFTWARE=1` |

You do not choose in your program: the library picks the best one when the window opens, and
the same program runs on all five. The frame statistics overlay (`show_stats()`, or
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

## 3D cameras

`orbit_camera(target, distance)` orbits a point with a mouse drag or the right stick;
`follow_camera(distance = 6, height = 1.5)` follows a character with
`update(cam, player_pos, dt)`. Call `camera3d(cam)` before drawing the scene.
Both cameras have `invert_y` and `invert_x` fields (false by default), which reverse
vertical or horizontal mouse and right-stick look. Zoom keeps its usual direction.

While a menu is open, `update(cam, player_pos, dt, input = false)` continues target
smoothing, any supplied chase `heading`, and recovery after `pull_in`, without
reading mouse, sticks or wheel. For an orbit camera,
`update(cam, dt, input = false)` continues smoothing toward its yaw, pitch and
distance. These values can still be set by code. Skip updating to freeze everything.

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

The compiler translates `shader(vs, fs)` at compile time: to **SPIR-V** for Vulkan
(the compiler writes it itself, so no shader compiler or SDK is needed), to **GLSL ES 3.00** for
OpenGL and WebGL, to **Metal Shading Language** for Metal, and to native code, which the
software renderer calls for each vertex and
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

## An animated glTF scene

Use an uncompressed glTF 2.0 export (`.glb` is simplest), with PNG/JPEG textures. For this
example, put the Khronos sample [Fox.glb](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/Fox)
at `assets/Fox.glb`, and a small **tone-mapped, equirectangular JPEG or PNG** panorama at
`assets/sky.jpg`. Poly Haven offers CC0 panoramas; choose its tone-mapped JPG and reduce it to
1024×512 for a small game. HDR/EXR files are not read. Check each model's license: Fox's model
is CC0, but its animation and glTF conversion require CC-BY 4.0 attribution, as its README says.

```gdscript
window("Fox walk", 960, 600)
hero = load_model(embed("assets/Fox.glb"))
panorama = load_texture(embed("assets/sky.jpg"))
ground = plane_mesh(40)
hero_scale = 1.4 / max(f64(model_size(hero).y), 0.001)
pos = vec3(0, 0, 0)
facing = PI
cam = follow_camera(distance = 7, height = 0.9)
anim: Animator

# Animation names belong to the asset: inspect them before choosing one.
loop clip in hero.animations: print("{clip.name}: {clip.length} seconds")

update = (dt: f64):
    global facing
    a = input_axis()                            # WASD/arrows, left stick and d-pad
    move = flat_forward(cam) * -a.y + flat_right(cam) * a.x
    if length(move) > 0.1:
        pos += move * 3.2 * dt
        facing = atan2(move.x, move.z)           # Fox faces +Z in its own space
        anim.play(hero, "Walk", fade = 0.25)
    else: anim.play(hero, "Survey", fade = 0.25)
    anim.update(hero, dt)                        # advance once per update
    cam.update(pos, dt)                         # RMB/mouse or right stick looks around

draw = ():
    clear()
    sky_image(panorama, intensity = 0.7)
    sun(vec3(-0.5, 1, -0.3), disc = 0)           # panorama supplies the visible sky
    shadows(true)
    camera3d(cam)
    draw_mesh(ground, material = Material(base_color = rgb(0.2, 0.3, 0.18), roughness = 0.9))
    draw_model(hero, transform(pos, facing, hero_scale), pose = anim.pose(hero))
    text("WASD / left stick: walk; right mouse / right stick: look", vec2(20, 20), 20)
```

`draw_model` uses the glTF materials automatically. Assets can arrive at very different
scales: inspect `model_size(hero)`, `hero.min` and `hero.max`; the example makes Fox 1.4 units
tall. `Animator.play` keeps the current clip running when called again with its name, and
crossfades when that name changes. An asset with animated morph weights uses the same
`Animator`/`pose_at` path; [manual weights](#morph-targets) can also be set per draw.

For a split export use `load_model(embed("assets/hero.gltf"), embed_dir("assets"))`: map keys
are relative to the `.gltf` directory, including subdirectories. The loader does not read
files beside the `.gltf` automatically. `embed` and `embed_dir` put those bytes in native and
web builds alike. Check texture sizes before sharing: even a tiny model can contain several
2048×2048 images. Build with `sloppy build game.jo --target wasm`; the result is one HTML file.
See [phones](START.md#phones) for touch movement and camera controls, and
[responsive layout](LANGUAGE.md#responsive-layout) for menus and settings.

## 3D materials

`draw_mesh` keeps its sun/sky lighting and `specular` highlight unless given a `Material`.
Imported glTF models use metallic-roughness PBR, including the glTF default (metallic 1,
roughness 1). Games can use the same path:

```gdscript
copper = Material(base_color = vec4(0.95, 0.64, 0.54, 1), metallic = 1, roughness = 0.25)
draw_mesh(ball, transform(pos), material = copper)
```

`Material` holds `base_color`, `base_texture`, `metallic`, `roughness`,
`metallic_roughness`, `normal_map`, `normal_scale`, `occlusion_map`, `occlusion_strength`,
`emissive_color`, `emissive_map`, `alpha_mode`, `alpha_cutoff`, `double_sided` and `unlit`.
The glTF `KHR_materials_unlit` extension selects `unlit`. Its maps
use UV set 0 by default; `base_uv`, `metallic_roughness_uv`, `normal_uv`, `occlusion_uv` and
`emissive_uv` can select set 1. glTF's corresponding fields are loaded automatically.
Metallic-roughness textures use **G for roughness, B for metal**; occlusion uses **R**.
Normal maps use tangent space, with +Y green. `normal_scale` scales their X/Y components.
Occlusion affects ambient light, leaving direct light and emission intact.

Color factors and vertex colors are linear; base-color and emissive texture RGB are decoded
from sRGB. Other maps contain linear data. PBR shading is in linear light, followed by the
existing ACES tone map and sRGB encoding. The simple path retains its previous color handling.
`draw_mesh`'s color multiplies the material factor; its texture is used if the material has no
base texture. Its scalar `emissive` still adds base-colored light; `specular` belongs to the
simple path. Imported parts retain `color`/`texture` for inspection and use `material` for
PBR settings and their colored emission.

The BRDF is Cook-Torrance with GGX, Schlick Fresnel (dielectric F0 0.04), separable Smith
masking and Lambert diffuse reduced by Fresnel and metalness. Perceptual roughness is squared
for GGX and floored at 0.045 to keep highlights finite. The sun and up to eight point lights
use this same BRDF, with the existing point-light range fade and sun shadow map. Ambient
light uses the sky/ground colors: hemisphere diffuse, a reflected sky gradient blurred toward
its average as roughness grows, and an analytic split-sum BRDF fit. This is an inexpensive
environment approximation; it has no scene reflections or baked irradiance probes. Fog and
post effects work as before.

`AlphaMode.opaque` ignores alpha, `.mask` discards alpha below `alpha_cutoff` in both the
color and shadow passes, and `.blend` uses alpha blending without depth writes or shadows.
PBR blends sort by their bounds' distance from the camera; intersecting transparent surfaces
still need to be split by the asset author. `double_sided` renders both faces and reverses
the back face's lighting normal. Reflected transforms reverse culling; nonuniform scale uses
inverse-transpose normals.

`Vertex3D` and `SkinVertex3D` have optional `tangent` (`vec4`, XYZ along +U, W handedness)
and `uv1` fields. glTF tangents are retained and skinned with the mesh. Missing tangents are
generated using angle-weighted triangle UV derivatives, orthogonalized against the normal,
with glTF/MikkTSpace handedness; degenerate UVs get a stable perpendicular. UV/normal seams
must use distinct vertices, as exporters normally produce. This is an approximation to
MikkTSpace, not a replacement for an exporter's exact bake basis. Mesh generators and
`custom_mesh` generate frames automatically; raw `mesh(vertices, indices)` callers can use
`tangents3d(vertices, indices, uv_set = 0)` first. No shader compiler extensions are needed:
the same shader functions run through Vulkan, OpenGL, WebGL, Metal and the software renderer.

### Sky images

`sky_image(texture, intensity = 1.0, rotation = 0.0)` selects an equirectangular panorama
for the background of a 3D scene and for PBR ambient light. A 2:1 PNG or JPEG is usual;
its RGB is sRGB. +Y is at the top, -Y at the bottom, +X at the horizontal center and +Z
three quarters across. `rotation` turns the environment about +Y in radians; `intensity`
scales its linear light before tone mapping. The image stays at infinity as the camera moves.
Keep its texture alive while selected. `sky(...)` selects the original gradient again;
`hide_sky()` hides the background while retaining the selected environment's light.

Two 128×64 linear maps are cached on the first 3D pass after selecting an image: GGX
importance-sampled convolutions at roughness 0.5 and 1, with 64 directions per texel.
Reflections interpolate these and the sharp original by squared roughness. The broad map
also approximates diffuse irradiance. This gives smooth rough-metal reflections at modest
cost, without a full cubemap mip chain, BRDF lookup texture or HDR image loader. The original
sun/sky gradient remains the ambient source when no image is selected. Updating a selected
texture's pixels requires `sky_image(texture, refresh = true)` to rebuild its cached maps;
changes to rotation or intensity reuse the maps. The same render-target passes run on the
CPU renderer, Vulkan, GLES/WebGL and Metal.

### Morph targets

Imported glTF meshes support weighted `POSITION`, `NORMAL` and `TANGENT` deltas, including
sparse float deltas. Weights default to the node's `weights`, then the mesh's, then zeros.
They are neither clamped nor normalized. The deltas are blended before skinning and node
transforms, following the [glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html).
Tangent W (handedness) stays fixed. Missing base normals are rebuilt as flat normals after
blending; missing tangents are regenerated from the deformed geometry and its normal-map UV
set. Authored normal/tangent directions are normalized, with a base-frame fallback if a blend
cancels them to zero. UV/color morph deltas and sparse base/animation accessors are not read.

`Pose.weights[node][target]` controls a mesh node's morphs. For a node named `Face` with a
morph target:

```gdscript
p = rest_pose(hero)
p.weights[find_node(hero, "Face")][0] = 0.7
draw_model(hero, pose = p)
```

`pose_at`, `blend_poses` and `Animator` also blend the weights. Morph-weight animations support
STEP, LINEAR and CUBICSPLINE, including Hermite slopes scaled by the key interval. Existing
TRS cubic channels retain the loader's linear-key approximation. `read_gltf` exposes each
`MeshData.targets`; `morph_vertices(mesh_data, weights)` returns blended CPU vertices without
changing the source, for collision or other tools.

Blending is on the CPU, with source data retained only for parts that have targets
(`ModelPart.morph`). Its cost scales with mesh size and active targets. Each queued draw
keeps its own vertices and bounds, including the current skin. Vertex data is streamed just
before each shadow or color draw, so several instances of the same model can have different
weights in one frame. The GPU backends retain each streamed address until its frame finishes;
the software renderer consumes each draw immediately. This uses the same shaders and buffer
API on all five renderers.

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
