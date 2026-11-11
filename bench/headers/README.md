# Affine loop versioning and histogram instruction counts

Measured 2026-11-11 on the shared Intel Core i7-6700 desktop (configured host name
`redfox`), x86-64 Linux, GCC 16.2.1 20261029, `cc -O2`. Comparison starts at
`65573fe4464c2a339544fe4dcf4f2672e0ffb47f`; both compilers were built from their
sources. Sloppy uses `--release` and `SLOPPY_EMIT_WORKERS=1`. All numbers are
whole-process user instructions, median of three hardware-counter runs. No
wall-clock benchmarking was performed.

## Workloads and results

`headers.jo` and `headers.c` implement identical kernels with parameter, local,
and global arrays. C pointers have no `restrict`; Sloppy destinations are `mut`
arrays. Initialization and printed results are included in the counts:

- Matrix: 64 x 64, eight repetitions, i/j/k order,
  `c[i*n+j] += a[i*n+k] * b[k*n+j]`.
- Stencil: 65,536 elements, 32 in-place sweeps,
  `c[i] = (c[i-1] + c[i] + c[i+1]) * 0.25`.
- Histogram: 262,144 indices cycling through 256 buckets, eight repetitions,
  `h[x[i]] += 1`.

| Kernel | Storage | Sloppy before | Sloppy after | C -O2 | After / C | Change |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Matrix | mut parameter | 41,787,325 | 38,576,020 | 17,321,800 | 2.227 | -7.68% |
| Matrix | local | 37,855,320 | 34,775,090 | 17,356,697 | 2.004 | -8.14% |
| Matrix | global | 42,345,770 | 39,036,169 | 17,321,804 | 2.254 | -7.82% |
| Stencil | mut parameter | 21,679,915 | 21,680,297 | 17,090,015 | 1.269 | 0.00% |
| Stencil | local | 21,679,995 | 21,680,346 | 17,090,645 | 1.269 | 0.00% |
| Stencil | global | 21,680,070 | 21,680,419 | 17,090,055 | 1.269 | 0.00% |
| Histogram | mut parameter | 29,902,067 | 21,513,443 | 11,945,230 | 1.801 | -28.05% |
| Histogram | local | 29,902,228 | 21,513,601 | 11,945,971 | 1.801 | -28.05% |
| Histogram | global | 29,901,971 | 21,513,344 | 11,945,231 | 1.801 | -28.05% |

All nine outputs match C (relative tolerance 1e-10). Repeated counts differ
slightly with startup and input paths. `measurements.json` retains the earlier
header-hoisting measurements and adds this comparison's raw samples. Both
comparison runs use the same environment. Stencil's hot loop is unchanged;
extra overflow guards add about 350-380 instructions per complete run
(less than 0.002%).

## Affine range guards

Release lowering's `fp_begin` already caches stable array pointers and guarded
lengths before range loops and handles uniqueness for destinations. There are
no header reads in these hot inner loops. Additional header motion was bounded
below 10% by the earlier experiment; the original samples and Callgrind bounds
are retained in `measurements.json`.

The versioner now recognizes `iv * s + c`, including commuted multiplication,
subtraction, and constant scales reduced to shifts. The scale and offset may be
parameters or expressions the loop does not change. An enclosing loop's counter
is invariant in the inner loop, covering both `a[i*n+k]` and `b[k*n+j]`.
Constant positive and negative induction steps are supported; vectorization
still requires step one. Runtime-unknown steps retain the checked loop.

Before selecting the unchecked copy, guards constrain counter endpoints and
scale to [-2^30, 2^30] and the computed offset to [-2^40, 2^40]. Only then are
both endpoint products and sums checked with unsigned comparisons against the
array length. Their magnitudes stay below 2^61, so signed overflow cannot turn
an invalid range into a valid one. Checking both endpoints handles positive,
negative and zero scales. For nonunit steps, the endpoints conservatively enclose
all visited counters, and extra induction guards prevent wrap on the final
step. Extreme values and inconclusive ranges run the original checked copy,
including valid programs whose index arithmetic wraps. Small constant offsets
also guard against counter overflow before adding the offset.

The original pre-loop trip test remains in place. A failed precheck does not
panic: the fallback preserves the first failing iteration, index and source
message. Resized or replaced arrays cannot supply an invariant pointer/length.
Decomposition has fixed depth and term limits and uses the existing 400-IR-
instruction loop limit; no new whole-function search is performed per access.

The matrix fast loop now has no per-element bounds checks. Multiplication,
address arithmetic, repeated accumulator loads/stores, and register pressure
remain. This change does not implement pointer induction or floating-point
reassociation.

## Histogram: instruction-by-instruction explanation

