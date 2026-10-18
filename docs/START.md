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
sloppy new my_tale story      # a story in lines and choices (a visual novel), its script as Ren'Py's
sloppy new my_duel online     # two players anywhere, no server: invite a friend by a link (rollback)
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

On phones (tick "Mobile friendly" on itch.io, and pick the orientation) games work with
fingers: [Phones](#phones) below says how to lay one out.

Each is one file with nothing to install alongside it (`--target macos` and `--target linux`
make the same from any system too; a Windows build's `.pdb` beside it is for debuggers only, so
leave it out of what you share; Windows warns about a program it has not seen signed before,
"More info", then "Run anyway").
`sloppy build game.jo --target macos -o Game.app` makes a Mac app (its icon, its name in the
Dock and the menu bar); `zip -r Game.zip Game.app` to share it. It is not signed by an Apple
developer account, so a Mac opens a downloaded one after a right click, Open (or System
Settings, Privacy & Security, Open Anyway).

## Phones

The first finger is the mouse, its left button down while it touches, so a game made for the
mouse works as it is; `touches()` has every finger (on-screen buttons: left, right, jump).
`touch_device()` says the screen is a touch screen from the start, `touch_input()` that the last
input was a finger (no hover then). `swipe()` is the way a drag just went (a 2048 move),
`long_press()` a finger held still. `toggle_fullscreen()` from a tap goes fullscreen as the
finger lifts (browsers allow it only then); iPhones' Safari has no fullscreen for a page's
canvas.

**A design size.** For a game held upright, give `window` a phone's shape in points, as
`window("Merge", 360, 640)`: phones are 360 to 430 points wide, and taller than 640, so with the
default `screen_fit(.expand)` the extra height shows; `visible_rect()` is all of it. Lay out from
its edges: a header at its top, the board in the middle, buttons at its bottom. `css_pixel()` is
how large a point (a CSS pixel: about 1/160 inch on a phone) is in your units, so `48 *
css_pixel()` is a button a finger hits on any screen; `pixel_ratio()` is the screen's pixels per
point.

**Held the other way, and on a desktop.** A game made taller than wide shows a note to turn the
phone upright while it is held sideways (`upright_hint(false)` for one laid out for both ways),
and one made wider than tall the other way round (`sideways_hint(false)`). On a desktop browser
the same 360 x 640 column shows in the middle of a wider screen, scaled to its height. A game
laid out for both shapes can change its units as the screen turns: `design_size(w, h)` (or
`window(...)` called again) at the start of `update`:

```gdscript
update = (dt: f64):
    p = pixel_size() / f32(pixel_ratio())       # the screen, in points
    if p.y > p.x: design_size(360, 640) else: design_size(800, 450)
```

Or draw a column designed at 360 x 640 under `camera2d_fit(Rect(0, 0, 360, 640), visible_rect())`:
menus and `hud_` boxes take taps where they show, under any 2D transform.

**The notch and the home bar.** `safe_rect()` is the part of `visible_rect()` that a phone's
notch, rounded corners and home bar leave clear (all of it elsewhere): backgrounds over
`visible_rect()`, buttons and text inside `safe_rect()`. The page around the game takes the color
the game clears the screen with.

**Taps, lists and menus.** Buttons act as the finger lifts, on the button it went down on; a
finger that slides away is no tap, so a drag that starts on a row of a `hud_scroll` list scrolls
the list (it glides on when let go moving) and buys nothing. `ui_` menus on a touch screen draw
each item as a box no wider than the screen (`ui_style.margin` from its edges), with no keyboard
focus marks.

**The keyboard.** A `ui_text_field` or `hud_text_field` tapped brings up the phone's keyboard,
with a Paste button beside what is typed; the page moves up over the keyboard as far as the field
needs (the game keeps its size), and when the player puts the keyboard away the field lets go of
it. `ui_typing()` says a field has the keyboard.

**Trying it on the desktop.** A native run takes a phone's shape and a finger's input:
`SLOPPY_WINDOW=360x800 sloppy run game.jo` opens a phone-shaped window, `SLOPPY_TOUCH=1` makes
it a touch screen (menus as on a phone, the turn-the-phone notes) and `SLOPPY_PIXEL_RATIO=3` its
pixels per point; `SLOPPY_INPUT="5:touch1=180x300 7:touch1-"` taps (in your units), and with
`SLOPPY_SCREENSHOT=out.png SLOPPY_FRAMES=10` saves the frame. In a browser, the developer tools'
device mode shows a phone, its rotation and its touches.

A board and buttons for a phone held either way: the board in the part of the screen the
buttons leave (`camera2d_fit`), a tool picked with a button, then a tap on the board; a tap on a
button is not one on the board (`hud_hovered()`):

```gdscript
tool = 0
update = (dt: f64):
    if mouse_pressed(.left) and not hud_hovered():
        cell = screen_to_world(mouse_pos()) / 64.0          # (the board: cells of 64)
        place(tool, int(cell.x), int(cell.y))
draw = ():
    clear()
    v = visible_rect()
    upright = v.h > v.w
    board = if upright: Rect(v.x, v.y, v.w, v.h - 160) else: Rect(v.x, v.y, v.w - 220, v.h)
    camera2d_fit(Rect(0, 0, COLS * 64, ROWS * 64), board)
    draw_board()
    reset_transform()
    loop i in 0.. and name in ["Gun", "Frost", "Cannon"]:
        r = if upright: Rect(v.x + 20 + f64(i) * 150, v.y + v.h - 140, 140, 120) else: Rect(v.x + v.w - 200, v.y + 20 + f64(i) * 130, 180, 120)
        if hud_button(r, name, selected = tool == i): tool = i
```

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

### Fetching from the web

`net.fetch(url)` (after `import net`) asks a web server for what is at an address and gives an
`HttpReply`: its `status` (200 when all went well, 0 when no reply came, and `why` says why),
`text`, `data` (the same as bytes), `headers` and `size`. JSON goes straight into a struct of
yours with `from_json[T]`, which reads the fields the struct has and skips the others:

```gdscript
import net

struct Repo:
    full_name = ""
    stargazers_count = 0
    description: str? = none          # null in the JSON is none

r = net.fetch("https://api.github.com/repos/python/cpython")
if r.status != 200:
    eprint("no: {r.status} {r.why}")
    exit(1)
repo = from_json[Repo](r.text)
if repo is TextError:
    eprint("not what was expected: {repo.message}")
    exit(1)
print("{repo.full_name}: {repo.stargazers_count} stars, {repo.description ?? "-"}")
```

- `net.fetch(url, method = "POST", headers = {"Authorization": "Bearer {token}"}, body =
  to_json(item))` sends a request of another kind; a body starting with `{` or `[` goes as JSON
  unless a `Content-Type` header says otherwise. `wait = 10.0` gives up sooner than 30 seconds.
- `net.fetch(url, save_to = "big.zip", progress = (got: int, all: int): print("{got} of {all}"))`
  downloads into a file as it comes.
- JSON of any shape: `j = parse_json(r.text)`, then `if j is JsonError: ...`, and
  `j.get("items").at(0).get("name").as_str() ?? ""` (each step gives none when that part is not
  there); `j.as_list()` and `j.keys()` to loop over it. `print(j)` shows it as JSON.
- `url_query({"q": "café au lait", "page": "2"})` makes a query (`q=caf%C3%A9%20au%20lait&page=2`),
  `url_encode(s)` and `url_decode(s)` one part of an address, and `html_unescape(s)` turns
  `&amp;` and `&#233;` back into `&` and `é`.
- Fetches happen one at a time (`parallel_map` cannot run them); a loop over the addresses does.
- `net.fetch` waits for the answer. `f = net.fetch_start(url)` (the same options) starts one and
  goes on; `net.fetch_result(f)` gives the `HttpReply` once it has come (none before): a game asks
  each frame, a server each time round its loop. Several can be on their way at once, and in a web
  page this is the browser's own fetch (the server must allow the page's site: CORS).
