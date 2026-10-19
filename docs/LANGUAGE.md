# The Sloppy Programming Language

Sloppy is a small, statically typed, compiled language that feels like a scripting
language. `sloppy game.jo` compiles the whole program (in milliseconds) and runs it.

Design goals, in priority order:

1. **Instant compiles.** Whole-program compilation every time, no incremental builds,
   no external toolchain. The compiler emits x86-64 machine code / WebAssembly directly.
2. **Python-level ease.** Type inference everywhere, minimal ceremony, top-level
   statements are a program, no build system, batteries included for games.
3. **Predictable performance.** Values are plain data laid out like C. No GC, no hidden
   allocations behind your back, no virtual dispatch you did not ask for.
4. **Programs keep working.** Native executables stand alone (on Linux they are fully static and
   make system calls directly; on Windows they import nothing but kernel32.dll), web builds are a
   single self-contained `.html` file.

---

## 1. A taste

```gdscript
# hello.jo
print("hello, world")

fib = (n: int) -> int:
    if n < 2: return n
    fib(n - 1) + fib(n - 2)

loop i in 0..10:
    print("fib({i}) = {fib(i)}")

nums = [5 3 9 1]
nums.sort()
squares = nums.map((x): x * x)
add = (a: int, b: int): a + b
inc = add(1, _)                # partial application
print(squares, inc(41))
print(nums .* 2, sqrt.([4.0 9.0]))     # elementwise
```

### The interactive prompt

`sloppy` with no file starts an interactive prompt. Type declarations and statements; they run
as you enter them, and the value of an expression at the end of an input is shown:

```
>>> xs = [3 1 2]
>>> xs.sort()
>>> xs .* 10
[10, 20, 30]
>>> f = (n: int):
...     n * n
...
>>> f(12)
144
```

A line ending with `:` starts a block and an empty line ends it. Names stay declared, and
declaring one again replaces it (code entered before keeps the old one). Each input is compiled
to machine code that runs in a session process, so it runs as fast as a program does. If an
input has errors, or panics, or crashes, or is stopped with ctrl-c, the program is exactly as it
was before it (what it did outside the program, like writing a file, stays done). `:type expr` shows an expression's type, tab completes names (including fields
after a `.`), up and down recall earlier lines, and ctrl-d or `exit` leaves. Input can also be
piped in (`sloppy < script.txt`).

## 2. Lexical structure

* Comments start with `#` and run to end of line.
* Blocks are introduced by `:` and are either the rest of the line
  (`if x: return 1`) or an indented block on the following lines.
  Inside brackets newlines are ignored (except in array literals, where they separate rows),
  and a `:` at the end of a line opens an indented block (this is how multi-line lambdas work).
* `;` may separate statements on one line, and a `\` at the end of a line continues it on the
  next (inside brackets lines continue by themselves).
* Indentation is spaces or tabs, a tab counting as up to 4 columns. Use one or the other: an
  indentation error in a file that mixes them says so.
* Integer literals: `42`, `1_000_000`, `0xff`, `0b1010`. Float literals: `1.5`, `2.0e-3`.
  Literals take the type their context expects, and must fit it (`x: u8 = 300` and
  `x: u64 = -1` are errors; a literal above the i64 range is a `u64`, or `int`'s bits).
* Strings: `"text {expr} more {value:.2}"` and `'the same'` — the two quotes are
  interchangeable, and both may span lines. `{}` interpolates any expression in either kind
  (so text with braces, such as JSON, needs `{{` and `}}` for literal braces, or a raw string). Escapes: `\n \t \r \0 \\ \" \' \xNN`. Format specs follow Python:
  `[[fill]align][+][#][0][width][,][.precision][type]` with align `<` `>` `^` and type `x` `X`
  `b` `o` `f` `e` `g` `%` — `{price:>8.2}`, `{n:,}`, `{ratio:.1%}`, `{name:<12}`, `{bits:08b}`,
  `{addr:#x}` (with `0x`). `{x=}` shows the expression before its value (`x=5`), for debugging.
  Raw strings `r"no {interp} \here"` (or `r'...'`: JSON in code is `r'{"a": 1}'`). Triple
  quoted strings run over lines: when the text starts on the line after the opening `"""`, that
  line break, the indentation all its lines share and the last line break (before the closing
  `"""` on a line of its own) are left out, so the text can be indented with the code;
  `r"""..."""` is both (help text with `{name}` in it). Widths in format specs count
  characters, so `"{city:<8}"` lines up "Zürich" with "Paris", and a precision on text cuts it to
  that many characters: `"{title:<20.20}"` is a column 20 wide.
