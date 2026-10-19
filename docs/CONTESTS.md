# Contests and Advent of Code

What a puzzle or contest program wants, for someone who writes them in C++ or Python: reading
the input, the integer facts, the containers, and the library's searching, number theory and
orderings. Everything here is in the library that every program has; nothing is imported.

## Reading the input

Read it all at once, then take it apart:

```gdscript
text = read_stdin()                     # all of standard input (or read_file("input.txt") ?? "")
nums = ints(text)                       # every whole number in it, in order
grid = text.lines()                     # the lines, without their ends ("\r\n" too)
loop line in grid:
    parts = line.split(" ")
    n = to_int(parts[1])!               # to_int gives an int? (none if it is not a number)
```

`read_line()` is for interactive input: it gives one line (a `str?`, none at the end), and it
writes out what was printed before it first, so an interactive judge sees each question before
the program waits for the answer. Output to a file or a pipe is collected and written in large
pieces, so printing many lines is fast; `flush_output()` writes it out now.

A string's `s[i]` is a byte (a `u8`), compared with character literals: `grid[y][x] == '#'`,
`int(c - '0')` for a digit. `text.lines()` of a grid gives its rows; `chars(s)` gives the
characters of text that is not ASCII.

`sloppy --release day1.jo < input.txt` runs a release build (inlined, registers, fewer bounds
checks): worth it for a long search; a debug build compiles faster and checks more.

## Integers