- A header sent more than once (`Set-Cookie`): `net.header_values(r, "set-cookie")` has each.

### Writing a server

`import http` serves web pages, an API, or a game's page with its WebSockets, from a native
program. Each route is a method and a path, with `:names` for the parts that vary, answered by a
function from a `Request` to a `Response`:

```gdscript
import http

struct Todo:
    id = 0
    title = ""
    done = false

struct TodoIn:
    title = ""

todos: Todo[]

http.get("/todos", (r: http.Request) -> http.Response: http.json(todos))
http.get("/todos/:id", (r: http.Request) -> http.Response:
    id = to_int(r.params["id"]) ?? -1
    loop t in todos:
        if t.id == id: return http.json(t)
    http.json_error(404, "no todo {id}"))
http.post("/todos", (r: http.Request) -> http.Response:
    t = TodoIn()
    if let bad = http.read_json(r, t): return bad     # 400, saying what is wrong with the JSON
    todos.push(Todo(todos.len() + 1, trim(t.title)))
    http.json(todos.last(), 201))
http.files("/", "public")                             # the rest: the files under public/

http.log_requests = true                              # a line for each, on standard error
if not http.serve(8080): eprint("port 8080 is taken")
on_quit = (): write_file("todos.json", to_json(todos))
```

- A `Request` has `method`, `path`, `params` (the route's `:names`), `query` (`?done=true`),
  `headers` (names in small letters), `cookies`, `body` and `text`, and `address`. Answers are
  `http.text(s)`, `http.html(s)`, `http.json(value)`, `http.binary(bytes, type)`,
  `http.status(404)`, `http.redirect("/login")` and `http.file(r, path)`, with `status`, `headers`
  and `http.set_cookie(res, name, value)` to change. A route of `"/files/*path"` takes the rest of
  the path; a path no route has is answered 404, and one routes have for other methods 405.
- `http.serve` answers until ctrl-c, or the SIGTERM that systemd and docker send, and then returns,
  so the program can save; `on_quit` runs as any program ends, so it is the place for that too.
  Other programs that run until stopped do the same with `loop not stopping(): ...`.
- A client that is slow to send or to read holds up no other, a big file goes a piece at a time
  (a 300 MB one is never in memory), and a handler that panics is answered 500 while the server
  goes on (the panic is on standard error). Bodies over 1 MB are refused (`largest = ...` takes
  more).
- A program that does more than answer (a game hosting, a job that fetches, WebSockets) answers in
  its own loop: `http.listen(8080)`, then `loop not stopping():` with `http.answer()`, its other
  work (`net.receive()`, `net.fetch_result(f)`), and `net.wait(1.0)`, which sleeps until something
  comes, a request or a message, rather than a fixed time.
- WebSockets on the same port: a route answers `http.websocket(r)` (after checking
  `r.headers.get("origin")` or a cookie), and the connection is a peer of `net`'s from then on
  (`net.receive()`, `net.send`, `net.handshake(peer)` for its path and cookies). Server-sent
  events: a route answers `http.events()` and keeps `r.conn`; `http.send_event(conn, text)`
  sends to it later.

**On a server of its own.** Listen on `host = "127.0.0.1"` and put Caddy in front: it gets the
certificate (https) and passes requests on. [Running a matchmaking server](MATCHMAKING.md) sets this
up on a small droplet, with a systemd service that starts the program and restarts it; for a site
of your own the Caddyfile is

```
example.org {
    reverse_proxy 127.0.0.1:8080
}
```

(WebSockets pass through it too.) Behind Caddy, `r.address` is Caddy's; the client's is in
`r.headers.get("x-forwarded-for")`.

**Keeping data.** A small server keeps its data in a JSON file: `to_json`, written to a new file
that then takes the old one's place (`write_file(tmp, text)`, `rename_file(tmp, path)`), so a crash
never leaves half a file; `from_json[T]` reads it back at the start. For more, SQLite (or any C
library) is a few `extern`s away (section 13 of [the language](LANGUAGE.md#13-calling-c)). Each
`extern` names its library with `@lib`; a constant keeps that short:

```gdscript
const SQLITE = "libsqlite3.so.0"
@lib(SQLITE)
extern sqlite3_open = (path: str, db: **u8) -> i32
@lib(SQLITE)
extern sqlite3_exec = (db: *u8, sql: str, cb: *u8, arg: *u8, err: **u8) -> i32

db: *u8 = null
if sqlite3_open("todos.db", &db) != 0: exit(1)
sqlite3_exec(db, "CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY, title TEXT)", null, null, null)
```

(`sqlite3_prepare_v2`, `sqlite3_bind_text` and `sqlite3_step` the same way, for values from
clients: never put them in the SQL text.)

## Coming from Scratch

A Scratch project is sprites, each with its scripts running at once. In Sloppy one program
holds them all: `update` runs every frame (Scratch's "forever" for everything at once) and
`draw` shows what each thing looks like. `sloppy new my_game arcade` is a whole game to start
from.

| Scratch | Sloppy |
|---|---|
| when green flag clicked | the lines at the top of the file run first, once |
| forever | `update = (dt: f64):`, which the game runs every frame (dt: the seconds since the last) |
| a sprite, its x and y | a variable for where it is, `cat = vec2(240, 300)`, and `draw` drawing it there: `sprite(cat_picture, cat)` |
| costumes | a few pictures, `load_texture(embed("cat1.png"))`, and which one is drawn |
| backdrops | a picture drawn first in `draw`, before the sprites |
| when key pressed, key pressed? | `if key_pressed(.space):` (just pressed) or `if key_down(.right):` (held), in `update` |
| change x by 10 | `cat.x += 10` (each frame: `cat.x += 300 * dt` moves 300 a second) |
| go to x: y: | `cat = vec2(100, 200)`; random position: `vec2(random(0, 1280), random(0, 720))` |
| glide 1 secs to | `move = tween(cat, vec2(600, 300), 1.0)`, then `move.update(dt)` and `cat = move.value()` |
| touching? | `overlaps(Rect(...), Rect(...))` or `circles_overlap(a, 20, b, 20)`; touching a color: `img.get(x, y)` of the picture |
| clones | a list of things: `apples: Apple[]`, `apples.push(Apple(pos))`, a `loop mut a in apples:` to move them |
| delete this clone | mark it (`a.gone = true`) in the loop, then `apples.retain((a): not a.gone)` |
| broadcast / when I receive | a function, called where the message would be sent: `level_up()` |
| wait 1 seconds | a timer counted down in `update`, or `Actions`: `steps.then(1.0, (): say_next())` |
| say Hello! for 2 seconds | a variable for what is said and a timer; draw it with `text` beside the sprite |
| ask and wait | `hud_text_field(...)`, a box to type in |
| pick random 1 to 10 | `random_int(1, 11)` (the top is left out), `random(0.0, 1.0)` for a fraction |
| variables, lists | `score = 0` at the top; `names: str[] = []`, `names.push("Ada")` |
| pen | a picture drawn into and never cleared: `pen = render_target(1280, 720)` at the top; in `draw`, `draw_to(pen)`, the line or dot, `draw_to_screen()`, then after `clear`, `draw_target(pen)` |
| sounds | `meow = load_wav(embed("meow.wav"))` at the top, `play(meow)` when it should sound |

## Coming from p5.js, Processing or Shadertoy

| p5 | Sloppy |
|---|---|
| `setup()`, `draw()` | the lines at the top of the file run once; `draw = ():` each frame (and `update = (dt: f64):` before it, to change things) |
| `createCanvas(800, 600)` | `window("title", 800, 600)` |
| `background(20)`, `fill`, `stroke`, `strokeWeight` | `clear(rgb(0.08, 0.08, 0.08))`; each shape takes its color and thickness: `circle(p, 20, RED)`, `line(a, b, 2, WHITE)`, `ring(p, 20, 2, c)` |
| colors 0 to 255, `colorMode(HSB, 360)` | each part 0 to 1: `rgb(1, 0.5, 0)`, `hex(0xff8000)`, `hsv(200.0 / 360.0, 0.8, 0.9)` |
| `ellipse`, `rect`, `line(x1, y1, x2, y2)` | `ellipse(center, radii, c)`, `rect(x, y, w, h, c)`, `line(vec2(x1, y1), vec2(x2, y2), width, c)` |
| `beginShape()`, `vertex(x, y)`, `endShape()` | a list of points: `polygon(pts, c)`, `polyline(pts, width, c)` |
| `push()`, `translate`, `rotate`, `pop()` | `push_transform()`, `translate(x, y)`, `rotate(a)`, `pop_transform()` |
| `mouseX`, `mouseIsPressed`, `keyIsDown(LEFT_ARROW)` | `mouse_pos().x`, `mouse_down(.left)`, `key_down(.left)` |
| `width`, `height`, `frameCount`, `millis()` | `screen_width()`, `screen_height()`, `frame_number()`, `elapsed()` (seconds) |
| `map(x, a, b, c, d)`, `constrain`, `dist`, `lerp` | `remap(x, a, b, c, d)`, `clamp`, `distance`, `lerp` |
| `random(a, b)`, `randomGaussian()`, `noise(x, y, z)` | `random(a, b)`, `random_normal(mean, sd)`, `noise(x)`, `noise(x, y)`, `noise(x, y, z)` (each 0 to 1), `fbm(x, y)` |
| `TWO_PI`, `radians(45)` | `TAU`, `45deg` |
| `background(0, 10)` for trails | each frame starts black: draw into a picture that is kept, `canvas = render_target(1280, 720)` with `draw_to(canvas)`, a see-through `rect` over it, then `draw_to_screen()` and `draw_target(canvas)` |
| `saveCanvas()` | `save_png(screenshot(), "art.png")`, then `download_file("art.png")`: a web page's browser downloads it |
| a Shadertoy shader | a fragment function over a full-screen rect, as below: its `iTime`, `iResolution` and `iMouse` are fields you give it each frame |

```gdscript
struct Toy:
    time: f32
    res: vec2
toy_fs = (p: Pixel2D, u: Effect2D[Toy]) -> vec4:
    uv = p.pos.xy / u.params.res                  # 0 to 1, from the bottom left
    t = u.params.time
    vec4(cos(vec3(t, t, t) + vec3(uv.x, uv.y, uv.x) * 6.0 + vec3(0, 2, 4)) * 0.5 + vec3(0.5, 0.5, 0.5), 1)
toy = make_shader(shader(effect_vs, toy_fs))

draw = ():
    use_effect(toy, Toy(f32(elapsed()), pixel_size()))
    rect(0, 0, 1280, 720, WHITE)
    no_effect()
```

Shader functions are Sloppy functions, and the GPU runs them (the CPU too, without one): GLSL's
`sin`, `cos`, `fract`, `floor`, `pow`, `step`, `smoothstep`, `mix`, `abs`, `min` and `max` work on
vectors' parts as there; `post_effects()` adds bloom and a vignette to 2D drawing as well as 3D.

## Coming from JavaScript

| JavaScript | Sloppy |
|---|---|
| `let x = 0` | `x = 0` (whole numbers stay whole: `x = 0.0` for one that holds fractions) |
| `for (let i = 0; i < n; i++)`, `while (x > 0)` | `loop i in 0..n:` (0 to n - 1), `loop x > 0:` |
| `const xs = [1, 2]` then `xs.push(3)` | `xs = [1, 2]`: a const never changes, its elements neither |
| objects `{name: "Drone", cost: 10}` | `struct Item:` with `name: str` and `cost: f64`, made as `Item("Drone", 10)`; a map's values are all one type |
| `` `cost: ${x}` ``, `x.toFixed(2)`, `toLocaleString()` | `"cost: {x}"`, `"{x:.2f}"`, `"{x:,}"`; `"{x:.2e}"` for 1.50e+45 |
| `===`, `null`, `undefined` | `==`, `none` (a `T?` may be none: `x ?? default`, `if let v = x:`) |
| `x?.y` | `(x ?? default).y`, or `if let v = x: v.y` (`x?.y` is not optional chaining: `x?` returns the none from the function) |
| `try`/`catch`, `throw` | a function gives back what went wrong as a value (`-> Item \| LoadError`, with `error struct LoadError:`); the caller checks `if r is LoadError:`, or passes it on with `item = load(p)?` |
| `xs.map(f)`, `filter`, `reduce((a, b) => a + b, 0)` | `xs.map(f)`, `xs.filter(f)`, `xs.reduce(0, (a, b): a + b)`, `sum(xs)` |
| `JSON.stringify`, `JSON.parse` | `to_json(x)`, `from_json[Item](s)` (into a struct), `parse_json(s)` |
| `localStorage` | `save_value("save", state)` and `state = load_value("save", State())` |
| `setInterval(f, 30000)`, `setTimeout` | `if every(1, 30.0): f()` in update; `Actions` for steps one after another |
| `Date.now()` | `unix_time()` (seconds since 1970: what to save to work out time away) |
| Phaser's `this.tweens.add({...})`, `onComplete` | `t = tween(from, to, 0.3, ease = ease_out_back)` in a variable or field; each frame `t.update(dt)`, `t.value()`, and `t.done()` for what comes next |
| a timeline / tween chain | `hop = chain([tween(a, b, 0.2), tween(b, a, 0.3)])`: one after another, `hop.value()`, `hop.done()`; `done(tweens)` for a set started together |
| scenes, `this.scene.start("Level")` | `enum Screen: title, play, over`, `screen = .play`, and a `match screen:` in update and in draw |
| `async`/`await`, a chain of animations | a phase for each step (`enum Phase: idle, swapping, clearing, falling`), moved on in update when its tweens are done; or `Actions` for timed steps |
| `btoa`, `atob` | `base64_encode(bytes(s))`, `base64_decode(s)` |
| `window.onbeforeunload` | `on_quit = (): ...`, which the game calls as it closes |
| `Number.isFinite`, `Infinity`, break_infinity.js | `is_finite(x)`, `INF` (floats reach about 1.8e308); past that, `use big`: `dust = big(1.5, 400)` |

## Coming from Python

| Python | Sloppy |
|---|---|
| `def f(a, b):` | `f = (a: int, b: int) -> int: ...` |
| `for i in range(n):`, `range(1, n + 1)`, `xs[2:5]` | `loop i in 0..n:`, `loop i in [1..n]:` (`]` keeps the end), `xs[2..5]` |
| `while x > 0:` | `loop x > 0:` |
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
| `requests.get(url)`, `urllib.request.urlopen(url)` | `import net`, then `r = net.fetch(url)`: `r.status`, `r.text`, and `from_json[T](r.text)` ([fetching from the web](#fetching-from-the-web)) |
| `requests.post(url, json=d, headers=h)` | `net.fetch(url, method = "POST", body = to_json(d), headers = h)` |
| `urllib.parse.quote(s)`, `urlencode(d)`, `html.unescape(s)` | `url_encode(s)`, `url_query(d)`, `html_unescape(s)` |
| `s[:4]`, `f"{s:.4}"` | `first(s, 4)` or `"{s:.4}"` (characters; `s[..4]` counts bytes, and can cut an `é` in two) |
| `re.search(r"\d+", s)` | `s.find(regex(r"\d+"))` (a `Match?`: `m.text`, `m.groups`) |
| `Counter(ws)`, `defaultdict(list)` | a map: a missing key starts at zero when changed (`counts[w] += 1`, `groups[k].push(x)`); reading one, `m[k]`, is an error: `m.get(k) ?? 0` |
| `set()` | a map to `bool`, or `unique(xs)` |
| `None`, `if x is None:` | `none`, `if x == none:`; `if let v = x:` gets what is inside |
| `t[0]` (a tuple) | `t.0` |
| `x = 1` in a function makes a local | `x = 1` in a function changes a global named `x` (one declared above it); `let x = 1` makes a local of that name |
| `max(xs, key=len)`, `sorted(xs, key=...)` | `max_by(xs, (x): len(x))`, `sorted_by(xs, (x): x.age)` |
| `try: ... except: ...` | a function gives back what went wrong as a value (`-> Config \| JsonError`), checked with `if r is JsonError:`, or passed on to the caller with `?` (`cfg = load(p)?`) |
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
