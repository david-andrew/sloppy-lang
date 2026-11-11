# Whole-vector instruction counts

These kernels measure f32 vec3/vec4 and column-major mat4 math, alongside a C
counterpart compiled with `cc -O2 -ffp-contract=off -lm`. There is no fast math,
`restrict`, architecture tuning, or explicit intrinsics in C. Sloppy uses
`--release`, one emission worker, and `SLOPPY_NO_AVX=1`. The x86-64 packing uses
only SSE2, independently of the existing AVX2 runtime check for array loops.

Run from the repository root, under the machine's shared test-worker budget:

```
TMPDIR=$HOME/dev/tmp/simd/tmp python3 bench/vmath/measure.py \
    --compiler bin/sloppy --label after
```

Use a different output label from the compiler filename. The script builds an
exact-count copy of `tools/icount.c` in `~/dev/tmp/simd`, compiles both languages,
and records three hardware-counter samples of whole-process retired user
instructions per mode. It checks that printed results round to identical f32
bits. Initialization and output are included. No wall-clock measurements are
used. `measurements.json` retains the raw samples.

Every kernel processes 1,024 elements, repeated 256 times. The modes cover
vec4 add/multiply/dot/lerp/normalize, matrix-vector and matrix-matrix multiply,
vec3 cross/normalize, and an update of particle positions and velocities.
`vertex` executes the cube example's CPU vertex shader and calls the actual
`__sw_project` from `lib/game/softgl.jo`, with ten varying floats and no flat
integer attributes. This measures a shader plus the renderer's real projection
stage; it does not claim to measure the full renderer or a physics simulation.
The C version uses the same shader and a translation of that projection stage.

## Design and numerical behavior

SRA and inlining still run unchanged. Immediately before x86-64 or ARM64 register
allocation, a bounded pass recovers small expression trees from adjacent f32
lane stores and ordered sums of products. It uses the existing VX register
allocator on x86-64 and the FP/SIMD allocator on ARM64, `vbin`, and `vsplat`, with unary kinds for lane extraction/shuffles,
square root and absolute value. Matrix multiplication consequently becomes
four scalar broadcasts, packed products, and left-associated packed additions
per result column. Scalar work with individual users remains available.

The pass never reassociates floating-point additions and never introduces FMA,
`dpps`, or a pairwise horizontal sum. A dot multiplies packed lanes, then adds
extracted lanes in debug's original left-to-right order. This deliberately
keeps cancellation and rounding the same, at the cost of several shuffles.
Library min/max choose the second operand on equality or an unordered
comparison; SSE operand order is retained and NEON uses an ordered comparison
and bit selection instead of hardware `fmin`/`fmax`. Library `abs` means conditional
negation (`x < 0 ? -x : x`), so its packed form preserves negative zero and
NaN sign rather than simply clearing sign bits. Explicit bit-absolute-value
IR retains its existing meaning.

Vec3 stays 12 bytes in arrays, structures, parameters and return values.
A packed load uses a 64-bit load plus a 32-bit load and shuffle; its fourth
lane is zero, and a three-lane reduction extracts exactly three lanes.
Stores write exactly 12 bytes. No padding is added to the ABI. The extra
instructions can outweigh packing's gain for short vec3 trees, so these retain
scalar code. The same profitability rule covers vec2.

Packing moves loads only across straight-line code without writes or calls.
Raw pointer stores, aggregate copies (including `M_BITS`), register redefinitions
and control flow end that region. A no-return panic guard may be crossed on
its continuing path, with the guard and diagnostic kept in place. Cached packed
values are discarded at control-flow joins. Searches are bounded to functions of at most 2,048 IR instructions, depth 12,
96 nodes per root, and at most 64 memoized groups retained between roots. Large,
branch-heavy functions retain the existing code generation; their smaller math
helpers remain eligible. This bound protects the 1% release compile-cost gate. Debug and `--release -g` bypass this packing pass.

## Remaining work and targets

Both x86-64 SSE2 and ARM64 NEON are implemented, including Linux ARM64 and
Apple Silicon Mach-O output. NEON uses separate `.4s` add/subtract/multiply/divide,
square root, absolute value and negation, `dup` broadcasts/lane extraction, and
ordered compare/select for the library's min/max/conditional abs semantics.
Matrix multiplication and lerp never use fused `fmla`: ARM64 debug also emits
separate multiply and add, so contraction would change rounding.

VX values share ARM64's scalar FP register pool, with full q-register moves and
loads/stores. Scalar spills retain reusable 8-byte slots; vector spills use a
separate pool of reusable, 16-byte aligned slots. AAPCS64 preserves only d8-d15,
so VX intervals crossing ordinary calls spill all 128 bits. A function using
q8-q15 still saves/restores the low 64 bits required by the ABI. Guarded refcount
calls already preserve every q register through their existing full-save stub.
Packed memory accesses write/read exactly 8/12/16 bytes; the 12-byte case uses
`ldr/str d` plus `ld1/st1` for lane 2 and never accesses the next object.
The same bounded packing and profitability rules apply on both targets; short
vec2/vec3 expressions remain scalar. Wasm SIMD128 remains out of scope.