`objdump -d` of the baseline and changed binaries shows the following executed
instructions on each successful iteration (panic-only paths are excluded):

| Work per element | Sloppy before | Sloppy after | C -O2 |
| --- | ---: | ---: | ---: |
| Input-array bounds compare + branch | 2 | 0 | 0 |
| Load `x[i]` | 1 | 1 | 1 |
| Bucket bounds compare + branch | 2 | 2 | 0 |
| Bucket load, add, store | 3 | 1 | 1 |
| Induction increment, compare, back branch | 3 | 3 | 3 |
| **Total** | **11** | **7** | **5** |

The hot loop has no uniqueness/refcount operations, header reloads, second
bucket check, or redundant index reload. Both languages use 64-bit integers.
C uses pointer induction and Sloppy a scaled counter, but each loop's control
costs three instructions.

Two changes remove four instructions per scan element:

1. Scalar versioning can remove one eligible range check when another bounds
   check must remain, as with the data-dependent bucket index. A lone scaled
   affine or invariant (zero-scale) check can also be versioned. The general
   one-check scalar cutoff is retained to limit code growth and compile cost.
2. The x86-64 emitter folds an adjacent full-width integer load/add-constant/store
   into `addq $constant, [address]` when both intermediate registers have exactly
   one definition and one use and the load/store addresses and widths match.
   No check or other memory operation is crossed. Aliasing, copy-on-write, and
   wrapping integer behavior are preserved. Arm64 retains load/add/store.

The changed histogram scan is:

```asm
mov    0x18(input,counter,8), index
cmp    bucket_length, index
jb     valid_bucket
# original bounds panic path
valid_bucket:
addq   $1, 0x18(buckets,index,8)
add    $1, counter
cmp    count, counter
jl     scan
```

For 2,097,152 scanned elements this saves 8,388,608 inner-loop instructions;
version guards add a few dozen instructions. The two remaining safety
instructions explain 4,194,304 instructions of the gap against C. About 6.83M
Sloppy instructions versus 1.46M C instructions lie outside the scan, mainly
input construction: Sloppy's growing comprehension has capacity/uniqueness
paths and signed remainder handling, while C allocates once and fills a known
size. Those initialization costs remain. Thus the complete program is 1.80x C,
while the scan itself is 1.40x with the required bucket check intact.

## Validation

- `tools/bootstrap.sh`: `bootstrap ok`, self-compilation fixed point. Its hardcoded
  `/tmp/sloppy*` paths were redirected in the executed script to
  `~/dev/tmp/affine/tmp/sloppy*`; the repository script is unchanged.
- `python3 tools/runtests.py`: 27 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy`: 1197 passed, 0 failed.
- `python3 tools/runtests.py --compiler sloppy --release`: 1191 passed, 0 failed.
  This includes all 14 `value_copy_*.jo` tests and `aggregate_copy_alias.jo`.
- New `affine_versioning.jo` and `histogram_versioning.jo`: exact debug/release
  output agreement, including caught panic messages, and 2 passed, 0 failed
  with `--target linux-arm64 --release`, `SLOPPY_ARM64_RUN=qemu-aarch64`.
  Cases cover parameter/computed/negative/zero scales, shifts, nonunit and
  descending steps, nested 2D indexes, zero trips, overflowing endpoints,
  unsigned counters, changed arrays, aliasing and wrapping memory updates.
- Release IR inspection confirms distinct unchecked/checked copies for `scan`,
  `unsigned_scan`, `local_scale`, `negative_one`, `zero_scale`, `shifted`,
  `subtracted`, `strided`, and `descending`: zero bounds-panic calls in each fast
  loop, one retained in each fallback.
- Compile-instruction speedcheck against the start commit passes the 1% gate
  (worst increase 0.92%); detailed counts are retained in `measurements.json`. Suites ran sequentially
  under a shared test-worker lock, with one emit worker.

## Reproduce

```sh
mkdir -p ~/dev/tmp/affine/tmp
export TMPDIR=~/dev/tmp/affine/tmp
export SLOPPY_EMIT_WORKERS=1
python3 bench/headers/measure.py --scratch ~/dev/tmp/affine/after
python3 tools/speedcheck.py --base 65573fe4464c2a339544fe4dcf4f2672e0ffb47f --release
```

The measurement script builds both programs, writes release IR and both
disassemblies to scratch, checks all nine numerical outputs, and saves exact
samples in `counts.json`. It uses `tools/icount.c` (a scratch copy with integer
precision) and falls back to Callgrind if hardware counters are denied. Use
`--compiler` to select a saved compiler and `--scratch` for separate before/after
artifacts. It opens no windows and plays no audio.
