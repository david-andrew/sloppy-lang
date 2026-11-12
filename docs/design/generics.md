# Generic requirements and fixed-array length parameters

## Decision (2026-11-11)

Stage 1 is done: generic diagnostics retain the inner and outer calls, show an
explicit omission count for long trails, and explain unsupported generic array
lengths. The original investigation below is retained as the design record.

Constraints and length parameters (`T[N]` / `[N: int]`) are deferred until a real
program needs them. The 34 probes and repository audit found 32 fixed-array
function signatures but **zero confirmed functions duplicated solely for
different lengths**. There are 26 useful operation-contract candidates and 40
numeric overloads, but neither establishes a need for a new constraint system;
overload/coercion behavior also prevents mechanical consolidation.

Reopen this decision with a concrete program that needs reusable fixed-shape
storage or named dimensions, or a generic API whose intended operation contract
cannot be adequately expressed and diagnosed today. Bring the program, its
current workaround, and the measurable source/diagnostic benefit; reconsider the
smallest applicable option below rather than treating the staged proposal as an
approved implementation roadmap.

Original design proposal, 2026-11-11. Baseline: `33e925b`. The decision above
supersedes its implementation recommendation. Syntax marked **proposed** is not
accepted today.

## Decision in brief

Keep template-style, implicitly generic functions. Improve the existing error
trail, especially its truncation, before adding a requirement language. Add
compile-time integer parameters for fixed-array lengths, inferred at calls,
using the existing explicit generic-parameter list:

```gdscript
# Proposed
dot[N: int] = (a: f64[N], b: f64[N]) -> f64:
    s = 0.0
    loop i in 0..N: s += a[i] * b[i]
    s

struct Mat[R: int, C: int]:
    m: f64[C][R]
```

Calls remain `dot(a, b)` and `Mat[2, 3]()`. Start with literal or named lengths,
including named length parameters; defer arithmetic inside type brackets and
implicit declaration of new names there. This separates **inferring a parameter's
value** from **implicitly declaring its name**.

If explicit requirements are wanted now, the smallest credible extension is
optional structural function signatures, checked once for the selected concrete
instance. Do not start with traits, protocols, or a permanently fixed `Number`
taxonomy. That alternative is specified below, but is not the recommendation for
the first implementation.

The evidence supports a modest change. There is a real representational gap for
named dimensions and generic inline storage. There is no observed epidemic of
fixed-array functions duplicated for different lengths. Useful generic error
trails already exist, and many unconstrained generic operations are intentional.

## 1. Evidence and method

### Source and execution examined

