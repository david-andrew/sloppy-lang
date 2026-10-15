# Getting started

## Install

<!-- install -->
On **Linux** (x86-64 or arm64) or **macOS** (Apple Silicon), in a terminal:

```sh
curl -fsSL https://sloppy-lang.org/install | bash
```

On **Windows** (10 or 11, x64), in PowerShell:

```powershell
irm https://sloppy-lang.org/install.ps1 | iex
```
<!-- /install -->

The installer puts Sloppy in your home directory (`~/.sloppy`, or `%LOCALAPPDATA%\sloppy` on
Windows) and the `sloppy` command on your PATH, ready in the same terminal (when `~/.local/bin`
is on your PATH, as on most Linux systems; if not, the installer shows the line that makes it
so). Nothing else is needed: no C compiler, no linker, no SDK or Xcode. `sloppy update` installs newer releases.

On a phone, or an Intel Mac, Sloppy's programs run in any browser: write and run them in
[the playground](https://sloppy-lang.org/playground/).

## A first program

Save this as `hello.jo`:

```gdscript
print("hello, world")

coins = 3
price = 1.5
print("{coins} coins at {price} each cost {coins * price}")

loop i in [1..4]:
    print("round {i}")
```

and run it:

```sh
sloppy hello.jo
```

(`sloppy run hello.jo` is the same.) Each run compiles the whole program, in a few milliseconds, and runs it. `sloppy` alone is an
interactive prompt, for trying things a line at a time.

A name is given a value with `=`, and `{...}` inside text puts a value there. `loop i in [1..4]:`
runs the indented line once for each number from 1 to 4.

New to programming? [Make a game](TUTORIAL.md) starts from an empty window and explains each
thing as it comes up; the rest of the documentation is written for people who have programmed
before.

## A first game

A program with `update` and `draw` functions is a game: it opens a window and calls them every
frame, `update` with the seconds since the last frame.

```gdscript
pos = vec2(400, 300)

update = (dt: f64):
    pos += input_axis() * 300 * dt

draw = ():
    clear(rgb(0.08, 0.08, 0.12))
    circle(pos, 24, rgb(1.0, 0.6, 0.2))
    text("arrow keys or W A S D", vec2(20, 20), 24, WHITE)
```

Save it as `game.jo`, then:

```sh
sloppy game.jo           # in a window
sloppy watch game.jo     # the same, reloaded each time you save: change a color and look
sloppy --web game.jo     # in your browser
```

## Starting from a template

`sloppy new` makes a directory with a program to start from, which runs as it is:

```sh
sloppy new my_game            # the smallest game: a window, update and draw
sloppy new my_game arcade     # a 2D arcade game: a title menu, a score, a best score kept, sounds
sloppy new my_game platformer # a 2D platformer: a level written as text, slopes, platforms, coins
sloppy new my_game 3d         # a first-person 3D game: mouse look, walking, jumping, shooting
sloppy new my_tool program    # a program for the terminal, with a test
sloppy watch my_game/my_game.jo
```

## Sharing it

```sh
sloppy build game.jo                       # game (game.exe on Windows): a program for this system
sloppy build game.jo --target windows      # game.exe, from any system
sloppy build game.jo --target wasm         # game.html: one file that runs in any browser
sloppy build game.jo --target wasm -o game.zip   # the same, ready for itch.io
```

On itch.io: make a project of kind HTML, upload `game.zip`, tick "This file will be played in
the browser", and give the viewport the size of your `window(...)` (1280 x 720 if it has none);
"Fullscreen button" lets players make it bigger. Give the game a name in its build block
(`build:` and `name = "Drone Arena"` below it): what `save_data` keeps is stored under it, and
games on one site share the browser's storage (it is the browser's localStorage, as
`sloppy:<name>/<key>`). Sound starts after the player's first click, tap or key, as browsers
require, and stops while the tab is hidden (the game gets no frames then). A file the game
reads is built in with `embed("x.png")` or `embed_dir("assets")`: a page has no disk. Debug
builds are the smaller ones; `--release` makes the code faster and larger.

