# The Sloppy Programming Language

Sloppy is a small, statically typed, compiled language that feels like a scripting
language. `sloppy game.jo` compiles the whole program (in milliseconds) and runs it.

The [API stability declaration](STABLE.md) identifies the supported contracts, remaining
pre-stability decisions and experimental areas. Stable contracts require a major version
for a breaking change.

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
  (so text with braces, such as JSON, needs `{{` and `}}` for literal braces, or a raw string). Escapes: `\n \t \r \0 \\ \" \' \xNN`, and a character by its code point, `\u00e9` (4 hex
  digits) or `\U0001F600` (8; a JSON surrogate pair, `\ud83d\ude00`, is the one character). Format specs follow Python:
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
* **Characters.** `c'a'` is a character's code, a number (97): `c - c'0'`, `c'a' + i`,
  `[c'a'..c'z']` in a match, `c'\n'`, `c'é'` (233, the character's Unicode number; text holds
  it as two bytes). Quoted text, in single or double quotes alike, stands for a character's code
  only where a byte (`u8`) is expected: `s[i] == "a"`, `c in "+-"`, `bytes.push("\n")`, a match
  on `s[i]`. Elsewhere text is not a number: `add(1, "2")` with `add` taking `int`s is an error
  (`to_int("2")` reads the number, `c'2'` is the character's code), and so is `'a' + 1`.
* **Units.** A unit right after a number (no space) converts to the SI base unit at compile
  time: `120ms` is `0.12`, `90deg` is `PI / 2`, `3km` is `3000.0`, `1.2(m/s)`,
  `9.81(m/s^2)`, `[1.2 0](m/s)`. Time `s ms us ns min h`, length `m cm mm km`, mass `kg g`,
  angle `rad deg turn`, force `N`, and long names (`10seconds`, `3meters`). Values are plain
  `f64`s (no dimension checking).

Keywords: `struct enum type if else loop in break continue return match import use as const true
false none null and or xor not is let mut when defer extern test build pass` (and `from` and
`error` before `import` and `struct`/`enum`) (`loop let xor is` and
`type` may still be used as field and variant names). `build` is a keyword only as `build:`
alone on its line (spaces, tabs and a trailing comment are allowed). Elsewhere it is an ordinary
name: `build = 1`, `hall.build`, `(build: int)` and `build: f64`.

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

`x = value` declares `x` when no variable `x` is visible, and assigns otherwise. At the top
level of a file, `x = 1` declares a global of that file, or assigns one the file `use`s (an
`import`ed file's names are apart: `physics.x`).

In a function, `x = value` makes `x` a variable of the function's own unless the function says
`global x`, as in Python, so a helper's `count = 0` or `best = 0` stays its own whatever globals
the file has, now or later:

```gdscript
score = 0
state = Screen.menu

start = ():
    global score, state          # these change the globals
    score = 0
    state = .playing

hit = (): score += 1             # += (and -=, ...) changes the global: it cannot make a variable
reset_enemy = (e: mut Enemy): e.hp = 3    # so does writing a field or an element
```

`score += 1`, `player.x = 5` and `grid[i] = 0` change the global when the function has no
variable of that name: they cannot make one. A function that reads the global `x` and also gives
`x` a value with `=` (and no `global x`) is an error, and so is a variable of the function's own
that is named as a global and never read: both say to write `global x`. A lambda in top-level
code changes the globals around it as any closure changes the variables around it; a lambda in a
function, as that function does (its `global` lines count for it). `let x = ...` always makes a
new variable.

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
| `T[]` | growable array (value semantics); `push pop insert remove_at remove extend len` ... (also `Array[T]`) |
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
release builds alike: `i8(127) + i8(1)` is -128). A shift on a type narrower than 64 bits keeps
what fits the type (`u8(0x80) << 1` is 0, and `hi << 8` with hi a u8 is 0: `u16(hi) << 8`); a
shift by 64 or more counts modulo 64 (`1 << n` with n at 64 is 1, as x86-64 and arm64 shift). Numbers written out are worked out
while compiling, and one that does not fit is an error rather than a wrapped value:
`9223372036854775807 + 1`, `x: u8 = 200 + 100`, `1 << 70` (numbers written in hex are bits, and
may wrap). Where overflow must not pass unseen, the library
has `checked_add`, `checked_sub` and `checked_mul` (an optional, `none` on overflow:
`checked_mul(w, h) ?? panic("too big")`), `saturating_add`, `_sub` and `_mul` (the type's
largest or smallest value) and `wrapping_add`, `_sub` and `_mul` (as the operators, said on
purpose), for every integer type. A conversion that must not lose anything is
`checked_cast[u8](x)` (`none` unless x is a value a `u8` has), and `saturating_cast[u8](x)` gives
0 or 255 past the ends. `gcd`, `lcm`, `isqrt`, `mul_mod`, `pow_mod` and `inv_mod` are exact for
every int (`mul_mod(a, b, m)` for m up to 2^63, with the 128-bit product). Past 64 bits,
`BigInt` keeps every digit: `bigint(2) ^ 1000`, `bigint("1234567890123456789012345")`, with the
same operators, ints mixed in (`x * 2`), and `int(x)` back ([API.md](API.md#big-integers));
`Big` (`use big`) is a float with a large exponent instead, about 15 digits. `x ^ y` is
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
- `not` is for bools; `~x` flips a whole number's bits (`~0` is -1), and conditions take bools.
- `+` on arrays of one dimension joins them (`[1, 2] + [3]`); on a matrix it adds element by
  element. `.+` always adds element by element.
- `x = 1` in a function makes a variable of its own, as in Python; `global x` in it changes the
  global (`x += 1`, `x.f = 1` and `xs[i] = 1` change the global without it).
- `a..b` leaves `b` out, as Python's `range(a, b)` does; `[a..b]` keeps it.
- `round(5.7)` is `6.0`, an f64 (as `floor` and `ceil`); `int(round(x))` is the whole number.
- Angles are in radians: `rotate(v, PI / 2)`, or `rotate(v, 90deg)` (a literal over 2π warns).
  Deliberate exception: every `camera3d` overload takes `fov_degrees = 60.0` in degrees,
  following common game-camera conventions. Write `camera3d(cam, fov_degrees = 60)`,
  not `60deg` (that literal already evaluates to radians). `perspective(fov_y, ...)` takes radians.
- `'a'` and `"a"` are both text, as in Python; `c'a'` is the character's code (97). `s[i]` is
  a byte, which compares with `"a"` (or `c'a'`).
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
bytes, which print as numbers: `str(c)` of an `a` is `"97"`). `index_of(s, sub)`, `last_index_of(s, sub)` and
`index_of(s, byte)` give an optional byte index: `none` when absent. The `start` offset of
`index_of` and regex `find` must be in `0..len(s)` inclusive; otherwise they give `none`.
Use `if let i = s.index_of("@"):` or `sub in s` for membership; `s.find(regex(...).unwrap())` gives a `Match?`, none when there is
no match.

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
happens when you mutate something that is shared. Ordinary values have no reference identity
and need no garbage collector; raw pointers are an explicit escape from these rules.

**Shared/resource handles are an exception to independent copied state.** Assignment copies
the handle, not the resource it identifies. Copies of `Channel`, `Task`, `TaskGroup`, `Atomic`
and `net.CookieJar` share their channel, completion/group, atomic cell or cookie storage.
`send`, `close`, `cancel`, Atomic `set`/`add`, and `clear_cookies` change that shared state
without a `mut` receiver. Absence of `mut` therefore does not promise an operation has no
observable effects. Construct a new channel/atomic/jar for independent state. Arrays, maps,
sets and physics `World` remain copied values.

Native resource handles have ownership rules too: copying `File`, a network connection id,
`Texture`, `Mesh`, `Shader` or other GPU handle does not duplicate the open file/socket/GPU
resource. Close/free it once after its users are finished, and do not use aliases afterward;
a copied handle does not grant a separate lifetime. Follow each API's close/free rules.
Synchronization handles retain their shared cells; they are not interchangeable with manually
freed graphics/file resources. Shared handles and raw pointers can form shared ownership
patterns; the ordinary-value rule is not a blanket leak/cycle guarantee for those resources.

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
inserted elements before it (`xs.remove_at(0)`, `xs.clear()`), or changed `xs[i]` itself, the copy
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
what a field or variable without a value starts as), from `fill(x, N)`, or from a comprehension
that makes N (`bits: u8[256] = [loop i in 0..256: u8(popcount(i))]`, a table worked out; another
count panics):

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

`m.has(k)`, `m.remove(k)`, `m.keys()`, `m.values()` and `m.len()` do what they say; `m.items()` is the (key, value) pairs, to sort them (`m.items().sorted((p): -p.1)`).

A set (`Set[T]`, values without repeats) is written with braces and no colons, `{"a", "e",
"i"}`, or made by a loop, `{loop w in words: w.lower()}`; `{}` is an empty one where a `Set` is
expected (`seen: Set[int] = {}`), and an empty map otherwise. `x in s`, `s.add(x)` and
`s.remove(x)`. `set(xs)` makes one from an array; membership is `x in s` or `s.contains(x)`.
`s.union(t)`, `s.intersection(t)` and `s.difference(t)` return new sets; `s.is_subset(t)`
asks whether every value in `s` is in `t`. They keep insertion order, and leave their inputs
unchanged. `s.items()` gives an array; `loop x in s:` visits each value once. Equality compares
membership regardless of order. More in [API.md](API.md#sets-and-deques).

For large text files, `open_file(path)` gives an optional buffered `File`; it reads 64 KB at a
time, keeping only the unread bytes and the current line. Close it even when leaving early:

```gdscript
if let f = open_file("big.log"):
    defer f.close()
    loop:
        line = f.read_line()
        if line is FileError:
            eprint(line.message)
            break
        if line == none: break
        print(line!)
else: eprint(file_error())
```

For stdin, `loop let line = read_line(): print(line)` uses the same buffered approach.
Both strip `\n` and Windows `\r\n`, return an empty string for an empty line, keep a final
line without a newline, and give `none` at EOF. `lines(text)` splits text already in memory;
it takes text, rather than a filename. Native file streams work on Linux, macOS and Windows;
a page's `File` reads files already supplied to the page.

Dates use `Date` (whole seconds, including an offset in seconds east of UTC). `date(t, utc = true)`
converts Unix seconds to UTC, `date(t)` to the computer's local zone; `unix_time(d)` converts
back. `parse_date("2024-02-29T12:30:00+02:00")` reads ISO 8601 directly. A format is the
second argument for strptime-style parsing, and `date_text(d, format)` formats it:

```gdscript
d = parse_date("29/02/2024 12:30", "%d/%m/%Y %H:%M", utc = true)!
print(date_text(d, "%A, %d %B %Y %T %z"))
later = date_add(d, 5400.0)
print(duration_text(date_diff(later, d)))       # 1h 30m
```

`Date` stores whole seconds and an explicit offset. `date_text(d)` is display text and
omits the zone; use `date_text(d, "%Y-%m-%dT%H:%M:%S%z")` for a zoned form that
`parse_date` can read back (fractional input is not retained). `utc_offset(t)` takes Unix
seconds as f64 and floors fractions, matching `date(t)`. HTTP dates use
`http.parse_http_date(text)`; they are always GMT.


Parsing gives `none` for invalid text or an unsupported directive. Both forms use the local
zone when the text has no offset, or UTC with `utc = true`. Supported directives: `%Y` (four
digit year), `%y` (00–68 mean 2000–2068, 69–99 mean 1969–1999), `%m`, `%d`, `%e` (space-padded
day), `%H`, `%I` with `%p` (12-hour clock, AM/PM), `%M`, `%S`, `%b`/`%B` (English month),
`%a`/`%A` (English weekday), `%j` (day of year), `%u`/`%w` (weekday, Monday=1/Sunday=0), `%z`
(`Z`, `+0530`, `+05:30`), `%Z` (`UTC`/`GMT` when parsing; UTC or numeric offset when formatting),
`%%`, and `%F`/`%T`/`%R` (`%Y-%m-%d`, `%H:%M:%S`, `%H:%M`). Numeric fields are fixed width;
unspecified fields start at 1900-01-01 00:00:00. Names do not depend on the machine's locale.
ISO fractions are accepted and discarded. Arbitrary named zones are not parsed.

Durations are elapsed seconds (`f64`): `date_add(d, seconds)` keeps the date's fixed offset;
`date_add(d, seconds, local = true)` converts the resulting instant to the local zone, including
its daylight saving rules. `date_diff(a, b)` is seconds from `b` to `a`, respecting offsets.
`duration_text(seconds)` writes days, hours, minutes and seconds, truncating fractional seconds
(`-65.0` is `"-1m 5s"`). Dates have whole-second precision, so `date_add` floors the instant.

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
  (`cfg.load[Settings](path)`) and in uniform call syntax (`db.query[Booking](sql)`).
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

A function's type is written as it is called: `(f64) -> f64`, `(str, int) -> bool`, `() -> void`,
with `mut` before a parameter it changes: `ops: ((mut Cpu) -> void)[]` is a table of functions
that each change a Cpu. A function value has no defaults for its parameters: it is given all of
them.

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
    [c'a'..c'z']: print("a letter's code")
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
is a value to compare with, not a new variable (`limit:` matches the value of `limit`); `as`
after an arm's patterns names the value matched, narrowed as they narrow it:

```gdscript
match x:
    1..10 as d: print("digit", d)
    _ as n if n > 100: print("big", n)
match shape:                             # Circle | Rect
    Circle as c: c.r * c.r * PI
    Rect as r: r.w * r.h
```

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

A field cannot be named with a keyword; `when_` (a `_` at its end) can, and JSON calls it
`when`: `to_json` writes `{"when": 1.5}` for `when_ = 1.5`, and `from_json` reads it back, so
JSON whose names are keywords (`when`, `in`, `if`, `match`) reads into a struct. Names that are
not names at all (`"content-type"`, `"first name"`) go in a map field (`{str: str}`) or through
`parse_json`.

**JSON of any shape.** `j = parse_json(text)` gives a `Json` or `JsonError`; after checking the
error, read with `j.get("name").as_str()`, `j.get(0).as_int()` and `j.as_list()`. Those reads
give `none` for absent fields, out-of-range elements or wrong kinds. Change a value with
`j.put("name", "ann")` (add or replace an object field), `j.put(0, 3)` (replace a list element),
`j.push(value)` (append to a list), and `j.remove("name")` (true if removed).

For nested changes, a path is a JSON list of string keys and integer indices:

```gdscript
j: Json = {"a": {"b": 1}, "list": [{"tags": []}]}
j.set_path(["a", "b"], 3)
j.push_path(["list", 0, "tags"], "new")
j.remove_path(["a", "b"])
print(to_json(j))
```

These methods mutate `j`; copies of it keep their old values. Each intermediate container must
exist. The last object key may be new; an array index must already exist. Wrong kinds, missing
intermediate fields and bad indices stop with an explanatory message. `set_path([], value)`
replaces the root, and `push_path([], value)` appends to the root list. `remove_path` must end in
an object key. Json indexing assignment (`j["a"]["b"] = 3`) is not supported; use `set_path`.

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
a `none` kept alike (`m.contains(k)` tells them apart). Array `get` has the same limit;
check bounds to distinguish a stored none. Channels reject optional element types: send a struct
with an optional field instead. A `T[]` passes where a `T?[]` is expected as
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

load_score = (path: str) -> int? | FileError:
    text = read_file(path)?                      # propagate FileError
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
  declared `error`) is an error, as is one where every member would be passed on. An error or
  nothing, `ParseError?` (none: it went well, as `db.exec(...)` gives), is the one exception:
  `check()?` passes the error on and goes on when there is none, giving no value.
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
- To pass on the error and keep the none (`int? | AsmError`, none meaning "not known yet"), test
  for it: `if r is AsmError: return r`, and r is an `int?` after it.
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

An arm binds a variant's fields by position, as plain names (or `_`). Variants share an arm when
they name the same fields, of the same types (`.add(a, b), .mul(a, b): ...`), or name none
(`.num(_), .zero:`).
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
`m[1..3, 3..]` a block (`a..b` leaves `b` out, as everywhere, and `[a..b]` keeps it; `a..` runs to the end of the axis, and indexes
left out at the end mean whole axes). A part is an array of its own; assigning to one writes into
the array: `m[.., 0] = xs`, `m[0, ..] = 0.0`. A 1-D one (a row, a column) is itself a `T[,]`, and
goes where a `T[]` is expected, as in `argmax(m[0, ..])`, a function of your own or a
comprehension of that type, `rows: f64[][] = [loop i in 0..n: m[i, ..]]` (one with more
dimensions there stops the program: `m.data` has all the elements); `row(m, i)` gives the `f64[]`
at once. An array of indexes, or a mask, among the indexes picks those parts along its axis, in
that order: `x[idx, ..]` (or `x[idx]`) the rows idx, a mini-batch, `x[.., [2, 0]]` two columns,
`x[x[.., 0] .> 0.5, ..]` the rows whose first element is over 0.5 (`take(m, idx, axis)` for any
axis). `sum(m, axis)`, `mean`, `min`, `max`, `argmax` and `argmin` reduce along one axis
(`sum(m, 0)` adds up the rows: one sum per column); `keepdims = true` keeps the axis with
length 1, so the result broadcasts against `m`: `m .- max(m, 1, keepdims = true)`. `softmax(m, 1)`
and `logsumexp(m, 1)` take the largest along the axis out first, so nothing overflows.
`concat(a, b, axis)` joins arrays along an axis, `vstack` and `hstack` lists of them.

```gdscript
img = zeros(480, 640, 3)
img[.., .., 0] = 1.0             # the red channel
top = img[0..239, ..]
brightness = sum(img, 2)            # (480x640)
```

Printed, `to_text` and `save_value` write an array as it is written in code, `[1.0 2.0; 3.0 4.0]`
(a single row ends with `;`, `[1.0 2.0;]`, and one with no elements says its shape), and
`from_text`, `load_value` read it back the same; `to_json` writes lists of lists, which
`from_json[f64[,]](text)` reads. `csv_array(text)` reads the numbers of a CSV file into a 2-D
array (a header row is left out), and `to_bytes(m)` / `ndarray_from_bytes[f64](b)` keep one as
its bytes.

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
| `a[0, :]`, `a[:, 1]`, `a[1:3]` | `a[0, ..]`, `a[.., 1]`, `a[1..3]` (`a..b` leaves `b` out, as Python's `a:b`) |
| `a[a > 0.5]`, `a[a < 0] = 0`, `a[np.argsort(a)]` | `a[a .> 0.5]`, `a[a .< 0.0] = 0.0`, `a[argsort(a)]` |
| `np.where(a > 2, a, 0)` | `[loop x in a: (if x > 2.0: x else: 0.0)]` |
| `a.sum(axis=0)`, `a.mean()`, `a.std()`, `a.var()` | `sum(a, 0)`, `mean(a)`, `std_dev(a)`, `variance(a)` |
| `a.max(axis=1, keepdims=True)`, `a.argmax(axis=1)` | `max(a, 1, keepdims = true)`, `argmax(a, 1)` |
| `softmax(a, axis=1)`, `logsumexp(a, axis=1)` (scipy) | `softmax(a, 1)`, `logsumexp(a, 1)` |
| `a[idx]`, `a[idx, :]`, `a[:, idx]`, `np.take(a, idx, axis)` | `a[idx]`, `a[idx, ..]`, `a[.., idx]`, `take(a, idx, axis)` |
| `mask.astype(float)` | `f64.(mask)` |
| `np.percentile(a, 90)`, `np.median(a)`, `a.argmax()`, `np.cumsum(a)` | `percentile(a, 90.0)`, `median(a)`, `argmax(a)`, `cumsum(a)` |
| `np.concatenate([a, b])`, `np.vstack([a, b])`, `np.dot(a, b)` | `a + b`, `[a; b]`, `dot(a, b)` |
| `np.concatenate([a, b], axis=1)`, `np.hstack([a, b])` | `concat(a, b, 1)`, `hstack([a, b])` |
| `np.loadtxt(path, delimiter=",")`, `a.tolist()` (JSON) | `csv_array(read_file(path).unwrap())`, `to_json(a)` |
| `np.linalg.solve(m, v)`, `np.linalg.inv(m)`, `np.linalg.det(m)` | `solve(m, v)`, `inverse(m)`, `det(m)` |

Three differences catch NumPy hands: `+` on 1-D arrays joins them (`.+` adds); a whole
dotted expression is one loop, so `a .* 2.0 .+ b` makes no array in between; and in brackets a
`-` joins what is on its two sides, so `[1.0 -2.0; 3.0 4.0]` has a first row of one element
(`1.0 - 2.0`): write `[1.0, -2.0; 3.0, 4.0]` or `[1.0 (-2.0); 3.0 4.0]`.

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
`_` are private to their file: `use` leaves them out, and `physics._helper`, `from 'physics.jo'
import _helper` and a struct's field `b._cache`, written in another file, are errors that say
so. A module's own functions with an imported function's name are overloads of it; any other
clash is an error (rename with `as`), as is a name two `use`d modules both have, when it is not
a function (a variable, a constant, a type): `import` one of them instead. Through a module,
its own imports are reached too: `import 'world.jo'` and then `world.grid.Grid[int]` and
`world.grid.make(...)`. Two modules' types of the same name are two types, and messages name
them by their modules, `expects grid.Cell, found board.Cell`.
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
    tween = package("https://github.com/bob/tween", "v1.2.0")   # a tag, a branch or a commit
    shared = package("../shared")                               # a directory
    local = package("file:///home/me/repos/tween")              # a repository on this machine

import physics                      # the package's main file
import 'physics/world.jo' as world  # any other file of it
```

A package's main file is named after the package itself: its directory's name, or its
repository's without `.git` and a `sloppy-` in front (`sloppy-physics` has `physics.jo`), or
else its only `.jo` file at its root. The name the build block gives it does not change that:
`ph = package("https://github.com/ann/sloppy-physics")` then `import ph` loads `physics.jo`.
A commit is its 40 characters or the first 7 or more of them. A name in the build block that
is also a directory or file beside the program (`physics/`, `physics.jo`) is an error that names
both: rename one.

*Each package's names are its own.* A build block's names are its package's: the program's
for the program's files, and a package's own build block (in the files at its root) for its
files. When the program calls something `util` and a package it uses calls something else
`util`, each `import util` gets its own; and the program's package names never hide a
standard-library module from a package (`big = package("../big")` in the program, and a
package's `import big` is still the library's).

*Versions side by side.* Two packages may use different versions of a third (one wants
`mathx` v1.0.0, another v2.0.0): each gets the version it names, as separate modules, so a
value of one version's type is not the other's (`expects mathx.Vec (v1.0.0), found mathx.Vec
(v2.0.0)`). The same repository at the same commit, wherever it is named, is fetched and
compiled once and shared.

*The lock file.* The first build pins each git package to a commit in `sloppy.lock` beside the
program; keep that file with the program, and every build uses the same code, whoever builds
it. Each line is a package as one build block names it (`physics`, or `physics/mathx` for the
`mathx` that `physics` names), its URL, the tag, branch or commit asked for (`-`: the default
branch), and its commit. Only the program's `sloppy.lock` counts: a package's own is not read.
Deleting a line takes that package's newest commit again at the next build.

```
sloppy add <URL> [version] [as name]    a package in the build block, fetched and pinned: URL@v1.2.0
                                        works too; with no version, the newest tag that is one
                                        (v1.2.0), else the default branch
sloppy update [name]                    the packages' branches (and default branches) pinned to
                                        their newest commits, each said old -> new; tags and
                                        commits stay, and newer version tags are listed
sloppy upgrade                          a newer Sloppy itself
```

*The cache.* Git fetches each commit once, into `~/.cache/sloppy/packages` (macOS:
`~/Library/Caches/sloppy/packages`; Windows: `%LOCALAPPDATA%\sloppy\packages`; the environment
variable `SLOPPY_PACKAGES` puts it elsewhere), so later builds need no network. Deleting that
directory clears it; the next build fetches what it needs again. Errors in a package's files
say which package and version they are in (`in package inikit (v1.1.0, 5d84792):`), above the
path in the cache. There is no registry: a package is any repository with Sloppy files, and
git reaches it as it would for `git clone` (a private one with the credentials git has).

*Publishing a package.* A package is a directory or git repository of `.jo` files:

- its main file at the root, named after the repository (`sloppy-physics` or `physics`:
  `physics.jo`), and its other files beside it or in directories under it, which the main
  file imports as any program's files do (`import 'world.jo'`), and which users can import as
  `'physics/world.jo'`;
- the packages it needs, in the build block of a file at its root, as a program names them
  (directory packages inside its own repository); a build block's other options (`name`,
  `target`, `opt`, `output`, `icon`, `js`) are the program's to set, and a package's are
  ignored;
- releases tagged `vX.Y.Z` (`git tag v1.2.0`), which `sloppy add` picks the newest of, and a
  new major number for changes that break code using it: both versions can be used at once;
- names starting with `_` for what is its own: they stay in their file;
- a `#` comment on the lines just above a definition, which editors show for it;
- `test` blocks, which `sloppy test` runs (`sloppy test .` runs those of every file in a
  directory).

## 10. Compile-time features

```gdscript
build:                          # build options live in the source
    target = wasm               # native (default: this machine) | linux | linux-arm64 | windows | macos | wasm
    opt = release               # debug | release
    output = "mygame"           # the file `sloppy build` writes (beside the program)
    name = "My Game"            # PROGRAM_NAME: window title, and where save_data keeps data
                                # (a folder's name, as Windows allows them: no / \ : * ? " < > |)
    icon = "icon.png"           # a square PNG (up to 256 px): the .exe's icon, the window's (on
                                # Windows, X11 and supporting Wayland desktops), the Dock's
                                # on macOS, the web page's; PROGRAM_ICON has its bytes
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
them. `sloppy test dir` (and `sloppy test` alone, for the current directory) runs the tests of
each `.jo` file under it, a module's own tests as that file's, and ends with the counts of all. A test that calls `exit()` fails (it did not reach its end). `assert(a == b)` (and the
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

The function runs on many threads at once: read immutable/copy-safe inputs and return results
instead of changing globals or captured variables. Use documented atomics/shared primitives for
communication; arbitrary library calls are not necessarily thread-safe. Parallel callback safety
remains experimental beyond the compiler's documented checks.
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

### Tasks and channels

A task is a function running alongside the rest of the program. `spawn` starts one and gives a
`Task`, whose `wait()` is the function's result; a channel carries values from one task to
another:

```gdscript
t = spawn((): net.fetch("https://example.com").status)   # starts it: the program goes on
...
print(t.wait())                         # its result, waiting for it if need be

jobs = channel[str]()                   # channel[int](100): one that holds 100 before send waits
results = channel[int](100)
workers = [loop _ in 0..4: spawn(():
    loop url in jobs: results.send(net.fetch(url).status)     # until jobs is closed and empty
)]
loop u in urls: jobs.send(u)
jobs.close()
wait_all(workers)
```

Tasks take turns on the program's one thread: one runs until it waits (to send or receive on a
channel, for `t.wait()`, `sleep`, the network, a line of input, a program it runs), then the next
ready one runs. So between two waits nothing else changes the program's variables, and they need
no locks; and a task that computes for long without waiting holds up the others (for the
processor's cores: `parallel_map`, above). Parallel callbacks must read immutable/copy-safe
inputs and use documented shared primitives; arbitrary library calls are not necessarily thread-safe.
So do file reads and writes, C functions, and
`run_program` on Windows: they wait without letting the others run. A send or receive that need
not wait goes on at once, and lets the others ready take their turns every 64th time, so a loop of
them never holds the rest up for long. A task's closure sees the variables around it, as any
closure does, and one made in a loop has that turn's.

- `ch.send(v)` waits until a receiver takes `v` (a channel of capacity 0), or while the channel
  holds `capacity` values. `ch.receive()` waits for the next value, and gives none once the
  channel is closed and empty: `loop let v = ch.receive():`, or `loop v in ch:`, go until then.
- `ch.receive(wait = 2.0)` waits at most 2 seconds (none: nothing came; `ch.closed()` tells it
  from a closed channel), and `ch.send(v, wait = 2.0)` is false when `v` could not go in that
  time. `ch.try_send(v)` and `ch.try_receive()` do not wait; `ch.len()` is how many wait in it. A
  time that has passed (below 0) is no wait at all; NaN is an error.
- Cancellation does not retract channel items. Untimed `send(v)` normally waits for a buffer
  slot or rendezvous. If cancelled after enqueueing, it may return while v remains queued,
  even on an unbuffered channel; a later receiver can still take it. If already cancelled
  before enqueueing, it sends only if a buffer slot or waiting receiver is available and
  otherwise returns without sending. Its void result cannot distinguish these cases.
  Timed `send(v, wait = seconds)` and `try_send(v)` return true only after enqueueing, false
  only if never enqueued. Acceptance is local, not a promise that a receiver processed it;
  later cancellation leaves accepted values queued. Send after close panics in every form.
  The void-send cancellation contract stays experimental; use a bool form when cleanup needs
  to know whether a final message was accepted.
- A channel's values cannot be optionals (`channel[int?]` is an error): `receive`'s none means
  the channel is closed.
- `select` takes the first of several operations that can go on, waiting until one can (one that
  is ready is picked fairly, not always the first):

  ```gdscript
  select:
      inbox.receive() as msg: handle(msg)       # msg: the value, or none once inbox is closed
      out.send(job): sent += 1
      worker.wait() as r: print("done:", r)     # a task has ended
      stopping(): break                         # ctrl-c or SIGTERM (lib/std/stop.jo)
      after 2.0: print("nothing for 2 seconds")  # or `else:`, for when none can go on now
  ```

  A closed channel's arm is always ready (with none). To stop selecting on it, keep the channel
  in an optional and set it to none: an arm on none is never ready.

  ```gdscript
  a: Channel[int]? = fast
  b: Channel[int]? = slow
  loop a != none or b != none:
      select:
          a.receive() as v:
              if let x = v: merged.push(x)
              else: a = none                    # closed: this arm is off from now on
          b.receive() as v:
              if let x = v: merged.push(x)
              else: b = none
  ```
- `wait_all(tasks)` gives their results in order; `t.done()` says whether one has ended, and
  `t.wait_for(5.0)` waits at most 5 seconds for it (true once it has); `yield_now()` lets the
  others take their turns in a task that computes for long.
- `t.cancel()` asks a task to stop: its waits end at once from then on, the one it is in too,
  giving nothing (`receive` none, `sleep` returns, a `send` stops waiting (queued values stay), `select` takes its `after` or
  `else` arm, `net.fetch` status 0, `tcp_receive` nothing), and `cancelled()` is true in it, for
  it to clean up and end. A task that never waits or looks is not stopped. `t.wait()` still waits
  for the result.
- A group: `g = task_group()`, then `g.spawn((): ...)` for each; `g.wait()` waits for them all,
  `g.cancel()` cancels them all. A panic in one ends that one only (it is told on standard error)
  and cancels the others; `g.wait()` then gives false, and `g.why()` the panic's message. A task
  that is cancelled while it waits for a group cancels the group's tasks.

  ```gdscript
  g = task_group()
  pages = [loop u in urls: g.spawn((): net.fetch(u, wait = 10.0).text)]
  if not g.wait(): eprint("a fetch failed: {g.why()}")
  ```
- `next_frame()` in a game's task waits for the next frame: a game's tasks take their turns at
  the start of each frame, before `update`, so a task can play out a sequence over several
  (show "Ready", `sleep(1.0)`, show "Go!").
- The program ends when `main` (or the top-level code) and every task have ended, or at `exit()`.
  `spawn(f, background = true)` starts one the end does not wait for: a server's loop, so a test
  can serve and fetch from itself (`spawn((): http.serve(port), background = true)`).
- If every task waits for something none of them will do (a receive on a channel nothing sends
  to, a send nothing receives), the program stops and says where each one waits, and where each
  was spawned. `report_tasks()` writes the same at any time (for a program that seems stuck), and
  `task_count()` is how many are running.
- A panic in a task (outside a group) ends the program, as anywhere else, and says where the task
  was spawned. An HTTP server's handlers run as tasks of their own: one that waits lets the
  others be answered.
- Ctrl-c and SIGTERM (`stopping()`, lib/std/stop.jo): the `sleep` and `net.wait` of a task that
  has asked `stopping()` end at once, and a `stopping():` arm is ready. The usual order: main (or
  the loop that watches) sees `stopping()`, tells the tasks (closes the channels they read, or
  cancels them), waits for them, then saves. If tasks go on once main has ended, the program says
  which and where they wait, after a second; a second ctrl-c or SIGTERM ends it.
- A connection (`net.tcp_*`, a WebSocket peer) is a number of its own: the task that has it reads
  it, answers, and closes it. One closed by another task is closed for all (a `tcp_receive`
  waiting on it ends with nothing), and a new connection is never given the old number. A
  server can have a task for each connection: `net.tcp_accept(s, wait = 1.0)` and
  `net.tcp_receive(c, wait = ...)` in it, or for WebSockets `p = net.accept(wait = 1.0)` and
  `net.receive([p], wait = ...)`, which waits for that peer's events only.
- In a web page, tasks need a browser that can pause WebAssembly code (JSPI: Chrome and Edge
  137 or later, and the newest Firefox and Safari); `sleep`, `net.fetch` and `net.receive([p],
  wait = ...)` wait there too in a program with tasks (not in a game's `update`). A panic in a
  task ends the program there, in a group too. A switch between tasks costs some microseconds
  there (about 0.1 natively).

### Fetching from the web

`import net`, then `net.fetch(url)` gives an `HttpReply`: `status`, `text`, `data`, `headers`
(names in small letters), `all_headers` (each header separately), `size` and `why`. Status 0
means no answer; redirects are followed up to five times (`follow = false` gives the redirect
itself). `net.fetch_start` starts the same request without waiting; `net.fetch_result(id)` gives
its answer once, or `none` while it is on its way. `net.fetch_all(urls)` fetches many at once.
See [fetching from the web](START.md#fetching-from-the-web) for methods, bodies, files and retries.

In a page, `fetch_start`/`fetch_result` work in any browser with WebAssembly: start a request,
then check once per frame (each reply is given once). `fetch` and `fetch_all` can wait in tasks,
using JSPI to give the browser its event loop back; for example:

```gdscript
import net
worker = spawn((): net.fetch_all(["/api/a", "/api/b"], at_once = 2))
replies = worker.wait()
```

Without tasks, or in a game's `update`/`draw`, waiting fetches return status 0 with an error
pointing to `fetch_start`/`fetch_result`. Browser tasks need JSPI support (see Tasks above).
Relative URLs resolve against the page. Methods, headers and bodies use the browser's Fetch
API; a nonempty body defaults to JSON or text as natively. Browsers forbid GET/HEAD bodies
(an error), control some headers themselves, enforce CORS, and expose only allowed response
headers (`Set-Cookie` is hidden). The browser manages cookies according to its normal policy.
`save_to` and an explicit `CookieJar` return status 0 with a clear error in a page.

`wait` is a timeout for the whole response, including its streamed body: an AbortController
stops it even if the program has not polled recently. `fetch_cancel(id)` aborts and discards a
request. Streamed progress is delivered when Sloppy polls or resumes its waiting task; `got` is
the bytes decoded by the browser, and `all` is the visible Content-Length, or -1 if unknown
(compression can make that length differ from decoded bytes). Redirects normally follow the
browser's policy. With `follow = false`, a redirect gives status 0 and explains that browsers
hide its status, headers and body; a native program can inspect those details.

Native requests can share cookies by passing `cookies = jar` to any of those three functions:

```gdscript
import net

jar = net.cookie_jar()
login = net.fetch("http://127.0.0.1:8080/login", method = "POST",
    headers = {"Content-Type": "application/x-www-form-urlencoded"},
    body = url_query({"user": "ann"}), cookies = jar)
page = net.fetch("http://127.0.0.1:8080/account", cookies = jar)
pages = net.fetch_all(["http://127.0.0.1:8080/account", "http://127.0.0.1:8080/settings"], cookies = jar)
net.clear_cookies(jar)
```

HTML forms send that Content-Type automatically; a `net.fetch` form request must set it.
`url_query` encodes field names and values, including spaces, `&` and non-ASCII text.

`cookie_jar() -> CookieJar` makes an empty jar; copies share it, including fetches still on their
way. `clear_cookies(jar)` forgets its cookies and allows reuse. Without the option, requests keep
no cookies. Each answer's Set-Cookie headers update the jar before its redirect is followed, and
each hop selects cookies for its own host, path and scheme. Cookies without Domain go to that
host only; Domain cookies also go to its subdomains, and never an unrelated host or an IP's
suffix. Paths match at a slash boundary, longer paths first. Ports do not separate cookies.
Secure cookies go over https only (and are accepted over https only). Max-Age takes precedence
over Expires; expired cookies are removed. A name, domain and path identify a cookie for
replacement or deletion. Wire values keep their quotes and percent escapes. An explicit Cookie
header overrides the jar for that request; the answer still updates it. A jar holds at most 300
cookies, each Set-Cookie at most 4096 bytes, dropping the oldest when full. Jars stay in memory.
In web builds the browser manages cookies; an explicit jar gives status 0 with an explanation.

### Writing a server

`import http`, register `http.get(path, handler)` or `http.post(path, handler)`, then
`http.serve(port)`. A handler takes `http.Request` and returns `http.Response`: `http.text`,
`http.html`, `http.json` or `http.redirect`. Cookies are set with `http.set_cookie(res, name,
value)` and read from `r.cookies`; `http.set_signed_cookie(res, name, value, secret)` and
`http.signed_cookie(r, name, secret)` authenticate a cookie's value. The secret is at least 16
bytes, kept outside the code. Set `http.secure_cookies = true` behind https. See
[writing a server](START.md#writing-a-server) for routing, forms, middleware and deployment.

For a local server without a fixed port, call `http.listen(0, host = "127.0.0.1")` and
read `http.port()` while it stays open. Several `listen` calls create separate listeners;
`http.port(1)` reads the second one. WebSocket servers have the same pattern with
`net.listen(0)` and `net.port()`; raw TCP uses `s = net.tcp_listen(0)` and `net.tcp_port(s)`.
UDP uses `net.udp(0)` and `net.udp_port(socket)`; a netplay session bound with `s.udp(0, addrs).unwrap()`
reports its port with `s.port()`. Each accessor returns -1 when its listener/socket does not
exist. The OS chooses a free port while binding the socket, so callers need no
probe-and-rebind step.

A message for the next page goes on a redirect with `http.flash(res, message, secret,
kind = "info") -> bool`. Several calls add messages in order. On the next request,
`http.flashes(r, res, secret) -> http.Flash[]` reads them and clears their cookie on `res`:
return that same response to the client. Each `Flash` has `message` and `kind`.

```gdscript
import http

secret = unwrap(env("SESSION_SECRET"))
http.post("/save", (r: http.Request) -> http.Response:
    res = http.redirect("/", 303)
    http.flash(res, "Saved", secret, kind = "success")
    res)
http.get("/", (r: http.Request) -> http.Response:
    res = http.html("")
    messages = http.flashes(r, res, secret)
    res.body = bytes(join([loop f in messages: "<p>{html_escape(f.message)}</p>"], ""))
    res)
```

Messages accept arbitrary text, carried in one signed, HttpOnly, SameSite=Lax cookie, good for
five minutes. `flash` returns false without changing the response when their JSON would exceed
2048 bytes. `flashes` gives `[]` for absent, forged, expired or malformed messages; a cookie
that was present is cleared even when invalid. Read before adding new flashes to that response.
Signing authenticates the messages; their text can still be read by the client.

For a response produced a piece at a time, return `http.stream(type)` and send chunks from
a task. The handler must return before the first chunk is sent; do not wait for the task
inside the handler. Tasks take turns, so the task below starts after the handler returns:

```gdscript
import http

http.get("/count", (r: http.Request) -> http.Response:
    conn = r.conn
    spawn(():
        loop i in [1..3]:
            if not http.send_chunk(conn, "{i}\n"): return
            sleep(1.0)
        http.end_stream(conn)
    , background = true)
    http.stream())
http.serve(8080, host = "127.0.0.1")
```

`curl -N http://127.0.0.1:8080/count` shows each number as it comes. `net.fetch` collects
the complete body, so it returns after `end_stream`; it cannot read an endless stream a
chunk at a time. A live web page usually uses `http.events()` and `EventSource` instead
([example](START.md#writing-a-server)). If an `http.after` callback waits, it can let the
task run before the stream is open: keep stream response callbacks free of waits, or send
from the program's own loop after `http.stream_open(conn)` becomes true.

`http.stream()` and `http.events()` keep `r.conn` open for `send_chunk` or `send_event`;
`end_stream` ends it, and `stream_open` reports whether it is still open. At most
`http.most_streams` (1000) are open in all, with 503 for another. Each address may hold at most
`http.most_streams_per_address` (16), with 429 for another; ordinary requests and HEAD still
work. Ending a stream or losing its client frees the slot. As with `http.allow(r.address,
per_minute)`, the address is the direct client's unless its proxy is in `http.trust_proxy`:
then X-Forwarded-For's last address outside that list is used. For Caddy on the same machine,
set `http.trust_proxy = ["127.0.0.1"]`. Untrusted forwarded headers cannot bypass the limit.

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
    global last
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
typed this frame, repeats included. `shortcut(.s)` is a tool's key: Ctrl+S (Cmd+S on a Mac),
`shortcut(.z, shift = true)` Ctrl+Shift+Z; browsers keep Ctrl+N, Ctrl+W and Ctrl+T for
themselves. Likewise `mouse_down`, `mouse_pressed`, `mouse_pos()`,
`mouse_wheel()`, and gamepads (`gamepad_down`, `left_stick()`); `input_axis()` combines arrows,
WASD and the left stick. On a Steam Deck the built-in controls are a gamepad when the game is
started from Steam (in Desktop Mode too, after Games → Add a Non-Steam Game); started any other
way, Steam turns them into a keyboard and mouse. For mouse look, `mouse_lock()` hides the pointer and keeps it in the
window while `mouse_delta()` reports how far it moved (Wayland, X11 and browsers, where the
lock starts at the next click and Escape ends it); `mouse_lock(false)` lets it go.
In a web page, `text_input()` also has what an input method composes (Japanese, Chinese,
Korean) and what the system's emoji panel inserts, once committed; natively, Windows gives it
too, while on Linux it is the keys' characters (X11's XIM and Wayland's text-input are not
used yet).

**Gamepads and joysticks.** `gamepads()` gives the connected pad numbers (0–7), and
`gamepad_connected(pad)` / `gamepad_name(pad)` describe one. A connected controller keeps its
number; a newly connected one takes a free slot. On Windows, four XInput users and HID
controllers share these eight slots; XInput interfaces are filtered out of HID enumeration.
`gamepad_down(pad, .a)`, `gamepad_pressed` and `gamepad_released` read one pad; without `pad`,
they read any pad. There are no separate connection callbacks: compare `gamepads()` between
frames. `PadButton` uses Xbox-style positions: `a`, `b`, `x`, `y` are south, east, west, north
(PlayStation Cross/Circle/Square/Triangle; Nintendo B/A/Y/X), plus `lb`, `rb`, `back`, `start`,
`home`, `lstick`, `rstick`, `up`, `down`, `left`, `right`.

`gamepad_axis(pad, i)` reads left X/Y, right X/Y, left/right trigger (indices 0–5). Sticks are
−1..1, Y down, triggers 0..1. `left_stick(pad)` / `right_stick(pad)` add a radial dead zone;
without `pad`, the stick pushed furthest wins. `joystick_buttons`, `joystick_button`,
`joystick_pressed`, `joystick_axes` and `joystick_axis` expose up to 32 raw buttons and 16 raw
axes for devices whose standard mapping is approximate. Windows HID raw buttons follow HID
button usages (usage 1 is button 0); raw axes follow the descriptor's capability order.

| Platform | Controller input |
| --- | --- |
| Windows | XInput (Xbox-compatible); Raw Input HID for USB DualShock 4 and DualSense/Edge, Switch Pro, common 8BitDo SN30/SF30 Pro, Pro+, Pro 2 and Ultimate D-input layouts, plus generic HID joysticks/gamepads. Hot-plug is supported. |
| Linux | `/dev/input/js0`–`js7`, with the Linux Xbox-style axis/button ordering; other layouts may need raw joystick controls or Steam Input. Access to the device nodes is required. |
| macOS | Apple's GameController framework: controllers for which it supplies an extended gamepad profile (Xbox, PlayStation, Switch Pro and MFi). |
| Web | The browser's Gamepad API; standard layout and controller availability depend on the browser/OS. |

On Windows the first gamepad/joystick reader enables XInput polling and Raw Input HID.
Actions using pad inputs and UI/layout pad navigation enable them through those same readers.
Programs that only draw or read keyboard/mouse input do not link or start either backend.
A reader used before the window opens defers Raw Input registration until it opens.

Windows' generic HID fallback maps buttons in order, a hat to the d-pad, X/Y to the left
stick, Rx/Ry to the right stick, Z/Rz to triggers. Four-axis X/Y/Z/Rz devices use Z/Rz for the
right stick instead. Known layouts override these assignments; 8BitDo D-input and Switch
triggers are digital. Other 8BitDo models use generic mappings; firmware differences may need raw controls. Switch
Pro USB starts the Nintendo report protocol asynchronously; its sticks use nominal ranges
rather than factory calibration. Its simple Bluetooth report is also decoded. Sony's
Bluetooth extended reports (DS4 report 0x11, DualSense 0x31) are not supported: use USB or an
XInput translation layer. Rumble, motion sensors, touchpads, and player LEDs are not exposed.

`set_cursor(c)` gives the mouse pointer a shape over the window: `.arrow`, `.ibeam`, `.hand`,
`.crosshair`, `.move`, `.resize_ew`, `.resize_ns`, `.resize_nwse`, `.resize_nesw`,
`.not_allowed`, `.wait`, or `.hidden` (as `show_cursor(false)`); while it is `.arrow`, a text
field under the pointer shows an I-beam. Web pages, Windows, X11 and macOS have them all
(macOS shows the arrow for the diagonals and `.wait`); Wayland where the compositor offers
cursor shapes (GNOME, KDE).

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
`is_fullscreen()` (in a browser, the page asks for fullscreen; it leaves on Escape);
`can_fullscreen()` is false where it cannot be had, in an iPhone's Safari.
`clipboard()` reads the system clipboard's text and `set_clipboard(s)` replaces it. A web page
may read the clipboard only as something is pasted, so there `clipboard()` is the text last
pasted (ctrl+V, or a text field's Paste button on a phone) into the page; the X11 fallback without libX11 keeps the text within the program.
`pasted_text()` is the text pasted in this frame ("" in others), for a widget of the game's own.

**Menus, boxes and text fields.** `ui_begin`/`ui_button`/`ui_slider`/`ui_text_field`/`ui_end` make
a column menu worked with keys, a gamepad, the mouse or a finger; `hud_button`, `hud_panel`,
`hud_checkbox`, `hud_slider`, `hud_scroll`, `hud_text_field` and `hud_text_area` are boxes placed
anywhere, for a game's own interface or a desktop tool. Both are immediate mode: drawn every
frame in `draw`, each says what was done to it (`if hud_button(r, "Save"): save()`, `name =
hud_text_field(r, name)`). Their boxes are in the units of the 2D transform (`camera2d_fit`,
`translate`, `scale`), and so is `clip(r)`.

```gdscript
query = ""
body = ""
draw = ():
    global body, query
    clear()
    if shortcut(.f): hud_focus("search")              # Ctrl+F (Cmd+F on a Mac)
    query = hud_text_field(Rect(10, 10, 300, 30), query, id = "search", hint = "Search")
    if hud_submitted(): find_next(query)
    body = hud_text_area(Rect(10, 50, 600, 400), body, id = "body")
```

Text fields edit as a desktop's text boxes do: a click puts the caret, a drag selects (a double
click a word), arrows, home and end move the caret (with ctrl, or alt on a Mac, by words; with
shift, selecting), backspace and delete (ctrl: a word), ctrl+A, ctrl+C, ctrl+X, ctrl+V, ctrl+Z,
ctrl+shift+Z and ctrl+Y (cmd on a Mac). Tab and shift+tab go between the fields in the order they
are drawn; Escape lets go of the keyboard; Enter does too, and `hud_submitted()` is true right
after the field (ctrl+Enter in a text area, where Enter starts a new line). `hud_focus(id)` gives
a field the keyboard, `hud_focused(id)` says whether it has it, and `ui_typing()` whether any
does (a game's own letter keys are better left alone then).

A `hud_panel` covers what was drawn before it: a dialog drawn last takes the clicks and the wheel
from the buttons under it, and `hud_panel(visible_rect(), rgba(0, 0, 0, 0.5))` drawn first makes
it modal. In a `hud_scroll` list, a row dragged somewhere (a card to another column) calls
`claim_press()` as the press goes down, and the list does not move with it; letting go of a
claimed press clicks no button. Labels too long for a `hud_button` or a `hud_checkbox` (given a
rectangle as wide as box and label) end in …, as `fit_text(s, width, size)` cuts any text;
`hud_button(r, label, align = .left)` puts the label at the left, for a list's rows.

### Choosing widgets and moving values between them

| System | Placement and identity | Slider arguments after placement |
| --- | --- | --- |
| `ui_` menu | Automatic column; label first | `label, value, step = 0.1, low = 0, high = 1` |
| `hud_` | Explicit Rect; text field identity is `id` | `rect, value, low, high, step = 0, label = ""` |
| `layout` (often imported as `ui`) | Responsive tree; retained identity is `key` | `value, low, high, step = 0, label = ""` |

Keep the existing positional conventions: when moving a slider between systems, pass
`low`, `high` and `step` by name. Menu step defaults to 0.1; HUD/layout step 0 permits
continuous pointer values (layout keyboard steps are 1% of the range). Labels stay first
in a menu because the menu chooses placement by row.

Single-line text fields all default to **64 Unicode code points**. The tails still differ:
`ui_text_field(label, value, max_chars = 64)`,
`hud_text_field(rect, value, id = "", max_chars = 64, hint = "")`, and
`layout.text_field(value, hint = "", max_chars = 64, ..., key = "")`.
Pass `max_chars = 24` to retain the former menu limit. The limit constrains inserted text;
it does not truncate a longer value supplied by the program. Layout remains experimental
because its prior-frame hit testing, key retention and focus lifecycle may evolve.

### Responsive layout

`import layout as ui` adds boxes whose positions follow their contents and the available
space. It is read only when imported; its short names are separate from the game library.
Describe the tree each frame in `draw`. `ui.screen` covers the visible area in the current
2D transform's units; `ui.at(r, ...)` uses any `Rect` in those same units. When the root returns,
it has solved the boxes and drawn them. A container's background draws before its children;
floating boxes draw after the normal tree. `examples/layout.jo` is an inventory screen made this
way, from a wide window down to a phone held upright.

```gdscript
import layout as ui

volume = 0.5
hints = true
difficulty = 1
name = ""
draw = ():
    global volume, hints, difficulty, name
    ui.screen(pad = 24, ():
        ui.column(gap = 12, cross = .center, width = ui.grow(), height = ui.grow(), ():
            ui.label("Settings", size = 40)
            ui.panel(pad = 16, gap = 12, width = ui.fit(max = 480), ():
                ui.label("The menu fits its contents and wraps this help when the screen narrows.", wrap = true)
                ui.label("Sound and play", size = 24)
                volume = ui.slider(volume, 0.0, 1.0, step = 0.05, label = "Volume", key = "volume")
                hints = ui.switch(hints, "Show hints", key = "hints")
                difficulty = ui.choice(["Easy", "Normal", "Hard"], difficulty, "Difficulty", key = "difficulty")
                ui.label("Player name", size = 16, color = hud_style.muted)
                name = ui.text_field(name, hint = "Your name", max_chars = 24, key = "name")
                if ui.get("name")!.submitted: print("hello {name}")
                ui.row(gap = 8, width = ui.grow(), ():
                    if ui.button("Play", width = ui.grow()): print("play")
                    if ui.button("Quit", width = ui.grow()): quit()
                )
            )
        )
    )
```

`slider(value, low, high, step = 0, label = "")`, `switch(on, label = "")`,
`choice(options, index, label = "")` and `text_field(value, hint = "", max_chars = 64)`
return their new values immediately, using the preceding frame's box for input, like buttons.
They all accept `width`, `height`, `enabled` and `key`; width defaults to `grow()`, height to
`fit()`. The caller keeps the value, while keyed identity keeps focus, slider capture and the
text editor's caret, selection and undo with the control when rows reorder. A disabled control
is faded, skipped by navigation and does not respond to input.

Drag a slider with the mouse or a finger: it follows the pointer in that frame, even outside
its box, and owns the gesture inside a scrolling panel. A positive `step` snaps from `low`;
zero allows continuous dragging and uses 1% of the range per key press. Its value is shown at
the right when the row has room: with the step's decimal places (a range's own for zero),
and as a percentage for a range from 0 to 1. Choices wrap through
the options (an empty list returns zero); clicking or tapping the left/right half of their
value goes back/forward. Enter, Space or A advances a choice or toggles a switch.

**Left/Right belong to the focused value control**, including at a slider's endpoints and in
a horizontal row: they adjust sliders and choices, and stay put on switches and text fields.
The d-pad and left stick follow the same rule. This keeps adjustment predictable, as in the
`ui_` menus: reaching an endpoint never unexpectedly selects a neighbor. Up/Down navigate
between boxes; Tab/Shift+Tab or gamepad RB/LB move forward/backward through visible, enabled
controls in draw order, wrapping at either end, so every control in a horizontal row is
reachable. Buttons, cards and custom slots still use Left/Right for directional navigation.

Click/tap a text field or press Enter/A while it is focused to start typing. Enter/A again
submits and stops typing; Escape/B stops typing while keeping the text. Up/Down, Tab/Shift+Tab
or RB/LB leave the field. While typing, keyboard Left/Right edit the caret and Space types a space.
The HUD editor supplies selection, undo, clipboard shortcuts, the touch keyboard and its
Paste button. After calling the field, `ui.get(key)!.editing` says whether it is typing and
`.submitted` is true for the frame it submits (`hud_submitted()` also works immediately
after the field call). For several lines of text, a custom slot can host `hud_text_area`.

The required closure is declared first (after `r` in `at`); named options can precede it at
the call site as above. `slot` still hosts custom widgets and drawing: it calls its closure at
draw time with its **current** solved box. Captured locals can be changed in that closure; a
named function changing a global still declares `global`. Slots cannot add more layout
elements: describe the entire tree before drawing starts. `focusable = true` lets keys and a
gamepad reach a custom slot; its returned state or `ui.get(key)` supplies focus and activation,
and the custom widget supplies its value-changing input.

Each element accepts `width` and `height`. A number means fixed units; the other sizes are:

| Size | Meaning |
| --- | --- |
| `ui.fit(min = 0, max = 1e30)` | Contents, bounded by min/max; the default. |
| `ui.grow(weight = 1, min = 0, max = 1e30)` | Share remaining space by weight, bounded by min/max and the contents' minimum. |
| `ui.fixed(n)` | Exactly n units. |
| `ui.percent(p)` | A fraction from 0 to 1 of the parent's inner size, before gaps. |

Widths are measured from the leaves up, then assigned from the root down. Text wraps at its
final width, then heights are solved the same way. Fit and grow boxes that overflow shrink
largest first toward their minimums. Padding, gaps, fixed boxes and unbreakable text do not
shrink; content can still overflow when those cannot fit. A wrapping label's minimum width is
its longest unbreakable word (or CJK unit). Percent children contribute zero to a parent's fit
size, avoiding a circular size calculation. Grow on a container's cross axis fills that axis.
When bounded grow sizes compete, space freed by a maximum is shared by the remaining grows.

`row`, `column`, `panel`, `scroll` and `over` return `ui.State`: `rect`, `hovered`, `pressed`,
`clicked` and `focused`. Buttons return a bool. These answers use the preceding frame's boxes,
and are false with a zero rectangle the first time an element exists. A pointer event belongs
to the topmost box and its ancestors, so a card may use `ui.panel(...).clicked`. A release must
be on the box where its press began; a scroll drag or `claim_press()` cancels the click.
Buttons use `hud_style`, including disabled and selected states. Direction keys, the d-pad and
left stick move focus by the previous boxes' directions; Enter, Space or gamepad A activate.
`ui.slot(focusable = true, ...)` joins that navigation; its returned state or `ui.get(key)`
inside its callback gives focus and activation for custom controls. `row`, `column` and
`panel` take `focusable = true` too, for a card that is a control as a whole: it joins the
navigation, lights up under the pointer, and Enter or A clicks it. A layout text field keeps
Up/Down and Tab/shoulder navigation while typing; an external HUD/menu text field pauses layout
navigation. Rebinding controls pauses navigation too. Focus moved by keys or a gamepad onto
a box inside a scroll container scrolls it into view, including through nested scrolls.
Arrows can reach controls clipped out by their shared scroll container, even with long headers
between controls. Along a scrolling axis, arrows finish the innermost list before leaving it;
the nearest row or column wins before alignment. Tab/Shift+Tab and RB/LB visit
all enabled focusable controls in tree order and wrap, scrolling the target into view. Disabled
controls and content omitted from a closed floating panel stay out of navigation. The focused
control has a ring around it once keys or a gamepad have been used, until the next press of
the mouse or a finger.

All five containers take `width`, `height`, `pad`, `gap`, `align`, `cross`, `color`, `radius`,
`border` and `key`. `pad = 12` applies to every side; `ui.insets(left, top, right, bottom)`
sets them separately. `align` is along the row or column: `.start`, `.center`, `.end`, or
`.space_between` (extra space between children, in addition to `gap`). `cross` is `.start`,
`.center`, `.end`, or `.stretch`; stretch expands fit/grow children within their bounds and
leaves fixed/percent sizes alone. Colors default to transparent, except a panel's
`hud_style.panel`; panels also default to 16 units of padding, `hud_style.panel_radius` and an
edge of `hud_style.panel_edge`. `ui.Border(color, thickness)` draws an edge; radius rounds the
background and edge.

The look follows `hud_style` (set its fields before describing the boxes; a change holds for
the boxes described after it). Besides the colors the `hud_` widgets use, layout reads
`muted` (secondary text, for a label's `color`), `track` (behind a bar, a slider's fill, an
off switch and a scrollbar's thumb), `focus` (the focus ring), `radius` (buttons, value
controls and bars' corners; a switch is rounded twice as much), `panel_radius`, `panel_edge`,
`scrollbar` (the thumb's width), `field` (behind a slider's, switch's or choice's row) and
`well` (inside a text field). A selected button is tinted with `accent` and edged with it; a
pressed one is darker, its label a unit lower; a disabled one is faded. A value control's
label is at the left of its row, and its value in a column that starts at the same share of
each row, so sliders and choices in a column line up. The value carries the accent: a slider's
fill (its thumb haloed while it is pointed at, held or chosen with keys), an on switch, the dot
of a choice's option under it (for 2 to 7 options), and a text field's edge while it is typed
in, when its focus ring makes way for the caret.

`scroll` is a column by default; `axis = .horizontal` makes a row. Give its scrolling axis a
bounded size. It clips children to the inner box, lets their content overflow on that axis,
and keeps its offset by id. The innermost scroll under the pointer takes the wheel. Dragging
the content or its scrollbar moves it; letting go of a moving drag glides with damping. The
thumb is drawn inside the container's far edge, faint at rest, clearer while the list moves or
the pointer is over it, wider over its last 12 units, where it can be dragged: give the
content padding on that side (`pad = ui.insets(0, 0, 14, 0)`) to keep it clear of the thumb.
`ui.scroll_to(key, offset, root = "root 0")`, called before the root, sets its offset, which
the next solve clamps to the content.

`over` is a floating column attached to its parent's box, outside the normal flow and scroll
clips. `anchor` names the parent's point, `at` names the floating box's point, and `offset` is
added to its position. Both points default to `.top_left`; the other points are `.top`,
`.top_right`, `.left`, `.center`, `.right`, `.bottom_left`, `.bottom`, and `.bottom_right`.
For a badge at the parent's upper right use `anchor = .top_right, at = .top_right`.
Floating elements are drawn and hit-tested after the normal tree, including elements
described after them. An outer clip installed by the game still applies. `clip = true` keeps
the floating box inside the scroll containers around it, as a count on a list row's picture
should be, where a tooltip or a menu would escape them.

Leaves are `label(s, size, color, wrap, align, width, height, key)`,
`button(text, width, height, enabled, selected, key)`, `space(width, height, key)`,
`bar(amount, color, width, height, back, key)`, `image(texture, width, height, tint, key)` and
`slot(draw, width, height, focusable, key)`. A grow spacer pushes the following children to
the end; a slot with fit sizes has no intrinsic content size. Images stretch to their boxes
and fit their pixel dimensions by default. A bar is filled over `hud_style.track` unless
`back` is given. Labels use `.left`, `.center` or `.right` text
alignment, independently of the container's alignment.

Identity is the parent's id plus the child's index. Give moving list rows `key = item.id`
(a string) so their input, focus and scroll offsets follow the item. Explicit keys are local
to their parent and must be distinct there. Give separate roots distinct keys and describe
each once per frame. Unnamed roots are `"root 0"`, `"root 1"`, and so on in call order.
`ui.bounds(key, root = "root 0") -> Rect?` returns the last solved box;
`ui.get(key, root) -> ui.State?` also gives its event state. During description or a slot
callback these query the preceding frame; after the root they query the just-solved boxes.
For queries use a key unique within the root, since separate parents can use the same key.

`ui.hovered()` tests the last boxes at the current pointer. Drawn layout boxes also count in
`hud_hovered()`. The root coordinate space and empty spacers do not capture pointer input.
`ui.debug = true` outlines every box over the drawing: containers blue (their padding a fainter
inner edge), scroll containers green, floating boxes orange, leaves pink. `ui.reset()` releases cached roots when the UI closes
permanently. `ui.at(r, render = false, input = ui.Input(...), ...)` solves without a window,
still runs slots, and accepts scripted pointer/navigation input; `ui.clip_bounds(key, root)`
exposes the inherited clip for headless tests. Omit `input` when using live game input.
`ui.profile = true` measures each solve in `ui.solve_seconds`, excluding description and drawing.

**A user's files.** `dropped_files()` is the paths of the files dropped onto the window, in
the frame they arrive ([] in the others): Windows, X11, Wayland and web pages. A dialog is
started, and its answer comes later, as a fetch's does: `open_file_dialog(types, multiple,
title)` and `save_file_dialog(name, types, title)` give an id, and `file_dialog_result(id)` is
none while the dialog is open, then the paths chosen ([] if it was cancelled), once. Natively
it is the system's dialog on Windows, zenity's or kdialog's on Linux (when one is installed),
AppleScript's on macOS. In a web page the browser gives the page a copy of each file, which
`read_file`, `read_bytes` and `load_image` read under its name; its file picker opens only as
a click, a tap or a key ends (asked for in another frame, at the next one), and saving gives
the name asked for at once: write the file there, then `download_file(path)` (which natively
does nothing more), so the same code works everywhere. `SLOPPY_FILE_DIALOG="a.txt|b.txt"`
answers every dialog at once (`""`: cancelled), and SLOPPY_INPUT's `5:drop=a.txt` drops a file.

```gdscript
asked = -1
update = (dt: f64):
    global asked
    loop p in dropped_files(): open_doc(p)
    if key_down(.ctrl) and key_pressed(.o): asked = open_file_dialog([".txt", ".md"])
    if asked >= 0:
        if let paths = file_dialog_result(asked):
            asked = -1
            if paths.len() > 0: open_doc(paths[0])
open_doc = (p: str): text = read_file(p).unwrap()
```

**Tools: frames on demand.** A game draws 60 frames a second; a notes app or an editor that
waits for its user need not. After `redraw_on_input()`, a frame is drawn only when something
may have changed: a key, the mouse moving or clicked, the wheel, text typed, the window resized
or focused, files dropped, a dialog's answer (and two frames after each), at the time
`redraw_after(seconds)` asked for (a clock, a message that goes away), or after
`request_redraw()`. In between the program sleeps, using next to no CPU (sound still plays).
What moves on its own calls `request_redraw()` in each frame it is not done in; tweens,
`hud_scroll`'s gliding and a text field's blinking caret do so themselves. While the program
fetches from the network or has tasks, frames come at least 10 times a second, so that it sees
their answers. A web page stops asking for animation frames meanwhile; screenshot runs draw
every frame as usual.

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
screen_fit(.native)       # no scaling: one unit per pixel as the desktop counts them (two of the
                          # screen's own at 200%, as on a phone), so a tool's text and boxes are
                          # one size everywhere; a window for a design smaller than 640 x 360
                          # opens at its own size, not larger as for pixel art

render_resolution(640, 360)   # draw at a fixed resolution, scaled up (sharp pixels, whole steps;
                              # smooth = true, whole = false for other looks)
pixel_art()                   # the same at the design size: window("game", 320, 180) + pixel_art()
                              # is a 320 x 180 pixel game (its window opens 4 times larger);
                              # textures loaded after it are sharp (smooth_textures)
render_scale(0.5)             # draw at half the window's resolution (fewer pixels: faster)
full_resolution()             # in draw: the rest of the frame at the window's own resolution
```

Text drawn at 320 x 180 is a few pixels tall, and blurs into blocks. For a HUD that stays sharp,
call `full_resolution()` in draw after the world: what follows is drawn at the window's
resolution, in the same units, over the pixel art (`text("Score {score}", vec2(4, 4), 8)` is 8
units tall, 32 pixels in a window four times larger). A pixel font is a TTF like any other,
`set_font(load_font(embed("pixel.ttf")).unwrap())`; give it sizes the window's scale turns into whole
pixels.

Menus (`ui_begin`, `ui_button`...) keep their sizes in step with the design size: at 480 x 270
they take the same part of the screen as at 1280 x 720 (`ui_scale()`), unless `ui_style` sets
its own.

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

**Linux window icons.** `build: icon = "icon.png"` supplies the window icon on X11 and
on Wayland compositors offering `xdg_toplevel_icon_manager_v1` (including KDE). Sloppy sends
immutable shared-memory buffers at several sizes, with premultiplied alpha; this also works
when libdecor manages the window. The protocol is optional, and a compositor decides where
it displays the icon. See the [Wayland icon protocol](https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/main/staging/xdg-toplevel-icon/xdg-toplevel-icon-v1.xml).

GNOME uses the application's desktop entry for its launcher/window icon. Install a
`.desktop` file whose basename matches the window's app id, which is `PROGRAM_NAME` (the
build block's `name`, else the source filename without `.jo`). For example, with
`name = "org.example.MyGame"`, install `~/.local/share/applications/org.example.MyGame.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=My Game
Exec=/absolute/path/to/mygame
Icon=/absolute/path/to/icon.png
Terminal=false
Categories=Game;
```

Use `window("My Game")` to give the window a friendly title while keeping that stable app id. Package/install the desktop entry
with the game; the library does not write launcher files into the user's account. The
[app-id request](https://wayland.app/protocols/xdg-shell#xdg_toplevel:request:set_app_id)
describes the desktop-entry naming convention.

**Pictures without a game.** `render_image(w, h, ():` with drawing below it`)` gives an `Image`
of exactly w x h pixels, drawn with the same functions as `draw` (pixels from its top left
corner): a chart a script saves with `save_png("chart.png", img)`, a texture made at the start.
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
sloppy test file.jo       run `test` blocks (sloppy test file.jo save: those with "save" in their names;
                          sloppy test dir, or sloppy test alone for .: those of each .jo file in it)
sloppy new dir [kind]     a project to start from: dir/dir.jo (kind: game, arcade, pico, platformer, 3d, character, story, online, program, tui, server)
sloppy check file.jo      type check only
sloppy add <git URL>      a package, in the build block (and sloppy.lock); sloppy update: the newest
                          commits of its branches
sloppy fmt file.jo        lay out the code one way (directories too; --check: only list what
                          would change; -: standard input to standard output)
sloppy upgrade            install the latest release of Sloppy (when this is not it)
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
  after `speed = 200.0`), when a file it names changes (`player = load_texture(embed("player.png")).unwrap()`
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
or release mode as the build block says. It runs headless as a game does ([Testing a
game](#testing-a-game)): `SLOPPY_SOFTWARE=1 SLOPPY_SCREENSHOT=shot.png SLOPPY_FRAMES=600 sloppy
watch game.jo` takes the reloads with no window and saves frame 600, with an error or a panic over
it as the window would show it.

**3D cameras.** `orbit_camera(target, distance)` turns around a point;
`follow_camera(distance = 6)` follows a moving character. Set `cam.invert_y = true`
(or `invert_x`) to reverse mouse and right-stick look; both default to false.
`update(cam, player_pos, dt, input = false)` keeps following and smoothing without
reading look or zoom input, useful while a menu is open. For an orbit camera, use
`update(cam, dt, input = false)`. A supplied follow-camera `heading` still applies.
Skip the update entirely to freeze the camera. See [3D cameras](GRAPHICS.md#3d-cameras).

**3D materials.** Place the camera with `camera3d`, light the scene with `sun` and `sky`,
and draw `cube_mesh`, `sphere_mesh`, `custom_mesh`, or an imported glTF model. Existing
`draw_mesh` calls keep their simple lighting. `draw_mesh(ball, material = Material(metallic = 1,
roughness = 0.25))` selects metallic-roughness PBR; `load_model(embed("ship.glb")).unwrap()` and
`draw_model(ship)` use the glTF material's factors, base/metallic-roughness/normal/occlusion/
emissive textures, alpha mode and double-sided state. Missing tangent frames are generated;
exported tangents and skinning are retained. Base/emissive texture RGB is sRGB; material and
vertex color factors are linear. `Material(alpha_mode = .mask, alpha_cutoff = 0.5)` cuts out
transparent texels, including their shadows; `.blend` draws transparent surfaces last.
See [3D materials](GRAPHICS.md#3d-materials) for channels, UV sets, tangent conventions and
lighting approximations. `sky_image(load_texture(embed("sky.png")).unwrap())` selects an
equirectangular background and ambient reflections; `sky(...)` returns to the gradient.
For glTF morph targets, `rest_pose(model).weights` contains each node's target weights;
change `p.weights[node][target]` and pass `pose = p` to `draw_model`, or use `pose_at` for
animated weights. Morphing runs before skinning, with independent weights for each draw.
The complete [animated glTF scene](GRAPHICS.md#an-animated-gltf-scene) puts model sizing,
animation crossfades, a sky image, PBR and a follow camera together, with embedded assets
that also work in a web build.

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
  screen's units), `7:text=hi there` types (to the next comma), `5:touch1=400x300` puts finger 1 down there (or moves it)
  and `9:touch1-` lifts it (the first finger down is the mouse too, as on a phone),
  `5:pad_a+`/`9:pad_a-` press and let go a gamepad's button (pad 0; PadButton's names:
  `a`, `b`, `x`, `y`, `up`, `down`, `left`, `right`, `start`...); `5:pad_down+` is d-pad down,
  `6:lstick=1x0` and `rstick=` set its sticks, `lt=1` and `rt=` its triggers (another gamepad
  by its number: `5:pad1_a+`, `6:pad1_lstick=1x0`). An item it
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

### Terminal programs

A program can take the whole terminal as a screen of characters, as curses, tcell or bubbletea
let one do: a file browser, an editor, a game in the terminal. `import term`, then `term.start()`:
keys come one at a time as they are typed, the program draws into a screen of cells, and
`term.flush()` shows what changed.
[examples/files.jo](https://github.com/david-andrew/sloppy-lang/blob/master/examples/files.jo)
is a file browser; `sloppy new my_list tui` makes a list of things to do to start from.

```gdscript
import term

x = 10
y = 5
term.start(mouse = true)
loop:
    w, h = term.size()
    term.clear()
    term.box(0, 0, w, h - 1, title = "arrows or a click move it, q quits")
    term.put(x, y, "@", fg = term.YELLOW, style = term.BOLD)
    term.put(0, h - 1, "at {x}, {y}", fg = term.GRAY)
    term.flush()
    e = term.read_event() ?? break
    if e.kind == .mouse and e.mouse == .press: x, y = e.x, e.y
    match e.name:
        "q", "escape": break
        "left": x -= 1
        "right": x += 1
        "up": y -= 1
        "down": y += 1
```

- **Drawing.** Columns (`x`) and rows (`y`) count from 0 at the top left, and what falls off the
  screen is left out. `put(x, y, text, fg, bg, style)` gives the column after the text;
  `fill_rect`, `box` (`lines = .single`, `.double`, `.rounded` or `.heavy`, with a `title`),
  `hline`, `vline` and `clear(bg = ...)` do what they say. Characters of East Asian scripts and
  emoji take two cells, marks on a letter none: `text_width(s)` counts the columns text takes,
  and `fit(s, 20)` cuts it to 20 with a `…`. `set_cursor(x, y)` shows the cursor where the user
  types.
- **Colors** are numbers: the 16 named ones (`term.RED`, `term.BRIGHT_BLUE`, `term.GRAY`...)
  follow the terminal's theme, `term.color(n)` is one of xterm's 256, `term.color(rgb(1, 0.5,
  0))` any color (24 bits), and `term.DEFAULT` the terminal's own. Styles join with `|`:
  `term.BOLD | term.UNDERLINE` (also `DIM`, `ITALIC`, `REVERSE`, `STRIKE`).
- **Showing it.** Draw everything each time, as a game's `draw` does: `flush` compares the screen
  with what the terminal shows and writes only the cells that changed, in one write, with the
  cursor moved as little as it can be (as synchronized output, which the terminals that have it
  show at once). It gives the bytes it wrote; `redraw()` makes the next flush write every cell
  (after something else wrote to the terminal).
- **Events.** `term.read_event()` waits for the next one, `read_event(wait = 0.1)` at most a
  tenth of a second (none: nothing came; for a loop that animates). An `Event`'s `kind` is
  `.key`, `.mouse`, `.resize` or `.paste`. A key is `e.key` (`.char`, the character in `e.text`,
  or `.enter`, `.tab`, `.backspace`, `.delete`, `.escape`, the arrows, `.home`, `.end`,
  `.page_up`, `.page_down`, `.insert`, `.f1` to `.f12`) with `e.ctrl`, `e.alt` and `e.shift`,
  and `e.name` says it as text to match on: `"a"`, `"A"`, `"space"`, `"enter"`, `"ctrl+c"`,
  `"shift+tab"`, `"alt+x"`, `"ctrl+up"`, `"f5"`. With `start(mouse = true)` the mouse's presses,
  releases, drags and wheel come too (`e.mouse`, `e.button` 1 to 3, `e.x`, `e.y`; `mouse_moves =
  true` for moves with no button held). A resize has given the screen its new size already
  (`term.size()`), and the next flush writes it all. Pasted text is one event, its lines ending
  with `\n`. A lone escape is told from the start of a key's sequence by 50 ms with nothing
  after it.
- **Putting the terminal back.** `term.stop()` puts the terminal back as it was (its screen, the
  cursor, its settings), and so does the program's end however it comes: its last line,
  `exit()`, a panic or a crash (whose message then shows on the terminal's own screen), ctrl-c,
  SIGTERM, the terminal closed. `on_quit` runs after that, so what it prints shows. Ctrl-c asks
  the program to stop as it does anywhere ([stop.jo](API.md#stopjo)): a program that looks at
  `stopping()` is given none once by `read_event`, and one that does not ends at its next
  `read_event`, `flush` or `sleep`; a second ctrl-c ends one that computes without waiting.
  `start(ctrl_c_key = true)` makes ctrl-c a key it reads instead (an editor's copy). Ctrl-z and
  ctrl-\ are keys (a program on the terminal's screen is not suspended).
- **Tasks.** A task waiting in `read_event` lets the others run: a clock can tick in a task,
  drawing as it goes, while main waits for keys. On Windows the wait looks for input every 10 ms.
- **Where.** Linux and macOS: any terminal with xterm's sequences (all of today's). Windows 10 and
  later: the console (Windows Terminal, the older console window), its keys, mouse and resizes
  read as the console's events; pasted text comes as keys typed there. A web page has no
  terminal: `start` gives false, and a web build that calls it is warned.
- **Testing.** Without a terminal the screen still works: `term.set_size(40, 10)`, then drawing,
  then `term.screen_text()` (its characters, a line for each row) or `term.render()` (what a
  flush would write). `term.decode(bytes)` gives the events in a terminal's input.
- A program that defines `update` or `draw` is a game, with a window: the function that draws a
  terminal program's screen needs another name (`show`).

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
(float sums keep their order, so that every machine gets the same result: `dot` and `sum` of
an array add in several running sums). So does an index that is the counter plus something the
loop does not change, as a row of a flat matrix, `c[i * n + j] += x * b[k * n + j]`, and the
same through a pointer from `data(xs)` (section 13). Through a pointer, write the loop in a
function, with the sizes as its parameters or variables: in top-level code they are globals,
which a write through the pointer could change, so they are read again for each element.
Indexes the compiler cannot follow (`c[idx[j]]`) keep their check on each access. For numeric
arrays the library does this already: `a * b` of two `f64[,]` is a matrix product in blocks that
stay in the cache, vectorized and shared among the cores when large, and a dotted expression
over `f64[,]` arrays of one shape is one vectorized loop, as over `f64[]`. Calls through function
values (`reduce`, `sort`, a lambda) are not inlined: in a hot loop, write the loop.
`soa T[]` keeps each field together, which is what loops over one or two fields want.

**Functions.** Release builds copy small functions into their callers; `@inline` on a function
copies it into every caller whatever its size (an interpreter's helpers), and `@noinline` keeps
one out. A `match` on whole numbers with many arms becomes a jump table: an interpreter's
`match opcode:` inside its loop is the fast way to dispatch, faster than an array of functions.
Parameters are borrowed, not copied: a struct passed on, from a `mut` parameter too, costs a
pointer.

**Numbers.** `int` is 64 bits and wraps around. Arithmetic on narrow types stays in them: two
`u8`s add as a `u8` (200 + 200 is 144), so widen first, `int(a) + b` (the compiler warns when the
narrow result is widened right after). Vectors (`vec2`..`vec4`, `mat4`) are plain floats in a
row: their math is scalar, the same as a struct of floats in C.

**Seeing where the time goes.** In a game, `show_stats()` (or `SLOPPY_STATS=1`) draws frame
times, long frames and the time of each `zone("physics") ... zone_end()`, on the CPU and the GPU.
For any program, `sloppy build -g` keeps names for gdb and `perf` (Linux), lldb (macOS) and
Windows' debuggers; `sloppy build --ir` writes the code the compiler made before machine code.

### File-writing argument order

File writers put the destination first: `write_file(path, contents, sync = false)`,
`write_bytes(path, bytes, sync = false)`, `save_png(path, image)` and `save_wav(path, sound)`.
`save_data(name, contents)` and `save_value(name, value)` use the same destination-first
convention. Text/path are both strings in `write_file`, so their established positional
order is unchanged. `encode_png(image)` and `encode_wav(sound)` return bytes without writing.
Writes return bool; on false, `file_error()` describes the failure. This differs from checked
reads, whose returned `FileError` owns its message.
