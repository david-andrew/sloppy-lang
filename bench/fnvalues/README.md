# Function-value inlining

## Follow-up: capture cells (2026-11-12)

Starting at `9125f9c`, the same instruction-count workload reproduces `each` at
13,474,486 instructions versus 2,762,439 for the plain loop (4.878×). Promoting
its scalar cell through the inlined loop reduces it to 2,830,064 (1.024×,
-79.00%). Raw follow-up counts are in `measurements2.json`.

Scalar, unmanaged capture accesses carry a private-cell memory marker only when
neither the variable nor any of its captures has its address taken or is passed
as a mut argument. Captured cell pointers use the environment's header memory
class. A bounded loop pass hoists an immutable capture-pointer load and keeps one
cell payload in a register until loop exit. It accepts call-free loops with one
cell address, no other stores and no exits beyond the loop. The resulting integer
reduction vectorizes. Narrow integers, managed/aggregate cells, opaque calls and
aliasing or escaping addresses retain their original memory accesses. Heap cells
and environments remain allocated outside the loop; writeback preserves mutations
observed after the helper and through stored closures. This is loop scalar
replacement, not general allocation elimination.

`fnvalue_cells` adds empty/single/multiple iteration cases, stored readers,
per-iteration captures, nested lambdas, internal callback returns, addressed-cell
aliases, narrow overflow and floating-point cells. All five fnvalue tests pass in
native debug and release.

Measured 2026-11-11 on the shared x86-64 Intel Core i7-6700 desktop (host name
`redfox`), against `3c5ab28dbcd7674390d4de9f00ca2ff191257df9`. Both compilers
were built to a self-compilation fixed point. Counts are whole-process retired
user instructions, median of three runs with the hardware counters from
`tools/icount.c`; no wall-clock measurements. Raw samples are in
`measurements.json`.

## Follow-up: keyed sort

Splitting the existing key-building traversal into `__sort_keys` and the stable
index-sort/reorder into `__sort_key_order` puts the callback traversal below the
existing helper limit. Known keys now inline through the small sort wrapper and
key traversal; the merge algorithm remains out of line. Keys still run once per
element in input order, and not at all for fewer than two elements. No extra
arrays are built. The benchmark goes from 1,598,559,163 to 1,565,806,308
instructions (-2.05%), versus 1,565,784,261 for its equivalent loop (1.000×).
Two new native debug/release tests cover stable ascending/descending ties across
merge runs, key-call counts, copy-on-write, managed keys and a panicking key.

## Workloads and counts

Each program initializes 8,192 integers cycling through 0..16, then runs its
kernel 200 times and prints a checksum. Each higher-order kernel and its loop
live in separate `@noinline` functions: a closure cannot force shared cells or
extra register pressure into the plain-loop comparison. Initialization,
dispatch, allocation, cleanup, and output are included. Checksums match in all
cases. `any` and `all` traverse the entire input. `map_sum` materializes the same
mapped array in both versions; this change does not fuse array operations.

| Kernel | HOF before | HOF after | Loop before | Loop after | Before / loop | After / loop | HOF change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| reduce | 39,620,732 | 2,755,485 | 2,752,080 | 2,752,040 | 14.397× | 1.001× | -93.05% |
| count | 45,794,297 | 17,935,246 | 11,378,042 | 11,378,001 | 4.025× | 1.576× | -60.84% |
| each | 36,416,312 | 13,474,467 | 2,762,460 | 2,762,420 | 13.183× | 4.878× | -63.00% |
| any | 44,551,139 | 16,693,093 | 10,135,289 | 10,135,247 | 4.396× | 1.647× | -62.53% |
| all | 44,564,589 | 10,152,945 | 10,148,738 | 10,148,698 | 4.391× | 1.000× | -77.22% |
| map | 64,284,422 | 36,427,976 | 36,418,172 | 36,418,130 | 1.765× | 1.000× | -43.33% |
| named_map | 59,364,061 | 36,422,815 | 36,413,010 | 36,412,969 | 1.630× | 1.000× | -38.65% |
| filter | 69,652,102 | 37,268,456 | 30,707,853 | 30,705,611 | 2.268× | 1.214× | -46.49% |
| map_sum | 66,759,960 | 38,901,710 | 38,894,507 | 38,894,265 | 1.716× | 1.000× | -41.73% |
| sort_by | 1,598,564,053 | 1,598,559,094 | 1,565,788,705 | 1,565,784,298 | 1.021× | 1.021× | -0.00% |
| parallel_range | 38,211,361 | 38,211,313 | 13,519,333 | 13,519,292 | 2.826× | 2.826× | -0.00% |

`sort_by` uses the same key/index/stable-merge-sort/reorder algorithm in both
arms; the loop arm computes keys directly. Both still use a comparator closure
for the index merge sort. Thus the 2.1% gap bounds the key callback's contribution
in this workload, not all possible sorting workloads. The 466-instruction
helper exceeds the 200-instruction bound and is left unchanged.

`parallel_range` runs with `SLOPPY_THREADS=1` so spin/wakeup scheduling cannot
pollute the instruction comparison. It still traverses the worker-closure/job
machinery, versus direct serial array writes. Its callback escapes into a worker
closure, and the new pass deliberately leaves it unchanged. These numbers are
not a parallel speedup measurement.

## Cause and implementation

Baseline release IR contains `calli` inside each traversal, a load of the function
pointer and environment, and a null-function check. A noncapturing function value
occupies a two-word frame slot. Capturing lambdas additionally allocate an
RC-managed environment; captured variables that change live in shared heap cells.
For example the old integer `reduce` executes `calli(env, accumulator, element)`
on every element. Existing inlining only follows `call` and treats such a helper
as a non-leaf, so the callback prevents both inlining and vectorization.

