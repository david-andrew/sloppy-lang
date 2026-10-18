# Teaching with Sloppy

For a class of students who have not programmed before: how they can run it, programs that ask
questions, an order to teach things in, the mistakes students make, and grading work with
`sloppy test`.

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
4. Loops: `loop i in [1..10]:` (1 to 10), `loop i in [0..n):` (0 to n - 1), `loop condition:`.
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
