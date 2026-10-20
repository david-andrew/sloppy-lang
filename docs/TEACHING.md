# Teaching with Sloppy

For a class of students who have not programmed before: how they can run it, programs that ask
questions, an order to teach things in, the mistakes students make, and grading work with
`sloppy test`. For a data structures course: lists, trees and graphs, and the library's sets,
queues and heaps.

## Where students run it

- **In a browser** (Chromebooks, locked-down machines): [the playground](https://sloppy-lang.org/playground/)
  needs no install. Programs that ask for input get a box to type the answer in. Share links
  hand in work.
- **On their own machines**: the one-line install in [START](START.md), into the user's own
  folder (no administrator rights).
- **On school Windows machines** where scripts are blocked: the release's
  `sloppy-windows-x86_64.zip`, unzipped anywhere, runs as `sloppy.exe game.jo` from that folder.
  `sloppy game.jo` builds the program into the temporary folder and runs it from there; where
  security software stops programs run from there, `sloppy build game.jo -o game.exe` builds it
  next to the source instead.

## Programs that ask questions

```gdscript
name = input("What is your name? ")
age = input_int("How old are you? ")         # asks again until it is a whole number
print("Hello {name}! Next year you will be {age + 1}.")
```

`input(prompt)` gives back the line typed (text); `input_int` and `input_float` give a number,
and ask again when what was typed is not one. Text is not a number even when it holds digits:
`"12" + 1` is an error, and `to_int(s)` turns text into a number (`none` when it is not one).

## An order to teach things in

1. `print`, text in quotes, numbers, `{x}` inside text.
2. Variables, arithmetic, `input` and `input_int`.
3. `if`, `else if`, `else`; comparing with `==`, `!=`, `<`; `and`, `or`, `not`.
4. Loops: `loop i in [1..10]:` (1 to 10), `loop i in 0..n:` (0 to n - 1), `loop condition:`.
5. Arrays: `scores = [3, 1, 4]`, `push`, `len`, `loop s in scores:`, `scores[0]`.
6. Functions: `area = (w: f64, h: f64) -> f64: w * h`; the last line is what it gives back.
7. A text game: guess the number (`random_int`), hangman (text and its characters).
8. A first game with a window: `update` and `draw` ([Make a game](TUTORIAL.md)).
9. Structs: `struct Ball:` and a list of them.
10. A project of their own.

## What students get wrong

The compiler explains most mistakes in plain words (`=` where `==` was meant, Python's `def`,
`for`, `elif`, a misspelled name, a missing `:`). A few things work differently from what they
may expect:

- **Dividing whole numbers gives a whole number**: `7 / 2` is 3. `7.0 / 2` is 3.5.
- **`random_int(lo, hi)` leaves `hi` out**: `random_int(1, 7)` is a die, 1 to 6 (the compiler
  warns about `random_int(1, 6)`).
- **A string's elements are character codes**: `word[0]` of `"cat"` is 99. The letter as text
  is `word[0..0]`, or `chr(word[0])`.
- **A value that may be missing**: `read_line()` and `to_int(s)` give `none` when there is no
  value. `?? default` says what to use then: `to_int(s) ?? 0`.

## Grading work with `sloppy test`

A grader is a file that brings in the student's functions with `use` and tests them:

```gdscript
# grade.jo, next to the student's grades.jo
use 'grades.jo'

test "90 is an A": assert(letter(90) == "A")
test "89 is a B": assert(letter(89) == "B")
test "0 is an F": assert(letter(0) == "F")
```

`sloppy test grade.jo` runs each test and says which failed and why, and exits with 1 when any
did. The student's file runs its top-level code first, so ask students to put what asks
questions in `main = (): ...`, which runs only when their program is run itself. For a program
that prints, `run_shell("printf '90\\n' | sloppy grades.jo")` gives its output to check.

## Data structures

Values in Sloppy are copied, not shared (a variable holds its own list, as it holds its own
number), and recursion goes deep: a native program's stack holds millions of calls. Both shape
how a course's structures are written.

**A linked list, a tree.** A struct can hold itself as an optional. Code that changes one
recurses with a `mut` parameter, which is the field itself, so assigning it changes the
structure:

```gdscript
struct Node:
    value: int
    next: Node?

push_back = (n: mut Node?, v: int):
    if n == none: n = Node(v)
    else: push_back(n!.next, v)

head: Node? = none
loop v in [3, 1, 4]: push_back(head, v)
print(head)                     # Node(value=3, next=Node(value=1, next=Node(value=4, next=none)))
```

A binary search tree's insert and delete go the same way ([the language](LANGUAGE.md#7-structs-unions-enums-optionals-tuples)
has both). What students bring from Java or Python, a cursor walking the list
(`cur = head!`, `loop let nx = cur.next: cur = nx`, then `cur.next = Node(v)`), changes only
the cursor, which is a copy: reading through one is fine, changing goes through `mut`. A doubly
linked list, parent links or a graph's edges point back at what holds them, which a value cannot
do: keep the nodes in an array and link them by index (`next: int`, -1 for none), as the
memory of a real machine does. That is also how to show what a pointer is.

**Graphs** are adjacency lists, an array of arrays (`adj: int[][]`) or a map
(`{str: str[]}`). A breadth-first search takes a `Deque` for its frontier and a `Set` for what
it has seen; Dijkstra's algorithm keeps `(distance, node)` pairs in an array used as a heap, as
Python's `heapq` does:

