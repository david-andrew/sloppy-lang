# Software renderer instruction report

Start commit: `9125f9c8a32775636ec652cbddd20ac4d9f1c28e`. Measured on the shared
Intel i7-6700 desktop, hostname `redfox`, with instruction counts only. No wall-clock
or GPU performance claim is made. No compiler or example source was changed.

## Method and scope

All runs use the same start-commit compiler, retained at
`~/dev/tmp/softgl2/sloppy-start` (SHA-256
`6783381df0830c782c4685becf0bb097c070de3f56ab233325b78c629e652dd2`).
The pristine library is `~/dev/tmp/softgl2/base/lib`; the harness copies and
instruments each library in its own run directory. Time seeds, scripted input,
empty saves, a fixed 60 Hz clock, headless operation and dummy audio follow
[the harness](README.md). A 320×180 window normally gives a 160×90 internal target.
This emphasizes geometry/submission; it is not a full-resolution frame-rate result.

The main native comparison measures **300 complete frames, 60–359**, with
`perf_event_open instructions:u` and `SLOPPY_THREADS=1`; frame 361 is captured.
Callgrind measures five matching complete frames, 120–124, with one and three
threads; frame 125 is captured. Monitor dumps include all workers. A separate
19-frame native pilot interval, 120–138, captures frame 140 and isolates fixes.
The native interval ends conservatively before the final screenshot frames.
REP copies count differently in Callgrind, so compare before/after within each
counter, rather than comparing absolute hardware and Callgrind values. Three-thread
counts include scheduling/spin overhead and are not wall-clock scaling measurements.

Rebound and Breakwater enter real play; Aces enters Practice and starts six planes;
Dunes walks/orbits/jumps; the 3D starter moves/jumps/shoots. The character starter
walks, runs, and changes direction. PBR grid and sky-image use their render-test
sources without scripted input. Example sources and render references remain unchanged.

## Current hot paths

Baseline Callgrind self shares, debug, frames 120–124:

| Scene | Largest current library work |
|---|---|
| Rebound | Composite 19.4%, raster spans 17.5%, blur 11.5%, 2D spans 7.9% |
| Breakwater | Fragment span/interpolation 21.5%, raster spans 15.4%, projection 6.8%, sampling 5.6% |
| Aces | Projection 37.8%, matrix-vector products 8.9%, vertex jobs 7.6%, instanced vertex shader 6.9% |
| Dunes | Projection 14.1%, triangle setup 11.3%, raster spans 8.4%, mesh submission 8.4% |
| 3D starter | Fragment spans 23.0%, raster spans 14.2%, sampling 7.6% |
| Character | Fragment spans 25.4%, projection 8.7%, PBR fragment shader 6.1% |
| PBR grid | Raster and fragment spans 13.0% each, projection 10.3%, triangle setup 9.4% |
| Sky image | Fragment spans 10.6%, exponential helper 9.9%, sampling 9.7%, power 8.4% |

The larger current varying layouts make projection and interpolation more expensive
than in yesterday's profile. Depth testing already precedes fragment shading.
After the changes, Aces debug projection is 15.4% of a much smaller frame;
conservative bound transforms cost 5.9%, included in the measured net saving.
Remaining shader lighting/power/exponential work is unchanged.

## Accepted fixes

Each row's saving is an isolated native pilot, debug / release, using matching
frames 120–138. Representative scenes are named; percentages are not additive.

| Change | Representative scene | Saved debug / release |
|---|---|---:|
| Skip the four position slots overwritten by FragCoord | Aces | 7.07% / 5.94% |
| Interpolate varying groups of four, with a scalar tail | Character | 7.13% / 4.98% |
| Cull bounded instances for the library's known pure vertex shaders | Aces | 18.91% / 24.32% |
| Project all-float varying groups of four; preserve flat integer path | Aces | 15.44% / 7.01% |
| Fast in-range clamped nearest lookup and packed bilinear channels | Breakwater | 3.29% / 3.52% |
| Hoist vertical blur rows and horizontal composite/vignette terms | Rebound | 8.53% / 4.35% |

Instance culling is opt-in at the library draw helper, checked against its lit and
shadow program IDs. Array and retained-buffer instances retain submission order.
Bounds are transformed through model and view-projection separately in f64 intervals,
widened for f32 multiply/add rounding and source-sphere construction. Side rejection
requires positive homogeneous w. Wind and unknown bounds use the original path.
Generic custom shaders still execute every vertex.

