# Function-value release optimization

Measured 2026-11-12 on the shared x86-64 Intel Core i7-6700 desktop (`redfox`),
starting at `9125f9c`. Both compiler binaries were built to a self-compilation
fixed point. Counts are whole-process retired user instructions, median of three
runs using Linux hardware counters through `tools/icount.c`; no wall-clock
measurements. Raw baseline, intermediate and final samples are in
`measurements2.json`. The first round, starting at `3c5ab28`, is preserved in
`measurements.json`. Final validation includes the renderer changes rebased
from `origin/master` through `0e3e6ae`.

## Workloads and counts

Each program initializes 8,192 integers cycling through 0..16, then runs its
kernel 200 times and prints a checksum. Each higher-order kernel and its loop
live in separate `@noinline` functions, keeping closure cells/register pressure
out of the reference. Initialization, dispatch, allocation, cleanup and output
are included. Every pair's checksums match. `any` and `all` traverse the entire
input; `map_sum` materializes the same array in both arms.

| Kernel | HOF before | HOF after | Loop after | Before / loop | After / loop | HOF change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| reduce | 2,755,505 | 2,755,951 | 2,752,506 | 1.001× | 1.001× | +0.02% |
| count | 17,935,266 | 17,935,711 | 11,378,466 | 1.576× | 1.576× | +0.00% |
| each | 13,474,486 | 2,831,331 | 2,762,886 | 4.878× | 1.025× | -78.99% |
| any | 16,693,113 | 16,693,560 | 10,135,715 | 1.647× | 1.647× | +0.00% |
| all | 10,152,964 | 10,153,409 | 10,149,164 | 1.000× | 1.000× | +0.00% |
| map | 36,427,997 | 36,428,842 | 36,418,997 | 1.000× | 1.000× | +0.00% |
| named_map | 36,422,834 | 36,423,680 | 36,413,836 | 1.000× | 1.000× | +0.00% |
| filter | 37,268,477 | 37,273,324 | 30,710,478 | 1.214× | 1.214× | +0.01% |
| map_sum | 38,901,734 | 38,902,576 | 38,895,131 | 1.000× | 1.000× | +0.00% |
| sort_by | 1,598,559,163 | 1,565,813,268 | 1,565,791,176 | 1.021× | 1.000× | -2.05% |
| parallel_range | 38,211,329 | 10,359,027 | 13,520,158 | 2.826× | 0.766× | -72.89% |

The benchmark still calls keyed sort `sort_by`; its public API is now `sort`.
Both arms use key/index/stable-merge-sort/reorder, with the loop arm computing
keys directly. Both retain a comparator closure inside merge sort, so this 2.1%
initial gap bounds the key callback's contribution, not all sorting overhead.

`parallel_range` uses `SLOPPY_THREADS=1` so scheduling/spinning does not pollute
instruction counts. The pool/job machinery is still used. The serial reference
uses checked array writes while the library already uses a raw output pointer;
its final count below the reference does not imply parallel speedup.

## Known callbacks through small helpers (first round)

Release IR originally called `calli(env, ...)` on every element, loading two
function-value words and checking the code pointer for null. Capturing lambdas
also allocate an RC-managed environment, and changing captures live in shared
heap cells. Ordinary small-call inlining could not follow the indirect call.

The bounded function-value inliner recognizes two-word local closure slots with
one dominating initialization and no escaping address. Uses must be full-word
reads or arguments to helpers whose corresponding parameter is read or safely
forwarded. Copies, stores, returns, unknown calls, reassignment, incompatible
scopes and conditional temporary resets reject the candidate. It expands the
helper, substitutes known code/environment words, resolves exposed indirect
calls and lets the ordinary inliner handle the callback and named thunks.

Bounds remain 200 IR instructions per helper, 800 added helper instructions per
caller/pass, three rounds and three forwarding levels. `@noinline`, exported/C
functions and frame-dependent intrinsics remain excluded. Single tail returns
need no exit wrapper, exposing arithmetic to vectorization. Recursive callbacks
remain calls. Debug does not run this pass. No persistent variants are created
by this inliner; general stored/escaping callbacks retain their original path.

## Scalar capture cells

