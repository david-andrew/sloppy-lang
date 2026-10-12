# Changelog

## Unreleased

- **Linux on arm64** (`--target linux-arm64`, the default when the compiler runs on arm64): a
  new code generator (compiler/arm64.jo), x86-64 system call numbers translated for arm64, C
  libraries loaded through arm64's ld.so, crash backtraces from arm64's registers. Every test
  passes there, and the compiler compiles itself on arm64 to the same bytes; CI runs the tests on
  an arm64 machine. Not yet: register allocation (values live in the frame, so the code is
  slower), the interactive prompt and `sloppy watch`. This is the first step toward macOS.
- `ARCH` (`"x86_64"`, `"arm64"` or `"wasm32"`) beside `TARGET`, for `when`.
- Shaders: the smallest integer `/ -1` (and `% -1`) and `abs` of the smallest integer give
  what the CPU gives (itself, 0, itself); GLSL and SPIR-V leave them undefined, and Intel's
  OpenGL driver gave other values. Found by tools/gpufuzz.py on an Intel UHD 620, where every
  test and render test now passes with Vulkan and OpenGL.
- Web games take touch: the first finger is the mouse with its left button held, so dragging
  moves it (Rebound's shield follows a finger; before, only the first touch registered), and the
  page no longer scrolls or zooms under the game.
- A new docs page, **Graphics and the GPU** (docs/GRAPHICS.md): the four renderers and when each
  runs, how shader functions reach each of them, what is the same and what differs, the three
  ways of computing on the GPU, and the switches for choosing and troubleshooting.
- `ivec3` and `ivec4` (i32 vectors, as `ivec2`), and compute functions over a 3D grid:
  `f(id: ivec3, params)` with `dispatch(compute(f), ivec3(w, h, d), params)` (groups of 4 by 4 by
  4 on the GPU).
- Shaders on OpenGL and the web: integer `+ - *` wrap on overflow as on the CPU (they are
  written through unsigned numbers; NVIDIA's GLSL compiler assumed signed results never
  overflow and simplified hash-like code wrongly). Found by tools/gpufuzz.py.

## 0.6.0

Graphics:
- **Vulkan.** Games draw through Vulkan 1.3 on Linux and Windows where the driver has it
  (OpenGL otherwise, or with `SLOPPY_VULKAN=0`), set up as current GPUs work best (after Mason
  Remaley's mr_gpu): every texture in one bindless array, buffers read by address, vertices
  fetched by the shader, dynamic rendering, per-frame upload memory, memory in large blocks.
  Frames are the same as with OpenGL; the CPU's time per frame is lower (Breakwater: 2.0 ms
  instead of 2.8). `SLOPPY_VK_VALIDATE=1` turns on the Khronos validation layer.
- The compiler turns shader functions into SPIR-V itself (as well as GLSL), so no shader
  compiler is needed; tools/spirvtest.py checks every module.
- Pipelines are kept between runs (a cache per program in `~/.cache/sloppy`, checked against
  the device and a hash): Breakwater's take 1-10 ms to make at start instead of 70 on NVIDIA.
  `SLOPPY_VK_PIPELINE_CACHE=0` leaves it out.
- **GPU buffers and compute functions** (lib/game/gpubuffer.jo): `gpu_buffer(xs)` keeps an array
  of plain data (numbers, bools, vectors and structs of them) on the GPU; a compute function
  `f(id: int, params)`, written in Sloppy, runs once per element with
  `dispatch(compute(f), n, params)`, reading and writing buffers by index (`u.bugs[id] = b`,
  `u.bugs[id].pos += v`), with atomics (`atomic_add`, `atomic_min`, `atomic_compare_exchange`...).
  Over a grid, `f(id: ivec2, params)` runs once per cell: `dispatch(k, ivec2(w, h), params)`.
  Shaders read buffers among their uniforms; buffers can be a mesh's vertices (`gpu_mesh`) or a
  draw's instances; `draw_indirect` draws as many as a compute function decided (`DrawArgs`),
  and `draw_indirect_count` takes how many draws there are from a buffer too. Compute
  functions can read textures. Barriers are automatic. Without Vulkan, buffers are CPU memory
  and compute functions run on every core, so the same program works with OpenGL, the software
  renderer and on the web.
- Subgroup operations in compute functions (`subgroup_add`, `subgroup_inclusive_add`,
  `subgroup_exclusive_add`, `subgroup_min`, `subgroup_max`, `subgroup_and/or/xor`,
  `subgroup_any/all`, `subgroup_elect`, `subgroup_broadcast_first`, `subgroup_size`): across the
  invocations the GPU runs together (32 on NVIDIA), 1 at a time on the CPU, so programs written
  for any size give the same results everywhere.
- GPU arrays run as Vulkan compute programs (with no window too), their `sum`, `min` and `max`
  on the GPU as with OpenGL.
- Shaders and compute functions follow the CPU's rules for numbers: unsigned division,
  remainders, shifts, comparisons, `min`, `max` and `clamp`; narrow integer types wrapping (`abs`
  too); float to integer conversions saturating; shifts by 32 or more; every compound
  assignment (`%=`, `>>=`, `and=`...) with its target and indexes computed once, before the
  right side; `ivec2(vec2(...))` converting each component; `i32(bool)`. (GPU arithmetic stays
  32-bit.)
- Arrays of arrays (`f32[2][3]`) work in shaders on OpenGL and the web (GLSL ES has none: they
  are kept in structs there). `fwidth()` in fragment shaders.
- Fixes: `-(-1.5)` in a shader broke GLSL (it read `--`); `mat4` takes integer vectors among
  its parts; a texture deleted, made again or given other sampling after a draw that uses it no
  longer changes that draw, and things released between frames wait for the frame that may
  still use them; a user struct named Texture is plain data.

Language:
- Type arguments at a call: `zero[int]()`, `gpu_buffer[Bug](100)`, `empty[str[]]()` (`T[]`
  written inside the brackets is the array type).
- `b[i].f = v` and `b[i].f += v` for types defining `[]` and `[]=` (a GpuBuffer, in compute
  functions too): the element is read, changed and written back. `b[f(x)] += v` computes the
  index once.
- `min`, `max`, `clamp` (and `abs` for signed ones) keep an integer type: `min(x, 5)` with
  `x: i32` is an `i32`, `max(a, b)` of two `u8` a `u8` (mixed types still take `int`'s). Ties
  between the library's overloads go to the one more arguments match exactly.
- Integer literals must fit: `x: u64 = -1` is an error like `x: u32 = -1`, as is a literal
  above 64 bits. Overloads rank integer types before `f64` before `f32` (`choose(-1)` with
  `u64` and `f64` overloads takes `f64`; it was ambiguous), and leave out what a call cannot
  match (`f(300)` with `f(x: i8)` and `f(x: i16)` is the `i16` one).
- Float to integer conversions saturate at the range of the type converted to (`u8(300.0)` is
  255, `i8(-200.0)` is -128, `u64(-1.0)` is 0); before, only `int` did. Signed division wraps
  like the rest of integer arithmetic (the smallest integer `/ -1` is itself, `% -1` is 0;
  native programs used to stop). `x %= y` on floats is `x % y`.
- Generic types are also worked out from what the result must be: `x: int = make((v): v + 1)`
  types the lambda's `v`, `f: () -> int = zero` picks `zero[int]`, and a lambda returning a
  member of a generic union makes that member. A generic function that expands without end
  stops with an error (found by its chain of instantiations: deep finite types and many
  instances are fine).
- `match` narrows a field (`match b.x:`) or a global in each arm, as it does a local variable;
  a closure using a name narrowed by `is` captures the variable itself, so it sees later
  changes and may assign it.

Memory safety and data races (from reviews of the compiler):
- An argument read from a global, a variable closures share, a capture, a `g!`, an operand of
  string or array `+` and `==`, or a part of `"...{x}..."` stays alive through the call, even
  if the callee (or a later argument) gives its variable another value; it used to be freed
  under the callee. (Where the callee cannot change that global, no reference is taken.)
- An element passed as `mut` (`hit(enemies[i])`) is written where it is, so while the call runs
  nothing may move or share its array: the same call can no longer also be given the array
  (`attach(nodes[0], nodes)`) or an element inside it, nor can a global array the function
  changes; the compiler says so. Where the function may call a function value that could
  resize the array, the element is passed as a copy and written back after the call.
- The data race check of `parallel_map` and the others covers partial applications
  (`f(k, _)`), calls of function values inside the function, `__fmt` functions and narrowed
  globals; a function kept in a variable is refused, since the compiler cannot see which it is.
  A function handing the function it is given on to them is marked `@parallel`, and such
  functions can only be called directly.
- On the CPU, negating an integer vector gave wrong components (it went through floats), and
  swizzles out of order (`v.zx`) read and wrote the wrong components (assigning one wrote past
  the vector). A swizzle naming a component twice cannot be assigned to (`v.xx = ...`).

Other fixes:
- Maps: keys that are unions, optionals or arrays work (they hashed wrongly), `-0.0` and `0.0`
  are one key as they are equal, and `remove` keeps the other entries in insertion order.
- Windows: a float given to a C function among its first four arguments also goes in the
  integer register (as varargs functions like `sprintf` read it); a @cabi function called from
  C may take more than four arguments; @cabi functions sign-extend narrow integers C passes.
- Editor: an unsaved change to a file is seen at once in the other open files that use it, and
  references across files follow a used file as it is opened and closed.

Tools:
- tools/gpufuzz.py: random compute functions run on the CPU, the GPU and lavapipe, and random
  fragment shaders drawn by the software renderer, OpenGL and Vulkan, must agree (`--reduce`
  shrinks a failure).

Website and install:
- The website works on phones: the top links fold into a menu, and a docs page's contents into
  a bar under the title. The pages are grouped (start, tutorials, reference), with previous and
  next links at the bottom.
- The install command shown is the one for your system (Linux, Windows; on a Mac, the
  playground), with a copy button. A new **Getting started** page (docs/START.md): installing, a
  first program and game, sharing it, editors.
- The Linux installer links `sloppy` into `~/.local/bin` when that is on the PATH (as on most
  systems), so the command works in the same terminal at once.
- **The library page, by topic** (arrays, strings, the window and input, 2D, 3D, sound...),
  each with a whole program to run in the playground (docs/api/; the tests build them), every
  function with its description, a search box (`?q=` links to a search), and the built-in
  functions (`print`, `push`, `pop`, `fill`, `embed`...), which were missing.

## 0.5.0

Games:
- **Breakwater** (examples/breakwater), a first-person shooter in one file: hold a platform at
  sea against waves of robots, with a shield that recharges, two weapons at a time (a pistol, a
  rifle, a shotgun, rockets, the robots' casters), grenades and melee; animated glTF robots and
  weapons by Quaternius (CC0). Play it at sloppy-lang.org/breakwater, or change it in the
  playground.
- A third tutorial, **Make a 3D shooter**: a small Breakwater in eight steps
  (docs/TUTORIAL_BREAKWATER.md): mouse look, cover, shots as rays, drones that fire back, waves.
- **Lowline** (examples/lowline): a glider down an endless valley, scoring for flying low.
- The playground keeps each game's files (icon, models) apart, and fetches large ones only when
  that game is chosen.

Library and language:
- **Controls players can change**: `action("jump", [.key(.space), .button(.a)])`, then
  `action_pressed("jump")`, `action_axis("left", "right")`...; `ui_controls()` in a menu lets the
  player rebind each action (press the new key or button), and the bindings are saved. Rebound
  has a Controls page. An array of shorthand values (`[.key(.space)]`) now takes its type from
  the parameter it is passed to. A long list of actions scrolls to fit the screen.
- **Several gamepads**: up to eight, each by its number (`gamepad_down(1, .a)`, `left_stick(1)`,
  `gamepads()`); without a number, any of them. Flight sticks and wheels: `joystick_button` and
  `joystick_axis` give a device's own inputs.
- **3D models**: `load_model` reads glTF 2.0 (.glb, or .gltf with its files): meshes placed by
  the scene's nodes, base colors, PNG and JPEG textures, vertex colors; `draw_model` draws one.
  `read_gltf` gives the model's data without the GPU (for collision, or to change it).
- **Animated models**: glTF skins (up to 64 joints, bent on the GPU) and their animations.
  `pose_at(model, find_animation(model, "Run"), time)` gives a pose (Blender's "Armature|Run"
  is found as "Run"), `blend_poses` fades from one to another, `turn_node` bends a joint (a
  spine aiming up), `node_transform` says where a joint is (to put a weapon in a hand);
  `draw_model(m, transform, pose = p)`. `draw_model` also takes `in_front` (a first-person
  weapon model).
- **JPEG**: `load_jpeg`, and `load_image`/`load_texture` read JPEG as well as PNG (baseline and
  progressive, any color sampling, grayscale, CMYK).
- 3D draws the camera cannot see are left out (meshes know their bounding sphere).
- **Paths over a grid** (lib/game/paths.jo): mark cells open or blocked, then `path_step(grid,
  from, to)` gives the next point to walk to round the walls (and `path_distance`): for enemies
  in 2D (tiles) or 3D (the ground's x and z).
- **Point lights** in 3D: `point_light(pos, color, radius)` for a frame (muzzle flashes, glowing
  shots, lamps); up to 8 light a frame, the ones nearest the camera.
- One mesh from many shapes: `add_box`, `add_cylinder` and `add_sphere` add a shape's vertices
  to an array (placed by a transform, in a color) for `custom_mesh`: a level or a robot drawn in
  one call. `draw_mesh(..., in_front = true)` draws over everything else (a first-person
  weapon that would poke into walls).
- Cameras for 3D: `orbit_camera` (drag to turn, the wheel to zoom) and `fly_camera` (WASD and
  the mouse), with gamepad sticks too; `camera3d(cam)` uses one.
- **Debugging on Windows**: `sloppy build` writes a PDB beside the program, and programs have
  unwind tables, so Visual Studio, WinDbg and RemedyBG show Sloppy functions, lines and call
  stacks (break at a function or a line, step through the source).
- The build block's `icon` is the window's icon on Linux too (X11); `PROGRAM_ICON` has its bytes.
- **The interactive prompt on Windows** (`sloppy` with no file), as on Linux: an input that has
  errors, panics, crashes or is stopped with ctrl-c leaves everything as it was before it.
- **Music that plays while it decodes**: `load_music` and `play_music` (Ogg Vorbis), for long
  tracks: no wait when they load, and little memory (`load_ogg` still decodes a sound whole).
- **Fonts**: `load_font` reads TrueType fonts (.ttf, .ttc) into sharp text at any size;
  `set_font` chooses the one `text` draws with. Text is UTF-8 now: accented letters, quotes,
  dashes and the euro sign in loaded fonts (characters a font lacks show as ?).
- A function that assigns a global declared further down its file gets a warning (it changes
  that global; `let x = ...` makes the function's own). A top-level `x = 0` now runs where it
  is, like other initializers.

## 0.4.0

Games:
- **Rebound** (examples/rebound) is the example game now, in place of Lumen: a one-file arcade
  game where you turn a shield to catch turrets' bolts and send them back (chain blasts, bank
  shots, upgrades, a saved best score). Play it at sloppy-lang.org/rebound, or change it in the
  playground.
- A second tutorial, **Make an arcade game**: a small Rebound in eight steps (docs/TUTORIAL_REBOUND.md).
- **Ogg Vorbis**: `load_ogg` (music at a tenth of the size of WAV).
- **Sprite sheets and animations**: `sprite_sheet`, `animation`, `draw_anim`, and
  `load_aseprite` for Aseprite's JSON with its tags.
- **Tilemaps**: from text (`tile_layer`) or Tiled's JSON (`load_tiled`), drawn by what is on
  screen (`draw_tilemap`), with `tilemap_move` for boxes that stop at walls and floors
  (examples/tiles.jo).
- **JSON** (`parse_json`, `to_json`, and `get`/`at`/`as_*` that chain) and **base64**.
- Menus ignore input in the frame they open, so the key that opened one does not also work it
  (`ui_ready()` for a game's own keys).
- `arc` (part of a ring) and `melody_loop` (music that loops without a seam).
- The playground opens an example by link (`#example=rebound`) and has the files examples use,
  like icons.

Language:
- At the top level, assigning to a variable of a `use`d module (or the library's, like
  `ui_style`) changes it, as in a function; before, it quietly made a new variable.
- Enums are members of unions like other types (`E | str` could not hold an `E`), and `.v` and
  `.v(args)` work as arguments, also for a union parameter.
- A function literal in a call's arguments works in an `if`/`loop` header
  (`if xs.any((x): x > 2): ...`).

## 0.3.1

Windows: `sloppy watch`, crash reports, the software renderer. Saving (`save_data`), menus
(lib/game/ui.jo), program icons, itch.io zips, the first tutorial, and correctness fixes from an
outside review. Earlier versions: the GitHub releases page.
