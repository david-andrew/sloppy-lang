# Function effects: design and instruction-count study

Study of `ecd04abdcc3185dcdc276331ccca2779cd20cd55`, 2026-11-14/15. This is a
proposal and measurement record. During the original study, no repository
compiler, library, or example source was changed. Probe programs and measurement
artifacts are in `~/dev/tmp/effects/`. Source line numbers below refer to that
commit.

The largest observed software-rendered game-frame traffic ceilings are **Rebound
3.0%, Breakwater 4.5%, Aces 1.6%, and Dunes 3.7%**, over 16 observations at 15
frame positions through the first 360 frames. These conservative pools include
required work, not just removable instructions. The compiler self-build has a
much looser **26.8%** pool; this study does not prove that 5% of it is
removable. Recommend deferring the full system, with at most a focused compiler
experiment subject to the gates below. The subsequently authorized compiler
experiment and its failed performance gate are recorded in the final section.

## Current behavior

### Permission to write is different from knowledge of what a call does

A function signature contains parameter/result types and a `mutmask`, including
when it is a function value (`compiler/check.jo:138`, `compiler/types.jo:188`).
`__check_fn_body` marks parameters `LF_PARAM` and optionally `LF_MUTPARAM`
(`compiler/check.jo:3410`). `finish_arg` checks that a mut argument is a place,
marks it `NF_MUT`, and records address/mutation exposure
(`compiler/expr.jo:1358`). Ordinary value parameters cannot be written;
`check_place` follows fields, indexes, narrowed aliases and capture roots to
check the owning variable (`compiler/expr.jo:665`). Raw pointer writes have
separate, explicitly unsafe reachability.

Inside a function, `global x` selects an existing global for assignment;
otherwise assigning that name normally declares a local. The declaration is
checked and erased (`compiler/check.jo:964`). `note_global_write` records
function-written globals; this lets lowering distinguish startup-only globals
from globals that can change during a call. This is not an inferred complete
call contract.

Closures semantically capture variables by reference. `capture_in` records the
outer/inner local relation; `capture_root` and `note_write` mark captures that
must share a cell (`compiler/check.jo:1898`, `1913`, `1923`, `1931`). An
unchanged capture may be copied without observable difference. A changed capture
must be a shareable variable declared with `=`; a temporary element alias cannot
become such a shared variable (`compiler/check.jo:1941`). A closure cannot write
a read-only parameter merely by capturing it (`compiler/expr.jo:687`). These are
language/lifetime rules, not all removable special cases.

### There already are interprocedural summaries

The roadmap is an extension/consolidation of existing analyses, not a proposal
to introduce the first call analysis:

* `FnWrites` has `all`, a set of written globals, direct call edges and a set of
mentioned globals (`compiler/lower.jo:4165`). `fw_scan` collects one body's
information, skipping nested lambda bodies. `fn_writes` walks direct callees,
caching each queried root's transitive answer. Calling a function value or C
function pointer sets `all` (`compiler/lower.jo:4192`, `4223`). This walk is
recursion safe through a visited set, but separate roots can repeatedly walk the
same graph; it is not one SCC-based solve. * `fn_writes_named` deliberately
ignores the unknown part of indirect calls while following named calls
(`compiler/lower.jo:4176`). It supports static rejection of known conflicts; it
is **not** a proof that the unknown part is harmless. * `fn_resizes` separately
follows the direct call graph and records replacement or resizing of global
arrays (`compiler/lower.jo:4253`). An element update differs from replacing the
array. These resize facts do not model every backing-storage change: for example
`reserve` is important to pointer stability even though it need not change
length. * `calls_leave` uses both writes and mentions: reading/copying a global
can change sharing even without writing it (`compiler/lower.jo:4137`). A mut
parameter can designate a caller's global, so any relevant global effect can
defeat the proof.

The checked AST distinguishes direct calls (`aux == 0`), closure calls (`aux ==
1`) and C function-pointer calls (`aux == 4`); `compiler/expr.jo:1955`, `2085`.
Direct extern declarations have no inspectable body. A new sound summary must
explicitly classify extern/FFI boundaries, rather than infer purity from an
absent body.

### Special cases relevant to the roadmap

These are the concrete sites a replacement must preserve or simplify. Much of
what users experience as a check is actually performed during lowering.

| Site | Current rule and why it exists |
| --- | --- |
| `compiler/check.jo:1913`, `1941` | Shared captures are distinguished from snapshots; mutable element aliases cannot be captured for later mutation. Effects cannot extend the lifetime of an element place. |
| `compiler/check.jo:3047` | Combined `loop mut` elements become `LF_ALIAS | LF_ELEMALIAS`, aliases of an indexed place. SOA combined aliases have a separate restriction. |
| `compiler/expr.jo:665`, `1358` | Check mutability of the root place and mark mut argument exposure, including capture/narrowing roots. These permission checks remain. |
| `compiler/lower.jo:1014` | `call_args` retains every managed borrowed value when **any** argument is mut; aggregate copies use a more selective shared-root rule. Pinned boxes also get a statement lifetime reference. |
| `compiler/lower.jo:1050` | `shares_mut_root` recognizes overlap for aggregate snapshotting. An effects query still needs alias/actual-place overlap. |
| `compiler/lower.jo:1060`, `1073` | `copy_through` passes a global/mut-parameter heap element through a temporary if the call may invoke unknown code; it cannot safely hand out an address into movable storage. |
| `compiler/lower.jo:1086`, `1168` | Copy-in freezes indexes and records lengths/bytes. Copy-back finds the place again and checks for removal, movement or conflicting change before overwriting it. Fixed-to-dynamic mut conversion has its own length check (`1128`, `1145`). |
| `compiler/lower.jo:1209` | `borrow_may_change` treats startup-only globals, transitive writes, later argument evaluation, ordinary locals, held/element views, mut parameters, aliases and shared captures separately. |
| `compiler/lower.jo:1252` | `mut_alias_check` rejects same-call container/element overlap, changes during later argument evaluation, shared-capture unknown calls, named writes to globals, and possible mut-parameter/global aliases. Indirect effects use copy-back rather than rejecting nearly every callback API. |
| `compiler/lower.jo:1661` | A closure value read from replaceable storage is kept alive across its own invocation. Its environment might otherwise disappear while the closure is running. |
| `compiler/lower.jo:1840`, `2140` | Formatting and binary operands also preserve borrowed values across code that might replace their source. Looking only at explicit call arguments misses these. |
| `compiler/lower.jo:3941`, `4066` | Held views and `unchanged_by` make local/path lifetime proofs; `may_write_root` separately scans direct writes, mut actuals, raw views and call effects. |
| `compiler/lower.jo:4335`, `4366`, `4399` | A mut parameter's fixed length requires a closed function. `harmless_call` recognizes constructors and core-library calls without callbacks using a library-path rule. |
| `compiler/lower.jo:4610`, `4634`, `4836` | Ordinary iteration can borrow an unchanged array instead of retaining a snapshot. Mut iteration rejects explicit path resizing and named callee resizing separately. |
| `compiler/lower.jo:4899`, `5032` | Fixed-path/header caching and uniqueness hoisting use separate scans. Captures, aliases, escape, lambda creation and calls limit eligibility. `uq_begin` rejects a mut-parameter hoist on any non-harmless call, even where more precise facts could suffice. |

