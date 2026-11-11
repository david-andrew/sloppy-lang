# Array header hoisting: measurement and stop decision

Measured at `b16c61999561bd009c231fd5b248139e7eeb3e7f`, 2026-11-11,
Intel Core i7-6700 desktop (host name `redfox`), x86-64 Linux, GCC
16.2.1 20261029 with `cc -O2`. Sloppy was bootstrapped from this checkout,
then used with `--release` and `SLOPPY_EMIT_WORKERS=1`.

**Stop decision: further array-header motion does not meet the requested 10%
instruction reduction on these kernels. No compiler change was made.** The
ROADMAP's claim that lengths are reloaded in the hot matrix inner loop is stale.
This is a bound for these kernels at this revision, not a claim about every
program or about elapsed-time speedups.

## Workloads and instruction counts

`headers.jo` and `headers.c` contain the same three kernels, each with parameter,
local, and global array storage. Parameters are ordinary C pointers without
`restrict`; Sloppy's destinations are `mut` arrays. Each program prints an
observable result. Inputs and iteration counts match:

- Matrix: 64 x 64, eight repetitions, i/j/k order, exactly
  `c[i * n + j] += a[i * n + k] * b[k * n + j]`.
- Stencil: 65,536 elements, 32 in-place sweeps,
  `c[i] = (c[i - 1] + c[i] + c[i + 1]) * 0.25`.
- Histogram: 262,144 indices cycling through 256 buckets, eight repetitions,
  `h[x[i]] += 1`.

Whole-process user instruction counts, including initialization and output;
median of three hardware-counter runs. No wall-clock measurements were used.
The counter was `tools/icount.c` with only its output precision changed in a
scratch copy. Raw samples and Callgrind bounds are in `measurements.json`.

| Kernel | Storage | Sloppy instructions | C -O2 instructions | Sloppy / C |
| --- | --- | ---: | ---: | ---: |
| Matrix | mut parameter | 41,785,792 | 17,319,984 | 2.413 |
| Matrix | local | 37,853,790 | 17,354,896 | 2.181 |
| Matrix | global | 42,344,243 | 17,319,977 | 2.445 |
| Stencil | mut parameter | 21,678,388 | 17,088,184 | 1.269 |
| Stencil | local | 21,678,467 | 17,088,823 | 1.269 |
| Stencil | global | 21,678,541 | 17,088,216 | 1.269 |
| Histogram | mut parameter | 29,900,539 | 11,943,394 | 2.504 |
| Histogram | local | 29,900,698 | 11,944,143 | 2.503 |
| Histogram | global | 29,900,442 | 11,943,391 | 2.504 |

There is no before/after compiler comparison: implementation stopped at the
measurement gate. Rebuilding the unchanged compiler would measure the same
behavior. Small differences between reproductions include process startup,
argument lengths, and the compiler input path; ratios rounded to two decimal
places are stable.

## Why hoisting more headers cannot close the gap

Release lowering already calls `fp_begin` (`compiler/lower.jo`) before range
loops. It caches stable array pointers and guarded lengths, handles uniqueness
for written arrays, and respects changes, escapes, captures, and calls. This is
separate from `lx_hoist` in `compiler/loops.jo`. Inspection of `--release --ir`
and `objdump -d` confirms **zero header loads in the hot inner loop of all nine
kernels**, including their checked fallback copies. Histogram's input-building
comprehension does have header accesses and allocation calls; those are
initialization, and cannot be treated as an unchanging-header loop.

For example, matrix_param's three `load ... c=72 imm=8` lengths are before the
k loop. The fast k loop uses the cached pointers, drops the c and a checks, and
keeps only the b check. In the measured binary:

```asm
# Before k: length reads, outside the backward branch span
4054fb: mov  0x8(%r8),%rax
40551a: mov  0x8(%rcx),%r15
405534: mov  0x8(%rcx),%rsi

# Inside k: b[k*n+j], checked against that cached length
405606: mov  %rbx,%r10
405609: imul %rdi,%r10
40560d: add  %r14,%r10
405610: cmp  %rsi,%r10
405613: jb   405628
# ... panic on the other path ...
405642: cmp  %rdi,%rbx
405645: jl   4055e0
```