The remaining `each` loop loaded its cell pointer from the environment, then
loaded and stored the accumulator through that pointer on every iteration.
It now uses a register accumulator and vectorizes: 13.47M → 2.83M instructions
(-79.0%), within 2.5% of the plain reduction.

Lowering marks unmanaged scalar cell payload accesses as private only when
neither the variable nor any capture has its address taken or is passed as a
`mut` argument. Captured cell pointers use the environment's header memory
class. A bounded loop pass hoists an immutable capture-pointer load, initializes
one register from the payload, replaces loop loads/stores, and writes it back
when the loop finishes. Every branch must stay inside the loop or target its
backedge. Other cell addresses, other stores, nested loops, opaque calls and
exits beyond the loop reject promotion. Narrow integer cells retain their
store/load conversions; floating cells retain their original operation order.

Functions with source-level raw dereferences do not promote cells. Lowering also
retains raw-read provenance through inlining: a small pointer helper must not
hide a possible cell alias from the loop pass. Untyped aggregate-copy reads
also reject promotion. Tests reach a cell through a
closure environment without taking the captured variable's own address, then
read it directly and through an inlined pointer helper. Harmless allocator
pointer operations outside the loop do not prevent the arithmetic reduction.

Cells and environments remain allocated outside the loop. Stored closures keep
their cells, and writeback makes the mutation visible after the helper and to
later calls. Managed/aggregate and addressed captures keep their existing memory
semantics. This is loop scalar replacement; general allocation elimination
would also need lifetime/escape proofs and matching ownership/destructor changes.

## Keyed sort

The library separates its existing key traversal into `__sort_keys` and its
stable index-sort/reorder into `__sort_key_order`. The wrapper and key traversal
fit the existing specialization bounds; the large merge/reorder stays out of
line. Keys still run once per element in input order, and not at all for fewer
than two elements. No extra arrays are built. The remaining key-call overhead
falls 2.05%, matching the equivalent loop. The comparator inside merge sort is
still indirect in both benchmark arms.

## Worker chunks

Release lowering specializes the library's `parallel_range` for a directly
supplied lambda or named function. Variants are keyed by helper, callback
parameter root and known code address. The worker lambda inherits that code
identity through the capture chain and up to three immutable local copies
(`g = f`). Reassignments, addressed copies and mut arguments fall back.

The actual function value/environment is still passed and captured normally;
each invocation uses its own environment. The worker borrows immutable scalar
captures, including its output pointer, into registers at entry. A per-index
callback becomes a direct call without a null check, which the ordinary inliner
can expand. Recursive/noinline callbacks stay calls, and the ordinary intrinsic
exclusions still apply. The final benchmark worker loop is
shift/store/increment/compare/backedge with no callback machinery per index.

The pool, worker-job closure ABI, atomic refcounts, per-chunk copy of the callback,
cleanup and race checking remain in use. The budget is 32 generated variants per
compilation (normally two per body); exhaustion uses the original helper/worker.
General escaping callbacks, partial applications and forwarded unknown bodies
are not specialized. Watch builds use the original path because their stable
function keys do not yet describe variants. This is specific to `parallel_range`,
not a general function-value monomorphizer.

## Size and validation

Compiler release binary: **7,587,584 → 7,658,648 bytes (+0.937%)**.
Benchmark release binary: **203,088 → 207,320 bytes (+2.084%)**.

Suites run serially, with scratch under `~/dev/tmp/fnvalues2` and audio/display
disabled:

- `tools/bootstrap.sh`: **bootstrap ok**, self-compilation is a fixed point.
- `python3 tools/runtests.py`: **28 passed, 0 failed** (C bootstrap).
- `python3 tools/runtests.py --compiler sloppy`: **1,365 passed, 0 failed**.
- `python3 tools/runtests.py --compiler sloppy --release`: **1,359 passed, 0 failed**.
- All six new tests pass in native debug/release and arm64 release under
  `SLOPPY_ARM64_RUN=qemu-aarch64-static`. The three previous portable
  `fnvalue_inline*` cases also pass on arm64. A broader arm64 fnvalue run is
  **9 passed, 1 failed**: existing `fnvalue_intrinsics` needs C dynamic loading,
  which the static arm64 runtime does not implement; both native suites pass it.
- All `value_copy_*`, `aggregate_copy_alias`, `affine_versioning` and fnvalue
  cases are included in the full native suites.