Effects should replace duplicated *may-change* queries, not erase snapshots,
alias checks, ordered evaluation, copy-back semantics or lifetime restrictions.
`tests/t/borrow_args.jo`, `mut_elem_callback.jo`, `mut_elem_moved.jo`,
`mut_elem_changed.jo`, and `closure_cells.jo` are existing semantic regressions
that any implementation must continue to satisfy.

### Reference counting, bounds and calls in release builds

An array/string object pointer addresses refcount, length and capacity words at
byte offsets 0, 8 and 16; element payload begins at 24 on this target. Object
header operations have `M_HDR` provenance in IR (`compiler/ir.jo:57`). Normal
parameters are **already borrowed** (`compiler/lower.jo:1`): a read-only call
does not ordinarily get a blanket retain/release pair. Storing a borrowed value
as an owned value retains it; call/constructor results are owned, and borrowed
owned temporaries are released at statement end (`lower.jo:378`, `386`).

Release lowering expands the common RC paths (`lower.jo:274`, `289`, `314`).
There is a multithreading-active test, null/immortal tests, and inline header
increment/decrement. The final decrement calls the appropriate destructor/free
helper. Parallel activity needs the atomic runtime path (`lib/core/rt.jo:438`,
`446`). Arrays with managed elements and boxes need typed helpers; their
elements/captures also own references. Counting calls to `__rc_inc` or
`__rc_dec` alone therefore badly undercounts release RC work.

Before an element write, `arr_unique` checks for a non-null pointer with RC 1;
otherwise a typed helper clones and retains managed elements (`lower.jo:818`,
`5661`). It emits `A_RC1` so later operations can reuse the proof. `fp_begin`
can cache pointer and length and ensure uniqueness before a loop. `uq_begin` can
hoist uniqueness separately. These optimizations already remove most repeated
checks in simple numeric kernels.

A release bounds check tests null and compares the unsigned index to the length,
calling `__panic_bounds` only on failure (`lower.jo:747`). Known ranges, fixed
lengths, fixed paths and versioned loops can remove/hoist it.
`compiler/loops.jo:186`, `282`, `754`, `879` are later IR consumers. A
data-dependent index (histogram bucket, for example) still needs its check even
when every callee is pure.

CSE separates integer, float and header memory generations. An ordinary
returning call kills **all** three, including the `A_RC1` header fact;
`compiler/opt.jo:371`, `437`, `452`, `500`, `585`, `590`. Loop preanalysis also
sets all kill bits for a returning call (`opt.jo:1040`, `1067`). This can leave
repeated header loads/RC tests, and keeps related bounds predicates from folding
when their operand reloads differ. It does not mean every call reloads every
live object: already materialized values, cached fixed paths and register values
can survive. Independently, LICM and versioning reject returning calls in
relevant candidate loops (`loops.jo:299`, `772`). A call's register-clobber ABI
is a separate constraint, unchanged by a memory summary.

### Function values today

A closure has code and environment words; indirect invocation loads both and
checks for a missing code pointer (`lower.jo:1661`). The function type carries
the mutmask, not globals/escape/effect information. Its environment uses the
same ownership system as other managed values. Unknown closure/C-pointer calls
are conservative barriers to memory optimization and global-write proofs.

Release compilation optimizes functions, inlines callees before callers,
optimizes changed callers, then runs final loop work and emission
(`compiler/main.jo:221`). Small known closure values are already resolved or
expanded by bounded inliner analyses (`compiler/inline.jo:210`, `228`, `257`,
`383`). They deliberately preserve real captured environments. `parallel_range`
has bounded callback specialization (`lower.jo:48`, `81`; at most 32 clones).
This reduces the remaining opportunity: a visible simple callback is often
already direct/inlined. Unknown values, stored callbacks, reassignment and
larger helpers remain conservative. Effect metadata would not itself remove
indirect-call overhead.

## Measurement

### Two diagnostic probes

`~/dev/tmp/effects/probes.jo` has a direct `@noinline read_only(int)` call, an
unknown callback parameter supplied with that same function, and `sink(out: mut
int, xs: int[])`, which adds `xs.len()` to the scalar. Release IR shows:

* `with_call(xs, n)` makes the mut array unique and caches its length before the
loop, despite calling `read_only` each iteration. `no_call` has the same
placement. Both still check the loop's access to element zero: effects alone are
not a proof that the array is nonempty. * `with_callback(xs, f, n)` repeats the
pointer/RC/length work **inside** the loop. The callback type has no way to
communicate that this particular invocation cannot reach the caller's array. *
`call_borrow(n)` retains the borrowed global array before calling `sink` and
releases it afterward. Callgrind attributes 210 inline-guard instructions to ten
iterations, or 21/iteration, out of 300 self instructions for that caller.
Source inspection proves that the scalar output cannot overlap the array
binding, later argument evaluation is inert, and this sink does not replace any
owner or retain the array. This is a concrete removable pair, not a
whole-program speedup estimate. The callee still needs to read the length.

The probe is deliberately tiny. Its startup/formatting costs dominate the whole
process; its percentages must not be substituted for application results. The
final probes and application runs use a compiler rebuilt from the studied
commit.

### Application runs and counters

All measurements ran on the shared i7-6700 desktop, whose configured hostname is
`redfox` (not the i5 laptop at `192.168.1.79`). One software worker and one
emission worker were used. Heavy builds/runs went through
`~/dev/tmp/sloppy-tw.py`; the first jobs waited about 41–42 minutes for tokens.
There were no windowed, audio, GPU-timing or wall-clock benchmarks.