Packed arithmetic retains the original component-wise multiplication/addition order.
Flat integer fields keep their original bits. Nearest sampling keeps its general
edge/repeat/nonfinite path; bilinear weights and filtering are unchanged. Post-effect
scratch is overwritten for the active viewport before synchronous worker jobs read it.
No shader equation, shadow tap count, depth rule or color quantization changed.

Unretained trials: a broader packed bloom rewrite regressed Rebound release by 4.5%;
a single serial raster band saved under 0.6%, and XY-only 2D projection under 0.8%.

## Native complete-frame results: 300 frames

Millions of retired user instructions per frame; medians and the largest observed
frame in the same 60–359 interval. Every before/after captured PNG is byte-identical.

| Scene | Mode | Before M | After M | Saved | Worst before → after M (frame) |
|---|---|---:|---:|---:|---|
| rebound | debug | 28.054 | 25.587 | 8.79% | 30.435 (248) → 27.955 (248) |
| rebound | release | 12.707 | 12.158 | 4.32% | 14.261 (248) → 13.711 (248) |
| breakwater | debug | 269.186 | 238.894 | 11.25% | 298.150 (162) → 262.731 (161) |
| breakwater | release | 150.785 | 138.319 | 8.27% | 169.264 (162) → 154.613 (162) |
| aces | debug | 423.257 | 236.359 | 44.16% | 437.447 (140) → 275.744 (142) |
| aces | release | 253.240 | 145.107 | 42.70% | 259.897 (140) → 170.878 (142) |
| dunes | debug | 208.287 | 168.609 | 19.05% | 301.943 (66) → 257.643 (66) |
| dunes | release | 118.395 | 97.626 | 17.54% | 169.073 (68) → 145.984 (66) |
| new_3d | debug | 86.061 | 79.513 | 7.61% | 122.631 (98) → 109.520 (98) |
| new_3d | release | 48.235 | 44.617 | 7.50% | 70.120 (98) → 63.760 (98) |
| new_character | debug | 232.251 | 191.225 | 17.66% | 237.753 (67) → 196.139 (67) |
| new_character | release | 126.143 | 116.049 | 8.00% | 129.356 (67) → 119.077 (67) |
| pbr_grid | debug | 59.446 | 53.070 | 10.72% | 59.446 (216) → 53.070 (123) |
| pbr_grid | release | 33.046 | 30.626 | 7.32% | 33.046 (61) → 30.626 (340) |
| sky_image | debug | 60.229 | 56.693 | 5.87% | 60.229 (61) → 56.693 (113) |
| sky_image | release | 42.267 | 40.835 | 3.39% | 42.267 (226) → 40.835 (292) |

## Callgrind: one thread

Five matching frames, 120–124. Every captured PNG is byte-identical.

| Scene | Mode | Before M | After M | Saved |
|---|---|---:|---:|---:|
| rebound | debug | 28.643 | 26.178 | 8.61% |
| rebound | release | 13.457 | 12.907 | 4.08% |
| breakwater | debug | 259.161 | 231.244 | 10.77% |
| breakwater | release | 146.620 | 134.938 | 7.97% |
| aces | debug | 439.833 | 277.689 | 36.86% |
| aces | release | 264.644 | 175.447 | 33.70% |
| dunes | debug | 229.007 | 189.655 | 17.18% |
| dunes | release | 132.714 | 112.480 | 15.25% |
| new_3d | debug | 104.298 | 95.915 | 8.04% |
| new_3d | release | 62.017 | 57.553 | 7.20% |
| new_character | debug | 236.201 | 195.087 | 17.41% |
| new_character | release | 130.369 | 120.333 | 7.70% |
| pbr_grid | debug | 60.964 | 54.588 | 10.46% |
| pbr_grid | release | 34.549 | 32.129 | 7.00% |
| sky_image | debug | 61.142 | 57.605 | 5.78% |
| sky_image | release | 43.176 | 41.744 | 3.32% |

## Callgrind: three threads

Five matching frames, 120–124; all worker instructions included. Every captured
PNG is byte-identical, and matches its one-thread counterpart.