Packed SSE narrows the gap; it does not remove all of it. Pointer induction,
register copies, matrix helper call/ABI overhead, conservative alias barriers,
and the original scalar ordering of reductions remain opportunities. C may
vectorize across successive structures while this pass packs within one value.

## Measured results

Measured 2026-11-11 on the shared Intel Core i7-6700 desktop (hostname
`redfox`), against `dc0099db8ab8a105a2db1e5d94618acf9aa2b4c3`. C and Sloppy
use identical inputs and f32 evaluation order. All printed outputs match C
after rounding to f32. Before and after use the same measurement environment.

| Kernel | Before | After | C -O2 | After / C | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| vec4 add | 4,878,298 | 3,043,284 | 2,049,472 | 1.485 | -37.62% |
| vec4 multiply | 4,894,461 | 3,059,448 | 2,058,956 | 1.486 | -37.49% |
| vec4 dot | 5,697,163 | 5,435,014 | 7,314,858 | 0.743 | -4.60% |
| vec4 lerp | 8,053,943 | 4,908,210 | 2,601,850 | 1.886 | -39.06% |
| vec4 normalize | 10,945,223 | 9,109,185 | 6,281,073 | 1.450 | -16.77% |
| mat4 × vec4 | 15,926,854 | 10,421,824 | 5,237,002 | 1.990 | -34.56% |
| mat4 × mat4 | 68,809,881 | 46,789,776 | 27,463,122 | 1.704 | -32.00% |
| vec3 cross | 7,229,032 | 7,229,028 | 7,550,929 | 0.957 | unchanged |
| vec3 normalize | 9,839,550 | 9,839,545 | 7,552,072 | 1.303 | unchanged |
| Particles | 12,264,421 | 6,235,103 | 3,403,041 | 1.832 | -49.16% |
| Vertex shader + projection | 100,309,518 | 89,299,462 | 59,450,294 | 1.502 | -10.98% |

The real vertex workload clears the 10% gain gate: two calls to the matrix-vector
helper each save 21 instructions per vertex. That branch-free helper shrinks
from 61 instructions to 40, giving 42 fewer per vertex and 11,010,048 fewer
over 262,144 vertices, apart from startup variation. Matrix-matrix multiplication
saves the same 21 instructions for each of four result columns.

The checked-fast vec4 add/multiply loop shrinks from 17 instructions to 10:
four scalar loads, four scalar memory-operand arithmetic instructions and four
scalar stores become two packed loads, a register copy, one packed arithmetic
instruction and one packed store. Address calculation and loop control still
take five instructions; C takes seven instructions per vector in total.
Lerp falls from 29 to 17 instructions per vector and particles from 45 to 22.
Dot falls only from 20 to 19: preserving the scalar sum requires three shuffles
and three scalar adds. Short vec3 cross/normalize stay scalar, where the
extra packing cost would not pay. Initialization and whole-process startup
explain the remaining differences from these exact hot-loop deltas.

## ARM64 NEON measurements

Measured 2026-11-11 with QEMU 11.0.3 on the shared desktop (`redfox`), against
`90e7dafcabe426c9a15cd70d89e813757fd8a83f`. These are **executed ARM64 guest
instructions**, counted by `insn.c` through QEMU's plugin API; host `perf` counts
would measure QEMU itself. Each translated block contributes its instruction
count every time it executes. These kernels have no mid-block faults. Counts
include initialization and output, using the same 1,024 elements × 256 repeats.
All before/after printed outputs match exactly, including the recorded x86-64
outputs. Both versions run from the same filename so argument scanning contributes
identical startup work. These are instruction counts, not Apple Silicon timing; real macOS measurements remain for the CI runner.
Raw counts and compiler hashes are in `arm64-measurements.json`.

```
TMPDIR=$HOME/dev/tmp/neon/tmp python3 bench/vmath/measure_arm64.py \
    --before $HOME/dev/tmp/neon/sloppy-before --after bin/sloppy \
    --plugin-include $HOME/.pixi/envs/cross/include/qemu-aarch64
```

Build the before compiler from the starting revision's sources. The QEMU header
must match the executable's plugin API version. `cc` and `pkg-config` with native
GLib development headers are needed to build the small plugin. If necessary,
point `PKG_CONFIG_PATH` at the installed GLib and PCRE2 `.pc` directories.

