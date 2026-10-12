# Changelog

## Unreleased

Graphics:
- GPU arrays' `sum`, `min` and `max` run on the GPU with Vulkan too (a compute function in the
  library; they read every value back before), giving the same sums as with OpenGL.
- Shaders: `-(-1.5)` no longer breaks GLSL (it read `--`); unsigned `min`/`max`/`clamp`
  compare as unsigned, and `abs` of a narrow integer wraps, as on the CPU.
- tools/gpufuzz.py: random compute functions run on the CPU, the GPU and lavapipe, and random
  fragment shaders drawn by the software renderer, OpenGL and Vulkan, must agree.
- Vulkan pipelines are kept between runs (a pipeline cache per program in `~/.cache/sloppy`,
  checked against the device and a hash): Breakwater's take 1-10 ms to make at start instead of
  70 on NVIDIA. `SLOPPY_VK_PIPELINE_CACHE=0` leaves it out.
- Subgroup operations in compute functions (`subgroup_add`, `subgroup_inclusive_add`,
  `subgroup_exclusive_add`, `subgroup_min`, `subgroup_max`, `subgroup_and/or/xor`,
  `subgroup_any/all`, `subgroup_elect`, `subgroup_broadcast_first`, `subgroup_size`): across the
  invocations the GPU runs together, 1 at a time on the CPU, so programs written for any size
  give the same results everywhere.
- Compute functions over a grid: `f(id: ivec2, params)` with `dispatch(compute(f), ivec2(w, h),
  params)` (groups of 8 by 8 on the GPU; rows on every core without Vulkan).
- `draw_indirect_count`: the number of indirect draws read from a buffer a compute function
  fills (vkCmdDrawIndexedIndirectCount; read back where the device lacks it, and on the CPU
  without Vulkan).
- Arrays of arrays (`f32[2][3]`) work in shaders on OpenGL and the web too (GLSL ES has none: they
  are kept in structs there).
- **Vulkan.** Games draw through Vulkan 1.3 on Linux and Windows where the driver has it
  (OpenGL otherwise, or with `SLOPPY_VULKAN=0`), set up as current GPUs work best (after Mason
  Remaley's mr_gpu): every texture in one bindless array, buffers read by address, vertices
  fetched by the shader, dynamic rendering, per-frame upload memory, memory in large blocks.
  Frames are the same as with OpenGL; the CPU's time per frame is lower (Breakwater: 2.0 ms
  instead of 2.8).
- The compiler turns shader functions into SPIR-V itself (as well as GLSL), so no shader
  compiler is needed; tools/spirvtest.py checks every module.
- GPU arrays run as Vulkan compute programs (with no window too).
- **GPU buffers and compute functions** (lib/game/gpubuffer.jo): `gpu_buffer(xs)` keeps an array
  of any struct on the GPU; a compute function `f(id: int, params)`, written in Sloppy, runs once
  per element on the GPU with `dispatch(compute(f), n, params)`, reading and writing buffers by
  index (`u.bugs[id] = b`), with atomics (`atomic_add`, `atomic_min`, `atomic_compare_exchange`...).
  Shaders read buffers among their uniforms; buffers can be a mesh's vertices (`gpu_mesh`) or a
  draw's instances; `draw_indirect` draws as many as a compute function decided (`DrawArgs`).
  Barriers are automatic. Without Vulkan, buffers are CPU memory and compute functions run on
  every core, so the same program works with OpenGL, the software renderer and on the web.
  Their elements are plain data (numbers, bools, vectors and structs of them): a buffer of
  strings or arrays is a compile error.
- `fwidth()` in fragment shaders.
- Shaders and compute functions follow the CPU's rules for numbers: unsigned division,
  remainders, shifts and comparisons, narrow integer types wrapping, float to integer
  conversions saturating, `i32(bool)`. (GPU arithmetic stays 32-bit.)
- Vulkan: a texture deleted, made again or given other sampling after a draw that uses it no
  longer changes that draw (each change takes a new slot of the bindless array; the old one is
  freed once the GPU is done with it), and things released between frames wait for the frame
  that may still use them.
- `SLOPPY_VK_VALIDATE=1` turns on the Khronos validation layer, where it is installed.

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