The release inliner now recognizes two-word local closure slots whose function
and environment have one dominating initialization, with no escaping address.
Every use must be a full-word read or a call argument to a small helper whose
parameter address is only read or forwarded to another safe helper. Copies,
stores, returns, unknown calls, reassignment, and conditional temporary resets
reject the candidate. Single-definition address aliases are followed. Function
and environment stores must share a structured scope; uses cannot outlive it.

The helper is expanded into the caller, closure-word loads become the known
function address and the original environment pointer, and existing propagation
exposes direct calls. The existing small-function inliner then handles the
callback, including named-function thunks. One bounded follow-up small-call pass
also expands a thunk's direct target when the thunk has not yet been visited by
callee order (`faddr` itself is not a call-graph edge). Unused closure-word stores and frame
addresses disappear, and the dead closure frame slot is reclaimed. No persistent specialized functions are created. Bounds:
200 IR instructions per helper, 800 added helper instructions per caller/pass,
three rounds and three levels of forwarding. Recursive summaries terminate at
the forwarding bound; recursive callbacks remain direct recursive calls.
`@noinline` helpers and callbacks retain that restriction.

A callback with a single tail return needs no enclosing exit block. Omitting
that block makes reduction arithmetic visible to the existing vectorizer.
The optimizer also removes byte widening of comparison results (already 0/1),
which avoids redundant boolean conversions after predicate inlining.

The after IR has no callback `calli` in the seven optimized traversals, named map, or mapped
sum; cold environment-destructor calls can remain outside their loops. Captured
cell pointers, cell reads/writes, environment allocation, retains and drops retain
their original semantics. In particular `each` improves 63% but remains 4.88× a
vectorized plain reduction because its shared cell still inhibits vectorization.
This pass does not promote captured cells or heap environments to registers.
Predicate and filter gaps also retain control-flow/register-allocation costs.
Escaping/stored closures keep the original indirect path. Debug does not run
the new inlining pass.

## Compile speed, size, and correctness

Compiler release binary: 7,332,440 → 7,364,256 bytes (+0.434%).
Benchmark release binary: 202,344 → 202,440 bytes (+0.047%).

Both `tools/speedcheck.py --base 3c5ab28` and the same command with `--release`
pass the 1% limit. Rounded G-instruction counts from the latter run:

| Compile input | Default before → after | Release before → after | Release change |
| --- | ---: | ---: | ---: |
| bench/big.jo | 1.542 → 1.542 | 3.679 → 3.681 | +0.05% |
| compiler/main.jo | 8.616 → 8.544 | 8.616 → 8.544 | -0.84% |
| examples/rebound/rebound.jo | 0.928 → 0.928 | 2.117 → 2.110 | -0.33% |
| examples/breakwater/breakwater.jo | 1.208 → 1.208 | 2.792 → 2.781 | -0.39% |

Library comparisons do not regress. The compiler's own build manifest already
requests release, so its two columns coincide. These measure compilation work,
not elapsed time. Full speedcheck output is retained in `measurements.json`.

Final validation, one shared test-worker token and suites run sequentially:

- Bootstrap ends `bootstrap ok`, compiler 7,364,256 bytes; stages 2 and 3 are
  byte-identical. The original `tools/bootstrap.sh` hardcodes `/tmp/sloppy1/2/3`;
  its script was copied into scratch with only those paths and its working
  directory relocated, to honor this task's scratch policy. Repository tools
  are unchanged.
- `python3 tools/runtests.py`: **27 passed, 0 failed** (C bootstrap).
- `python3 tools/runtests.py --compiler sloppy`: **1,207 passed, 0 failed**.
- `python3 tools/runtests.py --compiler sloppy --release`: **1,201 passed,
  0 failed**. The full suites include every `value_copy_*.jo`,
  `aggregate_copy_alias.jo` and `affine_versioning.jo`.
- New `fnvalue_inline*` tests: **3 passed, 0 failed** in native debug, native
  release, and `--release --target linux-arm64` with
  `SLOPPY_ARM64_RUN=qemu-aarch64-static`.

The new cases cover changing captures (including managed values), distinct
per-iteration captures, stored-and-passed callbacks, reassigned function values,
recursion, two helper levels, early returns, explicit and bounds panics with the
same messages, named functions, multiple callbacks, mut arguments, generic and
aggregate returns, conditional initialization, and no leaked capture allocations.
All three target/mode combinations compare to the same expected output.

## Reproduce

Use a scratch directory outside `/tmp` and the same library for both compilers:

```sh
mkdir -p "$HOME/dev/tmp/fnvalues/tmp"
export TMPDIR="$HOME/dev/tmp/fnvalues/tmp" SLOPPY_EMIT_WORKERS=1
python3 bench/fnvalues/measure.py --compiler /path/to/baseline/sloppy --scratch "$HOME/dev/tmp/fnvalues/before"
python3 bench/fnvalues/measure.py --compiler bin/sloppy --scratch "$HOME/dev/tmp/fnvalues/after"
python3 tools/speedcheck.py --base 3c5ab28dbcd7674390d4de9f00ca2ff191257df9
python3 tools/speedcheck.py --base 3c5ab28dbcd7674390d4de9f00ca2ff191257df9 --release
```

`measure.py` saves the release IR, binary size, and raw instruction samples, and
compares the printed checksums. It forces one emission worker and one
runtime thread. It requires Linux hardware instruction counters and fails if
they are unavailable.