The compiler was rebuilt from the studied source and then compiled itself in
release mode. The initial binary, self-build output and separate `--ir` build
are byte-identical: 7,668,304 bytes, SHA-256
`0f13d44c31ce2e5611e08ec0a897b8d934341e7e123b8aa10a4b055c83b033c2`. All measured
programs use that compiler and `--release`; release IR and `objdump` disassembly
were retained.

Games use the existing `bench/games/profile.py` setup and scripted inputs, via
an instrumented **scratch library copy**, with seed 12345, fixed 60 Hz input,
empty saves, a 320×180 window and 160×90 software rendering. The initial run
measured frames 120–124. A follow-up sampled frames 60, 90, 120, 150, 180, 210,
240, 270, 300, 330 and 359 using the **same binaries**, switching Callgrind
instrumentation off between samples. That is 16 observations at 15 distinct
frame positions, including a repeated frame 120. Each sample includes update,
draw and submission; startup, warmup, screenshot and exit are excluded.

The game table uses the **largest individual observed frame ratio**, rather than
averaging a late spike into an opening-play interval. Native and Callgrind
captures at both frames 125 and 360 are byte-identical for all four games; frame
360 captures were inspected and show active gameplay. The temporary follow-up
profiling helper was restored byte-for-byte afterward. These samples still do
not bound every scene or the GPU path; software rendering in the denominator
matters. Whole-process compiler/kernel counts are separate workloads.

`tools/icount.c`, copied to scratch with integer-precision printing, supplies
whole-process retired user instructions for the compiler/kernels. The existing
frame hooks use `perf_event_open` for native game instruction totals. Callgrind
3.28.0 with `--dump-instr=yes` supplies per-address attribution over the same
selected frames or whole kernel process. A feature probe reports AVX2 enabled
both natively and under Valgrind. Screenshot/termination dumps are excluded from
game attribution.

### What the ceiling counts

`classify.py` identifies inline retain/release regions from their cold runtime
arms, COW guards and clone paths, branches around bounds/copy-back panics, and
64-bit object-shaped integer loads at offsets 0/8/16 with adjacent null/pointer
setup. It also includes integer global loads as possible pointer/header reloads.
Floating-point vector/record loads and narrow integer field loads are excluded:
they are not object-header words. The IR-to-native function order and header
load widths were audited; the per-function static header-load census has no
count deficits. A guard-distance audit found no missed success-edge guards
beyond the classifier window in the measured executables. Equal census counts alone are not a proof of provenance.

Aggregate snapshot-copy patterns adjacent to typed copy helpers or inline RC
regions are included, with conservative neighboring address setup. These can
include unrelated nearby copies; they are not an exact census of borrow pins.
Typed ownership helpers are counted with their **inclusive subtrees**, so
allocation, freeing, element drops and copying induced by RC/COW are included.
Their self cost is not added a second time. Possible nested entry overlap
through other runtime routines makes this an overestimate. Functions containing
copy-back movement checks are widened to their whole self cost, with their
comparison helper cost, to cover inline copies and validation conservatively.
The union of tags avoids double-counting overlapping inline regions. Ordinary
integer fields and globals still generate false positives; that is deliberate.

The numerator is this broad Callgrind attribution envelope; the denominator is
native retired instructions. Callgrind counts REP iterations differently from
the hardware, so its helper-subtree cost can overstate copies. Do not divide by
Callgrind's inflated whole-frame total and call that a native percentage.
Percentages below are rounded **up**. Raw totals and classifications are in
`summary.json`, `*.counts.json` and the retained profiles.

These are **ceilings on the requested ownership/check/header traffic**, not
predicted speedups or counts proved removable. They deliberately include first
COW checks, required ownership and data-dependent bounds checks. They do not
bound general data-load CSE, arbitrary arithmetic changes, call hoisting, new
vectorization, or all secondary register-allocation effects. No optimized
compiler was implemented, so the demonstrated application speedup is zero.

| Release workload / observed unit | Native instructions | Broad traffic ceiling | Ceiling / native instructions |
| --- | ---: | ---: | ---: |
| Rebound, frame 180 | 12,201,027 | 362,680 | **3.0%** |
| Breakwater, frame 359 | 169,762,616 | 7,573,992 | **4.5%** |
| Aces, frame 330 | 132,569,122 | 2,010,600 | **1.6%** |
| Dunes, frame 121 | 105,581,454 | 3,888,715 | **3.7%** |
| Compiler, release self-build | 8,441,750,448 | 2,256,903,829 | **26.8%** |
| Compiler, release build of headers kernel | 255,789,269 | 66,397,739 | **26.0%** |

The entire counted category is below 5% in **every observed software-rendered
frame of all four games**, even with required work and conservative attribution
included. Recommend **not building a full effects system for that game-runtime
payoff**. This statement cannot be generalized to other scenes/renderers, nor to
the compiler: its broad ceiling is much larger and needs a more selective proof
before implementation.

### Kernels: required checks are not effects opportunities

| Kernel / command mode | Native instructions | Broad traffic ceiling | Effects-only upper, with exclusions below |
| --- | ---: | ---: | ---: |
| Histogram, mut parameter | 21,515,488 | 23.19% | 3.69% |
| Matrix, mut parameter | 38,578,261 | 1.47% | 0.02% |
| Stencil, mut parameter | 21,682,541 | 0.41% | 0.18% |
| N-body, 5,000,000 steps | 3,690,017,938 | 2.31% | 0.82% |
| Sieve, 20,000,000 limit | 457,565,446 | 22.31% | 0.003% |
| Function values, each/hof | 2,833,545 | 2.86% | 2.86% |

- Histogram's 2,097,152 bucket updates execute 4,194,304 successful comparison/
  branch instructions. The bucket index is data-dependent; these checks cost
  about **19.5%** of native runtime and do not become redundant from a no-effect
  call summary. The scan has no returning call. Leaving that call-free kernel's
  checks/headers intact gives the smaller 3.69% ceiling, mainly initialization.
- Matrix and stencil have call-free numeric scans with pointer/length and
  uniqueness already handled before the hot loops. Their numeric range/version
  guards are not a missing call-effect proof. The smaller column retains RC/COW
  entry work and all tagged work in returning callers outside those scans.
- N-body similarly has no ordinary returning call in `advance`'s numeric work.
  Even counting all 30 million entry-COW guard instructions as removable gives
  only about 0.82% with the remaining call-sensitive work. Removing entry guards
  may require caller uniqueness/specialization beyond the proposed summary.