Language:
- `min`, `max`, `clamp` (and `abs` for signed ones) keep an integer type: `min(x, 5)` with
  `x: i32` is an `i32`, `max(a, b)` of two `u8` a `u8` (mixed types still take `int`'s). Ties
  between the library's overloads go to the one more arguments match exactly.
- Negating an integer vector (`-ivec2(...)`) gave wrong components (it went through floats).
- Swizzles out of order (`v.zx`, `w.wy`) as operands or assigned to read and wrote the wrong
  components on the CPU (assigning one wrote past the vector); a swizzle naming a component
  twice cannot be assigned to (`v.xx = ...`), and only one in order can be a `mut` argument.
- A `mut` element of a global array or map, given to a function that may call a function value
  (which could resize the array), is passed as a copy and written back after the call; the
  change was lost before, written to memory the resize had freed.
- Integer literals: `x: u64 = -1` is an error like `x: u32 = -1`, a literal above 64 bits is an
  error, and overloads rank integer types before `f64` before `f32` (`choose(-1)` with `u64`
  and `f64` overloads takes `f64`; it was ambiguous).
- Type arguments at a call: `zero[int]()`, `gpu_buffer[Bug](100)`, `empty[str[]]()` (`T[]`
  written inside the brackets is the array type).
- `b[i].f = v` and `b[i].f += v` for types defining `[]` and `[]=` (a GpuBuffer, in compute
  functions too): the element is read, changed and written back. `b[f(x)] += v` computes the
  index once.
- An argument read from a global, a variable closures share or a capture stays alive through
  the call, even if the callee (or a later argument) gives that variable another value; it
  used to be freed under the callee. (Release builds leave the reference out where the callee
  cannot change that global.)
- An element passed as `mut` (`hit(enemies[i])`) is written where it is, so while the call runs
  nothing may move or share its array: the same call can no longer also be given the array
  (`attach(nodes[0], nodes)`), and a global array cannot be passed this way to a function that
  may change it. The compiler says so; before, the write could be lost or land in a copy.
- The data race check of `parallel_map` and the others now also covers partial applications
  (`f(k, _)`), calls of function values inside the function, and `__parallel_run`; a function
  kept in a variable is refused, since the compiler cannot see which it is. A function that
  hands the function it is given on to them is marked `@parallel`, and its callers are checked.
- Maps: keys that are unions, optionals or arrays work (they hashed wrongly: unions and
  optionals without end, arrays all alike), `-0.0` and `0.0` are one key as they are equal,
  and `remove` keeps the other entries in insertion order.
- A lambda returning a member of a generic union (`apply((): 42)` for `() -> T | E`) makes
  that member, whatever order inference puts the union's members in.
- A generic function calling itself with ever bigger types stops with an error instead of
  compiling forever.
- Overloads a call cannot match are left out before the choice: `f(300)` with `f(x: i8)` and
  `f(x: i16)` is the `i16` one, and a lambda's parameter types pick among `(int) -> int` and
  `(f64) -> f64`.
- `match` narrows a field (`match b.x:`) or a global in each arm, as it does a local variable.
- A closure using a name narrowed by `is` captures the variable itself, so it sees later
  changes and the variable may still be assigned (it was an error).
- Generic types are also worked out from what the result must be: `x: int = make((v): v + 1)`
  types the lambda's `v`, and `f: () -> int = zero` picks `zero[int]`.
- Editor: an unsaved change to a file is seen at once in the other open files that use it.
- Windows: a float given to a C function among its first four arguments also goes in the
  integer register, as C functions taking varargs (`sprintf`) read it.
- More of the same, from a fourth review: operands of `+` and `==` on strings and arrays, the
  parts of `"...{x}..."` given to a `__fmt` of the program's, `g!` and a closure called from a
  global also stay alive while a call changes where they came from; a `mut` element may not
  share a call with an element inside it (`f(xs[0][0], xs[0])`), a `loop mut` element with its
  array, nor an element of a variable a closure changes with a call that may run it; and
  `parallel_range` and the other @parallel functions can only be called directly, while the
  race check also follows `__fmt` functions and narrowed globals.
- From a sixth review: compound assignments in shaders compute their target first and its
  indexes once (as the CPU), `and=`/`or=` compute both sides, `ivec2(f(x))` calls f once,
  `mat4` takes integer vectors among its parts; `x %= y` on floats is `x % y` on the CPU too;
  a @cabi function sign-extends narrow integers C passes it; a user struct named Texture is
  plain data; a generic function that expands without end is found by its chain of
  instantiations (deep finite types and many instances are fine, and checking is linear).
- Shaders and compute functions: every compound assignment (`%=`, `>>=`, `<<=`, `and=`, `xor=`...)
  works (they all added before), a target's index is computed once, shifts by 32 or more give
  what the CPU gives, and `ivec2(vec2(...))` converts each component (saturating; the CPU copied
  the bits).
- A closure assigning a variable narrowed by `is` changes the variable itself.
- Generic code over big types compiles in time again (the depth check is remembered per type and
  runs only for functions with many instances), and deep but finite types are accepted.
- Windows: a @cabi function called from C may take more than four arguments.
- Editor: references across files follow a used file as it is opened and closed.
- Compute functions can read textures (Vulkan binds the texture array for them, and a texture's
  name in their parameters becomes its slot); `gpu_buffer` refuses Textures as elements.
- Float to integer conversions saturate at the range of the type converted to (`u8(300.0)` is
  255, `i8(-200.0)` is -128, `u64(-1.0)` is 0); before, only `int` did.
- Signed division wraps like the rest of integer arithmetic: the smallest integer `/ -1` is
  itself and `% -1` is 0 (native programs used to stop with an arithmetic error).

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
