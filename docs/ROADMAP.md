# Sloppy roadmap

Where Sloppy is (v0.7.0, October 2026): a self-hosted compiler (~30k lines of Sloppy, plus a C
bootstrap) that compiles a 50k-line program in 0.18 s, runs programs at ~1.24x the time of C -O2
(release), and targets Linux (x86-64 and arm64), macOS (Apple Silicon), Windows x64 and the web
(one .html file). It has a game
library (window, input, gamepads, 2D/3D drawing with a 2D camera, sprite sheets, tilemaps, menus,
collision and particle helpers, shadows, shaders written in Sloppy that run on the GPU through
Vulkan or OpenGL or on a software renderer, GPU buffers and compute functions, an audio mixer
and synthesizer, PNG/JPEG/WAV/Ogg Vorbis, glTF, JSON, saving), hot reloading (`sloppy watch`), a
REPL, a language server and VS Code extension, a playground, backtraces, DWARF and PDB,
modules, three tutorials and two showcase games (Rebound in 2D, Breakwater in 3D).

The aim stays the same: a small language that feels like Python and runs like C, for making
games, with the shortest path from an idea to something running and shippable.

How the order below is decided:
1. Correctness and compile speed are never traded away (they are checked on every change).
2. Then what makes a person who tries Sloppy stay: installing, a first game, sharing it, and
   finding what went wrong when it misbehaves.
3. Then what lets people build bigger things, and build them together: packages, tools,
   debugging, networking.
4. Then reach: more machines and platforms.

Sizes: S = days, M = a week or two, L = several weeks.

## Now

### 1. Real GPUs beyond NVIDIA (S, then repeated each release)

Vulkan is the default renderer, but it has only run on one NVIDIA card and Mesa's software
driver (lavapipe); OpenGL on Windows only in CI's virtual machines. Most players' machines have
Intel or AMD graphics. What can be done before hardware is at hand:
- **AMD on Linux (done, October 2026, a Steam Deck: RADV, Mesa 26, SteamOS):** all 58 render
  tests through Vulkan, the 73 SPIR-V modules through spirv-val, 300 random compute programs
  the same on the CPU and the GPU, 52 programs the same through OpenGL and Vulkan, windowed
  games at a steady 60 fps through KDE's compositor (Rebound: 2.8 ms of GPU a frame at
  1280x800; Breakwater playing: 1.3 ms offscreen at 720p); its built-in controls as a
  gamepad through Steam Input, and a USB pad, every button and axis. Not yet: AMD's Windows
  driver.