Read the reference's fixed-size arrays, functions/untyped parameters, overloads,
function values/partial application, generic structs, unions, and generic enums:
[LANGUAGE.md](../LANGUAGE.md#fixed-size-arrays),
[functions](../LANGUAGE.md#5-functions), and
[records and unions](../LANGUAGE.md#7-structs-unions-enums-optionals-tuples).
The [roadmap](../ROADMAP.md#language-ongoing-kept-small) sets the small-language
criterion. The compiler paths below refer to this baseline; line numbers will
move.

An existing compiler from the same repository HEAD built this worktree's
`compiler/main.jo` into `~/dev/tmp/generics/sloppy`; all probes used that binary
with `SLOPPY_LIB` set to this worktree's `lib`. Probe source, scripts, output, and
executables are under `~/dev/tmp/generics/`, outside the repository. The two
drivers are `probe.py` and `extra.py`; `results.json` and `extra-results.json`
record their results. Builds/runs are serial; subsequent probe builds explicitly
set `SLOPPY_EMIT_WORKERS=1`. These are behavior probes, not timing benchmarks.

There are **34 probes**: 14 pass checking and build, 20 produce the expected
compile-time rejection. Of the 14 executable probes, 13 finish normally and one
deliberately panics on unequal dynamic-array lengths. No compiler crash was
observed. No compiler, library, or example source was edited.

### How generics actually work

* `fn_sig` in `compiler/check.jo:1524` creates `.param` types for explicit names
  and a further parameter for each untyped function argument. A generic signature
  is cached in `DeclInfo`; omitted argument types do not introduce a separate
  dynamic dispatch mechanism. Local untyped lambdas use contextual/body inference
  instead, as the reference explains.
* `match_type` in `compiler/expr.jo:960` binds argument types to these parameters,
  scores existing conversions, recursively matches containers/functions/records,
  and requires equal concrete `.fixed.bits` for fixed arrays. Fixed-to-dynamic
  matching is explicitly allowed, with an additional cost. `match_union` handles
  the documented “remaining members” inference for `T | Err`.
* Call selection in `expr.jo` fills bindings from arguments, contextual lambda
  types, expected results, and omitted defaults. Unresolved bindings fail before
  `get_fn_inst`. Explicit generic call arguments currently denote types.
* `get_fn_inst` in `check.jo:1636` searches the declaration's existing instances
  using `type_eq` on their argument lists. A new instance zonks its arguments,
  substitutes parameter/result types, clones the generic body, and records its
  originating call and creating function (`use_pos`, `made_in`). Inferred returns
  can force immediate body checking; an explicit return allows checking later.
  There is no abstract check proving the body works for every possible type.
* `get_struct_inst` in `types.jo:929` caches records by declaration and type
  arguments; `check_struct_fields` resolves fields in the parameter scope.
  Generic enums share that record machinery. Constructors infer arguments from
  field/variant values or an expected concrete record type. Aliases use
  `resolve_alias`; they must also be considered when extending parameter kinds.
* Expansion guards exist: more than 500 nested new generic function instances
  and type nesting beyond 48 are diagnosed. Integer specialization needs an
  analogous defense: varying an integer does not necessarily deepen a type.
* Lowering consumes concrete function instances; `lf_of_inst` queues callees.
  This is monomorphization, without requirement dictionaries or vtables. A
  constraint checked only at instantiation need not change this model.

### Diagnostics are further along than the roadmap suggests

`check_fn_body` (`check.jo:3350`) reconstructs up to 32 generic creation links.
`fatal` (`util.jo:208`) already moves a failure in `lib/` to a non-library
instantiating call, and emits concrete signatures for user-code trail notes via
`trail_sig` (`ide.jo:452`). It shows at most **four distinct notes, innermost first**.
The IDE receives notes appended to the diagnostic message. Ordinary function
bodies deliberately reset the generic trail: their errors are their own.

Therefore “add an instantiation trail” is substantially already implemented.
Remaining problems are where the primary diagnostic appears for a user's own
generic, losing the outer caller in a long chain, and lack of an optional
declaration-level statement of intent. These are distinct problems.

### Misuse, several instantiations deep

Current valid syntax (`deep.jo`):

```gdscript
leaf = (x): x + 1
middle = (x): leaf(x)
outer = (x): middle(x)
print(outer("bad"))
```

Observed, paths shortened:

```text
deep.jo:1:17: error: cannot add this int to text: put the value inside the string ("...{x}") or convert it (str(x))
deep.jo:2:19: note: in leaf(x: str), called here
deep.jo:3:20: note: in middle(x: str), called here
deep.jo:4:12: note: in outer(x: str), called here
```

The first error points into the generic body, but the user's call is present.
The equivalent probe with explicit `-> int` returns also produces the complete
three-note chain, testing deferred checking. With `leaf` plus seven wrappers
(`deep_seven.jo`), the four notes stop at `g3`'s call to `g2`: the top-level
`g6("bad")` disappears, with no omitted-frame marker. That is a reproduced
diagnostic defect, not a hypothetical reason to add a trait solver.

Library failures are already reported more helpfully:

```gdscript
struct Thing: n: int
print(sum([Thing(1), Thing(2)]))
```

```text
lib_bad.jo:2:10: error: in this call to sum: operator + is not defined for Thing and Thing
  (a struct has the operators defined for it: `(+) = (a: Thing, b: Thing) -> ...`)
  (lib/core/array.jo:96:25)
```

`lower_bound([Thing(1)], Thing(2))` similarly reports its caller and missing `<`.
An unused `leaf = (x): x.no_such_operation()` passes `check` with a never-called
warning. Diagnostics alone do not validate unused generic bodies.

### “Anything with len” and “a number”

This works now (`len_good.jo`):

```gdscript
struct Bag: n: int
len = (x: Bag) -> int: x.n
size = (x) -> int: x.len()
a: int[3] = []
print(size("hi"), size([1, 2]), size(a), size(Bag(7)))  # 2 2 3 7
```

`size(42)` fails inside `size`, with a note at `size(42)`:

```text
len_bad.jo:1:25: error: no version of 'len' takes (int): argument 1 can be an array or a str, Map[K, V], Deque[T], Heap[T], T[,] ..., not int
len_bad.jo:2:11: note: in size(x: int), called here
```

A `len(Bag) -> str` overload is callable, but `size(Bag(3))` then fails with
`expected int, found str`. A useful requirement is a **signature**, not just a
test that a function name exists. Dot syntax adds no method requirement: this
language uses free functions and uniform call syntax.

```gdscript
square = (x): x * x
print(square(3), square(2.5), square(f32(1.5)))  # 9 6.25 2.25
```

`square("bad")` fails with `operator * is not defined for str and str`, plus the
caller note. Defining `(*)(Money, Money) -> Money` makes `square(Money(3))` work.
The repo itself has `Big` and `BigInt` arithmetic overloads. Conversely,
`add_self = (x): x + x` accepts strings, and `sum(["a", "b"])` returns `"ab"`.
Restricting every arithmetic generic to primitive `Number` would remove useful
behavior. “Numeric intent” and “these operations exist” are different contracts.

Existing unions do not stand in for generic constraints:

```gdscript
type Number = int | f64
square = (x: Number) -> Number: x * x
```

This fails because `*` is undefined for `int | f64` and `int | f64`: each value
can independently hold a different member. Narrowing or overloads can implement
it, with runtime union representation, but it does not mean “one concrete numeric
T, preserved in the result”. Similarly, a union of two user records with explicit
`len` overloads dispatches successfully in a probe, whereas `str | int[]` passed
through the same untyped `size` fails to resolve intrinsic `len`. Any requirement
check must follow the existing resolver, including its current limits; accepting
every member separately would promise calls the body cannot necessarily make.

### Fixed lengths: rejection and current workarounds

These are rejected today:

```gdscript
dot = (a: f64[N], b: f64[N]) -> f64: 0.0
# type 'f64' takes no type arguments

dot[N] = (a: f64[N], b: f64[N]) -> f64: 0.0
# same error: [N] declares a TYPE parameter, not an integer parameter

struct Mat[R, C]:
    m: f64[R * C]
# expected ']', found '*'
```

`Mat[2, 3]` is also rejected in a type annotation: literal integer generic
arguments are not supported. Changing the field to `f64[C][R]` does not fix this;
instantiating `Mat[int, int]` reaches `type 'f64' takes no type arguments` in the
field. Even concrete `f64[R * C]` fails to parse for two global constants, while
`const S = R * C` followed by `f64[S]` works and has length 6.

Current implementation explains the boundary:

* `parse_type_primary` (`parse.jo:370ff`) treats `Name[T, U]` as type arguments, excludes
  integer-leading brackets, and leaves `Name[N]` ambiguous until checking.
  `parse_type_postfix` accepts only a literal/name as a fixed length.
* `fixed_size_arg`/`fixed_size` (`check.jo:1366ff`) recognize an existing constant,
  evaluate it with `ceval`, and require `1 <= N <= 1 << 28`. Arrays of void are
  rejected. This proposal preserves those array rules, including no zero-length
  fixed arrays.
* `TypeInfo.bits` stores a concrete length. `mk_fixed` interns element+length;
  `subst` and `subst_partial` substitute the element but retain that concrete
  length. The `has_var` flag currently does not account for a symbolic length.
* `lower.jo:1037` converts a fixed array to a new dynamic array when a dynamic
  parameter is expected. `mut` conversion copies back and checks that its length
  stayed the same. Existing fixed-array indexing, inline storage, copying,
  equality, hashing, formatting and shader handling need concrete lengths.

Two useful workarounds must be credited:

```gdscript
# Current: independent untyped arguments preserve their fixed-array types,
# but promise neither f64 elements nor equal lengths.
dot_any = (a, b) -> f64:
    s = 0.0
    loop i in 0..a.len(): s += a[i] * b[i]
    s

# Current: a single type parameter enforces the same WHOLE type.
dot_same[A] = (a: A, b: A) -> f64:
    s = 0.0
    loop i in 0..a.len(): s += a[i] * b[i]
    s
```

Given `a: f64[2] = [1.0, 2.0]`, `b: f64[3] = [3.0, 4.0, 5.0]`,
`dot_any(a, b)` prints **11.0**, ignoring the last element. `dot_same(a, b)` is
already rejected: `argument 'b' expects f64[2], found f64[3]`. Equal-length inputs
work. Therefore equal-size safety alone is not a completely missing capability;
precise element types, separate dimensions and reusable storage declarations are.

The existing library `dot(a: f64[], b: f64[])` accepts both fixed values through
conversion, then panics with `dot: lengths 2 and 3 differ` (exit 101). A concrete
element-generic `same[T](a: T[3], b: T[3]) -> T` works now, preserves its return
type when written `-> T[3]`, and rejects length 2 at the call.

### Repository inventory: counts, with limits

Searched **152 `.jo` files**: 100 in `lib/`, 19 in `examples/`, 33 in `compiler/`.
`audit.py` inventories top-level named function declarations whose parameter list
is on one line, using balanced delimiters, masking strings and requiring a `:` or
`->` function tail. It excludes local lambdas, tuple initializers, comments and
call expressions. Counts below describe this reproducible inventory, not an AST
census of arbitrary syntax. Candidate bodies were then read manually. For repeat
searches, useful starting points are:

```sh
rg -n '^.*\[[A-Z][^]]*\].*=.*\(' lib/core/array.jo lib/std/algo.jo lib/std/nd.jo
rg -n '^(abs|min|max|clamp) = ' lib/core/math.jo
rg -n '^.*= \([^)]*\[[0-9]+\]' lib examples compiler
rg -n 'lengths.*differ|inner sizes differ|v.len\(\)' lib/std/nd.jo
```

| Observation | lib | examples | compiler | Interpretation |
|---|---:|---:|---:|---|
| Named functions with explicit type parameters | 485 | 0 | 0 | Generic library code is substantial; this is not a count of missing constraints. |
| Named functions with any untyped argument | 15 | 0 | 0 | Seven have a genuinely open argument; eight only have untyped defaults. |
| Open arguments without defaults | 7 | 0 | 0 | Formatting/hash/serialization wrappers, not undocumented numeric or len-only APIs. |
| Functions taking a literal-length fixed array | 32 | 0 | 0 | 50 parameter slots, all in `lib/crypto.jo`; most lengths are algorithm requirements. |
| Confirmed functions duplicated solely for different fixed lengths | 0 | 0 | 0 | No measured source-reduction claim for length generics. |

The seven open-argument functions are `__fmt_spec` (fmt:732), `__fmt_elem`
(fmt:755), `__assert_show` (fmt:758), `__fmt` (fmt:785), `hash` (map:31),
`http.json` (http:203), and `__repl_show` (repl:271). Four formatting functions,
one hash, one JSON response helper and one REPL helper. The eight default-only
cases are seven `keepdims = false` parameters in `std/nd.jo` and `t = "an int"`
in `std/text.jo:398`. **Zero confirmed untyped named functions exist solely as a
workaround for absent numeric/len constraints.** These wrappers often intend to
accept everything the compiler can format/hash/serialize; adding bounds by rote
would be counterproductive.

There are more relevant explicitly typed generic bodies. A conservative, manually
selected set of **26 operation-requirement candidates** (not an exhaustive count)
is:

| File | Count | Definitions at this baseline |
|---|---:|---|
| `lib/core/array.jo` | 14 | `sum` 94; `min` 99/122; `max` 106/123; `min` 127; `max` 137; tuple `<` 328/332; `__less` 339; `__more` 340; `__merge_sort_lt` 343; `__merge_pass_lt` 369; `sort` 415. |
| `lib/std/algo.jo` | 4 | `lower_bound` 16, `upper_bound` 28, `next_permutation` 70, `prev_permutation` 85. |
| `lib/std/nd.jo` | 8 | `__nd_reduce` 593, `__nd_arg` 638, `argmax` 731, `argmin` 737, `argsort` 744, matrix `*` 908, `__mm_rows` 933, matrix/vector `*` 964. |

Most require `<`; `sum` needs addition/zero initialization, matrix multiplication
needs multiplication/addition/zero construction. `sort` constrains its key
type **K**, not the element type T. `argsort` forwards that requirement. These
26 bodies would acquire clearer contracts, not disappear. `__nd_reduce` uses a
runtime operation selector, so all its branches are checked for a concrete T;
a constraint on only addition would not make its ordering branches valid.

Actual duplication: `core/math.jo:11–82` has **40 numeric overload declarations**
in six name/arity groups: `abs/1` 6, `min/2` 10, `max/2` 10, `clamp/3` 10,
`min/3` 2, `max/3` 2. That is 34 declarations beyond one per group, an upper
bound on consolidation, not 34 safe deletions. The source explicitly preserves
narrow integer result types while allowing mixed arguments through the `int`
overloads. Generic binary min/max already coexist in `core/array.jo:122–123`.
Constraints do not automatically reproduce overload ranking, conversions, or
specialized float behavior. `std/nd.jo`'s specialized f64 sum/sort also have
deliberate numeric/performance implementations; they are not gratuitous copies.

Length-related dynamic checks in **three concrete operations** are worth naming:
`dot` (nd:684), matrix/matrix `*` (nd:908), and matrix/vector `*` (nd:964).
Fixed-shape overloads could replace those checks for statically shaped inputs;
the dynamic APIs and their checks remain necessary for runtime data. Crypto's
u32[8], u64[8] and int[16] families implement different algorithms, not one
algorithm mechanically copied per N. Likewise built-in vec2/3/4 have distinct
fields and operations, and are not evidence that a single array generic removes
their implementations.

## 2. Constraint options

All estimates below are engineering ranges for production work in this compiler,
including diagnostics, formatting/IDE changes and focused tests. They are not
measured patches or performance predictions. “Check on instantiation” is a much
smaller feature than proving a generic body correct at its declaration.

| Option | Syntax, proposed unless noted | Error at bad call | Compile-time cost | Approximate implementation |
|---|---|---|---|---|
| A. Duck typing, improve errors | Current `size = (x) -> int: len(x)` | `size(x: int) cannot be instantiated: no version of len takes (int)`; retain body location and trail | Error-only formatting; no new successful-path resolution | 80–200 compiler lines, 1–2 days; most trail machinery already exists |
| B1. Fixed built-in bounds | `square[T: Number] = (x: T) -> T: x * x` | `square: T = str does not satisfy Number (integer or float)` | Primitive membership O(1); structural Ordered/Hashable needs traversal/memoization | 250–500 lines, 3–5 days; definition checking still separate |
| B2. Named structural sets | `size[T: Sized] = ...` with a `constraint Sized[T]` declaration | `size: Bag does not satisfy Sized; len(Bag) returns str, expected int` | Resolve k required signatures per new binding/environment; recursive generic requirements can instantiate bodies | 500–1,000 lines, 1–2 weeks; names/imports/cycles/cache semantics add work |
| C. Inline signature requirements | `size[T] = (x: T) -> int where len(T) -> int: len(x)` | `size requires len(int) -> int; no matching function` | k extra resolutions per selected instance; no global search or runtime witness | 300–650 lines, 4–7 days for use-site checking; abstract proof excluded |
| D. Compile-time assertions/predicates | `square[T] = (x: T) -> T where is_number(T): x * x` | `square: requirement is_number(str) failed` | Fixed predicates cheap; arbitrary comptime evaluation can be unbounded | 200–400 lines for a closed predicate subset; 800+ for a broader type/comptime facility |
| E. Traits/protocols, definition-checked | `square[T: Mul[T]] = ...`, with conformance declarations | Definition: unsupported operation outside bounds; call: missing conformance | Abstract body checks, obligation solving; possible specialization and witness machinery | 1,500–3,000+ lines, several weeks; poor fit for the demonstrated need |

### A. No declarations, better errors

Retain `twice = (f, x): f(f(x))` unchanged. On generic failure, make the
instantiating boundary easy to see while keeping the exact failing expression:

```text
deep.jo:4:12: error: cannot instantiate outer(x: str): operator + is not defined for str and int
deep.jo:1:17: note: operation required here in leaf(x: str)
deep.jo:2:19: note: while instantiating leaf(x: str)
deep.jo:3:20: note: while instantiating middle(x: str)
```

This is an illustrative format, not a demand to replace the existing useful
string-specific hint. Preserve the underlying diagnostic verbatim. For a long
trail, retain the outermost user call and the nearest failing calls, and insert
`note: 4 instantiation calls omitted`. Do not silently spend all four notes on
the innermost frames. The trail construction limit also needs an explicit
truncation marker and preservation of the outer boundary rather than assuming
that the outermost collected frame is the actual outer call.

Be selective about moving a user's own primary error: a hard-coded typo in a
generic body may be the author's bug. First ship outer-call retention and
elision; use probes/editor feedback to decide primary-placement policy.
Library call-site redirection should remain. Formatting signatures belongs on
the failure path, without successful-compilation string allocation. Errors in
ordinary functions remain anchored in those bodies.

This option improves explanation without a declaration contract. It cannot
reject an unused generic implementation or an accidental-but-valid string
instantiation. A requirement-only declaration also cannot prove its body unless
the compiler adds abstract checking.

### B. Named constraint sets

Two different notions should not be disguised as one:

```gdscript
# Proposed closed categories
square[T: Number] = (x: T) -> T: x * x
smallest[T: Ordered] = (a: T, b: T) -> T: if a < b: a else: b

# Proposed named set of free-function signatures
constraint Sized[T]:
    len(T) -> int

constraint Addable[T]:
    (+)(T, T) -> T

size[T: Sized] = (x: T) -> int: len(x)
```

`Number` as a fixed integer/float category is cheap, but excludes Big, BigInt,
Money, and vectors. As an extensible numeric protocol it needs a definition of
which operations, conversions and zero/one constructors are required; “all
numbers” is not a small, self-evident operation set. `sum` need not even require
multiplication. A named function-set `Addable` expresses the smaller truth.

`Ordered` should mean the existing `<` operation is callable with bool result,
including tuples/user overloads; it cannot prove mathematical total ordering
(floats include NaN). `Hashable` must follow existing equality and hash rules,
including nested fields containing function values and user overrides. Checking
only for a visible `hash` name would accidentally accept the generic fallback
before its body fails. No constraint can establish the law that equal values
have equal hashes merely from signatures.

Named sets improve reuse and docs for recurring sets, but require declaration
lookup/export, parameter substitution, cyclic-set rejection, and a distinction
from runtime types/unions. No conformance declaration, associated types, default
methods, runtime existential values or implicit implementation search should be
included in a minimal B2. It is a naming layer over C, not a new object model.

### C. Structural requirements as function signatures

```gdscript
# Proposed
size[T] = (x: T) -> int where len(T) -> int:
    len(x)

square[T] = (x: T) -> T where (*)(T, T) -> T:
    x * x

sort_keys[T, K] = (xs: T[], key: (T) -> K) -> T[] where (<)(K, K) -> bool:
    xs.sorted(key)
```

Use a small `where` signature list, not arbitrary expressions, in this option.
Names refer to free functions/operators in exactly the same lookup environment
as the eventual instantiated body. Mutability is part of a signature, as in
`where reset(mut T) -> void`. The return type must be the required concrete type;
merely finding a function with the right name is insufficient. Inference of a
generic required function's return may itself need body checking.

For the small use-site version, resolve the ordinary overload winner first,
infer all type/value parameters, then validate its requirements before checking
its body. Failure is a diagnostic, **not an instruction to backtrack through
other overloads**. Requirements are not an additional overload-ranking axis.
If two definitions differ only in their requirements they remain ambiguous,
rather than requiring implication/subsumption rules. This is less powerful than
Odin's predicate-filtered grouping, deliberately.

Requirements should reuse the normal resolver, including intrinsic operations
like `len`, operator rewrites, existing conversions and mut rules. A helper
that only looks up ordinary declarations would get this wrong. For a generic
fallback, check enough of its instance to establish validity, recording a
requirement-origin note and guarding cycles. Do not add a second, approximate
definition of “callable”. Cache on the instance/lookup environment where ordinary
call resolution is valid; if lookup can vary by caller, either include that
environment or bind lookup to the declaration. A global `(constraint, T)` cache
cannot be assumed sound in an extensible overload system.

An untyped function stays legal without requirements. The initially explicit
`[T]` in C is consistent with existing syntax and provides a name for signatures.
Inferring contracts from arbitrary bodies, field-presence constraints, associated
types, negative requirements and overload fallback are out of scope.

**Important limit:** this version documents and checks a boundary but does not
prove its implementation. A body annotated only with `len(T) -> int` can still
fail later on `x[0]`. Proving that every body operation follows from its declared
requirements would require an abstract checker for intrinsic/container rules,
overloads, union narrowing, contextual lambdas and nested generic obligations.
Budget that as a separate, substantially larger project (roughly 1,000–2,000+
additional lines), not a free consequence of adding `where` parsing.

### D/E. Lessons from comparable languages

The following are comparisons to documented mechanisms, not proposed imports of
their entire systems. Primary references were checked on 2026-11-11.

| Language | Useful mechanism | Judgment for Sloppy |
|---|---|---|
| [Zig](https://ziglang.org/documentation/master/#comptime) | Compile-time parameters, generic data construction, and errors when a concrete instantiation uses unsupported operations; explicit compile errors can state intent. | Closest to Sloppy's existing template model. Borrow concrete diagnostic context; a full type-as-value/comptime interpreter is much more than this roadmap item. |
| [Go](https://go.dev/ref/spec#Type_constraints) | A constraint describes permitted type arguments through an interface/type set, with operations restricted by that set. | A finite numeric set is understandable, but Go's constraint unions are not runtime value unions. Reusing Sloppy's `A | B` without a distinct constraint context would blur an existing, useful meaning. |
| [Rust](https://doc.rust-lang.org/reference/items/traits.html), [const parameters](https://doc.rust-lang.org/reference/items/generics.html#const-generics) | Explicit trait contracts and typed const parameters; the reference restricts const parameters in array types to standalone use. | Borrow explicit value-parameter kinds and the separation of matching a length from evaluating an expression. Coherence, impl search and associated items are disproportionate here. |
| [Swift](https://docs.swift.org/latest/documentation/the-swift-programming-language/generics/) | Protocol constraints and generic `where` clauses express reusable requirements and relationships. | Clear for larger API contracts; Sloppy has free functions and no need demonstrated for protocol conformance or existential values. |
| [Odin](https://odin-lang.org/docs/overview/#where-clauses) | `where` predicates on polymorphic procedures/records, including numeric-type tests and dimension conditions; can disambiguate procedure groups. | A predicate vocabulary can be lighter than traits. Do not import arbitrary predicate evaluation or requirement-based overload selection before evidence warrants them. |

A limited Odin-like option could be `where is_number(T)` and `where N > 0`, with
a fixed whitelist of predicates. Its errors can say which test failed, and it
could later be combined with C. It still needs a type-query vocabulary and
compile-time semantics. In this compiler `ceval` currently evaluates literals,
constants and a limited set of operators; it does not implement arbitrary
type-reflecting predicates. Reusing `when` is also not free: its current platform
configuration role does not amount to generic abstract checking.

### Interaction rules for any requirement option

| Existing feature | Required behavior |
|---|---|
| Overloads and literals | Preserve current ranking, user-definition precedence and numeric-literal preferences. A bound is checked after normal binding/selection in the minimal version. No narrower-bound-is-better rule. |
| Untyped parameters | Keep `twice(f, x)` syntax and behavior. Bounds remain optional. Do not infer `Number` from `+`, since strings and custom types can add. |
| Unions | A bound is checked on the actual inferred type. A concrete union works only if the body/resolver can perform the requested operation on that union. No implicit splitting or Cartesian-product monomorphization. Preserve remaining-member inference for `T | Err`. |
| Function values | Runtime function types stay `(A) -> B`; requirements are discharged when choosing a concrete instance, not carried as runtime capabilities. |
| Partial application | Check once its parameter types are fixed. A partial is a concrete closure, not a newly introduced polymorphic value. If holes leave parameters unknown, retain the current inference error or use existing contextual inference. |
| Generic records/enums | A future named bound may be checked when instantiating a record, but storing T should not automatically require its unrelated operations. Constructors use the same parameter inference. |
| Compilation model | Keep one concrete instance per binding set, demand-driven checking/lowering, no runtime dispatch tables. Do not claim requirements reduce instance count: they primarily improve contracts and failures. |

The existing `same[T](a: T[3], b: T[3])` probe supports partial application
`f = same(a, _)`; `same(_, _)` fails with `cannot infer generic types for partial
application of 'same'; annotate the arguments`. New requirements should preserve
that rule rather than adding polymorphic closure storage as a side effect.

## 3. Fixed-array length parameters

### Syntax alternatives

| Declaration | Attraction | Cost or ambiguity |
|---|---|---|
| `dot = (a: f64[N], b: f64[N]) -> f64: ...` | Lightest; N's existence and value are inferred from a length position. | A misspelled constant silently introduces a parameter; new binding pass and scope rules; clashes with current unknown-name errors and `Name[T]` ambiguity. A name only in a return type cannot be inferred. |
| `dot[N] = (a: f64[N], b: f64[N]) -> f64: ...`; `struct Mat[R, C]` | Reuses existing bare generic names; infer parameter kind from use. | `[T]` means type today. Need kind inference across fields/signatures, forwarding `Other[N]`, aliases, recursive records and unused parameters. One name used as both type and length needs a new diagnostic. |
| **`dot[N: int] = ...`; `struct Mat[R: int, C: int]`** | Explicit kind, inferred values at normal calls, preserves all existing `[T]` meanings and spelling errors. | A small amount of syntax at declarations; parameter-list parser/formatter changes. Recommended. |
| `dot[const N] = ...` | Also unambiguous and reuses a keyword. | New parameter-specific spelling; implies a wider family of const values unless explicitly limited. Reasonable alternative if `N: int` is disliked. |
| `(a: f64[_], b: f64[_])` | Anonymous arbitrary lengths. | Two underscores do not establish equal length; a shared name is still needed for the interesting case. |

The first row is feasible, and should be an explicit coordinator choice rather
than accidentally implemented by treating every unknown bracket name as a new
parameter. The recommended declaration is slightly longer because it fits the
existing rule that named generic type parameters are declared after the name.
Both designs infer N from arguments; neither requires `dot[3](a, b)` at normal
calls.

### Proposed first-version semantics

```gdscript
dot[N: int] = (a: f64[N], b: f64[N]) -> f64:
    s = 0.0
    loop i in 0..N: s += a[i] * b[i]
    s

copy[T, N: int] = (xs: T[N]) -> T[N]: xs
blank[T, N: int] = () -> T[N]: []

a: f64[3] = [1.0, 2.0, 3.0]
dot(a, a)                       # N = 3
dot[3](a, a)                    # explicit value argument
b: int[4] = blank[int, 4]()      # no argument carries its size
c: int[4] = blank()              # expected-result inference, as for types
```

* `[T]` remains a type parameter. `[N: int]` is a compile-time integer parameter,
  not a runtime argument/default and not the runtime type `int` substituted for N.
  First support only this value kind, not arbitrary `comptime` values or types as
  values. Reject other value-kind annotations with a targeted explanation.
* Integer arguments are exact compile-time integer values. Do not widen/truncate
  floats or bools into lengths. The current `ceval` conflates bool/integer literals
  in `CVal`; integer-kind validation is necessary, not just reading `.i`.
* A length variable is scoped to its declaration/body. In a concrete body it is
  an immutable constant usable in ordinary expressions and passed as a normal
  integer value if desired. Generic call brackets initially accept integer
  literals, constant names and forwarded integer parameters in value slots.
  Their interpretation follows the callee's declared parameter kinds.
* Match a concrete fixed-array length directly; bind the first occurrence and
  require equality at every subsequent one. Inference walks nested fixed types,
  record/enum arguments, function types and expected results, as type inference
  does. Keep different slots independent: `f64[N]` and `f64[M]` need not match.
* Preserve `1 <= length <= 1 << 28` whenever constructing a fixed array, and reject
  impossible byte sizes/layout arithmetic before allocation or lowering. An
  integer parameter outside an array context is still an integer; array length
  validation occurs when its use demands a valid length. A dynamic `T[]` carries
  no static length to infer. Do not guess N from a runtime `len` call.
* First bind from already fixed-typed arguments and expected types. Bare array
  literals remain dynamic by default. Once N is known (including an explicit
  `dot[3]`), existing literal-to-fixed contextual conversion can apply. If only
  bare literals are supplied and no N is known, diagnose inability to infer N;
  do not scan arbitrary comprehensions/fill calls to invent lengths in v1.
* Do not implicitly convert an already typed dynamic array to a fixed array to
  satisfy this signature. Existing fixed-to-dynamic fallbacks remain valid for
  other overloads. No new resize/copy-back rules are introduced for `mut T[N]`;
  it requires the same concrete fixed type as other mut parameters.
* `f = dot(a, _)` fixes N from a (or from an already available contextual function
  type); holes alone cannot create a polymorphic function value. This follows
  existing partial-application behavior. Likewise requirements, if added, are
  checked after these bindings exist.

Illustrative errors:

```text
error: dot: argument 'b' has type f64[4]; expected f64[3] (N = 3 from argument 'a')
error: cannot infer length parameter 'N' of 'dot' from f64[]; use a fixed-size array or give N explicitly with fixed-size inputs
error: cannot infer length parameter 'N' of 'blank'; give it as blank[int, 4]() or write the result type
error: length parameter 'N' expects a compile-time integer, found f64
error: size of a fixed-size array must be at least 1 (N = 0 in Buffer[int, 0])
```

Overload selection must remain deterministic. An exact `f64[3]` overload should
win over a length-generic fixed pattern, which should win over a conversion to
`f64[]`, subject to the existing user/library precedence policy. Give a new
length binding a specificity cost; do not inadvertently rank it exactly as a
fully concrete fixed type. A mismatched fixed candidate may legitimately fall
back to an existing dynamic overload; the language does not promise every call
named `dot` statically enforces equal lengths. If no candidate succeeds, show
the useful N-conflict rather than just `no version takes ...`. As today, duplicate
equally specific generic signatures remain ambiguous.

### Structs, enums and aliases

```gdscript
# Proposed, no length arithmetic needed
struct Buffer[T, N: int]:
    items: T[N]

struct Mat[R: int, C: int]:
    m: f64[C][R]                # R rows, C columns, contiguous inline storage

type Row[N: int] = f64[N]

enum Packet[N: int]:
    empty
    payload(bytes: u8[N])

matmul[R: int, K: int, C: int] = (a: Mat[R, K], b: Mat[K, C]) -> Mat[R, C]:
    out: Mat[R, C]
    loop r in 0..R:
        loop c in 0..C:
            loop k in 0..K: out.m[r][c] += a.m[r][k] * b.m[k][c]
    out
```

`Mat[2, 3]` and `Mat[3, 2]` are different nominal instantiations despite equal
element count/byte size. `Mat` constructors can infer R/C from a fixed field
value; `Mat()` with no expected type cannot infer them from zeros/defaults.
Likewise the empty Packet variant needs explicit arguments or a result context,
as an empty generic enum variant does now. Aliases forward value arguments but
do not create a second identity. Repeated value parameters in record patterns
must match their stored bindings, not just their field layouts.

It is reasonable to land function parameters before records, but the complete
roadmap item should use the same kind/binding machinery for functions, structs,
enums and aliases. Otherwise the first feature creates inconsistent generic
syntax across declarations. This plan does not require rewriting the dynamic
NDArray API or crypto examples.

### Arithmetic: evaluation is different from inference

The proposed nested Mat avoids needing `R * C` in a type. This has the same
contiguous element storage but indexing is `m[r][c]`, not `m[r * C + c]`.
Both are useful layouts; do not claim they are interchangeable source APIs.

The options are:

| Length expressions | Meaning | Compiler consequences |
|---|---|---|
| Literal/name only | `f64[N]`, nested `f64[C][R]` | Direct matching and substitution; smallest implementation. Recommended first. |
| Evaluate after all inputs bind | `struct Mat[R: int, C: int]: m: f64[R * C]` | Parse/store a symbolic expression, evaluate with known bindings, validate overflow/size. Practical second step. |
| Infer through arithmetic | Infer R/C from a flat `f64[R * C]` argument | Often ambiguous (12 = 2*6 = 3*4); requires an equation policy/solver. Reject this project scope. |

For the second row, infer R and C from the **nominal Mat arguments**, from direct
length occurrences elsewhere, or explicit arguments; then evaluate the product.
Do not solve backwards from its field. `f[N: int](x: f64[N * 2])` with only a
length-6 input should say N cannot be inferred, rather than silently dividing.
If N is explicitly 3, checking length 6 is trivial. Existing `ceval` arithmetic
can inspire evaluation, but its machine-integer operations are not an
overflow-safe layout evaluator. Checked add/multiply and diagnostics for
overflow, unsupported operators, cycles and out-of-range final sizes are needed.

A minimal follow-up could allow just integer literals, bound names, parentheses,
`+`, `-`, and `*`; no arbitrary calls, reflection, equation solving, or algebraic
normalization. Equal types compare **evaluated concrete lengths**, never source
expression text. Postpone this entire expression grammar until direct matching
and record substitution are reliable.

### Representation, instantiation and lowering

The current `int[] targs` stores type IDs everywhere. Integer values must not be
put into that list as raw type IDs: the number 3 is not type #3. Add declared
parameter-kind metadata and distinct integer bindings, or a properly tagged
generic-argument representation, consistently across function, struct, enum and
alias inference/cache keys. Keep cheap ordinary type-only paths when there are
no integer parameters.

Parsing mixed argument lists also needs a deliberate representation: a parser
cannot generally know whether `Other[N]` uses N as a type or a value. Preserve
name arguments until checking against the resolved declaration's parameter
kinds, and accept integer-literal argument nodes there; do not simply feed every
bracket argument through today's `parse_type`/`resolve_type` pair. Keep module
qualification and the existing `int[SLOTS]` versus `Stack[T]` distinction intact.

Signatures need a symbolic fixed-length form. It must carry the parameter slot
and participate in `has_var`, substitution, partial substitution, equality and
printing. In particular, `f64[N]` has a variable even when its element is concrete.
Use an explicit symbolic/concrete distinction; avoid a hidden “0 means unknown”
length convention because zero has a distinct invalid-size diagnostic. A symbolic
record argument similarly propagates variability. All symbolic forms must be
fully resolved before field layout or lowering.

Specialize by the complete binding tuple, e.g. `(copy, T=f64, N=3)` and
`(copy, T=f64, N=4)` are different instances; repeated calls at N=3 reuse one.
Record identity likewise includes integer values. The existing per-declaration
linear instance search is adequate to start but could become expensive for a
large family of sizes; stress-test that before introducing a new global cache.
Guard integer-driven recursive expansion, including record recursion where type
nesting does not grow. Diagnose a varying-N cycle; do not lower an endless family.

After substitution, use today's ordinary concrete `mk_fixed(elem, N)`, existing
record layout and fixed-array lowering. N in an expression becomes an integer
constant; it adds no runtime argument. No dictionary, vtable, dynamic length
field or new runtime array representation is needed. The typed fixed overload
avoids the fixed-to-dynamic array allocation/conversion, but value passing still
has the language's normal copy semantics; this is not a new borrow feature.
One instance per length may cost more compilation/code size than one T[] function;
do not automatically specialize all dynamic library operations.

### Likely work and compile-speed budget

| Slice | Main touch points | Approximate size and time |
|---|---|---|
| Integer kinds, parsing, call arguments and direct function lengths | `ast`, `parse`, `check` signatures/substitution/ceval bindings; `expr` matching/selection/partials; `types`; `fmt`, `ide` | 500–900 changed compiler lines, 4–7 days |
| Record/enum/alias arguments, constructors, identity and recursive layout guards | Shared argument machinery, `check_struct_fields`, `get_struct_inst`, constructor/variant inference | 250–500 further lines, 2–4 days |
| Post-binding length arithmetic, later | Parser expression subset, symbolic expression substitution, checked evaluator/layout validation | 200–400 further lines, 2–4 days |
| Implicit name/kind inference, alternative | Scope/binder pass, ambiguity diagnostics, forwarding/unused-name policies | 150–350 further lines, 2–4 days, on top of value-argument support |

Ranges overlap shared work; they are not a promise of an exact additive diff.
Tests/docs are additional. A typed generic integer is not a one-function change
to `fixed_size`: it crosses all the current type-only generic paths.

On unchanged programs, costs should be a cheap parameter-kind check and no
extra body analysis. For a pattern with k direct length occurrences, matching
adds O(k) equality/binding work; existing type equality remains cheap after
interning. Compilation of a newly used N costs a cloned/checked/lowered body,
as each distinct type combination does now. Nested shape families can multiply
the number of instances. A requirement language would add k resolver calls per
new instance on top of that; there is no demonstrated compile-speed saving from
adding bounds alone.

## 4. Recommendation and staged acceptance gates

**Choose A plus explicit integer length parameters.** It addresses the reproduced
diagnostic defect and introduces the missing representation without committing
the language to a hierarchy of numeric/collection interfaces. Consider C later
if maintainers want contracts on the 26 identified library candidates. Do not
mechanically constrain all 485 explicitly generic library functions.

1. **Diagnostics only.** Preserve the outermost user call when truncating a long
   generic trail; print an omission count and retain the failing expression and
   concrete signatures. Test inferred/explicit returns, cached instances,
   library and imported user modules, ordinary-function boundaries, and CLI/LSP
   parity. Prefer a small improvement to existing behavior before moving every
   user-generic primary diagnostic. Update the roadmap wording only if asked.
2. **Direct function lengths.** Implement `[N: int]`, mixed `[T, N: int]`, named
   lengths, argument/result inference, explicit integer arguments, immutable N
   in bodies, exact-length matching and concrete monomorphization. No arithmetic
   in type brackets. Cover same/different N, forwarding, nested fixed arrays,
   mut, overload ranking/fallback, literals with/without a known N, known/unknown
   partials, invalid integer kinds/ranges and recursion. Verify repeated N reuses
   instances, and lowering sees no unresolved length.
3. **The same feature on records/enums/aliases.** Buffer and nested Mat, constructor
   inference, zero-initialized values, explicit empty variants, repeated value
   identity and non-expanding/expanding recursion. Keep runtime NDArray APIs.
   Validate representative CPU and shader use, plus native/wasm/arm64 layout;
   do not invent unrelated new shader array rules.
4. **Reassess actual usage.** If flat storage needs products, add post-binding
   checked arithmetic without backward inference. If library contracts are still
   a pain, choose C's optional signature requirements on selected instances,
   perhaps followed by B2 as a naming convenience. Revisit definition-checked
   contracts only with a separately approved scope and cost budget.

For implementation stages, bootstrap to a fixed point and run focused positive,
negative, formatting, LSP and cross-target tests. Stage0 can continue to compile
the compiler's old source subset as long as the compiler implementation does
not start using the new syntax; avoid needlessly porting the feature to stage0.

Compile speed is a release gate, not a speculative benefit: compare instruction
counts on this desktop, with one emitter worker, against the base for hello,
the generated large source, self-compilation, and the existing game workloads.
Use the project's **1% maximum regression** criterion on unchanged workloads;
`tools/speedcheck.py` documents the counter approach. Keep all its temporary
files under `~/dev/tmp/generics` via TMPDIR/configuration when running it, and
ensure its nested compiler launches also honor the worker cap. Add synthetic
1/10/100-length families to expose instance growth and repeated-binding reuse;
report instance count and instruction count, not desktop wall time. Reduce scope
or revisit representation if the unchanged-program gate fails. No performance
numbers are claimed by this design-only investigation.

The bounded first implementation is stages 1–3. General comptime execution,
constraint-based overload specialization, associated types, runtime interfaces,
implicit union splitting, arithmetic equation solving and polymorphic partial
values are outside it. The coordinator should select the syntax/contract option
before compiler work begins.