- Sieve's arithmetic loop, native addresses `[0x4010b8, 0x40113a)` in the saved
  executable, executes 457,552,316 non-REP instructions and has no returning
  call on a successful execution. Keep that loop unchanged: the **entire rest of
  the native process** is only 13,130 instructions, 0.00287%. Its large
  bounds-check share is a range/fresh-allocation-fact problem, not call effects.
- The `each/hof` benchmark already inlines the callback and caches its private
  scalar capture in the scan. Its broad under-3% ceiling includes
  initialization, closure construction and cleanup, not just potential callback
  savings.

These exclusions concern the proposed call-effect consumers. Adding function
return ranges, arbitrary freshness contracts or a new ownership optimizer would
be a different project and would need its own bound.

The remaining `bench/rt` programs were also run at their repository defaults;
all five `bench/rt` native and Callgrind outputs agree exactly.

| Kernel | Native instructions | Broad traffic ceiling | Effects-only upper |
| --- | ---: | ---: | ---: |
| Fannkuch, n=10 | 2,144,073,891 | 30.64% | 0.001% |
| Mandelbrot, repository default | 1,379,230,377 | 0.19% | 0.19% |
| Spectral norm, repository default | 1,710,703,883 | 0.01% | 0.01% |

Fannkuch is another important false lead. Its broad bucket includes required
permutation-index checks and nearby ordinary copies. The measured non-REP CFG
cycles without returning calls execute 2,144,061,565 instructions; all remaining
native work is only 12,326 instructions, 0.000575%. Keeping those call-free
cycles unchanged bounds effects-only improvement below 0.001%. The components
are noncontiguous CFG sets, not a claim that every instruction between their
lowest/highest addresses is call-free; `fannkuch-bound.py` records the analysis.
Setup/cleanup and every executed callee remain in the allowed budget. Mandelbrot
and spectral norm are below 0.2% and 0.01% even before such pruning.


### Compiler attribution and compile-speed budget

The compiler is the exception to the small game ceilings. Self-build executes
47,634,280 inline RC-guard instructions (0.56% of native instructions),
287,718,726 instructions in COW guard/slow-path regions (3.41%), and a
294,178,269-instruction ownership-helper subtree envelope (3.49%). These
categories overlap and must not be summed naively. Including header/bounds/
global-load candidates yields the much looser 26.8% ceiling above.

The main places to inspect are `optimize`, `o_emit`, `ht_put`, `ht_slot` and
`__arr_clone`, not just indirect callbacks. For example, `ht_put` alone executes
65,785,932 COW-region instructions and 48,730,320 bounds-guard instructions.
That does **not** make both costs removable: proving `ht_slot`'s returned index
fits every table array is a range/postcondition proof, and first-entry
uniqueness requires ownership facts. Some clones preserve actual IR snapshots. A
write set cannot erase these costs merely because the callee reads a different
binding. This study does not establish that 5% of compiler runtime is actually
removable.

Existing global write/resize-summary query entries account for 62,354,300
inclusive Callgrind instructions in self-build, about 0.74% of native work.
Related loop/path scans account for 219,388,099 inclusive instructions, about
2.60%; these measurements overlap and are not additive. Both include useful work
a replacement must still perform. On the smaller headers compilation the
write-summary group has no executed entries, while the loop/path group has
3,855,895 instructions (about 1.51%). An unconditional new whole-program scan
would impose a tax on cases that currently need no global-write query.

The final self-build IR has 2,937 functions, 18,446 ordinary returning direct
call sites and 185 `calli` sites. These are post-inlining code counts, not the
exact source-summary graph or a claim that 185 callback sites are hot. A
bounded, demand-driven solver is plausible at this scale, but no measured
implementation cost or benefit is available.

### Reproduction and retained evidence

All artifacts are under `~/dev/tmp/effects/`: `environment.json`,
`compiler-binaries.json`, `measure.py`, `extra.py`, `classify.py`,
`summarize.py`, `details.py`, `ir-audit.py`, `sweep.py`, `original-frames.py`,
`assemble-final.py`, `analyze.py`, `guard-audit.py`, probe sources, IR/build logs, disassemblies,
Callgrind dumps, native count logs and replay PNG/hash records.
`final-summary.json` gives the selected per-game frame maxima; `sweep/` and
`original-frames/` retain all frame classifications and aggregate summaries.
Keep these for coordinator review. The instrumented library is under
`games/lib-ir`; the repository's examples and libraries are unchanged.

The main run was:

```sh
# From the studied worktree. All output/scratch paths are under this directory.
export TMPDIR="$HOME/dev/tmp/effects"
export SLOPPY_LIB="$PWD/lib" SLOPPY_THREADS=1 SLOPPY_EMIT_WORKERS=1
~/dev/tmp/sloppy-tw.py -- ~/dev/slop-lang/bin/sloppy build --release \
  compiler/main.jo -o "$HOME/dev/tmp/effects/sloppy"
PYTHONUNBUFFERED=1 ~/dev/tmp/sloppy-tw.py -- python3 \
  "$HOME/dev/tmp/effects/measure.py" games
PYTHONUNBUFFERED=1 ~/dev/tmp/sloppy-tw.py -- python3 \
  "$HOME/dev/tmp/effects/extra.py"
PYTHONUNBUFFERED=1 ~/dev/tmp/sloppy-tw.py -- python3 \
  "$HOME/dev/tmp/effects/sweep.py"
PYTHONUNBUFFERED=1 ~/dev/tmp/sloppy-tw.py -- python3 \
  "$HOME/dev/tmp/effects/analyze.py"
```

`measure.py games` also runs the kernel/compiler phase under the same token. The
scripts assume this task-specific path. Archive the old results and remove only
this study's old dumps/output symlinks before rerunning: counting two runs'
dumps would double the numerator. The saved scripts now also set a task-local
Valgrind pipe prefix and suppress import bytecode outside scratch. Initial
profiling created a Python import cache under `bench/games`; that cache was
removed. No tracked source was edited.

## Proposed summary

Use an internal, inferred summary per checked concrete function instance. Do not
begin with new syntax, declared purity, a new function ABI, or an effect
parameter language. The core representation is a bounded set of rooted places
and a few independent flags:

| Facet | Required meaning |
| --- | --- |
| Ambient reads and writes | Globals and shared capture cells, distinguishing reads, content writes, whole-place replacement, length change and backing-storage change. Reads alone do not imply sharing. |
| Per-parameter access | The same distinctions relative to each formal root; a non-mut value parameter's own binding remains read-only, while raw pointees need separate treatment. |
| Sharing/retention | May temporarily create another owned reference during invocation; may keep one beyond return; may flow into the result, a global, an escaping closure, a mut output, raw/foreign storage or another thread. Track argument and captured-object provenance. |
| Callback applications | Which callback formal may be invoked and how its actual arguments relate to the caller's formal/capture roots. Unresolved invocation is top. |
| Control/runtime flags | May panic/unwind, allocate, execute opaque raw/FFI operations, or start/use concurrent work. These are distinct from writes. |

An element-write facet must conservatively include possible COW detachment. For
an element update, entry uniqueness plus no new sharing can discharge that
possibility; merely proving no resize cannot. Use a few fixed entry predicates
rather than an unrestricted symbolic cost formula.

`read-only`, `no-escape`, `no-share-during-call`, `no-resize` and
`no-storage-change` are different properties. A temporary owned copy can defeat
uniqueness without escaping. A returned alias flows to the caller, even if
nothing is stored in a global. Allocation can panic. A helper with no external
writes can still be observable through I/O, panic, blocking or callbacks; this
design does not license deleting/reordering it as a pure expression.

Start with whole formal roots and a small number of field projections. Use
bounded sparse sets (for example 32 global/capture entries, four projection
steps, eight callback applications); widen excess to the appropriate top.
Distinguish the caller's binding slot from the entry object and its reachable
storage: replacing a mut binding and copying its old object have different
effects. Unknown array indexes overlap. `reserve` changes storage even with
stable length; replacing a containing record invalidates descendant paths. Keep
length, storage and sharing facts separate in consumers. Caps are proposed
engineering choices, to be validated by a census rather than treated as language
limits.

### Computation and compile cost

After type checking/generic instance discovery, collect direct events and call
edges once **on demand**, retaining cheap place/type fast paths before querying
a summary. A new query solves its previously unsolved reachable subgraph;
settled nodes are cache boundaries. On a frozen direct graph, a settled node
cannot acquire a backedge to an undiscovered component, so this avoids today's
repeated root-by-root traversals without taxing programs that never need a
query. Callback-flow precision can demand incoming callers too; missing input
flow is top, never an empty set. Skip nested lambda bodies in the enclosing
function; each lambda has its own instance summary. Include implicit
formatter/equality/hash/helper calls, argument/default evaluation and cleanup,
not just source `.call` nodes. Externs, unknown primitives and raw pointer
operations default to top for reachable memory, retention and runtime flags; a
tiny reviewed runtime contract table can narrow known primitives, keyed by
intrinsic/declaration identity rather than name spelling or library directory.

Use SCCs and a monotone worklist over the call graph. Substitute callee formal
roots with actual places **before** joining across every edge, including
recursive backedges. Join aliases at the call site. Distinguish unknown ambient
memory from private locals, but do not assume a mut parameter cannot alias a
global. Callback application terms are instantiated with the supplied closure's
summary when known; unresolved terms conservatively widen. No recursion fuel
cutoff may return an empty summary. Keep bounded known-write witnesses even when
an opaque-call flag is set, so the one summary can answer today's
`fn_writes_named` query as well as the conservative optimization query. A
saturated/unknown result must select the existing safe pin/copy-back fallback,
not blanket rejection of callback APIs that work today. Exact diagnostics for
arbitrarily large transitive root sets cannot simultaneously be promised with a
fixed-size, strictly linear summary representation; preserve ordinary small case
diagnostics and make that widening tradeoff explicit before migrating the
checker.

With a bounded summary lattice and bounded projection/substitution operations,
each node changes a bounded number of times: O(AST + call edges), with a
potentially significant constant, measured in the checked instantiated program
rather than the unexpanded source templates. Exact unbounded global sets or
arbitrary polymorphic callback rows would invalidate that compile-cost claim.
Bound the total formal-root/field/callback state as well as each global set;
excess formal roots collapse to an all-parameters summary. Saturating sets must
remain saturated, and callback composition must be bounded too. Do not promise
strict linearity for an unrestricted exact analysis.

Replace `fw_*`/`fr_*` transitive walks incrementally with adapters over the
solved summary. Avoid a second AST walk per query or a dense function-by-global
matrix. Record a deterministic witness for diagnostics without copying complete
call chains into each summary. Reset/cache by compilation generation for
watch/REPL; late synthesized functions must either trigger dependency updates or
remain top until solved. Lowered ownership/helper effects need their own
conservative contracts: source-level no-write does not mean emitted code changes
no RC headers.

Initial planning estimates, **not measured implementation costs**: 500–900 lines
for collection/SCC solving and adapters; 400–700 for bounded closure/callback
flow and substitution; 500–900 for alias-aware lowering/IR consumers; 300–600
for regressions and instrumentation. Rough total 1,700–3,100 lines, larger if
public effect syntax or whole-program points-to analysis is added. A rough
planning estimate for an added bounded scan/solve is +0.5–3% compile
instructions before removing old analyses; this is a judgment, not a benchmark.
Set an acceptance budget of at most 1% additional compile instructions on
whole-program builds, with a target near zero net cost after old repeated scans
disappear. The current study cannot estimate that percentage reliably without an
implementation. Reject a stage that misses the project's compile-speed gate;
measure default builds and `check`, not just release builds.

### Carrying information on function values

Keep runtime values as the existing code/environment pair. Carry inferred
summary IDs in compiler value metadata, separate from interned structural
function types. A known lambda/function reference supplies a summary; copy,
branch merge, reassignment, return and capture propagate/join the information. A
join widens guarantees; it never preserves only the initializer's effect. A load
from an untracked container, an escaped/replaced cell, opaque return or foreign
callback becomes top. An uninitialized function value must remain a potentially
panicking invocation; effect bounds alone do not prove a non-null code pointer.
An invocation must also include effects through that particular environment's
captured roots. Knowing the code pointer does not make two closure environments
equivalent.

For a higher-order helper, preserve a bounded symbolic “applies callback slot k”
term so its effect can be instantiated at a call without cloning its machine
code. Otherwise one unknown callback in a widely used helper would poison the
whole helper's summary and discard the main benefit. Limit initial support to
immutable locals, direct arguments and known environments; widen complex flows
rather than introducing general points-to inference. Partial application
substitutes bound actuals into the invocation summary and records
capture/retention at creation; remaining formal indices are remapped. It does
not relax today's restrictions on binding mut arguments. Metadata lost across a
boundary loses optimization, never safety.