`lx_decomp` handles addition/subtraction of the counter and invariant terms,
not multiplication of the counter by an invariant n. Hoisting lengths cannot
make `b[k * n + j]` eligible. C also strength-reduces addresses to pointer
increments and keeps the c accumulator in a register. Sloppy still performs
inner-loop multiplication, reloads, and address arithmetic.

Stencil already versions away every inner bounds check. Its Sloppy fast loop
has ten instructions per element, versus eight in C: C carries previous values
between iterations and increments a pointer. More header motion does not
provide either transformation.

Histogram's lengths are also invariant before the scan. `x[i]` can be checked
over the range, but `h[x[i]]` is data-dependent. The current versioner declines
scalar versioning with fewer than two eligible checks (`checks.len() < 2`),
leaving both checks here. The remaining gap includes explicit load/add/store
for the bucket versus C's memory increment, and more expensive input
construction. Changing the one-check cutoff or proving a data-dependent
index range is a separate optimization.

### Conservative bound, independently counted with Callgrind

With `--dump-instr=yes --collect-jumps=yes`, sum instruction costs inside the
fast inner backward branch span and subtract from the entire process. This
counts **all** work outside that loop as removable, including initialization,
printing, version guards, and unrelated arithmetic, so it greatly overestimates
what header motion could save:

| Kernel | Parameter | Local | Global |
| --- | ---: | ---: | ---: |
| Matrix: all instructions outside fast k loop | 4.64% | 5.82% | 5.90% |
| Stencil: all instructions outside fast element loop | 3.26% | 3.26% | 3.27% |

Since headers already do not obstruct inner check elimination, further header
motion leaves these inner loops unchanged. Even this impossible best case
misses 10%. The spans and exact costs are recorded in `measurements.json`.

Histogram initialization includes allocation calls, so deleting all work
outside the scan would not be a useful bound. Instead, sum the enclosing
repeat-loop span and subtract the scan span. Its entire repeated setup,
including lengths, pointers, and repeat-counter work, costs just **128 / 120 /
184 instructions** for parameter/local/global storage: each under **0.001%**
of the complete run. Moving those headers cannot change the eligibility of
either inner check.

Callgrind and hardware totals are kept separate. They account for REP
instructions differently (notably histogram construction), and instrumentation
changes startup slightly. Bounds use only Callgrind costs and totals.

## Reproduce

From the repository root:

```sh
mkdir -p ~/dev/tmp/hoist/tmp
export TMPDIR=~/dev/tmp/hoist/tmp
python3 bench/headers/measure.py
```

The script builds both programs, writes release IR and both disassemblies to
scratch, measures the nine variants three times, checks their numerical outputs
against C (relative tolerance 1e-10), and saves `counts.json`. It uses the
project's hardware counter, falling back to Callgrind if counters are denied.
`--compiler` selects a saved compiler; `--scratch` selects the artifact directory.
It neither measures elapsed time nor launches windows/audio.

For per-instruction costs, run the scratch Sloppy binary with a mode such as
`matrix_param`, `stencil_local`, or `histogram_global`:

```sh
valgrind --tool=callgrind --dump-instr=yes --collect-jumps=yes \
  --callgrind-out-file="$TMPDIR/matrix.callgrind" \
  ~/dev/tmp/hoist/headers-sloppy matrix_param
```

## Validation and scope

- Baseline bootstrap reached `bootstrap ok`, a self-compile fixed point. The
  existing bootstrap script's hardcoded `/tmp/sloppy*` paths were substituted
  with `~/dev/tmp/hoist/tmp/sloppy*` only in the executed script, without editing
  the repository script.
- All nine benchmark outputs match C; the retained measurement script was also
  run successfully, verifying all nine outputs with three samples per variant.
- Compiler files, including M_BITS alias handling, are unchanged. No correctness
  tests were added because no optimization was implemented.
- Full debug/release suites, arm64 correctness gates, speedcheck, and the
  standard `bench/rt` runtime measurements were not run: the task explicitly
  stops at measurement when the proposed optimization is below 10%. No
  performance improvement or correctness-gate pass is claimed.