* **Characters.** A one-character string in single quotes where an integer is expected stands
  for its character code: `c == 'a'`, `'0'..'9'` in a match, `'a' + i`, `u8('A')`, `'{'` (a brace
  alone is not an interpolation). In double quotes it is text, except where a byte (`u8`) is
  expected: `s[i] == "a"`, `c in "+-"`, `bytes.push("\n")`. Elsewhere text is not a number:
  `add(1, "2")` with `add` taking `int`s is an error (`to_int("2")` reads the number, `'2'` is
  the character's code).
* **Units.** A unit right after a number (no space) converts to the SI base unit at compile
  time: `120ms` is `0.12`, `90deg` is `PI / 2`, `3km` is `3000.0`, `1.2(m/s)`,
  `9.81(m/s^2)`, `[1.2 0](m/s)`. Time `s ms us ns min h`, length `m cm mm km`, mass `kg g`,
  angle `rad deg turn`, force `N`, and long names (`10seconds`, `3meters`). Values are plain
  `f64`s (no dimension checking).

Keywords: `struct enum type if else loop in break continue return match import use as const true
false none null and or xor not is let mut when defer extern test build pass` (and `from` and
`error` before `import` and `struct`/`enum`) (`loop let xor is` and
`type` may still be used as field and variant names).

## 3. Variables and constants

```gdscript
x = 10               # declares x (there is no x yet), type inferred (int)
x = x + 1            # assigns (x exists)
let x = "text"       # always a new variable (shadows the outer x)
y: f32 = 2           # explicit type (always declares)
z: str[]             # zero value: empty array
w = []               # an empty array whose type comes from what is pushed into it later
                     # (w.push("hi"): a str[]), at the top level too
x += 1               # compound assignment (also -= *= /= %= ^= <<= >>= and= or= xor=)
a, b = 1, 2          # several at once (from a tuple, or an array of exactly that many:
k, v = line.split("=", 1)   # another length panics)
const SPEED = 300.0  # compile-time constant
```

`x = value` declares `x` when no variable `x` is visible, and assigns otherwise: inside a
function, assigning to a global changes the global. At the top level of a file, `x = 1`
declares a global of that file, or assigns one the file `use`s (an `import`ed file's names are
apart: `physics.x`).

A function may not assign (with `=`) a global declared further down the file: a global added
there later (`i`, `best`) would quietly change what the function does. `let x = ...` makes a
variable of the function's own; declaring the global above the function says the function
means it. `score += 1` (and the other compound assignments) cannot declare anything, so it
always means the global, wherever in the file it is declared.

Top-level variables are globals, initialized in order before `main` runs (each where its line
is, even `x = 0`).
Top-level statements in the main file run in order, like a script.

## 4. Types

| Type | Meaning |
|---|---|
| `int` | 64-bit signed integer (`i8 i16 i32 i64 u8 u16 u32 u64` also exist, `byte` = `u8`) |
| `f64` `f32` | floats (`1.5` is an `f64` unless the context wants an `f32`) |
| `bool` | `true` / `false` |
| `str` | immutable UTF-8 string (`+` concatenates, `*` repeats) |
| `T[]` | growable array (value semantics); `push pop insert remove extend len` ... (also `Array[T]`) |
| `T[N]` | fixed-size array: N elements stored in place (in a struct, a variable, a shader's uniforms) |
| `T[,]` | n-dimensional array (see section 8) |
| `soa T[]` | array of structs stored as one array per field (see section 8) |
| `{K: V}` | hash map, insertion ordered (value semantics) |
| `(A, B)` | tuple |
| `T?` | optional: a `T` or `none` (the same as `T \| none`) |
| `A \| B` | union: an `A` or a `B` (see section 7) |
| `(A, B) -> R` | function value (may be a closure); `() -> void` returns nothing |
| `vec2 vec3 vec4 mat4` | f32 vector/matrix math types (GPU-compatible) |
| `ivec2 ivec3 ivec4` | i32 vectors (`+ - * /` by component, swizzles, `ivec3(v)` from a `vec3`) |
| `*T` | raw pointer (low-level code only) |

`type Name = ...` names a type: `type Shape = Circle | Rect`, `type Result[T, E] = T | E`.

**Numeric conversions.** Integers widen implicitly to larger integer types of the same
signedness and to floats; `f32` and `f64` convert implicitly in both directions.
Narrowing is explicit: `int(3.7)`, `u8(x)`, `i32(n)`; `f64(n)` makes a float of an integer.
An integer converted to a smaller integer type keeps its low bits, wrapping around as C's casts
do: with `n = 300`, `u8(n)` is 44; `u8(n - 301)` is 255 (a literal that does not fit, as in
`u8(300)`, is an error when compiling). `checked_cast[u8](n)` is `none` there instead, and
`saturating_cast[u8](n)` 255.
`as` reinterprets pointers, and integers as another size or sign (`x as u8`, `p as *f32`). It
does not go between integers and floats: `f64_bits(x)` and `f64_from_bits(b)` give and take a
float's bits. For C, `data(xs)` is a pointer to an array's or a string's first element, and a
string's bytes end with a 0. A union is not cast but tested with `is`.
Float to integer conversion truncates toward zero and saturates: NaN becomes 0 and values
beyond the integer range become its minimum or maximum (the same on every target).

**Operators.** Integer `/` truncates, `%` is remainder, integer overflow wraps (in debug and
release builds alike: `i8(127) + i8(1)` is -128), and a shift counts modulo the width
(`1 << 64` is 1, as x86-64 and arm64 shift). Where overflow must not pass unseen, the library
has `checked_add`, `checked_sub` and `checked_mul` (an optional, `none` on overflow:
`checked_mul(w, h) ?? panic("too big")`), `saturating_add`, `_sub` and `_mul` (the type's
largest or smallest value) and `wrapping_add`, `_sub` and `_mul` (as the operators, said on
purpose), for every integer type. A conversion that must not lose anything is
`checked_cast[u8](x)` (`none` unless x is a value a `u8` has), and `saturating_cast[u8](x)` gives
0 or 255 past the ends. `gcd`, `lcm`, `isqrt`, `mul_mod`, `pow_mod` and `inv_mod` are exact for
every int (`mul_mod(a, b, m)` for m up to 2^63, with the 128-bit product). There are no exact
integers past 64 bits: `Big` (`use big`) is a float with a large exponent, about 15 digits
([API.md](API.md#big-numbers)). `x ^ y` is
`pow(x, y)` (right-associative and tighter than unary minus: `-2 ^ 2 == -4`). On integers it
is an integer: a negative power truncates as `/` does (`2 ^ -1 == 0`), and it wraps on overflow
(`2 ^ 64 == 0`); `2.0 ^ -1` is 0.5. C's xor is `xor`: a `^` that looks like one (on hex
numbers, unsigned or sized integers, next to `&` or `<<`) gets a warning.
`and or xor not` are logical on bools (`and`/`or` short-circuit) and bitwise on integers,
with low precedence (below comparisons); `& | ~ << >>` are the bitwise operators with high
precedence, so `flags & MASK == 0` is `(flags & MASK) == 0`. `x in xs` tests membership
(`x in 1..10` compares, no array is made). `a ?? b` is `a` unless it is `none`.

**Looks familiar, means something else.** What Python, JavaScript or C would read otherwise:
- `x ^ y` is a power; xor is `xor`.
- `7 / 2` is 3 with whole numbers, and `-7 % 3` is -1 (as in C, not Python).
- `not` on a whole number flips its bits: `not 0` is -1 (conditions take bools).
- `+` on arrays of one dimension joins them (`[1, 2] + [3]`); on a matrix it adds element by
  element. `.+` always adds element by element.
- `x = 1` in a function changes a global named `x` when there is one; `let x = 1` makes a local.
- `a..b` leaves `b` out, as Python's `range(a, b)` does; `[a..b]` keeps it.
- `xs.remove(2)` removes the element at index 2 (Python's `del xs[2]`); the value 2 goes with
  `xs.retain((x): x != 2)`.
- `round(5.7)` is `6.0`, an f64 (as `floor` and `ceil`); `int(round(x))` is the whole number.
- Angles are in radians: `rotate(v, PI / 2)`, or `rotate(v, 90deg)` (a literal over 2π warns).
- `'a'` and `"a"` are both text, but where a number is expected `'a'` is its character code (97).
- `load()?.name` is not optional chaining: `?` returns from the function when `load()` fails.
- `!` unwraps an optional, not an error: `x is ParseError`, or `?`, handle those.
- `s[i]` is a byte (a number), not a one-character string: `s[i..i + 1]` or `chr(s[i])` is text.
- `read_file` keeps line ends as they are: `text.split("\n")` keeps the `"\r"` of Windows line
  ends (Python's text mode drops it); `text.lines()` takes either.
- `"C:\temp"` holds a tab (`\t`), as in Python: write a path `r"C:\temp"`, or with `/`.

From tightest to loosest (operators on one line bind alike, left to right but for `^`):

| Operators | |
|---|---|
| `x.f`, `f(x)`, `xs[i]`, `x!`, `x?` | field, call, index, unwrap, pass a failure on ([errors](#7-structs-unions-enums-optionals-tuples)) |
| `^` | power (right to left) |
| `-x`, `~x` | negation, bitwise not |
| `*` `/` `%` | |
| `+` `-` | |
| `<<` `>>` | |
| `&` | bitwise and |
| `|` | bitwise or |
| `..` | range |
| `??` | default for `none` (`a + b ?? 0` is `(a + b) ?? 0`) |
| `==` `!=` `<` `<=` `>` `>=` `in` `is` | comparisons |
| `not` | |
| `and` | |
| `or` `xor` | |

### Text

A `str` is text in UTF-8: one byte for each of the characters of plain English text, two to
four for others (`é`, `ж`, `中`, `😀`). Its bytes are what the basic operations count:

| | |
|---|---|
| `len(s)`, `s[i]`, `s[a..b]`, `loop b in s` | bytes: `s[i]` is a `u8`, a slice is a range of bytes |
| `char_count(s)`, `chars(s)` | characters (Unicode code points): how many, and each as its number |
| `first(s, n)`, `last(s, n)`, `"{s:.n}"` | the first or last n characters (a slice in the middle of an `é` would cut it in two) |
| `chr(233)` | the character with that number, as a `str`: `"é"` (`byte_str(b)`: a one-byte `str`) |
| `split(s, "")` | each character, as a `str` |
| `text_width(s, size)` | how wide it is drawn, in pixels (what a text box needs) |
| `wrap_text(s, width, size)` | its lines, broken at spaces to fit a width (`text_wrapped` draws them) |

`find`, `replace`, `split`, `trim`, `starts_with` and the other functions on text work on any
text, since a character's bytes never look like another's. For text from players or files, count
characters with `char_count`, and to step through them, `loop c in chars(s)` (`loop c in s` gives
bytes, which print as numbers: `str(c)` of an `a` is `"97"`).

`print(x)` and `"{x}"` show any value: a struct as `Big(m=1.5, e=300)`. A type of the program's
own shows as its own text when a `str` for it is written beside it, everywhere it is shown (in
arrays and other structs too); `to_text`, `to_json` and saving still write its fields, which
read back:

```gdscript
struct Big:
    m: f64
    e: int
str = (b: Big) -> str: "{b.m:.2f}e{b.e}"
print(Big(1.5, 300))          # 1.50e300
```

### Value semantics

Every type in Sloppy is a *value*: assignment copies. Arrays, strings and maps are
reference counted with copy-on-write, so copies are O(1) and a real copy only
happens when you mutate something that is shared. There are no reference types,
so reference cycles (and leaks) do not happen, and there is no garbage collector (raw pointers
are the way around that).

```gdscript
a = [1, 2, 3]
b = a           # O(1), shares storage
b.push(4)       # b is shared, so b gets its own copy here
print(a, b)     # [1, 2, 3] [1, 2, 3, 4]
```

Function parameters are borrowed (passed without copying, read-only).
Mark a parameter `mut` to let the function modify the caller's variable:

```gdscript
grow = (xs: mut int[]): xs.push(0)
grow(nums)
```

An element passed as `mut` (`hit(enemies[i])`) is changed where it is, in the array: while the
call runs, nothing else may hold or change that array, so the same call cannot also be given
the array (`attach(nodes[0], nodes)`), and a global array cannot be one the function changes,
itself or in a function it calls. The compiler says so; pass the index instead. Other elements
of the array are fine: `bounce(balls[i], balls[j])`, `hit(d.mesh, d.instances)`; an element and one
inside it (`xs[0]` and `xs[0][0]`) are not. When the function may call a function value (which
the compiler cannot see into), an element of a global array (or of a `mut` parameter's) is given
to it as a copy that is written back to `xs[i]` when it returns, since that code could resize
the array. Elements that code adds at the end leave `xs[i]` where it was; if it removed or
inserted elements before it (`xs.remove(0)`, `xs.clear()`), or changed `xs[i]` itself, the copy
cannot be put back without writing over another element, and the program stops, saying so.

To modify array elements in a loop, use `loop mut`:

```gdscript
loop mut p in particles:
    p.pos += p.vel * dt
```

A variable given a copy of another place (`e = xs[i]`, `cur = l.head!`, what `if let` or `loop
let` binds) and then changed, with nothing reading it after the change, changes only the copy:
the compiler warns of it, saying where the copy came from and how to change that instead (through
the place, `xs[i].hp -= 1`, or with a `mut` parameter: a function that adds at the end of a list
takes `n: mut Node?` and calls itself on `n!.next`).

### Fixed-size arrays

`T[N]` holds exactly N elements, stored in place: inside a struct, a variable or a shader's
uniforms, with no separate allocation. N is a number or a constant (`const SLOTS = 8`, then
`int[SLOTS]`). They are made from a literal with N elements, from `[]` (all zeros, which is also
what a field or variable without a value starts as) or from `fill(x, N)`:

```gdscript
struct Inventory:
    slots: int[8]                   # zeros
    hands: str[2]                   # ""
corners: vec2[4] = [vec2(0, 0), vec2(1, 0), vec2(1, 1), vec2(0, 1)]
inv = Inventory()
inv.slots[3] = 42                   # bounds-checked; a constant index is checked when compiling
loop mut c in corners: c *= 2.0
print(corners.len(), inv.slots == fill(0, 8))
```

They index, slice, loop (`loop x in xs`, `loop mut x in xs`), compare with `==`, print and
work as map keys like `T[]`. A copy copies the elements. A slice (`xs[1..3]`, `xs[[1..end]]`)
is a new `T[]` holding a copy of those elements, as a slice of a `T[]` is. Where a `T[]` is
expected (`sum(xs)`, a parameter `xs: T[]`) a fixed-size array is passed as a new array holding
a copy. Given for a `mut T[]` parameter (`sort(mut xs)`, `xs.reverse()`, `shuffle(mut xs)`) it is
passed as a `T[]` whose elements go back into `xs` when the call returns; a function that changes
the length (`push`, `pop`, ...) panics there, as a fixed-size array keeps its length.

### Maps

`{K: V}` maps keys to values and keeps them in insertion order. `m[k]` reads a value (a
missing key is an error; `m.get(k)` gives an optional, `m.get(k, default)` a default) and
`m[k] = v` sets one. Changing the value in place, `m[k] += 1`, `m[k].push(x)`,
`m[k].hp -= 5`, `m[k][i] = x` or `loop mut x in m[k]`, works on the stored value and adds a
missing key first, with V's zero value (for a struct, its default field values):

```gdscript
counts = {}                             # (its types from the first `counts[k] = v` or `+=`)
loop w in words: counts[w] += 1
groups: {int: str[]} = {}               # (written: what goes in it is pushed, not assigned)
loop w in words: groups[len(w)].push(w)
loop k, v in counts: print("{k}: {v}")
```

An empty `{}` with no type written takes its key and value types from the first `m[k] = v` (or
`m[k] += v`, or `m.get(k, default)`) after it, as an empty `[]` does from a push; until then it
cannot be read or printed.

`m.has(k)`, `m.remove(k)`, `m.keys()`, `m.values()` and `m.len()` do what they say; `m.items()` is the (key, value) pairs, to sort them (`m.items().sorted_by((p): -p.1)`).

A set (`Set[T]`, values without repeats) is written with braces and no colons, `{"a", "e",
"i"}`, or made by a loop, `{loop w in words: w.lower()}`; `{}` is an empty one where a `Set` is
expected (`seen: Set[int] = {}`), and an empty map otherwise. `x in s`, `s.add(x)` and
`s.remove(x)`; more in [API.md](API.md#sets-and-deques).

## 5. Functions

```gdscript
area = (w: f64, h: f64) -> f64: w * h            # the last expression is the result
clamp01 = (x: f64, lo: f64 = 0, hi: f64 = 1) -> f64:
    if x < lo: return lo
    if x > hi: return hi
    x
area(2, 3); area(h = 3, w = 2)                   # named arguments
```

A parenthesized parameter list followed by `->` or `:` is a function; the same syntax
written inside an expression is a lambda.

* The return type may be omitted; it is inferred from the body (recursive functions
  must declare it). `-> void` says explicitly that nothing is returned.
* A default value may use earlier parameters: `rect_at = (p: vec2, w: f64, h: f64 = w)` (the
  argument given for them is used again, so it is a value or a variable).
* **Untyped parameters make a function generic**: `twice = (f, x): f(f(x))` is
  instantiated for each distinct set of argument types (like a template). A lambda inside a
  function is one value, so its untyped parameters take their types from where it is passed
  (`xs.map((x): x * 2)`) or from how its body uses them (`inc = (x): x + 1` makes x an int);
  where neither says, give the type: `(x: f64): x * x`. Such a function can call itself by the
  name it is given, when its parameters' types are written: `dfs = (u: int): ... dfs(v)`.
* Explicit type parameters: `first[T] = (xs: T[]) -> T: xs[0]`. A call can give them when the
  arguments do not say (`from_json[Settings](text)`, `gpu_buffer[Bug](100)`), also a module's
  (`cfg.load[Settings](path)`).
* Through `[]` and `[]=` overloads, `b[i].f = v` and `b[i].f += v` work as for arrays: the
  element is read, changed and written back (its index computed once).
* **Uniform call syntax**: `x.f(a)` is the same as `f(x, a)`. There are no methods,
  only functions; any function can be called with dot syntax on its first argument.
* Functions may be **overloaded** by parameter types. A program's own definitions take
  precedence over standard-library functions with the same signature. An integer literal
  prefers `int`, then another integer type it fits, then `f64`, then `f32`.
* **Operators** can be overloaded: `(+) = (a: Money, b: Money) -> Money: ...`, also
  `([])` and `([]=)` for indexing. `!=` comes from `==`, and `>`, `<=` and `>=` from `<`
  (which is also what `sort`, `min` and `max` use).

### Functions as values, closures, partial application

```gdscript
double = (x: int): x * 2
nums.map(double)
nums.map((x): x * 2)            # parameter types inferred from context
nums.each((x):
    print(x)
    print(x * x)
)
scale = (k: f64, x: f64): k * x
half = scale(0.5, _)            # partial application: `_` marks missing arguments
print(half(10))                 # 5
```

**Closures capture variables, not values**, the same way everywhere: a closure made inside a
function sees (and can change) that function's variables, just as a closure at the top level
sees and changes globals.

```gdscript
make_counter = () -> () -> int:
    n = 0
    ():
        n += 1
        n
c = make_counter()
c(); c()
print(c())                      # 3
```

(A variable that is never changed after a closure captures it is simply copied into the
closure; one that is changed lives in a small shared heap cell. A loop body gets fresh
variables on every iteration, so closures made in a loop each see their own.)

One thing cannot be shared that way: a local variable that can hold functions (a closure, or
an array, struct or map with one inside). A closure stored in it would keep it alive forever,
so changing such a variable after a closure captured it is an error. Globals have no such
limit; or pass the value to the closure as a `mut` parameter:

```gdscript
make_button = () -> Button:
    b = Button("ok", (): pass)
    b.on_click = (): b.label = "clicked"      # error: b holds a function and is shared
    b
on_click = (b: mut Button): b.label = "clicked"  # instead: the button is passed in
```

## 6. Control flow

```gdscript
if a > b: print("a") else if a == b: print("eq") else: print("b")
m = if a > b: a else: b                # if is an expression
if let v = lookup(key): print(v)       # bind the value of an optional when present

loop: ...                              # forever (until break / return)
loop x > 0: x -= 1                     # while
loop i in 0..10: ...                   # 0 to 9, as Python's range(10)
loop i in [1..10]: ...                 # 1 to 10: ] keeps the end
loop i in 0, 2..10: ...                # 0 2 4 6 8
loop i in 10, 9..0: ...                # counting down, 10 to 1
loop x in xs: ...
loop k, v in table: ...                # unpacks: map entries, or an array of pairs
loop mut x in xs: x *= 2               # x is the element itself
loop let job = queue.next(): ...       # while the optional has a value
loop let .cons(x, rest) = list: ...    # while an enum value is that variant (section 7)
break / continue / return
defer close(f)                         # runs when the enclosing block exits
```

**Ranges.** `a..b` goes from `a` up to `b`, leaving `b` out, as Python's `range(a, b)`: `0..n`
is n numbers, and `0..xs.len()` is every index of `xs`. Brackets say which ends are kept: `[a..b]`
both, `[a..b)` without `b` (as `a..b`), `(a..b]` without `a`, `(a..b)` neither. `a..` is open
(counting up forever). `a, b..c` steps by `b - a` (`[a, b..c]` keeps `c`). A range used as a
value is the array of its numbers: `[0, 3..9]` is `[0, 3, 6, 9]`. In index brackets slices go as
Python's: `xs[2..5]` is elements 2, 3 and 4 (`xs[2:5]`), `xs[2..]` to the end, `xs[..3]` the first
three; `xs[end]` is the last element, `xs[[2..5]]` keeps element 5.

The brackets of a range are not an array's brackets, which can look alike. `[1..5]` is the
array `[1, 2, 3, 4, 5]`; one bracket more, `[[1..5]]`, is an array holding that one array (its
`len()` is 1), as `[xs]` holds `xs`. Inside an index the outer brackets are the index's, so
`xs[[2..5]]` is a slice that keeps both ends (elements 2 to 5), not an index by an array.
`[loop i in [1..5]: i]` and `range(1, 6)` are the array too, if the brackets read wrong.

| Written | Gives |
|---|---|
| `1..5`, `[1..5)` | 1 2 3 4 |
| `[1..5]` | 1 2 3 4 5 |
| `(1..5]` | 2 3 4 5 |
| `(1..5)` | 2 3 4 |
| `0..xs.len()` | every index of `xs` |
| `random_int(1, 7)` | 1 to 6, as `1..7` (`random(a, b)`: a number with a fraction, from a up to b) |

**Panics.** An index out of bounds, `!` on `none`, a division by zero, a failed `assert` or
`panic("message")` stops the program with the message and where each function on the way
was called from (the frames of the runtime left out):

```
panic: hit an enemy that was already defeated
    in hit (game.jo:6)
    called from fight (game.jo:9)
    called from update (game.jo:31)
```

A stack overflow (a function that calls itself without end) and a crash in code using raw
pointers or C are reported the same way. (Release builds inline small functions: their frames
show as the line of the call. In a web page the browser's console has the JavaScript stack.)
A run of the same call, or of a few calls over and over (functions calling each other), shows
once with how many times it repeats.

**How deep recursion goes.** A native program's main thread has a stack of 1 GB, taken from
the system only as it is used: a small recursive function (`depth(n - 1) + 1`) goes some 60
million calls deep, walking a linked list with `mut` (`append(n!.next, v)`) about 10 million,
and printing, `==` or hashing a recursive value millions of nodes long. Past that, a stack
overflow says how deep it got:

```
panic: stack overflow, 11,173,887 calls deep (a function that calls itself without end? Recursion this deep wants a loop instead, with an array as its stack if it needs one)
    in append
    called from append (list.jo:16) (11,173,884 times)
    called from the top level of list (list.jo:20)
```

Worker threads (`parallel_map` and the like) have 8 MB each, and a web page has the browser's
stack, which holds some 10,000 calls: there, a recursion that deep is a loop instead, keeping
what it still has to do in an array (`todo.push(n)`, `n = todo.pop()`).
A panic ends the program where it is: `defer`red code does not run (the system closes the
program's files).

**Debuggers and profilers.** Executables written by `sloppy build` carry DWARF line tables and
function names, so gdb and lldb work with the `.jo` source (`break game.jo:31`, `bt`, `next`,
`list`) and perf and other profilers report functions and lines. `sloppy build -g` adds the
variables (Linux on x86-64 and arm64, macOS; there also the lines, which macOS and arm64
executables otherwise leave out): every parameter and local with its type and where it is
while its function runs, and how each frame is made, so a debugger reads the variables of the
functions further up the stack too; the program's globals (top-level variables) are there by
name. In a debug `-g` build a variable lives on to the end of its function (it can be read
anywhere after it is set) and stays in memory or a register calls keep; in a release one it may
be gone (`<optimized out>`) after its last use. The program does the same as without `-g`. `lib/debug` has printers that show strings as text,
arrays and maps as their elements, optionals as their value or `none`, and an enum with fields
as its variant:

```sh
sloppy build -g game.jo
gdb -x ~/.sloppy/lib/debug/sloppy_gdb.py ./game        # break game.jo:31, run, info locals
lldb -o "command script import ~/.sloppy/lib/debug/sloppy_lldb.py" ./game
```

`break __panic` stops a program where it panics, with its variables still there (on Windows a
debugger attached stops there by itself). In VS Code, **Sloppy: Debug File** (F5) does all of this,
through CodeLLDB or Microsoft's C/C++ extension. On Windows, `sloppy build game.jo` also writes
`game.pdb` beside `game.exe`, with the functions and lines, and the program has unwind tables:
Visual Studio, WinDbg and RemedyBG stop at functions and lines, step through the source and show
the call stack; with `-g` the PDB also has the variables and their types. `lib/debug/sloppy.natvis`
shows strings, arrays, maps and optionals as values in Visual Studio and WinDbg (`.nvload
<sloppy>\lib\debug\sloppy.natvis`); VS Code loads it.

**Combined loops.** Bindings and conditions join with `and` / `or` in one loop header:

```gdscript
loop i in 0.. and v in values: ...             # counts alongside: stops when values runs out
loop i in 0.. and v in values and v ^ 2 < limit: ...   # also stops at the first false condition
loop a in xs or b in ys: ...                   # until both run out; a finished one gives none
loop (a in xs or b in ys) and ok(): ...
loop i in 0.. and mut e in enemies: e.hp -= i      # the elements themselves, counted
loop i in 0.. and name, cost in items: ...      # pairs (tuples) unpacked, counted
```

A loop over an array goes over the array as it was when the loop started: removing or adding
elements inside the loop changes the array, not the elements the loop visits (arrays are values).
`loop mut` writes the elements in place, so its body may not add, remove or replace elements of
the array it goes over (the compiler says so); do that after the loop. To keep what stays,
`xs.retain((x): x.alive)` (in place) or `xs = [loop x in xs if x.alive: x]`; to remove as you go,
count down by index (`loop i in [xs.len() - 1, xs.len() - 2..0]`).

Iterators joined with `and` advance together until one runs out; joined with `or` they advance
until all have run out (the variables of finished ones are `none`, so they are optionals).
`loop i, x in xs` does not count: names before `in` always unpack (two: a map's key and value,
or a pair; more: a tuple's parts, `loop name, n, cost in items`).

**Comprehensions** are a loop inside brackets; `if` filters, nested loops flatten:

```gdscript
squares = [loop i in [1..5]: i ^ 2]
evens = [loop n in 0..10: if n % 2 == 0: n]
pairs = [loop i in 0..3: loop j in 0..3: (i, j)]
numbers = [loop s in fields: if let n = to_float(s): n]   # the ones that read as numbers
lengths = {loop w in words: w: len(w)}         # in braces, key: value makes a map
```

**Match:**

```gdscript
match value:
    0: print("zero")
    1, 2: print("small")
    3..9: print("medium")
    'a'..'z': print("a letter code")
    _ if value < 0: print("negative")   # an arm with a condition
    _: print("big")

enum Screen: menu, playing, paused
match screen:                          # an enum's variants (the dot may be left out: `menu:`)
    .menu: draw_menu()
    .playing, .paused: draw_game()     # (a match that leaves some out is an error, unless `_:`)
label = match screen:                  # a match is an expression too
    .menu: "title"
    _: "play"
```

A match on an enum or a union names each variant or member, or has `_:`, also as a statement, so
that one added later is not passed over quietly. A match statement on numbers or text needs no
`_:`: like a `switch` without `default`, it does nothing for the values it does not name. A
match that gives a value needs an arm for every value (`true:` and `false:` cover a `bool`).
Where its type is known, as on a function's last line, each arm gives that type, so the arms
of a `match` or `if` among them may give different members of a union.

An arm can have a condition, `if` and a test after its patterns: `.rect(w, h) if w == h:`,
`int if v < 0:`, `_ if n > 100:`. It is tested when the pattern matches, and when it fails the
arms below are tried. The names the arm binds, and what its pattern narrows, are known in the
condition, and what the condition tests with `is` holds in the arm. An arm with a condition
does not count for naming each variant: an enum's match still needs an arm for that variant
without one, or `_:` (and a `bool`'s, a `true:` and a `false:` without one). A name in a pattern
is a value to compare with, not a new variable: for "any number above 100", `_ if n > 100:`.

A tuple is matched part by part, each part a value, a range, `.variant` or `_` (any), tuples
inside it too:

```gdscript
fizz = (i: int) -> str:
    match (i % 3, i % 5):
        (0, 0): "FizzBuzz"
        (0, _): "Fizz"
        (_, 0): "Buzz"
        _: "{i}"

match (state, key):
    (.idle, .space), (.run, .space): jump()
    (.run, _): run()
```

A match on tuples that gives a value has a `_:` arm for the rest.

## 7. Structs, unions, enums, optionals, tuples

```gdscript
struct Player:
    name: str
    pos: vec2
    hp = 100                   # field with a default

p = Player("ann", vec2(0, 0))
q = Player(name = "bob", pos = vec2(1, 2), hp = 50)
p.pos.x += 1
r = Player()                   # every field at its default, or zero ("", vec2(0, 0), 100)

struct Stack[T]:               # generic struct
    items: T[]

enum Dir: north, east, south, west     # simple enum
d = Dir.north
if d == .north: ...                     # `.name` when the type is known
n = int(Dir.west)                       # 3: a simple enum's variants are numbered from 0
d = Dir((n + 1) % 4)                    # .north: and a number gives its variant (checked)
```

A field left out starts at its default, or at zero (0, "", an empty array, `none`, false; a
function field has nothing to call: calling it stops the program, saying so).
Leave fields out by naming the ones given (`Player(name = "cy")`); values given in order that
stop one or two fields short of a number, text or struct without a default get a warning, as
that is usually a value forgotten.

Structs compare with `==` field by field (and so work as map keys), unless a field holds a
function: functions cannot be compared, so neither can such a struct (the compiler names the
field; compare the fields that can be, `a.name == b.name`).

**Recursive data.** A struct or an enum can hold itself: as an optional, in an enum's variant,
through a union, or through another struct that holds it.

```gdscript
struct Node:
    value: int
    next: Node?                        # a linked list

struct Tree[K]:
    key: K
    left: Tree[K]?
    right: Tree[K]?

enum Expr:
    num(v: f64)
    bin(op: str, l: Expr, r: Expr)     # exactly two operands

list = Node(1, Node(2, Node(3)))
list.next!.next!.value = 30
if let second = list.next: print(second.value)
e = Expr.bin("+", Expr.num(1), Expr.bin("*", Expr.num(2), Expr.num(3)))
```

Such a field keeps its value apart from the struct, in memory of its own that copies share:
assigning or passing a list copies a pointer, not the list. Changing a copy (`b.next!.value = 0`)
first copies the nodes on the way to the change, as an array is copied when it is shared, so
each copy keeps its own value. Reading `n.next!.value` follows the one pointer. A value cannot
hold itself in a loop (`a.next = a` stores a copy of `a` as it was), so printing it, `==`,
hashing and `to_text` end; they walk the value as a recursive function would (tens of thousands
of nodes deep in a native program, a few thousand in a web page), while freeing a list a million
long takes no deeper calls than freeing one node. A field not given, or in a value made zero
(`n: Node`), is `none` when it is optional; one that is not (`l: Expr`) holds its type's zero
value, which for an enum is its first variant (`num(0.0)` above), or the first variant without
the type in it when the first holds one (an `Expr` whose first variant is `bin` starts as
`bin("", num(0.0), num(0.0))`). A type whose values would hold themselves without end is an
error: `struct Bad: me: Bad` (make it `me: Bad?`, or an array). Arrays still hold their elements
apart too (`kids: Node[]` for a tree with any number of children). A struct holding itself is
not plain data: it cannot go to the GPU (`gpu_buffer`, shaders), be `@packed`, or be read by C
through a pointer.

Changing a recursive value, as a course's binary search tree does, is a recursion with `mut`:
the parameter is the field itself (`n.left`, `n.right`), so assigning it changes the tree.

```gdscript
struct Tree:
    key: int
    left: Tree?
    right: Tree?

insert = (n: mut Tree?, k: int):
    if n == none: n = Tree(k)                  # an empty place: the new node goes here
    else if k < n!.key: insert(n!.left, k)
    else if k > n!.key: insert(n!.right, k)

delete = (n: mut Tree?, k: int):
    if n == none: return
    if k < n!.key: delete(n!.left, k)
    else if k > n!.key: delete(n!.right, k)
    else if n!.left == none: n = n!.right      # the node goes; its one child takes its place
    else if n!.right == none: n = n!.left
    else:
        m = n!.right!                          # two children: the smallest key on the right
        loop let l = m.left: m = l             # (reading through a copy is fine)
        n!.key = m.key
        delete(n!.right, m.key)

root: Tree? = none
loop k in [5, 3, 8, 1, 4]: insert(root, k)
delete(root, 3)
```

A variable is a value of its own, so a cursor is a copy: after `cur = list.head!` and
`loop let nx = cur.next: cur = nx`, a change through `cur` (`cur.next = Node(v)`) changes
`cur` only, and the list stays as it was. Reading through a cursor is fine; to change the
structure, recurse with `mut` as above (`append(n!.next, v)`), or keep the nodes in an array (or
a [`Pool`](API.md#pools-and-handles)) and link them by index: `next: int` (-1 for none) is what
a doubly linked list, a tree with parent links or a graph needs, since a value cannot point
back at what holds it.

```gdscript
struct Node:
    value: int
    prev = -1
    next = -1

nodes: Node[]
push_back = (nodes: mut Node[], tail: int, v: int) -> int:
    nodes.push(Node(v, prev = tail))
    if tail >= 0: nodes[tail].next = nodes.len() - 1
    nodes.len() - 1
```

**Unions** hold a value of one of several types. `is` tests which, and a variable that has
been tested *is* that type where the test holds — in the `if`, after an `if` that returns or
breaks, on the right of `and`, and in `match` arms:

```gdscript
struct Circle: r: f64
struct Rect: w: f64; h: f64
type Shape = Circle | Rect

area = (s: Shape) -> f64:
    if s is Circle: return PI * s.r ^ 2
    s.w * s.h                           # s is a Rect here

describe = (v: int | str) -> str:
    match v:
        int: "the number {v + 1}"
        str: "the text {v}"

parse_int = (s: str) -> int | ParseError: ...
r = parse_int(text)
if r is ParseError: return r            # (`?` says this in one step: see Errors below)
print(r + 1)                            # r is an int
```

`x is not T` is `not (x is T)`. A branch that cannot go on (it returns, breaks, continues,
panics or exits) narrows what follows it, in functions and at the top level alike. Ruling a member out narrows to the others: after `if s is Circle: return` in a function taking
`Circle | Rect | Tri`, `s` is a `Rect | Tri`, and in an `if`/`else if`/`else` chain each branch
knows what the earlier tests excluded. A `match` arm listing several types (`int, str: ...`)
sees their union, and `_:` the members no earlier arm matched. Fields and globals narrow the same
way as variables (`if self.target is Enemy: self.target.hp -= 1`); assigning a member to a field
narrows it to that member, and passing the value on as a `mut` argument forgets what was known.
Assigning another member to a narrowed variable makes it the whole union again from there on;
inside a loop that reads it as the narrowed member, that would make the next round read the
new value as the old member, so it is an error there unless the loop ends right after (`break`,
`return`). A variable that code the compiler cannot follow (a closure, a function changing a
global) changes after the test stops the program when it is read as the member, saying where
the test was. A union fits
any union that has all of its members (`int | str` passes for `int | str | f64`), and a generic
parameter inside a union stands for the members the union does not name: `value_or[T] = (r: T |
Err, d: T) -> T` called with an `int | str | Err` has `T = int | str`. With two parameters,
`unwrap_or[T, E] = (r: T | E, d: T) -> T`, the other arguments decide one (`d: T`) and the other
stands for the rest; when nothing does (`expect(r, "msg")`), the call gives them:
`expect[int, ParseError](r, "msg")`. A union value prints as the value it holds. `T | none` is
`T?`, so a `T??` is a `T?` too: a map of optionals' `m.get(k)` is `none` for a missing key and for
a `none` kept alike (`m.has(k)` tells them apart). A `T[]` passes where a `T?[]` is expected as
a copy, its elements as optionals (`count(xs)` for `count = (xs: int?[]) -> int`).

A union does the work of a base class. Passing one where a function has an overload for each
of its members calls the overload for what it holds (a `mut` parameter changes it in place), and
a field every member has, of one type, is read from whichever it is:

```gdscript
struct Walker: pos: vec2; speed: f64
struct Flyer: pos: vec2; height: f64
type Mob = Walker | Flyer

step = (w: mut Walker, dt: f64): w.pos.x += f32(w.speed * dt)
step = (f: mut Flyer, dt: f64): f.height += dt

loop mut m in mobs: m.step(dt)          # Walker's or Flyer's step
loop m in mobs: circle(m.pos, 8, RED)   # both have pos
```

(Assigning such a field still needs the member: `if m is Walker: m.pos = p`, or a `match`.)

**Optionals:**

```gdscript
best: int? = none
if let v = lookup(key): print(v)        # bind when present
if let h = env("HOME") and h != "": print(h)   # and a condition on it (else: when either fails)
if best is int: print(best + 1)         # `is` works on optionals too
if best != none: print(best + 1)        # and so does comparing with none (`is not none` too)
n = lookup(key) ?? 0                    # default
k = lookup(key)!                        # unwrap or panic
```

**Errors.** A function that can fail returns its result or the reason: `T?` when there is
nothing to say (`none`), or `T | SomeError`, where `SomeError` is a struct of your own, declared
`error struct`, holding what the caller needs to know. Panics are for mistakes in the program (an
index out of bounds, a broken assumption); things that can go wrong while it runs (bad input, a
missing file) are values.

The caller can handle a failure where it is: `x ?? default` or `if let v = x:` for a `none`,
`is` (or a `match`) for an error, after which the value is what is left:

```gdscript
error struct ParseError:
    msg: str
    line: int

parse_num = (s: str, line: int) -> int | ParseError:
    if let n = to_int(s): return n
    ParseError("not a number: '{s}'", line)

r = parse_num("12", 1)
if r is ParseError: print("line {r.line}: {r.msg}")
else: print(r + 1)                      # r is an int
```

Or it can pass the failure on to its own caller. `?` returns a missing value or an error from
this function; otherwise it gives you the value:

```gdscript
total = (text: str) -> int | ParseError:
    sum = 0
    loop i in 0.. and l in split(text, "\n"):
        sum += parse_num(l, i + 1)?         # a ParseError is returned from total as it is
    sum

load_score = (path: str) -> int?:
    text = read_file(path)?             # none: no file
    to_int(text)?                       # none: not a number
```

A function that gives back nothing but can fail returns `void | SomeError`: a bare `return`, or
reaching the end, gives the void, and `?` on its call passes the error on:

```gdscript
save_all = (dir: str) -> void | SaveError:
    loop s in sheets: save_sheet(dir, s)?
```

A missing value can also end the function, or a loop round, right there: `n = to_int(s) ??
return ParseError("not a number")`, `?? continue`, `?? break`.

`sum += parse_num(l, i + 1)?` is short for

```gdscript
r = parse_num(l, i + 1)
if r is ParseError: return r
sum += r
```

- `?` passes on `none`, and each member of the union declared `error struct` or `error enum`
  (only the value's own members: a `ParseError[]` is an array, not a failure); what is left is
  the value. `error` adds nothing else (no fields, no base type), and a name ending in `Error` is
  a habit, not what decides: the library's `JsonError`, `TextError` and `ModelError` are
  declared so. `?` on a value with nothing to pass on (an `int`, or a union whose structs are not
  declared `error`) is an error, as is one where every member would be passed on.
- What `?` can return must fit the result type of the function it is in (the nearest one: in a
  lambda, the lambda's): the compiler says what to add (`-> int | ParseError`), or convert it
  there, `if r is ParseError: return EvalError(r.msg)`. The result type has to be written where
  `?` is used, unless an earlier `return` has settled it. `?` cannot be used at the top level of
  a program or in a test (there is no function to return from), nor in deferred code; a `defer`
  runs when `?` returns, as for any `return`.
- It is an expression, so it goes anywhere one does, evaluated left to right: `add(a()?, b()?)`
  calls `b` only when `a` gave a value, a `loop` condition with a `?` in it checks it each time,
  and `"{f()?}"`, `x and f()?` (only when x holds), `load()?.items[0]` work.
- `a()?.b` returns from the function when `a()` gives none; it is not optional chaining. For a
  value that may be none, `(a() ?? default).b` or `if let v = a(): v.b`.
- `??`, `if let` and `!` handle `none` only: an error goes through them unchanged.
- An error cannot pass through `?` as a value: the members of a union that are errors always
  return. To give one back as data (a list of the problems found), return them in an array, or
  wrap the error in a struct of its own.
- A call whose result can be an error, written as a statement, gets a warning (`save(path)` with
  `-> bool | SaveError`): handle it, pass it on with `?`, or drop it on purpose with
  `_ = save(path)`.

**Tuples:**

```gdscript
pair = (1, "one")
a, b = pair
print(pair.0)
```

Tuples compare element by element, the first that differs deciding: `(1, "z") < (2, "a")`, and
sorting `(score, name)` pairs sorts by score, then by name.

Enums whose variants carry fields also exist (unions are usually simpler):

```gdscript
enum Shape:
    circle(r: f64)
    rect(w: f64, h: f64)
s = Shape.rect(2, 3)
area = match s:
    .circle(r): PI * r ^ 2             # an arm names the variant and binds its fields, in order
    .rect(w, h) if w == h: w * w       # a condition on them (a square)
    .rect(w, h): w * h
if s is .circle: print("round")        # which variant it is (`is not` too)
if let .rect(w, _) = s: print(w)       # its fields, when it is that variant (`_`: one not used)
enum Tree[T]:                           # generic: the type arguments come from the fields given
    leaf
    node(v: T, kids: Tree[T][])
t = Tree.node("a", [])                  # a Tree[str]
```

An arm binds a variant's fields by position, as plain names (or `_`), one variant to an arm.
`x is .rect` tests which variant a value is without naming its fields (for an enum without
fields it is `x == .rect` too). `if let .rect(w, h) = s:` names them when `s` is that variant,
with `else:` (or `else if let`) for the rest and `and` for a condition on them, as `if let` does
for an optional; it is an expression too, `if let .num(v) = e: v else: 0.0`. `loop let .cons(head,
tail) = list:` goes round while the value is that variant, which walks a list made of an enum
holding itself (`list = tail` in the loop). Patterns do not nest, and do not test a field's value
in its place (`.bin("+", .num(a), _)`): name the fields and test them in a condition,
`.bin(op, l, r) if op == "+" and l is .num:`, then `if let .num(a) = l:` in the arm.

## 8. Arrays for numeric work

Inside array brackets elements are separated by spaces or commas: `[1 2 3]`, `[a, b]`.
An operator joins what is on both sides of it, whatever the spaces: `[a -b]` and `[a - b]` are
both one element, a - b; a negative element is put in parentheses or after a comma, `[a (-b)]`,
`[1 (-2) 3]`, `[a, -b]`. A space before `(` or `[` starts a new element (`[a (-b)]`), and `f(x)`
/ `xs[i]` are written without one. `[xs... 4 5]` spreads an array into a literal and
`fill(x, n)` repeats a value.

**Elementwise operations.** The dotted operators `.+ .- .* ./ .% .^ .== .!= .< .<= .> .>=`
apply element by element, and `f.(xs)` applies any function to each element. Arrays of
different shapes broadcast like numpy: a scalar, or a dimension of length 1, stretches to fit.
A whole dotted expression runs as one loop, without temporary arrays:

```gdscript
xs = linspace(0, 1, 5)
ys = 3.0 .* xs .^ 2 .+ 1.0       # one loop
mask = xs .> 0.5                 # bool[]
roots = sqrt.(xs)
```

(Plain `+` on 1-D arrays concatenates, as for lists.)

**Picking elements.** An array of indexes or a mask picks elements, as in numpy: `xs[mask]`
(a `bool[]` as long as `xs`) gives the elements where it is true, `xs[[3, 0]]` (an `int[]`) the
ones at those indexes, in that order. Assigning to them sets them: `xs[xs .< 0.0] = 0.0`,
`xs[idxs] = values`.

```gdscript
big = xs[xs .> 0.5]
sorted = xs[argsort(xs)]
```

**n-dimensional arrays** (`T[,]`). How many dimensions an array has is part of its value, as
in numpy: `T[,]`, `T[,,]` ... all name the same type (the commas are for the reader), and
`m.shape` holds the dimensions. Rows are separated by `;` or line breaks; `[a; b]` stacks arrays
(1-D arrays become rows, n-dimensional ones gain a dimension).

```gdscript
m = [1.0 2.0; 3.0 4.0]
grid = [0 1 0
        1 1 1]
rows = [a; b]                    # stack arrays a and b as rows
print(m[1, 0], m.shape)          # 3.0 [2, 2]
m[0, 1] = 5.0
v = m * [1.0, 1.0]               # matrix times vector
p = m * transpose(m)             # matrix product
k = m .* 2.0 .+ [10.0 20.0]      # broadcasting a row
cube = zeros(4, 4, 4)            # 3-D
cube[1, 2, 3] = 1.0
layers = cube .* reshape([1.0, 2.0, 3.0, 4.0], 4, 1, 1)   # broadcasting along the first axis
```

Ranges among the indexes select parts: `m[i, ..]` is row `i`, `m[.., j]` column `j`,
`m[1..2, 3..]` a block (ranges include both ends; `a..` runs to the end of the axis, and indexes
left out at the end mean whole axes). A part is an array of its own; assigning to one writes into
the array: `m[.., 0] = xs`, `m[0, ..] = 0.0`. A 1-D one (a row, a column) goes where a `T[]` is
expected, as in `argmax(m[0, ..])` or a function of your own (one with more dimensions there
stops the program: `m.data` has all the elements). `sum(m, axis)`, `mean`, `min` and `max` reduce along
one axis (`sum(m, 0)` adds up the rows: one sum per column).

```gdscript
img = zeros(480, 640, 3)
img[.., .., 0] = 1.0             # the red channel
top = img[0..239, ..]
brightness = sum(img, 2)            # (480x640)
```

`zeros`, `ones`, `rand` (uniform in [0, 1)) and `randn` (normal) take 1 to 4 dimensions (with
one, they make a plain `f64[]`); also `eye(n)`, `linspace(a, b, n)`, `reshape(xs, dims...)` or
`reshape(xs, shape)`, `ndarray(data, shape)`, `transpose` (reverses the axes), `row(m, i)`,
`col(m, j)`, `flatten`, `size`, `ndim`, `len` (the first dimension), `sum`, `mean`, `min`,
`max`, `dot`, `norm`. On 2-D arrays `+ -` work elementwise on equal shapes and `*` is the matrix product.
Indexing with the wrong number of indexes, and shapes that do not broadcast, are errors when
the program runs, with the shapes in the message.

**From NumPy.** The library has most of what numeric code reaches for (the API reference lists
the rest under Arrays):

| NumPy | Sloppy |
|---|---|
| `np.zeros((3, 4))`, `np.ones(5)`, `np.eye(3)`, `np.full(3, 7.0)` | `zeros(3, 4)`, `ones(5)`, `eye(3)`, `fill(7.0, 3)` |
| `np.arange(5)`, `np.arange(0, 2.5, 0.5)` | `0..5`, `[loop i in 0..5: f64(i) * 0.5]` |
| `np.linspace(0, 1, 5)`, `np.random.rand(3, 4)`, `np.random.randn(100)` | `linspace(0, 1, 5)`, `rand(3, 4)`, `randn(100)` |
| `a * 2`, `a + b`, `a ** 2`, `a > 0.5` (elementwise) | `a .* 2.0`, `a .+ b`, `a .^ 2`, `a .> 0.5` |
| `np.sqrt(a)`, `np.clip(a, 2, 4)` | `sqrt.(a)`, `clamp.(a, 2.0, 4.0)` |
| `a @ b`, `a.T`, `a.reshape(2, 2)`, `a.shape` | `a * b`, `transpose(a)`, `reshape(a, [2, 2])`, `a.shape` |
| `a[0, :]`, `a[:, 1]`, `a[1:3]` | `a[0, ..]`, `a[.., 1]`, `a[1..2]` (ranges include both ends) |
| `a[a > 0.5]`, `a[a < 0] = 0`, `a[np.argsort(a)]` | `a[a .> 0.5]`, `a[a .< 0.0] = 0.0`, `a[argsort(a)]` |
| `np.where(a > 2, a, 0)` | `[loop x in a: (if x > 2.0: x else: 0.0)]` |
| `a.sum(axis=0)`, `a.mean()`, `a.std()`, `a.var()` | `sum(a, 0)`, `mean(a)`, `std_dev(a)`, `variance(a)` |
| `np.percentile(a, 90)`, `np.median(a)`, `a.argmax()`, `np.cumsum(a)` | `percentile(a, 90.0)`, `median(a)`, `argmax(a)`, `cumsum(a)` |
| `np.concatenate([a, b])`, `np.vstack([a, b])`, `np.dot(a, b)` | `a + b`, `[a; b]`, `dot(a, b)` |
| `np.linalg.solve(m, v)`, `np.linalg.inv(m)`, `np.linalg.det(m)` | `solve(m, v)`, `inverse(m)`, `det(m)` |

Two differences catch NumPy hands: `+` on 1-D arrays joins them (`.+` adds), and a whole
dotted expression is one loop, so `a .* 2.0 .+ b` makes no array in between.

**Struct-of-arrays.** `ps: soa Particle[]` is used like `Particle[]` for `push`, `pop`,
`remove`, `clear`, `reserve`, `truncate`, `len`, `ps[i]`, `ps[i].x += 1`, `loop p in ps`,
`loop mut p in ps`, conversion from `Particle[]`, printing and saving (as the array of its
elements) — but keeps each field in an array of its own. (Not there: `retain`, `filter`, `map`,
`count`, `any` and the other functions taking an array; a combined loop's `mut` element.) A
loop variable stands for the element itself: `p.x` reads (or, in `loop mut`, writes) only the
`x` array, so a loop that looks at two fields of a large struct touches only those two arrays.
Using a whole element, `o = ps[j]` or `p` as a value, reads every field: in a hot loop, read the
fields you need, `ps[j].pos`. `ps.x` is the whole field array, for elementwise math:

```gdscript
ps: soa Particle[] = make_particles()
loop mut p in ps:
    p.pos += p.vel * dt                 # reads vel, writes pos: no other field is touched
ps.age = ps.age .+ dt
```

**GPU arrays.** `gpu(xs)` copies an array to GPU memory and `cpu(g)` copies it back. A dotted
expression whose arrays are GPU arrays runs on the GPU as one program, generated from the
expression at compile time (a compute program with Vulkan, a fragment program with OpenGL and
WebGL) — functions applied with `f.(g)` are translated like shader functions, and the numbers in
the expression become its parameters:

```gdscript
g = gpu(rand(4_000_000))
h = wave.(g) .* 0.5 .+ g          # one GPU program
ys = cpu(h)
```

GPU arrays have the shape of the array they were made from (up to 4 dimensions) and broadcast
like arrays on the CPU; `cpu(g)` gives an array of that shape. Values on the GPU are `f32`, or `i32`
for arrays made from integers: integer arithmetic keeps integer semantics (`7 / 2` is 3, `%` keeps
the dividend's sign, as on the CPU), and mixing integers with floats gives floats. `sum`, `mean`,
`min` and `max` are computed on the GPU (float sums add 64 values at a time in `f32`, then the
partial sums in `f64`; integer sums are exact, on the CPU). GPU memory is
reused automatically once no copy of a GPU array is left. Native programs use Vulkan (no window
needed), else OpenGL ES; web builds WebGL 2. Where none of them can (no driver,
`SLOPPY_SOFTWARE=1`, an old browser) the same expressions run on the CPU, so programs work
everywhere; `gpu_available()` tells which.

**GPU buffers and compute functions.** For data that lives on the GPU: `gpu_buffer(xs)` holds
an array of plain data there (numbers, bools, vectors and structs of them; no strings, arrays
or functions), and a *compute function* `f(id: int, params: P)`, written like a
shader function, runs once for each `id` — on the GPU — when `dispatch(compute(f), n, params)`
is called. It reads and writes the buffers among its parameters by index:

```gdscript
step = (id: int, u: Step):           # struct Step: bugs: GpuBuffer[Bug]; dt: f32
    u.bugs[id].pos += u.bugs[id].vel * u.dt

dispatch(compute(step), len(bugs), Step(bugs, dt))
```

(`u.bugs[id].pos = v` reads the element, changes it and writes it back, as for any type
defining `[]` and `[]=`; changing several fields, `b = u.bugs[id]` first is shorter.) An empty
buffer of n elements is `gpu_buffer[Bug](n)`. A compute function over a grid takes
`id: ivec2` and runs once per cell: `dispatch(compute(blur), ivec2(w, h), params)` (in groups of
8 by 8 on the GPU; with `id: ivec3`, `ivec3(w, h, d)` and 4 by 4 by 4).

Shaders read buffers among their uniforms too (`u.bugs[instance_id()]`), a buffer can be a
mesh's vertices (`gpu_mesh`) or a draw's instances, and `draw_indirect` takes the counts of its
draws from a buffer that compute functions fill (GPU-driven drawing); `draw_indirect_count`
takes how many draws there are from a buffer too. Subgroup operations combine values across
the invocations a GPU runs together (`subgroup_add`, `subgroup_exclusive_add`, `subgroup_min`,
`subgroup_elect`, `subgroup_broadcast_first`...: 32 at a time on NVIDIA, 1 on the CPU), e.g. one
atomic per subgroup rather than one per element. `atomic_add` and the other
atomics change an element that many invocations change at once; what a dispatch writes is
seen by every dispatch and draw after it. Through Vulkan buffers are GPU memory read by
address and compute functions compute programs (SPIR-V made by the compiler); elsewhere
(OpenGL, the software renderer, the web) they are CPU memory and the same functions run on the
CPU's cores, so the program behaves the same. `gpu_compute()` tells which.
Numbers follow the CPU's rules on the GPU too (unsigned division, comparisons and shifts,
narrow types wrapping, float to integer conversions saturating), with one difference, as in
shaders: GPU arithmetic is 32-bit, so there an `int`, `i64` or `u64` wraps at 32 bits and an
`f64` is computed as an `f32`. Compute functions that use `i32`, `u32` and `f32` give the same
results everywhere. A compute function can read a texture among its parameters (`texel`,
`sample`) through Vulkan and the software renderer; run on the CPU beside OpenGL or WebGL, those
give white.

## 9. Modules

A module is a file: `'physics.jo'` (relative to the importing file) or a standard-library
module by name (`thread`). There are three ways to bring one in:

```gdscript
import 'physics.jo'                         # physics.step(b), physics.Body: the names under the module's
import 'physics.jo' as ph                   # ph.step(b)
from 'physics.jo' import step, Body, gravity as g     # just these names, as they are (or renamed)
use 'physics.jo'                            # all its names, as they are
```

`import` keeps a module's names apart and is the one to reach for in a program of several
files; `from ... import` picks names (a long list can go in parentheses over several lines);
`use` suits a small program split into files that share one set of names. Names starting with
`_` are private to their file: `use` leaves them out, while `physics._helper` and
`from 'physics.jo' import _helper` reach them deliberately. A module's own functions with an
imported function's name are overloads of it; any other clash is an error (rename with `as`).
`use` and imports are not transitive: a file sees the names of the modules it brings in itself.
A module's top-level code runs when the program starts, before the code of the file that brings
it in (each module once). Its `main`, if it has one, does not: only the program's own file's
`main` runs, as Python's `if __name__ == "__main__":` does, so a module can keep a `main` that
tries it out by itself (`sloppy physics.jo`), and its `test` blocks run with `sloppy test
physics.jo`.
A variable brought in by `use` (or the library's, like `ui_style`) is changed by assigning to
it, at the top level as in a function: `volume = 0.5` after `use 'audio_settings.jo'` sets that
module's `volume`, not a new one.

The core standard library (strings, arrays, maps, math, vectors, files, numeric arrays, and
the game/graphics/audio API) is always available without importing.

**Packages.** Other people's code comes by git URL (or from a directory), named in the build
block:

```gdscript
build:
    physics = package("https://github.com/ann/sloppy-physics")
    tween = package("https://github.com/bob/tween", "v1.2")     # a tag, a branch or a commit
    shared = package("../shared")                               # a directory

import physics                      # the package's main file: physics.jo at its root (or its only file there)
import 'physics/world.jo' as world  # any other file of it
```

`sloppy add https://github.com/ann/sloppy-physics` writes that line (into the `.jo` file in the
current directory, or the one given) and fetches it. The first build pins each git package to a
commit in `sloppy.lock` beside the program: keep that file with the program, and every build
uses the same code, whoever builds it (delete a package's line to take its newest commit). Git
fetches each commit once, into a cache (`~/.cache/sloppy/packages`; `SLOPPY_PACKAGES` puts it
elsewhere), so later builds need no network. The packages a package names in its own build
block come along. There is no registry: a package is any repository with Sloppy files.

## 10. Compile-time features

```gdscript
build:                          # build options live in the source
    target = wasm               # native (default: this machine) | linux | linux-arm64 | windows | macos | wasm
    opt = release               # debug | release
    output = "mygame"           # the file `sloppy build` writes (beside the program)
    name = "My Game"            # PROGRAM_NAME: window title, and where save_data keeps data
                                # (a folder's name, as Windows allows them: no / \ : * ? " < > |)
    icon = "icon.png"           # a square PNG (up to 256 px): the .exe's icon, the window's (on
                                # Windows and X11), the Dock's on macOS, the web page's;
                                # PROGRAM_ICON has its bytes
    js = "glue.js"              # web builds: JavaScript put in the page; it gives `extern`s

when TARGET == "wasm":          # compile-time conditional; the dead branch is not compiled
    ...
else when TARGET == "windows":  # (TARGET is "linux", "windows", "macos" or "wasm"; also DEBUG,
                                #  and PROGRAM_NAME: the build block's name, else the file's)
    ...
else:
    ...

logo = embed("logo.png")        # file contents baked into the program as u8[]
assets = embed_dir("assets")    # every file under a directory: {"hero.png": ..., "sfx/hit.wav": ...}

test "math works":
    assert(1 + 1 == 2)
```

**JavaScript in a web build.** A web build's `extern` functions are JavaScript ones: the build
block's `js` file goes into the page before the program starts, and sets them on `sloppy.env`
(a site's analytics, a leaderboard, the page around the game). Text goes as a pointer and a
length, read with `sloppy.text(p, n)`; an `int` arrives as a BigInt, an `f64` as a number:

```gdscript
build:
    js = "glue.js"

when TARGET == "wasm":
    extern js_report = (p: *u8, n: int, score: int)
    report = (name: str, score: int): js_report(data(name), len(name), score)
else:
    report = (name: str, score: int): pass
```

```js
// glue.js
sloppy.env.js_report = (p, n, score) => console.log(sloppy.text(p, n), Number(score));
```

`sloppy test file.jo` runs the file's top-level code, then each `test` block in order,
reporting `test name ... ok` per block. On Linux and macOS each test runs in a process of its
own: one that fails (an `assert` with its message and location, or a panic) is reported
`FAILED`, the others still run (and do not see what it changed), and the run ends with how many
passed and failed and exit status 1. On Windows and the web the first failure stops the run.
`sloppy test file.jo parse save` runs only the tests whose names have `parse` or `save` in
them. A test that calls `exit()` fails (it did not reach its end). `assert(a == b)` (and the
other comparisons) with no message of its own says what each side was when it fails,
`assertion failed: xs == ys (xs is [1, 2], ys is [1, 3])`; `unwrap(r)` and `expect(r, "what")`
give an optional's or a result's value, stopping with what it held instead. `sloppy check
file.jo` and editors check the `test` blocks too; `sloppy file.jo` builds the program without
them, so a test half written does not keep it from running.

**Release builds.** `opt = release` (or `sloppy build --release`) inlines refcount, uniqueness
and bounds-check fast paths and runs the optimizer (constant folding, copy propagation,
common subexpressions, redundant load and bounds-check elimination, inlining, keeping small
vectors in registers). Debug builds compile faster; both have identical behavior, including
bounds checks.

In release builds, `b = xs[i]` where `b` is only read (and nothing changes `xs` while `b` is
used) is the element itself, not a copy: reading a few fields of a big struct in an array
costs only those reads. A loop whose bounds checks index by the loop variable checks the
whole range once, up front (and runs as before when that test fails, so a failing check
still stops it where it always did). A loop that does the same arithmetic to element `i` of
arrays of numbers (`ys[i] = ys[i] + a * xs[i]`, a dotted expression, `loop mut x in xs`
with `+ - * /`) runs several elements at a time: 256-bit AVX2 instructions where the processor
has them, else SSE2, chosen when the program starts (`SLOPPY_NO_AVX=1` forces SSE2). Every
element gets the same operations in the same order as one at a time, so the results are
identical on every machine (sums over a loop keep their order and are not vectorized).

Array indexing is always checked, except where the check cannot fail: in
`loop i in 0..xs.len()` (or `0..n` with `n = xs.len()`, or `xs = fill(v, n)` and
`0..n`, starting from any expression that cannot be negative) `xs[i]` has no check, as long
as the function never resizes `xs` — writing its elements is fine. So the usual index loop
costs what it would in C.

## 11. Parallelism

Data-parallel helpers run a function over many elements on all CPU cores (fork-join):

```gdscript
lengths = parallel_map(words, (w): expensive(w))      # [loop x in xs: f(x)]
parallel_update(particles, (p): step(p, dt))          # xs[i] = f(xs[i]) in place
rows = parallel_range(height, (y): render_row(y))     # [loop i in 0..n: f(i)]
```

The function runs on many threads at once: it may read anything, but it must not change
globals or the variables it captured (that would be a data race). Return results instead.
A call costs a few microseconds beyond its work (the threads wait for jobs and take parts of
one as they are free), so work of a few tenths of a millisecond or more is worth sharing; each
part should do more than a handful of operations.
`random()` may be called there: each thread draws from a generator of its own, so the numbers
differ from run to run even after `seed_random`; for the same ones every run (and faster), give
each piece of work its own generator, `g = rng(seed + k)` and `g.next_float()`. The
compiler checks this, also in the functions it calls, and names the variable, so it must see
which function runs: give a function by name, a lambda or a partial application (`f(k, _)`), not
a function kept in a variable, and call functions by name inside it. These helpers are only called
directly, not kept in a variable or partially applied. A function of your own that hands the
function it is given on to them is marked `@parallel`, and then what its callers give it is
checked:

```gdscript
@parallel
each_row = (f: (int) -> Row) -> Row[]: parallel_range(height, f)
```

`@deterministic` marks a function whose function arguments must give the same results on every
machine, as netplay's tick does (`netplay.session` is marked): the compiler warns where they, or
the program's functions they call, take random numbers (but from an `Rng` they are given), read
the clock or the input, or change a global.

A number the threads change together is an `Atomic`: `done = atomic(0)`, then `done.add(1)`,
`done.get()`, `done.set_max(v)` and `done.compare_swap(old, new)` from parallel code (copies
of it are the same number). It counts work done, or flags that the answer is found so the other
threads skip the rest:

```gdscript
found = atomic(-1)
parallel_range(n, (i: int) -> int:
    if found.get() < 0 and is_answer(i): found.compare_swap(-1, i)
    0
)
```

(Writing through a raw pointer is left to the program: it is how disjoint parts of one buffer are
filled in parallel.) Web builds run the same code on one thread.

## 12. Programs and the game loop

A program runs its top-level statements, then `main()` if defined. A `main = () -> int` gives
the program's exit code (0: all went well); `exit(code)` ends it anywhere.
If the program defines `update(dt: f64)` and/or `draw()`, a window opens and they are
called every frame (this is also how programs run in the browser). `dt` is the seconds since
the last frame, at most 0.1: after a long stall (the window dragged, a hidden tab) the game
takes one 0.1 s step, not a jump. A clock that must keep up with real time reads `elapsed()`
(or, for music, `audio_time()`) instead of adding up `dt`. An `on_quit = ():` runs once as
the game ends (its window closed, `quit()` called, or a web page closed or left): the place to
save. A program without a window has it too: it runs as the program ends, at its last line,
`exit()`, or ctrl-c or SIGTERM (which then end it at its next `sleep` or `net.wait`; one that
loops `loop not stopping():` ends its loop itself).

```gdscript
pos = vec2(100, 100)

update = (dt: f64):
    if key_down(.right): pos.x += 200 * dt

draw = ():
    clear(rgb(0.1, 0.1, 0.15))
    circle(pos, 20, rgb(1, 0.5, 0.2))
```

Each frame starts black, on every platform: a picture kept from frame to frame (a trail, a
pen, a painting) is a render target, drawn into and never cleared (`draw_to`, then
`draw_to_screen()` and `draw_target(rt)`). `window("x", 480, 270)` asks for 480 x 270 units:
the window may be bigger, its picture scaled to fit (on a HiDPI display, twice the pixels).

Time away, as an idle game counts it: save the moment with the rest (`unix_time()`, seconds
since 1970), and on loading, the seconds since then are what was missed; the same catches up
after a hidden tab or a stall, which `dt` (at most 0.1) does not:

```gdscript
struct Save:
    dust = 0.0
    rate = 1.0
    saved_at = 0.0
state = load_value("save", Save())
if state.saved_at > 0.0: state.dust += state.rate * min(unix_time() - state.saved_at, 8.0 * 3600.0)
last = unix_time()

update = (dt: f64):
    now = unix_time()
    state.dust += state.rate * (now - last)          # (real time, hidden tab or not)
    last = now
    if every(1, 30.0): keep()

keep = ():
    state.saved_at = unix_time()
    save_value("save", state)
on_quit = (): keep()
```

**Input.** `key_down(k)` is true while a key is held, `key_pressed(k)` / `key_released(k)` in
the frame it goes down or up, and `key_typed(k)` when pressed and again as it repeats while held
(at the desktop's repeat rate: for moving through text or menus). `text_input()` is the text
typed this frame, repeats included. Likewise `mouse_down`, `mouse_pressed`, `mouse_pos()`,
`mouse_wheel()`, and gamepads (`gamepad_down`, `left_stick()`); `input_axis()` combines arrows,
WASD and the left stick. On a Steam Deck the built-in controls are a gamepad when the game is
started from Steam (in Desktop Mode too, after Games → Add a Non-Steam Game); started any other
way, Steam turns them into a keyboard and mouse. For mouse look, `mouse_lock()` hides the pointer and keeps it in the
window while `mouse_delta()` reports how far it moved (Wayland, X11 and browsers, where the
lock starts at the next click and Escape ends it); `mouse_lock(false)` lets it go.

Dragging is a pick on `mouse_pressed`, a follow while `mouse_down`, and a drop on
`mouse_released` (with a camera, `screen_to_world(mouse_pos())` is where the pointer is in the
world; for a turned or scaled card, test `rotate(mouse_pos() - card.pos, -card.angle)`):

```gdscript
dragged = -1
grab = vec2(0, 0)
update = (dt: f64):
    m = mouse_pos()
    if mouse_pressed(.left):
        loop i in 0.. and c in cards:
            if length(m - c.pos) < 40.0:
                dragged = i
                grab = c.pos - m
    if dragged >= 0 and mouse_down(.left): cards[dragged].pos = m + grab
    if dragged >= 0 and mouse_released(.left):
        if not drop_ok(cards[dragged]): cards[dragged].pos = cards[dragged].home   # back
        dragged = -1
```

**Fullscreen and the clipboard.** `set_fullscreen(true)`, `toggle_fullscreen()` and
`is_fullscreen()` (in a browser, the page asks for fullscreen; it leaves on Escape).
`clipboard()` reads the system clipboard's text and `set_clipboard(s)` replaces it. A web page
may read the clipboard only as something is pasted, so there `clipboard()` is the text last
pasted (ctrl+V, or a text field's Paste button on a phone) into the page; the X11 fallback without libX11 keeps the text within the program.

**Window size.** `window("Title", 1280, 720)` (called for you with those defaults) sets the
window's starting size and the program's 2D coordinate space: 2D drawing and `mouse_pos()` are in
those units however large the window becomes — resized, maximized, or a browser page, which the
game fills — scaled to fit and centered. A window of another shape shows more around that
area: `visible_rect()` is the part of the plane on screen (draw backgrounds over it),
`screen_size()` is the size given to `window()`, `pixel_size()` the real size. 3D rendering
uses the whole window.

**Screens of any size and shape.** 2D drawing is in units of the size given to `window()` (the
design size), whatever the window's real size; `screen_fit` says how that area fits a window
of another shape, and the render resolution says how many pixels draw it:

```gdscript
screen_fit(.expand)       # (default) scaled to fit, centered; a wider or taller window shows more
                          # around it (visible_rect() is what is shown)
screen_fit(.letterbox)    # just the design area, with bars (letterbox_color(c))
screen_fit(.crop)         # the design area fills the window; what sticks out is cut off
screen_fit(.stretch)      # stretched to the window (shapes distort)
screen_fit(.native)       # no scaling: one unit per window pixel

render_resolution(640, 360)   # draw at a fixed resolution, scaled up (sharp pixels, whole steps;
                              # smooth = true, whole = false for other looks)
pixel_art()                   # the same at the design size: window("game", 320, 180) + pixel_art()
                              # is a 320 x 180 pixel game (its window opens 4 times larger)
render_scale(0.5)             # draw at half the window's resolution (fewer pixels: faster)
full_resolution()             # in draw: the rest of the frame at the window's own resolution
```

Text drawn at 320 x 180 is a few pixels tall, and blurs into blocks. For a HUD that stays sharp,
call `full_resolution()` in draw after the world: what follows is drawn at the window's
resolution, in the same units, over the pixel art (`text("Score {score}", vec2(4, 4), 8)` is 8
units tall, 32 pixels in a window four times larger). A pixel font is a TTF like any other,
`set_font(load_font(embed("pixel.ttf")))`; give it sizes the window's scale turns into whole
pixels.

`mouse_pos()` is in the same 2D units, and 3D follows the same picture (a letterboxed game's 3D
view has the design area's shape). `SLOPPY_FIT=letterbox` and `SLOPPY_RESOLUTION=320x180` try a mode
on any game without changing it.

Window sizes are in the desktop's logical units, and frames are rendered at the display's real
resolution: on a screen scaled by 1.67, a 1280x720 window has 2133x1200 pixels, so text and edges
stay sharp (in the browser too). The rendered frame goes to the compositor without being copied
through the CPU.

Native games open a Wayland window when `WAYLAND_DISPLAY` is set and an X11 window otherwise
(`SLOPPY_PLATFORM=x11|wayland` chooses). Windows have the desktop's own decorations: on GNOME they
are drawn by libdecor (with GTK, as other apps' title bars are), elsewhere by the compositor
(xdg-decoration) or the X11 window manager; without libdecor (or with `SLOPPY_LIBDECOR=0`) the
program draws a plain title bar itself. A window's title is the program's name unless
`window(title)` gives one. Everything a game loads at run time is optional: without
libwayland-client (or with `SLOPPY_WAYLAND=protocol`) it speaks the Wayland protocol itself, and
without libX11 the X11 protocol. They draw with Vulkan where the system has a Vulkan 1.3
driver (as current drivers for Intel, AMD and NVIDIA GPUs do), else with OpenGL ES;
`SLOPPY_VULKAN=0` chooses OpenGL (see [Graphics and the GPU](GRAPHICS.md) for how the renderers
compare). With Vulkan, the pipelines the driver makes for shaders are
kept between runs in `~/.cache/sloppy` (`%LOCALAPPDATA%\sloppy` on Windows), so later runs start
drawing sooner. Without either (or with `SLOPPY_SOFTWARE=1`) the same program draws with the built-in software
renderer, which runs your shader functions (see `make_shader`) on the CPU; `soft_rendering()`
tells the program which is in use, e.g. to draw fewer particles. Frames are rendered at half
resolution (`SLOPPY_SOFT_SCALE=1` for full resolution: lines one pixel wide can drop out at
half) and paced to 60 per second.

**Pictures without a game.** `render_image(w, h, ():` with drawing below it`)` gives an `Image`
of exactly w x h pixels, drawn with the same functions as `draw` (pixels from its top left
corner): a chart a script saves with `save_png(img, "chart.png")`, a texture made at the start.
Called before any window is open, it opens none (the software renderer draws it, at full
resolution), so it works in a script and on a machine without a display.

**Frame statistics.** `show_stats()` (or `SLOPPY_STATS=1`, or `?stats` at the end of a web page's
address) draws an overlay with the frame rate, a graph of recent frame times, the CPU time of
`update` + `draw`, the time spent handing frames to the screen, and how many frames took much
longer than usual (stutter). `SLOPPY_STATS=log` (`?stats=log`) prints the same numbers every two
seconds, and each long frame as it happens. In a web page, `env(name)` reads the page's URL
parameters, in any letters (`?join=` is `env("JOIN")`'s), so `?SLOPPY_STATS=1` and `?stats` are the same. Files in a web page (`read_file`,
`write_file`, `list_dir`) are the page's own, in memory (`sloppy.files` in JavaScript); a web build
run under node (`tools/runwasm.js page.html args...`) uses the real ones and gets the arguments.
Screenshots, pressing keys at given frames and the other environment variables for running a
game with no one at the keyboard are in [Testing a game](#testing-a-game) below.

```
sloppy file.jo [args]     compile and run (wasm target: opens the browser)
sloppy watch file.jo      run it, and reload it while its files change
sloppy --web file.jo      compile for the web and open it in the browser
sloppy build file.jo      write the executable / .html (-o game.zip: the page as index.html in a
                          zip, ready to upload to itch.io; on Windows the .exe in one)
sloppy test file.jo       run `test` blocks (sloppy test file.jo save: those with "save" in their names)
sloppy new dir [kind]     a project to start from: dir/dir.jo (kind: game, arcade, platformer, 3d, story, online, program)
sloppy check file.jo      type check only
sloppy add <git URL>      a package, in the build block (and sloppy.lock)
sloppy fmt file.jo        lay out the code one way (directories too; --check: only list what
                          would change; -: standard input to standard output)
sloppy update             install the latest release (when this is not it)
```

Options (`--release`, `--target windows`, `--time`, `--web`) go before or after the file:
`sloppy test --release f.jo` and `sloppy test f.jo --release` are the same. Running a program
is the exception: what follows its file is the program's own arguments, so `sloppy --release
game.jo level2`.

On Windows, `sloppy` is `sloppy.exe` and programs are Windows executables (`sloppy build game.jo`
writes `game.exe`, and `game.pdb` beside it, which only debuggers use); `sloppy build --target
windows` makes them on Linux too, and `--target linux` Linux ones on Windows. On Windows, `-o
game.zip` writes the program in a zip, to share (`--target wasm -o game.zip` the web page, as
elsewhere). A game has no console of its own: `sloppy game.jo` shows what it prints in the one it
was started from, and a built game that stops with an error when it was started some other way
(double-clicked) shows the error in a message box and writes it to `crash.txt` in its save folder
(`%APPDATA%\<name>`). `--target linux-arm64` makes programs for Linux on 64-bit ARM (a Raspberry
Pi, ARM laptops and servers), the default when the compiler itself runs there.

**Reloading while it runs.** `sloppy watch game.jo` runs the game and keeps watching the files it
is built from. Each time one is saved the game is rebuilt and the running game takes the new
code between two frames, without starting over: the window stays open and every global keeps
its value (the player where they are, the level as it is, what is loaded on the GPU), so a
change to how something moves or looks shows at once.

- Changed and new functions take effect at the next frame, also in function values and closures
  the game keeps (a lambda that captures other variables than before is a new one: closures made
  earlier keep running the old code).
- A global is set again from its declaration when that declaration changes (`speed = 300.0`
  after `speed = 200.0`), when a file it names changes (`player = load_texture(embed("player.png"))`
  after the image is saved), or when the functions of a GPU program it makes do
  (`sky = make_shader(shader(sky_vs, sky_fs))`). New globals are set when they appear.
  Top-level statements and `main` do not run again.
- When a struct the game holds changes (a field added, removed, reordered, or of another numeric
  type), the values are kept: each is converted to the new layout field by field (by name),
  through arrays, optionals, maps and nested structs; a new field starts at its default (a
  literal default; otherwise zero).
- A build with errors leaves the game running as it was, with the errors over it and in the
  terminal. A panic in `update` or `draw` pauses the game with the message on the screen; saving
  a fix goes on from there.
- `r` (and enter) in the terminal starts the program again from the beginning (`sloppy watch` says
  when an edit needs it: top-level statements that changed); `q` quits. A game that gains or
  loses `update` or `draw` is started again by itself.
- A program without `update`/`draw` is run again from the start each time its files change.

`sloppy watch` runs native builds (Linux or Windows; on Windows `r` and `q` need no enter), in debug
or release mode as the build block says.

### Testing a game

A game can be run with no one at the keyboard: to look at a frame, to check that a level can be
finished, or in a test of your own. Environment variables say what happens:

- `SLOPPY_SCREENSHOT=out.png` with `SLOPPY_FRAMES=n` saves frame n and exits (`SLOPPY_FRAMES=n`
  alone runs n frames and exits, in real time). With a screenshot the clock advances exactly
  1/60 s per frame, so the image is reproducible (the desktop's keys and mouse are ignored); it
  has the window's pixels, the size asked for (on a scaled Wayland display too: `SLOPPY_SCALE=2`
  renders at twice it). With `SLOPPY_SOFTWARE=1` no display is needed at all, and without it
  and no display (unset `WAYLAND_DISPLAY` and `DISPLAY`) the frames are drawn through Vulkan
  with no window; where there is a display, the window opens on it.
- `SLOPPY_INPUT="5:space+,9:space-"` presses and releases keys at given frames (commas or
  spaces between items). Keys are as `Key` names them: `a`, `n1`, `space`, `enter`, `escape`,
  `left`, `shift`...; `mouse_left`, `mouse_right` and `mouse_middle` are the mouse's buttons,
  `12:mouse=400x300` moves the mouse there and `3:wheel=1` turns the wheel a notch (in the
  screen's units), `7:text=hi` types, `5:touch1=400x300` puts finger 1 down there (or moves it)
  and `9:touch1-` lifts it (the first finger down is the mouse too, as on a phone),
  `5:pad_a+`/`9:pad_a-` press and let go a gamepad's button (pad 0; PadButton's names),
  `6:lstick=1x0` and `rstick=` set its sticks, `lt=1` and `rt=` its triggers. An item it
  cannot read is reported. A web build takes it in the page's address,
  `page.html?SLOPPY_INPUT=5:space%2B`, with `+` written `%2B`.
- `SLOPPY_SEED=n` makes `random()` the same each run; `SLOPPY_WINDOW=800x600` opens the window
  at that size; `SLOPPY_NO_AUDIO=1` plays no sound (for tests and machines without a sound card).
- `SLOPPY_THREADS=n` caps the threads used by the parallel functions; `SLOPPY_SCALE=1` renders
  at the logical size and lets the compositor scale it up; `SLOPPY_FRAME_STATS=1` (with
  `SLOPPY_SCREENSHOT`) reports frame times and how frames reach the screen; `SLOPPY_MSAA=1`
  draws without antialiasing (through Vulkan the screen is drawn with 4 samples a pixel, smooth
  edges as in a web page's canvas).

```sh
SLOPPY_SCREENSHOT=start.png SLOPPY_FRAMES=120 SLOPPY_INPUT="10:enter+ 12:enter- 30:right+" sloppy game.jo
```

A web build in a headless browser: Chromium's `--screenshot` with `--virtual-time-budget` runs
only a few of the game's frames before it takes the picture. Drive the browser over its
DevTools protocol instead (`--remote-debugging-port`, as Playwright and Puppeteer do): load the
page, wait in real time, send keys with `Input.dispatchKeyEvent` and take the picture with
`Page.captureScreenshot`.

## 13. Calling C

Native programs can call functions from system shared libraries; the library is loaded the
first time one of its functions is called, so a missing library only matters to code that
actually uses it (check with `lib_available("libfoo.so.1")`).

```gdscript
@lib("libm.so.6")
extern cbrt = (x: f64) -> f64

@lib("libGLESv2.so.2")
@symbol("glClear")                 # the C name, when the Sloppy name differs
extern gl_clear_native = (mask: u32)

@lib("libc.so.6")
@variadic(3)                       # C's `...` after the first three parameters
extern snprintf = (buf: *u8, n: int, fmt: *u8, x: f64) -> i32
```

Arguments and results are numbers, pointers, or structs and vectors passed by value (below);
`cfn(...) -> T` is the type of a C function pointer, and `@cabi` makes a Sloppy function
callable from C. Windows programs name DLLs
(`@lib("user32.dll")`) and are called with the Windows x64 convention; the same code can serve
both systems under `when TARGET == "windows":`. A variadic C function (`printf(fmt, ...)`) is
declared with the arguments a call gives it and `@variadic(n)`, n being its fixed parameters:
macOS passes the others differently. macOS programs find C functions in the system's libraries
(libSystem holds what Linux's libc and libm do) when they start.

A `str` argument goes to C as its bytes, which end in a zero byte (C's `char *`); an array is
passed as `data(xs)`, a pointer to its first element (which unshares an array shared with a
copy first, so C's writes go to this one only). `@lib(NAME)` takes a constant naming the
library, too. What C's stdio holds (`printf`) is written out when the program ends.

**Pointers.** `*T` is a pointer to T: `&x`, `&xs[i]` and `&s.field` take an address, `p[i]`
reads and writes the i-th T from p, `p + n` is n elements on (not n bytes), `null` is none,
`p as *u8` and `int(p)` reinterpret it, and `**u8` is a pointer to a pointer (C's
out-parameters). A struct is laid out as C lays it out (`size_of(T)`, fields in order and
aligned), so a C struct is declared as a struct of the same fields; `data(bytes) as *Header`
reads one in place. A C callback is a top-level function marked `@cabi` (a function value made
in the program, a lambda or closure, cannot be called from C), and `cfn(A, B) -> R` is its type.
`str_from_c(p)` copies C's text, `bytes_from(p, n)` C's bytes.

```gdscript
@lib("libc.so.6")
extern qsort = (base: *u8, n: int, size: int, cmp: cfn(*i32, *i32) -> i32)
@lib("libc.so.6")
extern strtol = (s: str, end: **u8, base: i32) -> int

@cabi
by_value = (a: *i32, b: *i32) -> i32: a[0] - b[0]

xs: i32[] = [30, 10, 20]
qsort(data(xs) as *u8, xs.len(), size_of(i32), by_value)
print(xs)                                    # [10, 20, 30]

end: *u8 = null
n = strtol("42 apples", &end, 10)            # an out-parameter: &end
print(n, str_from_c(end))                    # 42  apples

p = data(xs)                                 # *i32: the first element
p[1] = 99                                    # writes xs[1]
q = p + 2                                    # two elements on, not two bytes
print(xs, q[0], size_of(i32))
```

**C's types**, and what to write for them:

| C | Sloppy |
|---|---|
| `int`, `unsigned`, `short`, `char` / `unsigned char` | `i32`, `u32`, `i16`, `i8` / `u8` |
| `long`, `unsigned long` | `int`, `u64` on Linux and macOS; `i32`, `u32` on Windows (its `long` is 32 bits) |
| `size_t`, `ssize_t`, `int64_t`, `intptr_t` | `u64` or `int`, `int`, `int`, `int` |
| `bool` (C99) | `u8` (1 is true) |
| `float`, `double` | `f32`, `f64` |
| `const char *` in | `str` (C may read it, never write it), or `*u8` |
| `char *` out, or kept by C | `*u8`, copied with `str_from_c(p)` (`""` for null: check `p == null` first when that matters) |
| `void *`, `T *`, `T **` | `*u8`, `*T`, `**T` (`p.field` reads a struct through its pointer) |
| a struct | the same fields, in order; by value (`Vector2 v`) or by pointer (`&s`, `data(xs)`) |
| `float v[4]` in a struct | `v: f32[4]` |
| raylib's `Vector2`, `Vector3`, `Vector4`, `Matrix` | `vec2`, `vec3`, `vec4`, `mat4` (or structs of the same floats) |
| `__attribute__((packed))` | `@packed` above the struct: no padding between its fields (it holds plain data only) |

What crosses, and for how long:
- **`str` is read-only to C.** It may share its bytes with other strings. Give C a buffer to
  write into as `u8[]`: `buf = fill(u8(0), 256)`, then `data(buf)`.
- **Text passed as a `str` lives for the call.** A library that keeps the pointer for later
  (sqlite's `SQLITE_STATIC`) needs bytes that last: a `u8[]` kept in a variable, or the library's
  copying form (`SQLITE_TRANSIENT`).
- **`data(xs)` stays valid while `xs` neither grows nor goes away.** A `push` or `resize` may
  move it.
- **Structs by value** go as C's convention for each system has them (small ones in
  registers, larger ones copied), so `extern draw_circle_v = (center: vec2, radius: f32, color:
  Color)` (Color a struct of four `u8`s, as raylib's) and `extern get_mouse_position = () ->
  vec2` call raylib as C does. A struct passed
  by value holds numbers, bools, pointers, vectors, fixed-size arrays and structs of them, and
  is a copy: C's changes to it are not seen. A web build's externs are JavaScript functions,
  which take no structs.
- **What can't cross:** an `extern` can't give back a `str` (it gives `*u8`, read with
  `str_from_c`), `@cabi` functions take and give scalars and pointers only (a struct from C as
  `p: *Vec2`), a struct can't be one of a variadic function's `...` arguments, and a struct C
  reads through a pointer has no `str`, array or map fields (`*u8` and a pointer with a length
  instead). The compiler says so where each is declared.
- **Variadic arguments are promoted as C promotes them:** an `f32` goes as a double (`%f`), and
  smaller integers and bools as an int (`%d`).
- **`print` is buffered.** Call `flush_output()` before C writes to the same output
  (`puts`, `write`), or the lines come out of order.
- **Names that clash.** An `extern` with the name of a library function (`abs`, `write`, `exit`)
  adds an overload of it rather than replacing it. Give it another name and the C one in
  `@symbol("abs")`.

`@cabi` functions may run on threads C makes (pthreads, a library's callbacks): such threads
take turns at memory of their own. What they share with the rest of the program is theirs to
guard (reference counts change without atomics there); for work on several threads, use
`parallel_map` and the rest of [Parallelism](#11-parallelism).

## 14. Performance

Debug builds (the default) compile fastest; `--release` builds inline, keep values in
registers, remove bounds checks a loop cannot fail, and vectorize simple loops over arrays (on
x86-64, with AVX2 when the processor has it). Most of what makes a program slow is the same in
both:

**Copies.** Arrays, strings and structs are values that share their storage until one of them
changes. Assigning or passing one costs nothing; the first change to a shared one copies it
whole:
- `ys = xs`, then `ys[0] = 1` copies all of xs (once: ys is its own after that);
- `e = es[i]; e.hp -= 1; es[i] = e` copies e's arrays each time: change it in place instead,
  `es[i].hp -= 1` or `loop mut e in es`;
- a slice (`xs[a..b]`) is a new array;
- `s = s + x` and `s += x` both add to the end in place (the compiler writes the first as the
  second); `t = s + x` makes a new one, as it must.

`SLOPPY_COPIES=1 sloppy game.jo` tells each copy of an array of 64 KB or more that was made
because it was shared when it changed, with the line that changed it (`SLOPPY_COPIES=4096`:
from 4 KB): where a frame spends time copying, or a frame's spike comes from.

**Allocation.** Making arrays and strings each frame is cheap, but not free: an array kept from
frame to frame and emptied with `clear()` keeps its memory. A closure made inside a loop is
allocated each time round; make it once outside.

**Loops the compiler can speed up.** `loop mut p in ps:` and `loop i in 0..n: a[i] ...`
lose their bounds checks and vectorize in release builds, as do integer sums over a loop
(float sums keep their order, so that every machine gets the same result). An index the compiler cannot follow
(`c[i * n + j]` in a matrix) keeps its check on each access: a row array per row (`c[i][j]`),
`soa` arrays (section 8), or a pointer from `data(xs)` (section 13) let it go. Calls through
function values (`reduce`, `sort_by`, a lambda) are not inlined: in a hot loop, write the loop.
`soa T[]` keeps each field together, which is what loops over one or two fields want.

**Numbers.** `int` is 64 bits and wraps around. Arithmetic on narrow types stays in them: two
`u8`s add as a `u8` (200 + 200 is 144), so widen first, `int(a) + b` (the compiler warns when the
narrow result is widened right after). Vectors (`vec2`..`vec4`, `mat4`) are plain floats in a
row: their math is scalar, the same as a struct of floats in C.

**Seeing where the time goes.** In a game, `show_stats()` (or `SLOPPY_STATS=1`) draws frame
times, long frames and the time of each `zone("physics") ... zone_end()`, on the CPU and the GPU.
For any program, `sloppy build -g` keeps names for gdb and `perf` (Linux), lldb (macOS) and
Windows' debuggers; `sloppy build --ir` writes the code the compiler made before machine code.