Pause when `window_focused()` is false: the player clicked outside the page's frame (`sloppy
new` makes games that do). The page takes the keyboard as it loads.

On phones (tick "Mobile friendly" on itch.io, and pick the orientation): the first finger is the
mouse, its left button down while it touches, so a game made for the mouse works as it is;
`touches()` has every finger (on-screen buttons: left, right, jump), and `touch_input()` says
the last input was a finger (no hover then). `screen_fit(.expand)` and `visible_rect()` lay
the game out for any shape of screen. `toggle_fullscreen()` from a tap goes fullscreen as the
finger lifts (browsers allow it only then); iPhones' Safari has no fullscreen for a page's
canvas.

Each is one file with nothing to install alongside it (`--target macos` and `--target linux`
make the same from any system too; a Windows build's `.pdb` beside it is for debuggers only, so
leave it out of what you share; Windows warns about a program it has not seen signed before,
"More info", then "Run anyway").
`sloppy build game.jo --target macos -o Game.app` makes a Mac app (its icon, its name in the
Dock and the menu bar); `zip -r Game.zip Game.app` to share it. It is not signed by an Apple
developer account, so a Mac opens a downloaded one after a right click, Open (or System
Settings, Privacy & Security, Open Anyway).

## Editors

The [Sloppy extension](https://marketplace.visualstudio.com/items?itemName=RedFoxLabs.sloppy)
for VS Code, Cursor and VSCodium (also [on Open VSX](https://open-vsx.org/extension/RedFoxLabs/sloppy))
has highlighting, errors as you type, completion, hover, go to definition and rename, and
commands to run a file:

```sh
code --install-extension RedFoxLabs.sloppy
```

For other editors, `sloppy lsp` is a language server: the
[README](https://github.com/david-andrew/sloppy-lang#editors) shows Neovim and Helix.

## Scripts and tools

Sloppy is for programs without a window too: `sloppy new my_tool program` makes a command-line
program with a test to start from, and `sloppy my_tool.jo a b` runs it with `args()` being
`["my_tool.jo", "a", "b"]`. A function named `main` runs after the top-level code (or where
the file calls it).

```gdscript
#!/usr/bin/env sloppy
# count.jo: lines and words in files, largest first

struct Options:
    words = false               # --words, or -w: count words too
    top = 0                     # --top 5: only the largest five (0: all)
    files: str[]                # the arguments that are not options

main = () -> int:
    opts = parse_args[Options]("lines (and words) in files, largest first")
    if opts.files.len() == 0:
        eprint("count.jo: which files? (count.jo --help)")
        return 2                                  # main's int is the exit code
    rows: (str, int, int)[]
    loop path in opts.files:
        if let f = open_file(path):               # line by line: any size of file
            n_lines = 0
            n_words = 0
            loop let line = f.read_line():
                n_lines += 1
                if opts.words: n_words += words(line).len()
            f.close()
            rows.push((path, n_lines, n_words))
        else: eprint("count.jo: cannot read {path}")
    rows.sort_by((r): r.1, descending = true)
    if opts.top > 0 and rows.len() > opts.top: rows.resize(opts.top)
    loop r in rows:
        if opts.words: print("{r.0:<30} {r.1:>8} {r.2:>8}")
        else: print("{r.0:<30} {r.1:>8}")
    0
```

With the first line `#!/usr/bin/env sloppy` and `chmod +x count.jo`, it runs as
`./count.jo -w --top 3 *.txt` (on Linux and macOS). Everything after the file's name goes to the
script, `--release` too; `args()[0]` is the script's own path (`exe_path()` is where its build
is kept). `parse_args` reads the options into the struct: a `bool` field is a flag, others take
a value, the last list field gets the other arguments, and `--help` lists them all; a mistake
(`--top many`) is said with that help, and exit code 2.

- `run_program("make", ["-j8"], show = true)` shows a program's output as it runs;
  without `show`, it is returned as text. `cwd = "build"` runs it in another directory.
