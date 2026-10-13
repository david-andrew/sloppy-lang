# Changelog

## 0.9.0

Tools:
- **Packages**: `name = package("git URL" [, "tag, branch or commit"])` (or a directory) in the
  build block; `import name` loads the package's main file, `import 'name/file.jo'` another. The
  first build pins each to a commit in `sloppy.lock` beside the program and fetches it once,
  with git, into a cache, so builds after are the same and need no network. `sloppy add <url>`
  writes the line and fetches it. A package's own packages come along.
- **An examples gallery** on the website (sloppy-lang.org/examples): each game, example and
  `sloppy new` template, with its picture, to play in the browser or change in the playground.
- `run_program(program, args)`: run a program, wait for it, its exit code and output.
- **Variables in debuggers**: `sloppy build -g` (Linux on x86-64 and arm64, macOS) adds every function's
  parameters and locals with their types and where they are while it runs, and how each frame
  is made (`.debug_frame`), so gdb and lldb show the variables of every frame on the stack. A
  variable of a `-g` build lives on to the end of its function and stays where calls keep it.
  `lib/debug` has printers for gdb and lldb: strings as text, arrays and maps as their
  elements, optionals as their value or `none`, an enum with fields as its variant. In VS Code,
  F5 (**Sloppy: Debug File**) builds with `-g` and debugs through CodeLLDB or the C/C++
  extension, stopping where the program panics. `tools/dbgtest.py` checks what gdb and lldb
  show; the fuzzer also compares `-g` builds.
- **Quick fixes** (the language server's code actions, Ctrl+. in VS Code) for errors that say
  what to change: a misspelled name ("did you mean"), `loop mut` for a loop variable changed, a
  parameter changed made `mut`, a number of another type converted (or `2.0` written `2`).

Games:
- **Networking**: `import net`, then `net.listen(port)` (a server), `net.connect(host, port)`,
  `net.send(peer, msg)`, `net.send_all(msg)` and `net.receive()` each frame (peers joining and
  leaving, their messages, whole and in order). Over WebSockets: a web page and native programs
  play together, a native program being the server; on Linux, macOS, Windows and in browsers.
  examples/netpong: Pong for two over the network. `tools/nettest.py` checks a server and
  clients (and a web page's client, in a browser) in CI.
- A camera that follows (`follow(cam, target, dt, speed, deadzone)`) and a screen shake
  (`Shake`: `add` trauma, `update`, `offset`); sounds from a place (`play_at` in 2D, from a
  listener, and in 3D, from the camera; `move_sound` for one playing; `set_pan`).
- **Zones in the frame statistics**: `zone("physics")` ... `zone_end()` (or `zone("physics", f)`)
  times a part of the frame; the overlay (`show_stats()`, SLOPPY_STATS=1) lists each zone,
  nested, with its average and longest time over the last frames, and SLOPPY_STATS=log prints
  them. `update` and `draw` are zones already. Off, a zone costs a check.

Errors:
- An argument of the wrong type is pointed at, not the call.
- A function's final expression has its own line in backtraces and debuggers.

## 0.8.1

Fixed:
- The library's 3D example called `sun()` with the direction its light goes; it takes the
  direction toward the sun (now said where it is defined).
- The software renderer drew a faint box behind small text (16 px and less).

Faster:
- **arm64 code keeps values in registers** (macOS and Linux arm64): linear-scan allocation over
  the same lifetimes as on x86-64, callee-saved registers for values living across calls, x0-x7
  for those that live between calls; comparisons branch on the flags, constant operands are
  immediates, float constants are read from a literal pool. Under emulation, the compiler
  compiles itself in 8.5 s instead of 13.2 s, and is 4.4 MB instead of 6.6 MB.

Tools:
- **`sloppy fmt`**: code laid out one way: blocks indented by four spaces, one space around
  binary operators and after commas and colons, none inside brackets; line breaks, strings and
  comments stay (a comment after code keeps its column). Only spaces change, and only where
  the compiler reads the same tokens afterwards (the spaces it pays attention to, as in
  `[a -b]` and `x xor= 1`, included), else the file is left alone. `--check` lists what would
  change; `-` formats standard input. The language server formats (`textDocument/formatting`),
  and the VS Code extension formats on save.
- **`sloppy new <directory> [kind]`**: a project to start from, which runs as it is: `game` (the
  smallest: a window, update and draw), `arcade` (a 2D arcade game: a title menu, a score, a best
  score kept, sounds, particles, a pause menu), `3d` (first person: mouse look, walking and
  jumping among crates, shooting orbs) or `program` (for the terminal, with a test).
- Language server: symbols across the workspace's files (VS Code's Ctrl+T). The extension:
  **Sloppy: New Project** (`sloppy new` from the command palette).
- `tools/fuzz.py --arm64`: each random program also built for arm64 and run under qemu (each
  night in CI).

## 0.8.0

Platforms:
- **The interactive prompt and `sloppy watch` on macOS and Linux arm64.** The prompt compiles
  each input with the arm64 code generator, linked to the running session (far calls through
  veneers). On macOS the inputs' code goes into MAP_JIT memory (Apple silicon runs code made at
  run time only from there), the session starts without address space randomization (as
  debuggers start programs) so it is where its code was linked, and C functions an input uses
  for the first time are found when first called. A game run by `sloppy watch` on macOS keeps all
  its code in such a region, put there at start by a loader in its executable (a signed page
  cannot be patched), and takes patches through a copier outside it; files are watched by when
  they were last written. Every test of both runs on GitHub's arm64 Linux and macOS runners.