- **AMD, by the hour:** AWS's g4ad instances have an AMD Radeon Pro V520 (RDNA): a real
  graphics GPU, on Linux (Mesa's RADV, the driver most AMD Linux players use) and on Windows
  (AMD's driver). An hour or two per round, for a few dollars.
- **NVIDIA's Windows driver:** AWS's g4dn instances (a T4) on Windows.
- **Intel:** there is no practical rentable Intel GPU with Vulkan graphics. The cheapest way is a
  small Intel mini PC (N100/N150, around $150) or a used laptop with Iris Xe graphics, which also
  covers Intel's Windows driver; Intel graphics are the most common in laptops, so it is worth
  it.
- **Not useful for this:** DigitalOcean's AMD MI300X droplets are compute accelerators without
  graphics (ROCm only); its NVIDIA droplets repeat what is already tested.
- The check is one script (done: `tools/gpucheck.sh [--install]`): the render tests through
  Vulkan on the machine's GPU, spirv-val, `tools/gpufuzz.py`, the games' frame times, and with a
  display `tools/vkcompare.py`, in one report. Any machine can run it, a rented one or a
  volunteer's. AWS's g4ad needs the "G and VT instances" quota raised first (it is 0).
- Windows on real hardware beyond graphics: DPI scaling, fullscreen, raw mouse, XInput, sound
  (never heard yet), alt-tab, minimize.

### 2. Keep it honest automatically (S, done)

- **Compile speed in CI** (done): `tools/speedcheck.py` counts the instructions that compiling
  bench/big.jo, the compiler and the games takes (debug and release), against the commit before;
  above 1% fails. (CI's virtual machines have no instruction counters: valgrind counts there.)
- **Fuzzing each night** (done, .github/workflows/nightly.yml): `tools/fuzz.py`,
  `tools/fuzz_errors.py`, and `tools/gpufuzz.py` (compute on lavapipe; fragment shaders on the
  software renderer, llvmpipe's OpenGL and lavapipe), new seeds each night. Its first night
  found a compiler hang (types spelled out exponentially in an error message), now a test.
- Keep each bug found as a test.

### 3. The games in people's hands (S, ongoing)

Upload Rebound and Breakwater to itch.io (the zip is `sloppy build --target wasm -o game.zip`),
watch people play them (the autopilot measured the difficulty curve, not fun), and write down
what was awkward to build. What the games taught so far went into the library (menus, saving,
rebindable controls, touch on the web).

## Next: what makes people stay

### 4. Finding what went wrong (M)

- **Debugging:** variables in DWARF (`sloppy build -g`: Linux x86-64 and arm64, macOS, where
  the executable carries a __DWARF segment), printers for gdb and lldb, F5 in VS Code
  (CodeLLDB or the C/C++ extension), stopping at a panic, and on Windows the same in the PDB
  (types, variables, natvis for Visual Studio and WinDbg; unwind codes for saved registers):
  done.
- **Profiling:** Sloppy function names in `perf` and Windows' profilers (there: symbols, DWARF,
  PDB), and a frame profiler in the stats overlay: named zones per frame with their CPU time and,
  through Vulkan, their GPU time (done: `zone()`; the 3D scene, its shadows and post-processing
  are zones).
- **Error messages:** the commonest mistakes (130 written the way newcomers from Python, C,
  JavaScript, Go and Rust write them, tests/errors/habit_* and hint_*) each say what to write
  instead (done); quick fixes in the editor for misspelled names, names and operators from
  other languages, `loop mut`, `mut` parameters and numbers of another type. Next: watch what
  people get wrong in the playground and add those.

### 5. Sharing code: packages (M, done)

Another person's Sloppy code by git URL (or path) in the `build:` block
(`name = package("url")`), pinned by commit in `sloppy.lock`, fetched once into a cache;
`sloppy add <url>`; a package's own packages come along. No central registry: next, a list of
packages on the website instead.

### 6. Everyday tools (S each)

- `sloppy fmt`, and format on save in the extension (done).
- `sloppy new` with a few templates (done: game, arcade, platformer, 3d, story, online, program; lib/new/*.jo, each
  built and its first frames drawn in the tests).
- Language server: workspace symbols, semantic highlighting, rename across files (done).
- An examples gallery on the website, each runnable in the browser (done: sloppy-lang.org/examples).

### 7. Networking and netplay (M, then L)

Done: `import net`, messages over WebSockets between native programs and web pages (a native
server; Linux, macOS, Windows, the browser), and a two-player example (examples/netpong).

Netplay that feels local despite latency, with the established techniques as library pieces a
game picks from (and an example of each):
- **Rollback (done, `import netplay`, examples/duel):** every machine runs the game, only inputs
  travel; remote inputs predicted, and on a late one the state (a copied value) rolled back and
  the ticks since played again; input delay; waiting when too far ahead and slowing when ahead
  of the other's clock; inputs resent until acknowledged; hashes of confirmed ticks to catch a
  desync; simulated latency, jitter and loss. Sloppy's math is its own, so ticks agree across
  operating systems and the web. UDP in `net`, a relay over WebSockets for web pages, and WebRTC
  data channels between pages (unordered and never resent, as UDP; the relay passes on only how
  they connect) (done). Next: spectators, more than one local player per machine,
  WebRTC between a page and a native program. (Measured round-trip time, `s.ping(p)`: done.)
- **Client-server (done: `netplay.server`/`client`, examples/arena):** an authoritative server;
  client-side prediction with reconciliation; snapshot interpolation; lag compensation. Next:
  delta-compressed snapshots (only what changed, and per player what is near), UDP for native
  clients, extrapolation when worlds stop arriving.
- From a first try at multiplayer: reconnecting (a rollback player who restarts; a client
  rejoining), a version handshake (two builds that differ say so at once), the relay handing
  out player numbers and a lobby (who is here, ready), the game's own messages alongside netplay
  (names, chat, rematch), lag simulation for client-server, spectators and replays (rollback's
  inputs are small), and worlds sent as what changed rather than whole, as text.
- Lobbies and connecting players: a small relay/matchmaking server program (NAT traversal for
  pages: WebRTC's ICE with a STUN server, done; a TURN server for pages that cannot reach each
  other is the relay for now).

### 8. Game library gaps (in pieces, as games need them)

- 2D: slopes and one-way platforms in tilemaps, tweening, camera follow and shake: done.
- 3D: PBR materials (metal, roughness, normal maps), skyboxes, morph targets, culling instances
  one by one.
- Physics: 2D rigid bodies with joints, as `import physics` (done: circles, boxes, convex
  polygons, pins, rods, ropes, springs, sensors, raycasts; next as games need them: several
  shapes per body (done, with concave polygons cut into convex parts), sleeping, motors and limits on pins, continuous collision for fast bullets (done: swept), welds, sliders and wheels (done),
  a character controller). 3D, as `import physics3d` (done: spheres, boxes, capsules, a level's
  triangles, ball and hinge joints, rods, ropes, springs, rays, a character controller,
  deterministic stepping; next: convex hulls, continuous collision; motors, limits and sphere casts are done). Sleeping in both (done:
  bodies at rest, with all they touch, are left out until something touches them).
- Audio: sounds placed in 2D/3D (panning and distance): done (`play_at`, `move_sound`).
- Assets: a whole directory embedded at once (done: `embed_dir`), Tiled's XML maps and external
  tilesets (done), OpenType fonts with CFF outlines and kerning.
- Input: non-XInput gamepads on Windows, actions bound per player.
- Linux window icons on Wayland (KDE's xdg-toplevel-icon; GNOME needs a .desktop file).
- Scripts (from a Python programmer's pass): an HTTP client (http first; https needs TLS, a
  large piece), date parsing (`strptime`) and durations, a set type or its operations on maps,
  changing a Json object in place, reading a file line by line without loading it whole.
- A serializer (structs to text and back) for saves and settings: done (`save_value`,
  `load_value`, `to_text`, `from_text`).

## Tools that make things without code (later)

Any way of making things other than writing code (a UI builder, a node graph, an inspector of
components and their properties, a level or scene editor) is a view of a program file, both
ways: what is done in the editor writes the code that does it, what is written in the code
shows in the editor, and running the file alone makes the same thing (as MATLAB's App Designer
works from a class file). A graph can be made by code as well as drawn. Nothing the editor
knows is kept anywhere the code does not show.

## Language (ongoing, kept small)

Fill the gaps real programs hit, nothing speculative:
- Constraints for generic code (today errors appear only where a generic is used), and
  fixed-size array lengths as generic parameters (`T[N]`).
- Sugar for passing errors on (a `try`), if code shows the two-line pattern is too much.
- What a function may change, worked out once and carried on function values (from the audit):
  it would replace several special cases in the checks for `mut` elements and borrowed
  arguments, and let release builds leave out more reference counting and bounds checks.
- Lints: a local variable that has a global's name and type (it changes the global); results
  left unused (done for the library's functions that give a new value: `s.trim()`).
- Text: bytes vs code points vs what is displayed, made clear in the API (done: LANGUAGE.md's
  Text, `chr` by code point).
- A consistency review, then a written list of what is stable, before any 1.0.

## GPU (after item 1)

- Pipelines made before they are first drawn with (they are kept on disk between runs already).
- Barriers by hand, for independent dispatches; textures by index in buffers; writes and atomics
  from fragment shaders.
- Workgroup shared memory with barriers: on the CPU (and the web), a workgroup's invocations
  must run in step, which means splitting a compute function at its barriers; designed first.

## Platforms (L each)

- **macOS on Apple Silicon** works since v0.7.0 (Mach-O written by the compiler, ad hoc
  signatures, libSystem, a Cocoa window, OpenGL 4.1, AudioQueue; everything tested on GitHub's
  Apple Silicon runners, whose GPU is a paravirtual one: OpenGL there is Apple's software
  renderer). Since then: Retina resolution, the interactive prompt and `sloppy watch` (on Linux
  arm64 too; on macOS the code made at run time lives in MAP_JIT memory, and a watched game's
  code all runs from there, put there by a loader in its executable). Gamepads through
  GameController (done; not yet tried with a controller). Next: Metal (shaders as MSL; OpenGL
  is deprecated on macOS), and testing on a real Mac's GPU. arm64 code keeps values in registers since 0.8.1 (linear scan; release builds could
  use x86-64's second, priority-based pass too).
- Phones (Android, iOS): not before the above; the web build already runs there.

## Compiler maintainability (ongoing, never a rewrite)

expr.jo and lower.jo are ~4k lines each, much state is global, and AST nodes reuse generic
fields. Split large files by feature when touching them, keep configuration in one place, and
document invariants per phase (docs/COMPILER.md). The fuzzers (CPU, errors, GPU) are the
safety net for changes here.

## Performance (ongoing)

- Measure the finished games first: allocation churn and frame-time spikes matter more than
  synthetic benchmarks.
- Then the remaining gap to C -O2 in release builds (fannkuch 1.5x, spectral 1.4x, nbody 1.3x).
- From a C programmer's benchmarks: `c[i * n + j] += ...` on a `mut` array keeps its bounds
  checks (3x C) because the array's length is loaded again in each pass of the loop; moving
  loads that nothing in the loop can change out of it (array headers, with no calls or header
  stores in the loop, and only where the loop surely reaches them) would let loop versioning
  drop the checks. vec4/mat4 math is scalar (2-2.8x C); packed SSE for vec4 would close it.
  Function values are not inlined (reduce, count, a lambda: 2-3x a plain loop).
- Debug builds stay the default; compile speed comes first (item 2 tracks it). What they lose
  to release builds, measured October 2026: the out-of-line uniqueness and refcount calls were
  most of it (done: the code generator tests the common case and skips the call, through a
  stub that keeps every register when it is taken, with the IR unchanged: nbody 1.8x, swarm
  1.2x, no compile time). The rest (nbody 2.7x, swarm 2.5x slower than release) is the
  optimizer and inlining; release's register allocator alone gains nothing there. Inlining the
  fast paths as IR instead cost 12-19% more compile time.

## Compile speed for large programs

Measured October 2026 on bench/big.jo (50k lines, debug, 8 cores, a busy machine): checking 46%
(parsing included), lowering 20%, code generation 30%; about 0.19 s in all.
- Code generation in parallel (done for x86-64 on Linux and macOS hosts: compiler/par.jo,
  forked workers, the same bytes as one processor makes): about 10% off here, more on an idle
  machine. Next: the same for arm64 code (native builds on Macs).
- Allocation in the compiler: about 5% of the time, the allocator already doubling arrays and
  remapping large blocks in place; nothing big there.
- Lowering in parallel (the next lever, about 1.4x on big.jo with code generation in the same
  workers): lowering discovers the functions and globals it needs as it goes, so that would come
  first (the instances are known after checking; globals given places up front), with each
  worker's string constants and source positions renumbered when joined. Days of work; worth it
  when programs this large exist.
- The optimizer's first pass in parallel (release builds: about 20% of building the compiler),
  its results returned through shared memory.
- No caching of the library between builds: it is a small part of a large program, and caching
  it would add complexity for small programs only.

## Community (S, ongoing)

A changelog per release (done), issue templates, a contributing guide, and a place to show
games made with Sloppy.

## Not planned for now

Tracing garbage collection, exceptions, inheritance, a JIT, a central package registry,
consoles (their SDKs are under NDA). Code signing on Windows is out of reach for now; the docs
should say what SmartScreen shows for an unsigned game and how players get past it.

## An aspiration, last of all

A million lines a second (Jai's target). Nice if it happens, behind everything above: past
parallel code generation it needs type checking in parallel, or a much faster checker.