- A file function that fails gives `none` or `false`, and `file_error()` says why ("permission
  denied", "no such file or directory"): `if not write_file(p, s): eprint("{p}: {file_error()}")`.
- `sha256(read_bytes(path) ?? [])` fingerprints a file; `glob("**/*.log")` finds files (hidden
  ones, .git's, only with a pattern that names them).
- Text widths in `"{name:<12}"` and `pad_end` count characters, so "Zürich" lines up with "Paris";
  `upper` and `lower` know accented Latin, Greek and Cyrillic letters. `r"""..."""` is text over
  several lines with no `{}` interpolation and no `\` escapes (help text with `{name}` in it).
- `sloppy test count.jo` runs its `test` blocks; `sloppy test count.jo sort` only those with
  "sort" in their names.

## Coming from Python

| Python | Sloppy |
|---|---|
| `def f(a, b):` | `f = (a: int, b: int) -> int: ...` |
| `[w.upper() for w in ws if w]` | `[loop w in ws: if w != "": w.upper()]` |
| `f"{x:.2f}"`, `"{:.2f}".format(x)` | `"{x:.2f}"`: every string puts values in; `r"..."` does not (a regular expression's `{4}`) |
| `7 // 2`, `7 / 2` | `7 / 2` is 3 with whole numbers (`-7 / 2` is -3, and `-7 % 3` is -1, as in C); `7.0 / 2` is 3.5 |
| `with open(p) as f: f.read()` | `read_file(p)` (a `str?`: none when it cannot be read), `write_file`, `append_file`, `read_bytes` |
| `sys.argv`, `sys.exit(1)` | `args()`, `exit(1)` |
| `argparse` | a struct of the options, `opts = parse_args[Options]("what it does")` |
| `os.path.join`, `os.listdir`, `os.walk`, `glob.glob` | `join_path`, `list_dir`, `walk_dir`, `glob("src/**/*.jo")`; `make_dirs`, `rename_file`, `copy_file`, `delete_file`, `file_time` |
| `subprocess.run(["ls", "-l"])`, `os.system("ls *.jo")` | `run_program("ls", ["-l"])`, `run_shell("ls *.jo")` (each gives its exit code and output; `show = true`: the output shows as it runs) |
| `for line in open(p):` | `if let f = open_file(p):` then `loop let line = f.read_line():` (a file of any size) |
| `hashlib.sha256(b).hexdigest()` | `sha256(b)` (bytes or text) |
| `json.loads(s)`, `json.dumps(x)` | `parse_json(s)` (a Json), `from_json[Config](s)` (into a struct), `to_json(x)` |
| `re.search(r"\d+", s)` | `s.find(regex(r"\d+"))` (a `Match?`: `m.text`, `m.groups`) |
| `Counter(ws)`, `defaultdict(list)` | a map: a missing key starts at zero when changed (`counts[w] += 1`, `groups[k].push(x)`); reading one, `m[k]`, is an error: `m.get(k) ?? 0` |
| `set()` | a map to `bool`, or `unique(xs)` |
| `None`, `if x is None:` | `none`, `if x == none:`; `if let v = x:` gets what is inside |
| `t[0]` (a tuple) | `t.0` |
| `x = 1` in a function makes a local | `x = 1` in a function changes a global named `x` (one declared above it); `let x = 1` makes a local of that name |
| `max(xs, key=len)`, `sorted(xs, key=...)` | `max_by(xs, (x): len(x))`, `sorted_by(xs, (x): x.age)` |
| `try: ... except: ...` | a function gives back what went wrong as a value (`-> Config \| JsonError`), checked with `if r is JsonError:` |
| `def test_x(): assert ...` (pytest) | `test "x": assert(...)`, run with `sloppy test file.jo` |
| big integers | `int` is 64 bits and wraps around |

## Coming from pandas and matplotlib

| pandas / NumPy / matplotlib | Sloppy |
|---|---|
| `pd.read_csv("sales.csv")` | `sales = from_csv[Sale](read_file("sales.csv") ?? "")`: a struct per row, its fields by the header's names (or `csv_rows(text)`: rows of text) |
| `df["price"]`, `df[df.price > 10]` | `[loop s in sales: s.price]`, `sales.filter((s): s.price > 10.0)`; a `soa Sale[]` keeps each field as an array: `t.price`, `t[t.price .> 10.0]` |
| `df.groupby("region").price.mean()` | `group_by(sales, (s): s.region)`, then `mean(...)` of each group's prices; or a map: `totals[s.region] += s.price` |
| `.dropna()`, `.fillna(0)`, `~mask` | `xs[not is_nan.(xs)]`, `x ?? 0.0` for an optional, `not mask` |
| `np.mean`, `np.median`, `np.std`, `np.percentile` | `mean`, `median`, `std_dev`, `percentile(xs, 90.0)`, `histogram`, `correlation`, `cumsum` |
| `np.linalg.solve(A, b)`, `A @ B` | `solve(A, b)`, `A * B` (on `f64[,]` matrices) |
| `plt.plot(...)`, `plt.savefig("c.png")` | `img = render_image(800, 500, (): ...lines, rects, text...)`, then `save_png(img, "c.png")` (no window needed) |
| `df.to_csv(...)`, `json.dump(...)` | `to_csv(rows)`, `to_json(value)` |

## Coming from Unity or Godot

| There | Here |
|---|---|
| a GameObject with components, a scene tree | a struct for each kind of thing, kept in arrays; `update` and `draw` go through them |
| a prefab | a function that makes the struct (`spawn_enemy(pos) -> Enemy`) |
| methods, `this` | functions taking the thing first: `e.hit(5)` calls `hit(e, 5)`; `mut` lets one change it |
| inheritance | a struct holding another (`base: Body`), or a union of kinds (`type Enemy = Walker \| Flyer`) with `match` |
| coroutines, `yield` | a timer in a field, counted down each frame (`e.wait -= dt`) |
| `OnTriggerEnter`, events | look each frame (`w.contacts()`, a distance check) and act |
| `Time.timeScale`, pausing | the game's own clock: add `dt` only while not paused |
| the Animator | `pose_at` for a clip at a time, `blend_poses` to mix two, the time and weights kept in the struct |
| the inspector | `print(x)` shows any value, and `sloppy watch` reloads the code as it changes |
| `Time.deltaTime` | `dt`, what `update = (dt: f64):` is given |
| `Input.GetKey(KeyCode.W)`, `GetKeyDown`, `GetAxis` | `key_down(.w)`, `key_pressed(.space)`, `input_axis()` |
| `Mathf.Clamp`, `Mathf.Sin`, `Debug.Log` | plain functions: `clamp`, `sin`, `lerp`, `PI`; `print` |
| `Instantiate`, `Destroy` | a function that makes the struct, pushed onto its array; `xs.remove(i)` or `xs.retain(...)` |
| `List<T>`, `Dictionary<K, V>`, `null` | `T[]`, `{K: V}`, `none` (a `T?` may be none: `if let v = x:`) |
| `Rigidbody`, `Physics.Raycast`, a CharacterController | `import physics3d`: `w.add_sphere(...)`, `w.raycast(a, b)`, `w.character(...)` and `w.walk(...)` |
| `Quaternion.Euler(0, 45, 0)`, `LookRotation` | `quat_euler(0, 45deg, 0)`, `facing(dir)`; or matrices: `rotation_y(45deg)` (angles are radians: `45deg` is 45 degrees) |
| `q1 * q2`, `q * v` | `quat_mul(q1, q2)`, `quat_rotate(q, v)` (quaternions are vec4s: `*` multiplies their parts one by one) |
| `transform.forward` | a model's front is +z (glTF's), turned as it is: `transform_dir(m, vec3(0, 0, 1))`; a camera looks along -z |
| Cinemachine, a third-person camera | `cam = follow_camera()`, then `update(cam, player_pos, dt)` and `camera3d(cam)`; walk along `flat_forward(cam)` |

## Where next

- [Make a game](TUTORIAL.md): a small platformer, built step by step. Then
  [an arcade game](TUTORIAL_REBOUND.md) and [a 3D shooter](TUTORIAL_BREAKWATER.md).
- [The language](LANGUAGE.md): everything Sloppy has, with examples.
- [Teaching with Sloppy](TEACHING.md): for a class, an order to teach things in, and grading.
- [The library](API.md): windows, input, drawing in 2D and 3D, sound, files and the rest.
- [The playground](https://sloppy-lang.org/playground/) has more examples, including two
  complete games.
- Building Sloppy from source, and working on the compiler: the
  [README](https://github.com/david-andrew/sloppy-lang#getting-started).