A symbolic callback term improves the *caller's* view of a helper; it does not
magically specialize the helper's compiled body. For body optimizations without
cloning, propagate the union of all known incoming callback summaries to each
formal slot of a closed, non-exported function. Unknown incoming flow widens
that slot to top. Include these value-flow edges in the same bounded fixed
point, and freeze the result only after all reachable callers are discovered.
This lets the probe's `with_callback` body benefit if every reachable call
supplies a harmless callback. Mixed callers lose that precision. Alternatively,
bounded effect-based clones could recover it, but add code size and compile
cost; defer them. Public callback contracts would be the other alternative. Do
not claim per-invocation body optimization merely from a summary attached to an
actual argument.

Only if real APIs later need an explicitly constrained unknown callback should
effects become part of callable compatibility. That would require subset
checking, variance, joins and serialization/versioning of contracts, plus
handling effects of captured environments. It is a separate language proposal;
adding an effect ID to `TypeInfo` without those rules would be unsound.

### Consumers and safety obligations

1. **Borrow/copy-in decisions.** A borrowed actual can stay unowned only if its
   original storage stays alive throughout all later argument evaluation and the
   callee, accounting for mut aliases, globals and shared captures. A no-retain
   guarantee alone is insufficient. Read-only values must also retain snapshot
   semantics when another actual can write overlapping storage. Remove the
   `any_mut` blanket reference only after proving relevant
   disjointness/stability. Preserve copy-back when an element's storage or
   identity may change.
2. **Fixed paths and COW.** A no-storage-change/no-replacement proof preserves
   an element address/header; a no-new-sharing proof preserves uniqueness.
   Length invariance alone proves neither. A future balanced-RC postcondition
   could preserve uniqueness on normal return despite temporary sharing; the
   initial consumer should require the stronger absence of sharing.
   Share/replacement through a callback or ambient alias invalidates the
   corresponding facts.
3. **IR memory generations.** Give call instructions a summary/provenance handle
   rather than overloading `Ins.c` (it already carries cold/noreturn/RC modes).
   Prefer compact call-only IDs/side tables to growing every IR instruction, and
   remap provenance when inlining. Initially skip global/header invalidation
   only for strongly proven cases; later use rooted alias classes. A call that
   retains internally still writes an RC header even if its semantic parameter
   is read-only. Distinct binding names do not prove distinct heap objects: a
   COW detach from one global can decrement the old object also held by another
   global. Preserve RC facts only with the corresponding object-alias proof;
   length facts have different kills.
4. **Bounds/loop optimizations.** Reuse valid lengths and dominating bounds
   facts across harmless calls, and allow suitable LICM/versioning loops.
   Effects do not prove arithmetic ranges or unknown indexes. Keep checks on
   real resizing paths and preserve which access panics first. Do not move a
   possibly panicking operation onto a zero-trip path.
5. **Diagnostics.** Replace named-write/unknown-call exceptions with one
   substituted effect query and a useful witness. Keep place permissions,
   overlapping actuals, ordered evaluation and lifetime checks. Race and
   determinism analyses may reuse facts later; effects do not by themselves
   prove thread disjointness or determinism.

FFI/reentrant callbacks, raw pointers, threads/atomics, mutable capture cells,
recursive callbacks, generic instantiation and implicit generated calls are the
main soundness risks. A generic summary belongs to a concrete checked instance;
user-defined formatting/hash/equality can differ across instantiations. A thread
can change sharing while the caller is inactive; the existing atomic RC mode
cannot be removed from a mere no-write summary. Other workers may change sharing
even when this callee does not: preserve uniqueness across calls only for a
proven serial context or a proven thread-local object, retaining the existing
parallel/isolation checks. Watch hot replacement and callback registration also
need conservative boundaries. Treat hot-swappable calls as top until watch can
recompile every dependent optimized caller; merely resetting compiler-side
summary caches is insufficient. Keep a safe fallback for every widening/unknown
case and differential tests for panic behavior, copy-on-write values and
allocation balance.

## Recommendation and gates

Recommend **deferring the full roadmap item**, especially effects carried
through arbitrary function values. All observed frames of the four game
workloads are below the requested 5% cutoff even on the deliberately broad
traffic count, and every measured kernel's effects-only ceiling is below 5%. Do
not build the system for those payoffs.

The compiler is a qualified exception: its broad ceiling is 26.8%, not a proof
that an effects summary can save 26.8%, or even 5%. I cannot honestly report an
under-5% compiler bound from this study. If the coordinator wants to pursue that
case, approve only a bounded direct-call experiment, with the compiler as its
primary acceptance workload. There is no demonstrated application gain yet.
Checker simplification can be a separate reason to do work, but should be priced
as maintenance work rather than claimed runtime speed.

The stages, **all conditional on a later coordinator decision**, are:

1. **Direct summaries and one consumer.** Keep function-value calls top. Replace
   repeated direct-call closure walks with the demanded bounded SCC cache; add
   parameter/global sharing and storage-change facets only where a concrete
   borrow/loop query needs them. Start with one compiler hotspot and one
   disjoint borrowed-argument case, rather than a new public type system.
   Consolidation alone leaves generated target-program code unchanged. The
   compiler itself is the exception: its analysis algorithm has changed, so its
   own execution cost needs a separate measurement. Those savings are limited by
   the measured query/scan budgets, much of which remains necessary. Reject an
   unconditional whole-program pass that penalizes simple programs with no
   queries.
2. **Precise memory consumers, only after a useful proof.** Feed conservative
   header/length/storage/sharing facts to lowering, CSE and existing loop
   passes. Measure actual removed instructions and require equivalent outputs,
   panic behavior and ownership cleanup. First-entry uniqueness, index ranges,
   object aliasing and COW snapshots remain separate proof obligations.
3. **Callback metadata, only after a real callback bottleneck appears.** Add
   bounded value-flow joins and symbolic callback applications. Keep the
   code/environment ABI and structural types. Unknown flows keep the current
   checked fallback. Defer effect-based clones and public callable contracts.
   The present game/function-value measurements do not justify this stage.