| Scene | Mode | Before M | After M | Saved |
|---|---|---:|---:|---:|
| rebound | debug | 28.862 | 26.373 | 8.62% |
| rebound | release | 13.541 | 12.992 | 4.06% |
| breakwater | debug | 267.781 | 234.149 | 12.56% |
| breakwater | release | 148.126 | 136.184 | 8.06% |
| aces | debug | 440.455 | 278.507 | 36.77% |
| aces | release | 268.892 | 175.671 | 34.67% |
| dunes | debug | 230.083 | 193.242 | 16.01% |
| dunes | release | 132.908 | 112.661 | 15.23% |
| new_3d | debug | 104.854 | 97.021 | 7.47% |
| new_3d | release | 62.255 | 57.791 | 7.17% |
| new_character | debug | 237.313 | 198.897 | 16.19% |
| new_character | release | 130.907 | 121.401 | 7.26% |
| pbr_grid | debug | 60.976 | 54.600 | 10.46% |
| pbr_grid | release | 34.560 | 32.140 | 7.00% |
| sky_image | debug | 61.147 | 57.610 | 5.78% |
| sky_image | release | 43.180 | 41.748 | 3.32% |

## Identity and regression gates

- `python3 tools/rendertest.py --no-gpu`: **43 passed, 0 failed**, references unchanged.
  The final full-size PNGs are also compared as complete file bytes with start-commit
  captures: **43/43 identical**, stricter than the runner's image-difference tolerance.
- Primary profile capture pairs: **16 full native + 16 short native + 16 one-thread
  Callgrind + 16 three-thread Callgrind = 64/64 identical**. Together with the render
  suite, **107 exact before/after PNG pairs**. Both before and after also have 16/16
  exact cross-thread PNG matches. Primary profiles contain 10,528 measured frames
  across before and after; pilot trials are additional.
- Dedicated post probes compare offset, clipped, exact-size and resized viewports:
  four distinct cases in each build mode, **8/8 exact PNG pairs**. Probe-only helpers
  live in scratch library copies, without expanding the production API.
- `python3 tools/runtests.py`: **28 passed, 0 failed**.
- `python3 tools/runtests.py --compiler sloppy`: **1359 passed, 0 failed**.
- `python3 tools/runtests.py --compiler sloppy --release`: **1353 passed, 0 failed**.
- New tests cover projection tail lengths/flat bits; 400 interval transforms with
  shear, reflection, cancellation and small/large scales; eight filtered/unfiltered
  instance configurations including wind and shadows; all 78 custom vertex callbacks;
  nearest boundaries/wrapping/nonfinite inputs; and ordered bilinear channels.

Suites ran directly, serially, without the other project's token wrapper, with
`TMPDIR=~/dev/tmp/softgl2/tmp`, DISPLAY and WAYLAND_DISPLAY unset, dummy audio,
two suite threads, and one code-emission worker. Software profiles cap the pool at
one or three threads. No wasm run, push, or example edit was made.

`python3 tools/speedcheck.py --base 9125f9c8a32775636ec652cbddd20ac4d9f1c28e`
passes. Library rows (G instructions, same compiler with old/new library):

| Input | Before G | After G | Change |
|---|---:|---:|---:|
| hello.jo | 0.148 | 0.148 | +0.00% |
| game.jo | 0.581 | 0.581 | +0.00% |
| Rebound | 0.753 | 0.755 | +0.27% |
| Breakwater | 1.150 | 1.153 | +0.26% |

All compiler-comparison rows are +0.00%. The library maximum is **0.27%**, below
the 1% limit; the small non-3D programs do not acquire the new instance/shader work.

## Artifacts and commits

Raw run directories, immutable library copies, fixed compiler, build/test logs,
per-frame CSVs, resolved profiles, worst-frame dumps and PNGs are retained under
`~/dev/tmp/softgl2`. Main tags are `before-full-perf`, `after-full-perf`,
`before-t1`, `after-t1`, `before-t3`, `after-t3`; short native and isolated pilot
tags include `fragcoord-perf`, `packed-perf`, `cull-perf`, `samples-perf`,
`project-perf`, `sampler-control-perf` and `post-control-perf`. The comparison
JSONs include SHA-256 digests; [compare.py](compare.py) requires matching sampled
frames and exact PNG files. Reproduce with the commands in [README.md](README.md),
using `--warmup 60 --frames 361 --perf --threads 1` for the 300-frame native run.

The branch was rebased onto `origin/master`; commits remain local for the coordinator:

```text
0995dc5 Skip unused position interpolation to cut Aces instructions by 6%
c88d6a0 Pack software varying interpolation to save 5% in the character starter
48f917f Cull bounded library instances to save 24% of Aces release instructions
b3b9162 Pack all-float projection to cut Aces debug instructions by 15%
4309502 Specialize texture sampling to cut Breakwater instructions by 3.5%
072fa41 Hoist post-effect coordinates to save 8% of Rebound debug instructions
faff1c3 Profile software character, PBR and sky scenes with multiple workers
```