- `__code_sync(p, n)` for machine code written at run time (arm64: the caches).

Fixed:
- arm64: the prompt's jump buffer was too small for arm64's `__setjmp` (168 bytes), which wrote
  past it into the heap.
- macOS: a stack overflow in the prompt's input, or in anything running in a copy made by fork,
  killed it without a word (the copy's thread had no alternate signal stack).
- An error message about a type made of aliases of aliases (`(F, F) -> int` with
  `F = (G, G) -> int`...) took exponential time: type names are cut short past 150 parts.

Tools:
- CI checks compile speed against the commit before (`tools/speedcheck.py`: instructions
  counted, debug and release, the compiler, bench/big.jo and the games; above 1% fails).
- The fuzzers run each night with new seeds (.github/workflows/nightly.yml): programs built four
  ways, broken programs, GPU compute functions and fragment shaders on Mesa.

## 0.7.1

Editor (the extension is 0.4.0, now on the VS Code Marketplace and Open VSX both, published by
each release):
- Names are coloured by what they are: the language server sends semantic tokens (variables,
  parameters, fields, functions, structs, enums and their members, modules, constants as
  read-only, the standard library's names), and the grammar colours names before it answers.
- Fixed: inlay hints repeated (`x: int: int: int`) in a file whose program had errors; the
  brackets of `[a..b)` and `(a..b]` marked as unmatched; `(a..b]` running on into the next lines.
- Rename: an alias (`from m import x as y`) renames its binding and its uses; renaming to a
  keyword, or to a name that would change what other names mean, is refused; uses in open files
  that import the file are renamed too (and found by Find References).
- Names with non-ASCII letters work in every feature; signature help, hover and completion read
  strings as the compiler does; the outline finds `f=(x: int)` and multi-line signatures, and
  nothing inside strings; doc comments above `@attributes` show on hover; a generic function's
  hints only where all its instances agree.
- Files changed on disk (not in the editor) are checked again; closing a file keeps the errors
  other open files have for the files they share; new unsaved files get the language features.
- The extension: a server that fails to start no longer leaves requests waiting; restarting
  cannot start two servers; errors from an older version of a file are dropped; Run and Test stop
  when saving fails; Install Sloppy works on Linux arm64 and macOS too.
- Highlighting: octal numbers, `<<` and `<<=`, `ivec3`/`ivec4`, `f[int](x)`, interpolations as
  code; indentation after a line ending in `:` with a `#` in a string.

macOS: OpenGL at a Retina screen's full resolution (window sizes and the pointer in pixels, the
scale followed as the window moves between screens).

## 0.7.0

Platforms:
- **macOS on Apple Silicon** (`--target macos`, the default when the compiler runs on a Mac;
  the installer sets it up as on Linux, with no Xcode): Mach-O executables written by the
  compiler itself, with dyld binding the C functions they use and an ad hoc code signature, so
  they can be made on Linux too. The library's system calls go through libSystem; threads
  (`parallel_map` and the rest) are pthreads. Games open a Cocoa window (keyboard, mouse, wheel,
  mouse look, clipboard, fullscreen), draw with OpenGL 4.1 (or the software renderer) and play
  sound through AudioQueue. Every test and render test passes on a Mac, the compiler compiles
  itself there to the same bytes, and the language server works; CI runs all of it on a GitHub
  macOS runner, with a game on its screen. Not yet: Metal, Retina resolution (windows are drawn
  at one pixel per point), the interactive prompt and `sloppy watch`.
- **Linux on arm64** (`--target linux-arm64`, the default when the compiler runs on arm64; the
  installer has it too): a new code generator (compiler/arm64.jo), x86-64 system call numbers
  translated for arm64, C libraries loaded through arm64's ld.so, crash backtraces from arm64's
  registers. Every test passes there, and the compiler compiles itself on arm64 to the same
  bytes; CI runs the tests on an arm64 machine. Not yet: register allocation (values live in the
  frame, so the code is slower), the interactive prompt and `sloppy watch`.
- `ARCH` (`"x86_64"`, `"arm64"` or `"wasm32"`) beside `TARGET` (now also `"macos"`), for `when`.
- `@variadic(n)` on an `extern`: a C function with n fixed parameters, then C's `...` (macOS
  passes the others on the stack).

Graphics:
- `ivec3` and `ivec4` (i32 vectors, as `ivec2`), and compute functions over a 3D grid:
  `f(id: ivec3, params)` with `dispatch(compute(f), ivec3(w, h, d), params)` (groups of 4 by 4 by
  4 on the GPU).
- Shaders on OpenGL and the web: integer `+ - *` wrap on overflow as on the CPU (they are
  written through unsigned numbers; NVIDIA's GLSL compiler assumed signed results never
  overflow and simplified hash-like code wrongly). Found by tools/gpufuzz.py.
- Shaders: the smallest integer `/ -1` (and `% -1`) and `abs` of the smallest integer give
  what the CPU gives (itself, 0, itself); GLSL and SPIR-V leave them undefined, and Intel's
  OpenGL driver gave other values. Found by tools/gpufuzz.py on an Intel UHD 620, where every
  test and render test now passes with Vulkan and OpenGL.
- Web games take touch: the first finger is the mouse with its left button held, so dragging
  moves it (Rebound's shield follows a finger; before, only the first touch registered), and the
  page no longer scrolls or zooms under the game.

Docs:
- A new page, **Graphics and the GPU** (docs/GRAPHICS.md): the four renderers and when each
  runs, how shader functions reach each of them, what is the same and what differs, the three
  ways of computing on the GPU, and the switches for choosing and troubleshooting.

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