The table gives **upper bounds, not forecasts**. Stage 1's ownership side is
bounded by the RC/COW/snapshot pool. Stages 2 and 3 can consume either ownership
or header/check work, so each has the shared total ceiling in the last column.
Those are **not additive gains**: all stages together remain bounded by that
same total for that counted traffic. General data-load CSE and other
transformations enabled by effect facts outside the census can have additional,
unmeasured gains. The pools contain required work and conservative false
positives; actual gain for every stage can be zero. This table covers only the
counted ownership/check/header traffic; changing the compiler's analysis
algorithm has a separate cost/benefit budget, as measured above, and is not
included in these traffic pools.

| Workload | Stage 1 ownership-focused upper | Stage 2, Stage 3, and combined upper (shared) |
| --- | ---: | ---: |
| Rebound | 0–1.917% | 0–2.98% |
| Breakwater | 0–1.792% | 0–4.47% |
| Aces | 0–0.624% | 0–1.52% |
| Dunes | 0–1.350% | 0–3.69% |
| Compiler self-build | 0–8.530% | 0–26.74% |
| Compiler → headers | 0–7.800% | 0–25.96% |
| Histogram | 0–0.006% | 0–3.69% |
| Matrix | 0–0.003% | 0–0.02% |
| Stencil | 0–0.051% | 0–0.18% |
| N-body | 0–0.814% | 0–0.82% |
| Sieve | 0–0.001% | 0–0.003% |
| each/hof | 0–1.357% | 0–2.86% |
| Fannkuch | 0–0.001% | 0–0.001% |
| Mandelbrot | 0–0.001% | 0–0.19% |
| Spectral norm | 0–0.001% | 0–0.008% |

For the compiler experiment, set an explicit stop gate: demonstrate at least 5%
fewer native runtime instructions on a representative compiler workload before
funding the full inference/closure machinery, and keep additional compile/check
instructions within 1% across small programs, real games and self-build. An
upper bound alone does not pass that gate. Record code size and memory as well;
no unbounded field sets, graph rewalk per query, or general points-to analysis
to chase the last few cases.

Before replacing safety decisions, retain the existing borrowing, mut-element,
copy-back, capture, alias, generic and parallel regression cases in debug and
release; add the later-argument, shared-cell, indirect/FFI and recursive cases
for the implemented facet. Differential outputs and panic locations matter more
than testing that a summary contains a chosen bit. Only after those gates should
any old checker exception be removed.

The original study stopped here for the coordinator's decision. The following
section records the later authorized experiment.


## Compiler experiment, stage 1: stop at the performance gate

On 2026-11-15 the coordinator authorized a compiler-focused implementation with
an explicit first-stage stop below 3% fewer whole-compile instructions. **Stage 1
fails that gate. Stop; do not advance to parameter/object summaries, retention
analysis, function-value metadata or checker changes.** The prototype is retained
on this experiment branch for review, not recommended for landing.

The branch was fetched and rebased onto `origin/master` at `5101a26` before
building or measuring. The original design commit rebased to `a197517`.
The following figures supersede the original study only for this experiment;
the earlier source audit and software-game measurements retain their stated base.

### Implemented facet

`compiler/effects.jo` adds a three-bit summary of **emitted writes**: integer
data, float data, and object headers. It follows known direct calls on demand.
Tarjan SCCs union recursive writes; completed bodies are scanned once and cached.
Each query stops after 8,192 inspected instructions or 128 active SCC members;
all unfinished components become the all-writes mask on exhaustion. This bounds
both work per demand and recursion. A completed or abandoned body is not re-walked
for each caller, so total scanning is linear in collected IR plus call queries.

Unknown or uncollected callees, function-value calls, FFI, syscalls, intrinsics,
raw writes and untyped copies remain all-writes. Header writes include actual
refcount operations. Only no-return calls can be ignored on the returning path.
Stack-slot clearing is local to the callee. No borrowed-argument pins or
retain/release pairs are removed by this facet.

The release pipeline takes a frozen pre-optimization IR snapshot. CSE and its
loop prepass query the masks and invalidate only the affected memory generations.
After the first optimization pass, the snapshot is released and uncached queries
remain conservative; inlining only moves already-seen calls. Functions with raw
memory accesses still invalidate every class when a callee writes any class.
Late-bound/watch code receives no summary proof. State is cleared at compile
entry and after code emission. There are no effect annotations on public types,
no new runtime representation and no changes to checking rules.

Implementation size: 124 lines in the new summary module, 17 added/changed lines
in the optimizer, and five added lines in the release driver. The experiment
measures the net effect of both improved compiler code and its summary overhead.
Peak memory was not measured. The four per-function integer tables are small,
but the frozen snapshot keeps original lowered IR alive until the first pass
finishes; that extra retention is another cost to check before any future landing.

### Whole-compile instruction results

All builds/runs used the machine-wide token wrapper, one compiler/emit worker,
no display, and scratch under `~/dev/tmp/effects/compiler-stage1/`. This is the
shared i7-6700 desktop. These are native retired user instructions counted by
`tools/icount.c` with exact-integer printing, not wall-clock measurements.
The same current library, paths and frozen source inputs were used on both sides.
`hello.jo` and `game.jo` exactly match `tools/speedcheck.py`'s generated inputs;
`big.jo` is `tools/genbench.py 2000` generated under scratch. Example sources
were read in place and never modified.

The compiler input was copied before implementation. Its release row uses the
normal `compiler/main.jo` release build block. A second scratch copy changes only
that block to `opt = debug`, so the debug row really exercises debug-input code
generation. Without this twin, adding or omitting `--release` would measure
release input twice. Both measured compiler executables are themselves release
builds. This distinction matters: debug-input rows measure the compilation users
normally run, while the release rows also pay for the new summary analysis.

Positive reductions mean fewer instructions; negative values mean more.
These are one complete counter pass per compiler, with no claim that differences
near a tenth of a percent exceed run-to-run variation. They are far below the
3% stop threshold, so more sampling cannot justify another implementation stage.

| Input | Input mode | Baseline instructions | Stage 1 instructions | Reduction | Output ELF |
| --- | --- | ---: | ---: | ---: | --- |
| hello | debug | 148,386,945 | 148,510,848 | -0.083% | identical |
| hello | release | 238,227,854 | 239,043,111 | -0.342% | changed |
| game | debug | 585,275,583 | 584,692,079 | +0.100% | identical |
| game | release | 1,431,213,375 | 1,434,945,323 | -0.261% | changed |
| rebound | debug | 760,974,531 | 760,094,276 | +0.116% | identical |
| rebound | release | 1,887,105,319 | 1,891,927,381 | -0.256% | changed |
| breakwater | debug | 1,316,817,001 | 1,315,314,982 | +0.114% | identical |
| breakwater | release | 3,406,410,563 | 3,413,917,565 | -0.220% | changed |
| big | debug | 1,310,952,288 | 1,310,541,298 | +0.031% | identical |
| big | release | 3,356,745,526 | 3,379,944,285 | -0.691% | changed |
| self | debug | 2,727,571,024 | 2,723,249,275 | +0.158% | identical |
| self | release | 8,440,228,634 | 8,444,360,728 | -0.049% | changed |