- `int` is 64 bits (`MAX_INT`, `MIN_INT`); `u64`, `i32`, `u8` and the rest exist too.
- `+`, `-`, `*` and `^` wrap around on overflow, in debug and release builds alike (`MAX_INT + 1`
  is `MIN_INT`). Where that must not pass unseen, `checked_add`, `checked_sub` and
  `checked_mul` give `none` instead, and `saturating_add` and the others stop at the ends
  ([checked.jo](API.md#checkedjo)).
- `/` truncates toward zero and `%` keeps the sign of the left side, as in C (`-7 / 2` is -3,
  `-7 % 3` is -1); `mod(-7, 3)` is 2, as Python's `%`.
- `x ^ y` on ints is an int power (`10 ^ 18`); `2.0 ^ 0.5` is a float one.
- For numbers past 64 bits there are no exact big integers. `Big` (`use big`) is a float with
  a large exponent: about 15 digits, for an idle game's money, not for exact answers.
- Number theory, exact for every int (no float in between; [integer.jo](API.md#integerjo)):

| C++ / Python | Sloppy |
|---|---|
| `std::gcd`, `std::lcm`, `math.gcd`, `math.lcm` | `gcd(a, b)`, `lcm(a, b)` |
| `math.isqrt(n)` | `isqrt(n)` (exact past 2^52, where `int(sqrt(f64(n)))` is not) |
| `pow(b, e, m)` | `pow_mod(b, e, m)`; a negative `e` is a power of the inverse |
| `pow(a, -1, m)` | `inv_mod(a, m)`: an `int?`, none when a and m have a common divisor |
| `(__int128)a * b % m` | `mul_mod(a, b, m)`: for m up to 2^63 (and `u64`s up to 2^64) |
| `stoull(s)` | `to_u64(s)` (to_int stops at 2^63 - 1) |

## Containers

| C++ / Python | Sloppy |
|---|---|
| `vector<int> v(n, 0)`, `[0] * n` | `v = fill(0, n)` |
| `vector<vector<int>> g(h, vector<int>(w))` | `g = [loop _ in 0..h: fill(0, w)]` (`g[y][x]`) |
| `map<pair<int,int>,int>`, `Counter`, `defaultdict(int)` | `counts: {(int, int): int}`, then `counts[(x, y)] += 1` (a missing key starts at 0 when changed); reading a missing one is an error: `counts.get(k) ?? 0` |
| `defaultdict(list)` | `groups: {str: int[]}`, `groups[k].push(x)` |
| `set<pair<int,int>>`, `set()` | `seen: Set[(int, int)]`, `seen.add((x, y))`, `(x, y) in seen`; `{1, 2}` is a set literal |
| `deque`, `collections.deque` | `q: Deque[(int, int)]`, `q.push(p)`, `q.pop_front()`, `q.push_front(p)`, `q.pop()` |
| `priority_queue`, `heapq.heappush(pq, (d, v))` | `pq: (int, int)[]`, `pq.heap_push((d, v))`, `d, v = pq.heap_pop()`: smallest first, tuples compared by their first element, then the next; `heapify(xs)` makes an array one |
| a priority queue of values with priorities | `h: Heap[str]`, `h.push(x, priority)` (an int priority keeps its order exactly), `h.pop()`, `h.pop_with_int_priority()` |
| `sort(v.begin(), v.end())`, `sorted(xs, key=len, reverse=True)` | `v.sort()`, `sorted(xs, key = len, descending = true)`, `xs.sort(key = (p): p.1)`; stable |
| `max(xs, key=len)` | `max(xs, key = len)`, `xs.max()`, `xs.max(default = 0)` for one that may be empty |
| `lower_bound`, `upper_bound`, `bisect_left`, `bisect_right` | `lower_bound(xs, x)`, `upper_bound(xs, x)` (also as `bisect_left`, `bisect_right`): indexes in a sorted array |
| `partition_point` | `partition_point(xs, (x): x < 10)`: the first index where the condition is false |
| `next_permutation`, `prev_permutation` | `next_permutation(xs)`, `prev_permutation(xs)` (in place, true until it wraps around) |
| `itertools.permutations(xs)`, `combinations(xs, k)` | `permutations(xs)`, `permutations(xs, k)`, `combinations(xs, k)`: arrays of arrays, all of them at once (10! is 3.6 million arrays: for more, loop on `next_permutation`) |
| `reverse(v.begin() + a, v.begin() + b)` | `xs.reverse(a, b)` (`xs.reverse()` for all of it) |
| `accumulate`, `itertools.accumulate` | `xs.sum()`, `cumsum(xs)` (the running sums) |
| `" ".join(map(str, xs))`, `print(*xs)` | `xs.join(" ")` (any array: each as print shows it) |
| `cerr << x`, `print(x, file=sys.stderr)` | `eprint(x, y)` (takes what print takes) |

A loop over a map gives its keys and values in the order they were added: `loop k, v in counts:`.
Maps and sets take any key that can be compared and hashed: numbers, text, tuples, structs.

## Recursion

A native program's main thread has a stack of 1 GB: a depth-first search goes millions of calls
deep, with no `setrecursionlimit` and no rewriting as a loop. A recursion that has no end says
how deep it got, where a C++ program would just crash. (In a web page the stack holds some
10,000 calls.)

Memoization is a map beside the function:

```gdscript
memo: {int: int}
ways = (n: int) -> int:
    if n < 2: return 1
    if let v = memo.get(n): return v
    r = ways(n - 1) + ways(n - 2)
    memo[n] = r
    r
```

In a function, `x = ...` changes a global named `x` if there is one above it (`let x = ...` makes
a local of that name): a name such as `n` or `seen` at the top level and in a helper is the same
variable.

## Advent of Code

A day in one file, with the puzzle's example as a test:

```gdscript
# the elves' calories, most first
totals = (text: str) -> int[]:
    sums = text.split("\n\n").map((block): ints(block).sum())
    sums.sort(descending = true)
    sums

test "the example":
    assert(totals("1000\n2000\n\n3000\n\n4000") == [4000, 3000, 3000])

t = totals(read_file("input.txt") ?? "")
print(t.first(), t.first(3).sum())
```

`sloppy test day1.jo` runs the top-level code, then each `test` block; `sloppy watch day1.jo`
runs the program again each time the file is saved.