```gdscript
adj: (int, f64)[][] = [[(1, 4.0), (2, 1.0)], [(3, 1.0)], [(1, 2.0), (3, 5.0)], []]
dist = fill(1e18, adj.len())
dist[0] = 0.0
pq = [(0.0, 0)]
loop pq.len() > 0:
    d, u = pq.heap_pop()                 # the nearest not yet done
    if d > dist[u]: continue             # (an older, longer way to u)
    loop e in adj[u]:
        if d + e.1 < dist[e.0]:
            dist[e.0] = d + e.1
            pq.heap_push((dist[e.0], e.0))
print(dist)                              # [0.0, 3.0, 1.0, 4.0]
```

**The library's structures:**

| Python | Sloppy |
|---|---|
| `set()`, `set(xs)`, `x in s`, `s.add(x)` | `s: Set[int]`, `set(xs)`, `x in s`, `s.add(x)` (true when it was new), `union`, `intersection`, `difference` |
| `collections.deque`, `append`, `popleft` | `q: Deque[int]`, `q.push(x)`, `q.pop_front()`, `push_front`, `pop` |
| `heapq.heappush`, `heappop` | `pq.heap_push(x)`, `pq.heap_pop()` on an array; `Heap[T]` with a priority for each value |
| `dict`, `d.get(k, 0)` | `{K: V}`, `d.get(k) ?? 0` (`d[k] += 1` starts a missing key at zero) |

**How deep recursion goes.** A recursive function a million calls deep runs as it is (the main
thread's stack is 1 GB, taken from the system only as it is used), so a recursive quicksort on
sorted input or a depth-first search down a long path does not need rewriting. One that never
stops is told as a stack overflow, with how deep it got and the function that called itself.
Worker threads (`parallel_map`) and web pages (the playground) have small stacks, some 10,000
calls in a browser: there a deep recursion becomes a loop with an array as its stack.

**Asserts that explain.** In a grader, `assert(bubble_sort([3, 1, 2]) == [1, 2, 3])` says what
the student's function gave when it fails, so a failing test is a hint, not only a mark:
`assertion failed: bubble_sort([3, 1, 2]) == [1, 2, 3] (bubble_sort([3, 1, 2]) is [1, 3, 2])`.

**A file of structures, used by others.** A file's top-level code runs when another brings it in
with `use`, but its `main` does not (as Python's `if __name__ == "__main__":`), and its tests run
only with `sloppy test` on it: a student's `linkedlist.jo` can keep its own tryouts in `main` and
its tests beside the code.

## A simulation for a class

A demonstration students open on their own (a projectile, a pendulum) is a game with sliders
and a chart:

```gdscript
angle = 45.0
speed = 20.0

# the flight from the ground until it lands, a point each 0.02 s
path = (angle: f64, speed: f64) -> (f64[], f64[]):
    a = angle * PI / 180.0
    xs: f64[]
    ys: f64[]
    t = 0.0
    loop xs.len() == 0 or ys[ys.len() - 1] >= 0.0:
        xs.push(speed * cos(a) * t)
        ys.push(speed * sin(a) * t - 4.9 * t * t)
        t += 0.02
    (xs, ys)

draw = ():
    global angle, speed, ui_style
    clear(WHITE)
    ui_style = ui_light_style()                 # (menus over a light background)
    ui_begin("controls", vec2(300, 60))
    angle = ui_slider("θ = {int(angle)}°", angle, 1, 5, 85)
    speed = ui_slider("v₀ = {int(speed)} m/s", speed, 1, 5, 40)
    ui_end()
    c = Chart(title = "Path", x_label = "x (m)", y_label = "y (m)", equal_axes = true)
    xs, ys = path(angle, speed)
    c.line(xs, ys, "path")
    draw_chart(c, Rect(620, 40, 620, 420))
```

Where no formula gives the answer (a pendulum swinging wide, a ball with drag, an orbit), the
program steps the motion along. `rk4(state, t, dt, rate)` moves a state dt seconds on, by the
Runge-Kutta method: `rate` says how fast each part changes. A pendulum's state is its angle and
its angular speed:

```gdscript
# (angle, angular speed): the angle changes by the speed, the speed by gravity's pull
swing = (s: vec2, t: f64) -> vec2: vec2(s.y, -9.81 / 2.0 * sin(s.x))

s = vec2(1.2, 0)
t = 0.0
loop t < 10.0:
    s = rk4(s, t, 0.01, swing)
    t += 0.01
```

The state can be a number, a vector, an f64[] (`[x, y, vx, vy]`), or a struct with `+` and `*`
of its own. Stepping by `s + rate(s, t) * dt` instead (Euler's way) is the first thing to try in
class, and the place to see why: its pendulum swings higher each time.

`hud_slider(rect, value, low, high, step, label)` puts a slider anywhere. The built-in font has
Greek letters, subscripts and superscripts, arrows and the common mathematical signs (θ ω Δ
v₀ x² → ≈ ≤ √). A chart for a worksheet is a picture without a window:
`save_png(chart_image(c, 800, 500), "path.png")`.

To give students the link:
- **From the playground:** *Link to play* copies a link that runs the program on the whole page,
  without the editor (*Edit* in its corner opens the code). Nothing to host.
- **As a file:** `sloppy build sim.jo --target wasm -o sim.html` makes one page that works offline
  and from a file. Put it where students can open it: a school's learning system (upload the
  file), GitHub Pages (a repository's files, published), or itch.io (an HTML game, zipped:
  `-o sim.zip`). On a phone it is played sideways (a note says so when held upright).