The largest debug-input reduction is **0.158%**, on the compiler input; the
largest release-input instruction increase is **0.691%**, on `big.jo`. All six
debug-input ELFs are byte-identical across compilers. The unchanged debug outputs
also mean this experiment's runtime changes did not alter checking/lowering/code
emission results on those six inputs. Release ELFs change, so their full behavior
still needs the unrun validation gates below.

### Why the large pool did not turn into a saving

The current debug-`big.jo` Callgrind profile has different priorities from the
original release self-build profile. The largest self-costs are `analyze`
(74,784,227 instructions), `allocate` (64,663,063), `lex` (60,202,474), `emit_ins`
(55,123,318), and `check_expr` (50,610,231). `__arr_clone` executes 19,654,742
self instructions. The profile contains 92,166,268 tagged bounds-guard
instructions, 34,466,536 COW-region instructions, and 13,413,432 inline RC-guard
instructions. These counts include required work; categories overlap and do not
estimate a removable gain. Callgrind's REP accounting differs from the native
counter, so none of these costs should be substituted for the whole-compile
native results above.

The paired-inline-RC scan's largest ordinary-call candidate is `resolve_fn_call`
calling `map_args`: 182,679 guard instructions over 6,787 invocations. Other
pairs include `op_set` -> `__map_add` (119,223 instructions) and `str_data` ->
`op_set` (116,394). These are candidates for a future argument/object proof,
not read-only calls that this facet could safely unpin. Even a no-write callee
summary would not by itself prove all the surrounding ownership traffic
unnecessary. No such pins were removed in this stage.

`ht_slot` is read-only, and the summary can preserve caller facts across it.
However, the main table costs are not repeated reads of the same header across
that call. `ht_put` checks distinct arrays, and its first checks still require
range/ownership proofs. The summary does not prove `ht_slot` returns an index
within every table array. Calls such as `operands` actually mutate `use_buf`;
allocator/raw callees remain conservative, so the summary cannot preserve an
unrelated object's facts across them without additional provenance.

This is visible in emitted x86-64 code for the same prototype sources, comparing
baseline code generation (`candidate1`) with summary-enabled code generation
(`candidate2`):

| Function | Machine instructions before / after | Static bounds-panic calls before / after |
| --- | ---: | ---: |
| `ht_slot` | 124 / 124 | 4 / 4 |
| `ht_find` | 163 / 163 | 14 / 14 |
| `ht_put` | 320 / 320 | 20 / 20 |
| `ht_put_gen` | 125 / 125 | 6 / 6 |
| `o_emit` | 1,115 / 1,101 | 63 / 60 |
| `check_expr` | 23,947 / 23,785 | 1,060 / 1,031 |
| `analyze` | 2,716 / 2,716 | 13 / 13 |
| `allocate` | 1,688 / 1,688 | 23 / 23 |
| `lex` | 1,955 / 1,955 | 24 / 24 |

These are static counts, not dynamic savings. They confirm that some guards are
removed, while the named table and debug-input hot paths mostly remain intact.
The 26.8% original traffic ceiling was not a promise that this small summary
could eliminate that work, nor does this failed facet prove that a more precise
system could never help.

### Validation, gates, and disposition

- First-stage 3% reduction gate: **failed**. The final 5% requirement is also
  missed on every measured row.
- At most 1% extra release-input compile instructions: within budget in this
  pass (worst increase 0.691%), but that does not compensate for the missing gain.
- All six debug-input output executables: byte-identical by SHA-256.
- `tools/runtests.py --compiler <candidate2> --release alias`: **14 passed,
  zero failed**.
- Self-build fixed point: `candidate2` and `candidate3` are byte-identical,
  7,660,440 bytes, SHA-256
  `b4cee10b4bdcccc26626b3f65a04af3caa1ca1b70253f2f9c61fce7c16c03b53`.
  This starts from the current release compiler; it is not the full C-stage0
  bootstrap gate.
- Per the stop instruction, **not run**: full stage0/sloppy/release suites,
  full error/warning differentials, C-stage0 bootstrap, parcheck, arm64/qemu,
  and release behavior comparisons for all six benchmark programs. The prototype
  is consequently not validated for landing.

Stop after this stage. Keep the report and prototype for the coordinator's
review; do not expand the analysis or remove checker safety special cases.
A further experiment would require a new decision explicitly funding
per-object/global disjointness or argument ownership and its added proof cost.

### Reproduction artifacts

Scratch contains `run.py`, `profile.py`, `baseline.json`, `candidate2.json`, all
12 compile logs per binary, `baseline-big.cg.<pid>`, `profile-summary.txt`,
`baseline.counts.json`, disassemblies, `candidate2.ir.log`, the alias-suite log,
and `manifest.json` with executable and frozen-input hashes. The baseline
executable SHA-256 is
`0963c7c939ee7f9d1a871b0daab4420d9f255cc11670afa27f293f9b4c0eb753`.
`baseline` builds the rebased source; it builds `candidate1` with the prototype
source but without summary-enabled code generation. `candidate1` builds
`candidate2`; `candidate2` builds `candidate3`. Compare only the frozen benchmark
inputs, not a moving compiler input containing the new analysis itself.

For each executable tag, the measurement driver is invoked from the worktree:

```sh
env TMPDIR="$HOME/dev/tmp/effects/compiler-stage1" \
    ~/dev/tmp/sloppy-tw.py -- \
    python3 ~/dev/tmp/effects/compiler-stage1/run.py baseline
# Repeat with candidate2 in place of baseline.
```

The driver sets `SLOPPY_LIB`, `SLOPPY_THREADS=1`, `SLOPPY_EMIT_WORKERS=1`,
headless/audio environment variables, and uses the exact counter retained at
`~/dev/tmp/effects/icount`. To inspect generated IR, use
`<compiler> build compiler/main.jo --ir -o <scratch-output>` under the same
wrapper and environment. Nothing was pushed and no example source was changed.