| Kernel | Before | NEON | Change |
| --- | ---: | ---: | ---: |
| vec4 add | 8,896,098 | 3,391,074 | -61.88% |
| vec4 multiply | 8,909,299 | 3,404,275 | -61.79% |
| vec4 dot | 9,708,036 | 5,513,732 | -43.20% |
| vec4 lerp | 12,063,981 | 4,461,805 | -63.02% |
| vec4 normalize | 16,523,634 | 12,329,330 | -25.38% |
| mat4 × vec4 | 17,836,133 | 8,661,093 | -51.44% |
| mat4 × mat4 | 106,751,385 | 54,322,585 | -49.11% |
| vec3 cross | 8,883,465 | 8,883,465 | unchanged |
| vec3 normalize | 18,307,897 | 18,307,897 | unchanged |
| Particles | 20,462,959 | 6,307,183 | -69.18% |
| Vertex shader + projection | 134,134,206 | 117,356,990 | -12.51% |

The branch-free matrix-vector helper shrinks from 58 instructions to 26; the
vertex workload calls it twice per vertex, saving 64 instructions per vertex
(16,777,216 across 262,144 vertices), exactly the measured whole-process delta.
Dot retains separate scalar adds in the original order. Vec3 cross and normalize retain scalar code.

## Original x86-64 validation

- Bootstrap: `bootstrap ok`, self-compilation is a fixed point. A scratch copy
  of `tools/bootstrap.sh` redirects its hardcoded `/tmp` paths to `$TMPDIR`.
- `python3 tools/runtests.py`: 27 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy`: 1212 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy --release`: 1206 passed, 0 failed.
- ARM64 release under `qemu-aarch64`, new `simd_` tests: 1 passed, 0 failed.
- `python3 tools/rendertest.py --no-gpu`: 35 passed, 0 failed.
- `tools/speedcheck.py --base dc0099db8ab8a105a2db1e5d94618acf9aa2b4c3`:
  maximum regression 0.03%; with `--release`,
  0.96%, below the 1% limit. Raw compile counts are in
  `measurements.json`.

Native test suites run one at a time in a private user/network namespace with
the normal user ID preserved and loopback enabled, avoiding other agents' fixed-port servers on this shared
machine. All compilation uses one emission worker; the run holds one of the
machine-wide test-worker locks. No display or audio output is enabled.

`tests/t/simd_values.jo` checks all operators, broadcasts, dot cancellation,
NaNs/infinities/signed zero, conditional-abs signs, vec3's unused lane, unaligned
byte storage, overlapping raw pointers, joins, structures/arrays and matrix
inverse/transpose. Its expected output comes from the unchanged baseline's debug
compiler. The full suites include all `value_copy_*` and `aggregate_copy_alias`.
The final expanded fixture was also rerun separately in debug, release and ARM64 release.
An initial debug simulation timeout passed on retry; its generated `.text` is
byte-identical to the baseline, and the final complete debug run passes.

Shared compiler files touched: `ir.jo`, `opt.jo` (new vector pass and operand
classification) and `x64.jo`. SRA itself, `lower.jo`, `inline.jo`, `main.jo`,
`par.jo`, `arm64.jo`, the library and all examples are unchanged.


## NEON validation

- `tools/bootstrap.sh`: `bootstrap ok`, self-compilation is a fixed point.
- `python3 tools/runtests.py`: 27 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy`: 1260 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy --release`: 1254 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy --release --target linux-arm64`:
  510 passed, 0 failed; two SQLite tests skipped.
- Both `simd_` fixtures: 2 passed in each of native debug, native release,
  ARM64 debug and ARM64 release. Their shared expected output comes from x86-64
  debug. `simd_rounding.jo` compares exact bits for products that FMA would change,
  matrix sums, lane negation, NaN payload/sign selection and signed zeros.
- `python3 tests/check_neon.py`: passed. It builds real ARM64 machine code from
  synthetic IR and executes it under QEMU: forty simultaneously live vectors
  force spills; forty vectors crossing a call must retain all four lanes after
  the callee destroys caller-saved vectors and the upper halves of v8-v15.
  It also checks arbitrary lane permutations, 8/12-byte stores with adjacent
  sentinels, zeroed unused load lanes, and spill alignment/non-overlap.
- `python3 tools/parcheck.py --workers 4`: 84 byte-identical comparisons across
  native, Linux ARM64 and macOS, in default, release, `-g` and `--release -g` modes.
  This includes 28 Apple Silicon Mach-O build comparisons; the release benchmark also builds
  successfully with `--target macos`. Real Apple Silicon timing is left to CI.
- `tools/speedcheck.py --base 90e7daf` and the same command with `--release`:
  both pass, maximum reported regression 0.13% (limit 1%). Raw output is in
  `arm64-measurements.json`.

The first full ARM64 run passed 505 tests and failed five C interop tests because
this x86-64 host has no `/lib/ld-linux-aarch64.so.1`. The baseline fails the same
way. With an ARM64 loader exposed at that path in a private filesystem namespace
and ARM64 libc on the guest's `LD_LIBRARY_PATH`, all five pass with both compilers.
The namespace retains the host's other libraries; no repository library or system
library was modified. SQLite tests are skipped on this cross target.

The NEON implementation changes `arm64.jo`; `ir.jo` and `opt.jo` only gain
comments describing the shared backend hook. x64, lowering, library sources and
examples are unchanged. Mach-O and ELF require no alignment changes.