- `tools/parcheck.py --workers 4`: **84 comparisons passed** across native, arm64
  and macOS; **48 additional comparisons passed** on the new cases (debug/release,
  with/without debug information).
- Both speedchecks against `9125f9c` pass the 1% limit, including release compile
  instructions. The worst increase is **0.48%**. Raw output is in `measurements2.json`.
- The initial round checked wasm32 environment pointers (`M_HDR | 4`) by build/IR
  only. The follow-up below adds both full Node wasm suites.

Rounded compile G-instruction counts from the release speedcheck:

| Input | Default before → after | Release before → after | Release change |
| --- | ---: | ---: | ---: |
| bench/big.jo | 1.309 → 1.310 | 3.354 → 3.356 | +0.06% |
| compiler/main.jo | 8.416 → 8.420 | 8.416 → 8.420 | +0.05% |
| examples/rebound/rebound.jo | 0.756 → 0.757 | 1.870 → 1.879 | +0.48% |
| examples/breakwater/breakwater.jo | 1.156 → 1.157 | 2.872 → 2.882 | +0.35% |

The compiler's own build manifest requests release in both columns. Library
comparisons, including the integrated renderer changes, rise at most 0.43%.

New cases cover empty/single/multiple iterations, mutations observed after the
call, stored readers, per-iteration cells, nested lambdas, internal callback
returns, raw addressed-cell aliases, narrow overflow, floating captures,
stable ascending/descending merge ties, key-call counts, copy-on-write,
managed/panicking keys, read-only parallel captures, different environments for
one body, unique mut-array per-index writes, named/noinline and recursive bodies,
nested jobs/lambdas, managed/aggregate output, allocation balance, clone-budget
fallback
and a parallel callback panic. The previous tests retain recursion, bounds/explicit
panics, intrinsic exclusions, aggregate values and stored/reassigned callbacks.

## Reproduce

```sh
mkdir -p "$HOME/dev/tmp/fnvalues2/tmp"
export TMPDIR="$HOME/dev/tmp/fnvalues2/tmp" SLOPPY_EMIT_WORKERS=1
python3 bench/fnvalues/measure.py --compiler /path/to/baseline/sloppy --scratch "$HOME/dev/tmp/fnvalues2/before"
python3 bench/fnvalues/measure.py --compiler bin/sloppy --scratch "$HOME/dev/tmp/fnvalues2/after"
python3 tools/speedcheck.py --base 9125f9c
python3 tools/speedcheck.py --base 9125f9c --release
```

`measure.py` saves release IR, binary size and raw samples, compares checksums,
honors `TMPDIR` and forces one emission worker and one runtime thread. It requires
Linux hardware instruction counters and fails if they are unavailable. No wasm
program is run by this measurement.

## Wasm entry repair and full wasm validation

The worker specialization is restored after its revert at `d83dea4`. The new
parallel-panic test exposed a separate entry-adapter bug, also reproducible with
the reverted compiler: an inferred `main` returning an array leaves its pointer
on wasm `__start`'s void stack. The adapter now drops a non-exit-code result
according to the lowered function's return signature. New tests cover array,
f64 and f32 main results; the existing integer-main test still checks exit codes.
The parallel worker code and its bounded specialization are unchanged.

Node wasm game simulations receive a 90-second correctness deadline (native
remains 20 seconds). `skybarons_pick` produces byte-identical wasm with the
reverted and fixed compilers and matches its expected output with the longer
deadline. The filesystem fixtures used by `glob_backslash` and `http_forms` are
initialized by their native tests before the wasm suites: wasm `mkdir` is a stub,
whereas Node file I/O uses real directories. Both failures reproduce on the
reverted compiler with fresh scratch. No example or game source is changed.

Validation on the restored compiler:

- Self-compilation is a byte-identical fixed point.
- Full wasm debug: **433 passed, 0 failed**.
- Full wasm release: **433 passed, 0 failed**.
- Native fnvalue and main-return regressions: **13 passed in each mode**.
- **32 Windows builds passed**: all fnvalue/main-return cases, integer main,
  the benchmark and the compiler, with default/release flags.
- `python3 tools/parcheck.py --workers 4`: **84 comparisons passed**.
- The original parallel-panic repro validates and reaches its expected panic.

Raw follow-up results and baseline checks are in `measurements2.json`.
