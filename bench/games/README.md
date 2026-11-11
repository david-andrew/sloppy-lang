# Finished-game profiles

Measure games before optimizing library code. `profile.py` runs the showcase games and
visual `sloppy new` templates with deterministic scripted input, a fixed 60 Hz clock,
no display and no audio. It supports the software renderer and Mesa lavapipe, in debug
and release builds. Each run plays 360 frames and measures frames 60–359.

Requirements: a bootstrapped `bin/sloppy`, a C compiler, Valgrind with its development
headers, and `addr2line`. Vulkan runs use the installed x86-64 lavapipe ICD at
`/usr/share/vulkan/icd.d/lvp_icd.x86_64.json`; adjust the script on another distribution.

```sh
mkdir -p ~/dev/tmp/game-prof/tmp
export TMPDIR=~/dev/tmp/game-prof/tmp
python3 bench/games/profile.py --tag before --prepare
python3 bench/games/profile.py --tag before --prepare --churn
# After editing a library hot path:
python3 bench/games/profile.py --tag after --prepare
python3 bench/games/profile.py --tag after --prepare --churn
python3 bench/games/resolve.py before after
```

Full Callgrind runs can take hours, particularly for software 3D rendering. Narrow
`--games`, `--modes`, or `--renderers` for a pilot. Use distinct tags for pilots and full
runs. Profiles and an instrumented library copy live under `~/dev/tmp/game-prof`, or
`--output DIRECTORY`. No example source is edited. `--repo` and `--compiler` allow
measurement of a separate existing checkout and compiler. `--library` selects a pristine
library tree from a baseline commit. Run test suites serially
under the machine's shared worker budget.
Each run starts with empty save and driver-cache directories under its output directory.

The scratch library pins `time_ns()` to 12345 because Rebound explicitly reseeds a new
run from that clock. It leaves `time()` unchanged. This pin and the frame hooks are
measurement instrumentation only. The small window (320x180, internally 160x90 in the
software renderer) emphasizes submission and geometry work; use `--window 640x360`
for a resolution check. Do not infer full-resolution frame times from these counts.

Instruction runs start Callgrind after warmup and dump each measured frame separately,
and retain `frames.csv`, aggregate self costs and call edges, plus the worst frame's
Callgrind dump. Each sample includes update, draw and presentation. Monitor requests
zero and dump all threads together, including lavapipe workers; client-only dump requests
would omit those workers. `resolve.py` resolves Sloppy addresses with each executable's symbols
and line table. Per-frame dumps are removed after aggregation to bound disk use.
Callgrind counts each REP string-operation iteration, so `__sw_fill`'s doubling copies
have an inflated instruction share relative to hardware time. Driver JIT code may
have unresolved names.

On Linux, `--perf` instead reads retired user instructions around each software frame
with `perf_event_open`. It uses the software renderer's single main thread
(`SLOPPY_THREADS=1`), so Vulkan worker traffic cannot be measured with this mode.
The last frame, which writes the screenshot, is excluded. Use a fresh tag and at
least two frames after warmup; this measures frame 120 and captures frame 121:

```sh
python3 bench/games/profile.py --perf --tag debug-perf --modes debug \
    --renderers soft --games rebound breakwater aces dunes new_3d \
    --frames 122 --warmup 120
```

`frames.csv` and `summary.json` contain hardware counts in this mode. Run three
samples with `--reuse` to keep the same executable, retaining each sample before
the next run overwrites the per-game results. This mode needs access to user-space
hardware counters; it does not use wall-clock timing or allocation instrumentation.

`--churn` instead runs natively with allocation/free and refcount-helper counters.
Its CSV also records cumulative counts after update, draw and frame submission.
`alloc_count()` is the number of live allocations, not total allocation traffic.
Refcount counters cover non-null out-of-line helper entries; the compiler's inline fast paths
are excluded. These are helper traffic, not counts of all refcount mutations. Heap counters
cover Sloppy allocations, not Mesa/C malloc. Sloppy has no tracing GC. Counter
instrumentation is absent from instruction runs. Compare the saved PNGs and run
`python3 tools/rendertest.py --no-gpu` after a rendering change.

The initial report is `~/dev/tmp/game-prof/REPORT.md`; raw run directories are alongside it.
