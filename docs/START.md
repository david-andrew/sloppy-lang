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
so). Nothing else is needed: no C compiler, no linker, no SDK or Xcode. `sloppy upgrade` installs newer releases.

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

On Windows, an editor makes this simplest: VS Code with the [Sloppy
extension](https://marketplace.visualstudio.com/items?itemName=RedFoxLabs.sloppy) runs the open
file with the run button at the top right, or Ctrl+F5. With Notepad, choose "All files" under "Save as type" (or it saves `hello.jo.txt`),
and keep the encoding UTF-8; then in Explorer, right-click the folder and pick "Open in Terminal"
to type the command there. PowerShell's `>` and `Out-File` write UTF-16, which Sloppy does not
read as a program: save files from an editor, or with `Set-Content -Encoding utf8`.

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
sloppy new my_list tui        # a program for the whole terminal: a list of things to do (keys, the mouse)
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
`sloppy:<name>/<key>`, the bytes in base64). Sound starts after the player's first click, tap or key, as browsers
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
mouse works as it is; `touches()` has every finger (on-screen buttons: left, right, jump), and
`touch_ids()` a number for each that stays the same while it is down (a drag that turns a camera:
how far that finger moved since the last frame).
`touch_device()` says the screen is a touch screen from the start, `touch_input()` that the last
input was a finger (no hover then). `swipe()` is the way a drag just went (a 2048 move),
`long_press()` a finger held still. `toggle_fullscreen()` from a tap goes fullscreen as the
finger lifts (browsers allow it only then); iPhones' Safari has no fullscreen for a page's
canvas (`can_fullscreen()` says so).

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
    words = false               # count words too
    top = 0                     # only the largest n (0: all)
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
a value, the last list field gets the other arguments, and `--help` lists them all, each beside
its field's comment (`-w, --words   count words too`: the comment need not name the option); a
mistake (`--top many`) is said with that help, and exit code 2.

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

A program can also take the whole terminal, as a screen of characters it draws on (a file
browser, an editor, a game in the terminal): `import term`, `term.start()`, then `term.put(x, y,
text, fg = term.YELLOW)`, `term.box(...)` and `term.flush()`, which writes only what changed, and
`term.read_event()` for keys, the mouse and resizes. The terminal is put back as it was however
the program ends. `sloppy new my_list tui` starts one; [terminal
programs](LANGUAGE.md#terminal-programs) says the rest, and
[examples/files.jo](https://github.com/david-andrew/sloppy-lang/blob/master/examples/files.jo) is
a file browser.

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

- A JSON name that is a keyword (`"when"`, `"in"`) is a field with `_` after it: `when_ = ""`
  reads `"when"`, and `to_json` writes it so.
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
- `url_join(page, href)` is where a link on a page leads (`../c.html` from
  `https://example.com/a/b/x.html` is `https://example.com/a/c.html`), and `parse_url(s)` takes
  an address apart: `u.scheme`, `u.host`, `u.port` (-1 when not written), `u.path`, `u.query`,
  `u.fragment`, or a `UrlError`; `str(u)` puts it back together.
- Many at once: `net.fetch_all(urls, at_once = 8)` gives their answers in the order of `urls`,
  with at most 8 on their way at a time (Go's worker pool, an errgroup with a limit). One that
  failed, or found the server busy (429, 503...), is asked again, `retries = 2` more times, half a
  second later, then a second...; `done = (i: int, r: net.HttpReply): ...` sees each answer as it
  comes. (`parallel_map` does not run fetches: it shares out work for the processor's cores, and
  a fetch is waiting.)

  ```gdscript
  import net

  urls = [loop id in [1..50]: "https://api.example.com/items/{id}"]
  rs = net.fetch_all(urls, at_once = 8, wait = 10.0)
  loop i in 0.. and r in rs:
      if r.status != 200: eprint("{urls[i]}: {r.status} {r.why}")
  ```
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
- `http.serve` answers until ctrl-c, or the SIGTERM that systemd and docker send, then stops
  taking requests, gives the handlers still running up to 10 seconds to answer (`drain = ...`),
  and returns, so the program can end its own tasks and save; `on_quit` runs as any program ends,
  so it is the place for that too. Other programs that run until stopped do the same with
  `loop not stopping(): ...` (and `http.shutdown()` in their own loop).
- A client that is slow to send or to read holds up no other, a big file goes a piece at a time
  (a 300 MB one is never in memory), and a handler that panics is answered 500 while the server
  goes on (the panic is on standard error). Bodies over 1 MB are refused (`largest = ...` takes
  more).
- Each request's handler runs as a [task](LANGUAGE.md#tasks-and-channels): one that waits (a
  `net.fetch`, `sleep`, a channel) lets the others be answered meanwhile. Tasks take turns on the
  program's one thread, so handlers change its variables (`todos` above) with no locks: between
  two waits nothing else runs. One that computes for long, or runs a program, or reads a big
  file, holds up the others while it does.
- `http.read_json(r, t)` sets the fields the body has and keeps the others as they were, so a
  PATCH is `t = todos[i]`, `if let bad = http.read_json(r, t): return bad`, `todos[i] = t`; a body
  that does not read leaves `t` as it was.
- A program that does more than answer (a game hosting, a job that fetches, WebSockets) answers in
  its own loop: `http.listen(8080)`, then `loop not stopping():` with `http.answer()`, its other
  work (`net.receive()`, `net.fetch_result(f)`), and `net.wait(1.0)`, which sleeps until something
  comes, a request or a message, rather than a fixed time.
- To try the server from the same program (a test), listen, serve in a task, then fetch from it:

  ```gdscript
  http.listen(8080, host = "127.0.0.1")
  spawn((): http.serve(8080), background = true)     # (the program's end does not wait for it)
  r = net.fetch("http://127.0.0.1:8080/todos")       # answered meanwhile
  assert(r.status == 200)
  ```
- WebSockets on the same port: a route answers `http.websocket(r)` (after checking
  `r.headers.get("origin")` or a cookie), and the connection is a peer of `net`'s from then on
  (`net.receive()`, `net.send`, `net.handshake(peer)` for its path and cookies). A task for each:
  `p = net.accept(wait = 1.0)` gives the next one, and that task waits for its own with
  `net.receive([p], wait = 30.0)`. A task reads only its own peer's socket, so this costs no more
  than one loop over `net.receive_server()`: an echo server with 200 clients sending 20 messages
  a second each takes about a fifth of a core either way. `net.close(p, 4001, "the room is full")`
  sends a code and a reason, which the other side's `.left` event has (`e.code`, `e.text`) and a
  browser's WebSocket its close event (`event.code`, `event.reason`); 4000-4999 are the
  program's own. Rooms, as Socket.IO's: `net.join_room(p, "match-7")`,
  `net.send_room("match-7", text)`, `net.members("match-7")`; a peer that leaves leaves its rooms.
  Server-sent events: a route answers `http.events()` and keeps `r.conn`; `http.send_event(conn,
  text)` sends to it later.
- Around the routes: `http.before((r: mut http.Request) -> http.Response?: ...)` sees each request
  first, and answers it itself (a sign-in missing, a rate limit: `http.json_error(429, ...)`) or
  gives `none` to let it go on, maybe with `r.params["user"]` set for the handlers;
  `http.after((r: http.Request, res: http.Response) -> http.Response: ...)` sees each answer
  (headers to add, a log). `http.cors(["https://example.com"])` lets those sites' pages read the
  answers (`http.cors()`: any site), and answers the browser's preflight `OPTIONS` before any
  `before`. Answers of text, JSON, JavaScript and wasm of 1 KB or more go gzip'd to browsers
  (files once per change); `http.gzip = false` turns that off.
- Passwords: `crypto.hash_password(pw)` gives text to store (PBKDF2-SHA256, a salt of its own),
  and `crypto.check_password(pw, stored)` says whether a password is it. A token or a signature a
  client sent is compared with `crypto.constant_time_equal(a, b)`, which takes as long wherever
  they differ.
- A health check for a load balancer or a monitor is a route of its own:
  `http.get("/health", (r: http.Request) -> http.Response: http.text("ok"))` (answered at once by
  a server that is running: one that also checks what it needs, its database file, answers
  `http.status(503)` when that fails).

**On a server of its own.** Listen on `host = "127.0.0.1"` and put Caddy in front: it gets the
certificate (https) and passes requests on. [Running a matchmaking server](MATCHMAKING.md) sets this
up on a small droplet, with a systemd service that starts the program and restarts it; for a site
of your own the Caddyfile is

```
example.org {
    reverse_proxy 127.0.0.1:8080
}
```

(WebSockets pass through it too; `encode gzip` on a line of its own in the block has Caddy gzip
what the program does not, and leaves what it did.) Behind Caddy, `r.address` (and
`net.handshake(p).address` for a WebSocket) is Caddy's, 127.0.0.1; the client's is the last
address in `r.headers.get("x-forwarded-for")`, which Caddy adds. Trust that header only from the
proxy: a server that listens on every address lets anyone send one saying anything, so listen on
`host = "127.0.0.1"`, or take the header only when `r.address == "127.0.0.1"`.

A systemd service for it, `/etc/systemd/system/todos.service`:

```
[Unit]
Description=todos
After=network-online.target

[Service]
User=todos
WorkingDirectory=/srv/todos
ExecStart=/srv/todos/todos
Restart=always
RestartSec=2
MemoryMax=512M

[Install]
WantedBy=multi-user.target
```

`WorkingDirectory` matters: `http.files("/", "public")`, `read_file("todos.json")` and the like
are relative to it (without it, to `/`). `MemoryMax` has systemd stop a program that grows past
it (and `Restart` start it again), rather than the machine running out. `systemctl stop` sends SIGTERM, which `http.serve` answers by
finishing what it is answering (up to `drain` seconds) and returning.

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
| `switch (s.kind)`, `case "rect":` on a tagged union | `enum Shape:` with `circle(r: f64)` and `rect(w: f64, h: f64)`; `match s:` with `.rect(w, h):` (and a condition: `.rect(w, h) if w == h:`), `if s is .rect:`, `if let .rect(w, h) = s:` |
| scenes, `this.scene.start("Level")` | `enum Screen: title, play, over`, `screen = .play`, and a `match screen:` in update and in draw |
| `async`/`await`, a chain of animations | a phase for each step (`enum Phase: idle, swapping, clearing, falling`), moved on in update when its tweens are done; or `Actions` for timed steps |
| `btoa`, `atob` | `base64_encode(bytes(s))`, `base64_decode(s)` |
| Express: `app.get("/todos/:id", ...)`, `app.listen(8080)` | `http.get("/todos/:id", handler)`, `http.serve(8080)` ([writing a server](#writing-a-server)) |
| Express middleware, `cors()`, `compression()` | `http.before(f)` (may answer early: a sign-in, a rate limit) and `http.after(f)`; `http.cors(["https://example.com"])`; gzip is on (`http.gzip = false`) |
| Socket.IO: `io.on("connection")`, `socket.join(room)`, `io.to(room).emit(...)` | `http.websocket(r)` in a route, then `net.accept` and `net.receive([p], wait = 30.0)` in a task for each (or one loop over `net.receive_server()`); `net.join_room(p, room)`, `net.send_room(room, text, except = p)`, `net.members(room)` |
| `socket.disconnect()`, a close code | `net.close(p, 4001, "the room is full")`: the other side's `.left` event has `e.code` and `e.text`, a page's WebSocket `event.code` and `event.reason` |
| Socket.IO's reconnection | a netplay client's `c.reconnect = true` (1, 2, 4... up to 30 s between tries); with net alone, `net.connect` again when `.left` comes |
| `bcrypt.hash`, `crypto.timingSafeEqual` | `crypto.hash_password(pw)`, `crypto.check_password(pw, stored)`, `crypto.constant_time_equal(a, b)` |
| JSON keys that are keywords (`{"when": ...}`) | a field named `when_`: `to_json` and `from_json` call it `"when"` |
| `window.onbeforeunload` | `on_quit = (): ...`, which the game calls as it closes |
| `<input type="file">`, Electron's `dialog.showOpenDialog`, a drop zone | `d = open_file_dialog([".txt"])`, then `if let paths = file_dialog_result(d):` each frame; `dropped_files()` |
| CSS `cursor: pointer`, `cursor: col-resize` | `set_cursor(.hand)`, `set_cursor(.resize_ew)` |
| a page that redraws only as things change | `redraw_on_input()`: frames only on input; `request_redraw()` while something animates |
| `Number.isFinite`, `Infinity`, break_infinity.js | `is_finite(x)`, `INF` (floats reach about 1.8e308); past that, `use big`: `dust = big(1.5, 400)` |

## Coming from React or Electron: desktop tools

A tool is a program like a game: `draw` runs each frame and draws its boxes, each of which says
what was done to it. There is no tree of components to keep in step with the data: the data is
drawn as it is, every frame. Three lines make a window behave as a desktop program's:
`screen_fit(.native)` (units are the desktop's pixels, and a wider window shows more, laid out
from `visible_rect()`), `redraw_on_input()` (frames only when something happens, so an idle tool
takes no CPU) and `on_quit` to save.

```gdscript
struct Note:
    title: str
    body: str

window("Notes", 900, 600)
screen_fit(.native)
redraw_on_input()
notes = load_value("notes", [Note("First", "")])
at = 0
query = ""

on_quit = (): save_value("notes", notes)

draw = ():
    global at, query
    clear(rgb(0.11, 0.12, 0.14))
    if shortcut(.n):
        notes.push(Note("Untitled", ""))
        at = notes.len() - 1
    if shortcut(.f): hud_focus("search")
    v = visible_rect()
    query = hud_text_field(Rect(10, 10, 220, 30), query, id = "search", hint = "Search")
    y = 50.0
    loop i in 0.. and n in notes:
        if len(query) > 0 and find(lower(n.title), lower(query)) < 0: continue
        if hud_button(Rect(10, y, 220, 32), n.title, selected = i == at, align = .left): at = i
        y += 36.0
    notes[at].title = hud_text_field(Rect(240, 10, v.w - 250, 30), notes[at].title, id = "title")
    notes[at].body = hud_text_area(Rect(240, 50, v.w - 250, v.h - 60), notes[at].body, id = "body")
```

| React / Electron | Sloppy |
|---|---|
| `useState`, props, re-rendering | plain variables; `draw` shows them as they are each frame |
| `<input value onChange>`, `<textarea>` | `name = hud_text_field(r, name)`, `body = hud_text_area(r, body)` |
| `<button onClick>`, a checkbox, a range input | `if hud_button(r, "Save"): save()`, `on = hud_checkbox(r, "Sound", on)`, `v = hud_slider(r, v, 0, 1)` |
| `autoFocus`, `ref.focus()`, Tab order, Enter | `hud_focus("search")`, Tab goes in drawing order, `hud_submitted()` |
| a scrolling `<div>` | `off = hud_scroll(r, content_height, "list")`, then `clip(r)` ... `no_clip()` |
| a modal dialog | `hud_panel(visible_rect(), rgba(0, 0, 0, 0.5))` then the dialog's boxes, drawn last |
| drag and drop in a list | `claim_press()` when a row is pressed, then follow `mouse_pos()` |
| CSS (theme, font size) | `hud_style.button = ...`, `hud_style.text_size = 18.0` |
| `cursor: pointer` | `set_cursor(.hand)` (text fields show an I-beam themselves) |
| keyboard shortcuts | `if shortcut(.s): save()` (Ctrl+S, Cmd+S on a Mac) |
| `dialog.showOpenDialog`, a file `<input>`, drop events | `d = open_file_dialog(["csv"])`, then `file_dialog_result(d)` each frame; `dropped_files()` |
| `fs.readFile`, `fs.writeFile` | `read_file(path)`, `write_file(path, s)`; in a page, `download_file(path)` to hand a file over |
| `localStorage`, electron-store | `save_value("notes", notes)`, `load_value("notes", default)` (a file natively, the browser's storage in a page) |
| `navigator.clipboard` | `clipboard()`, `set_clipboard(s)` (text fields do Ctrl+C/X/V themselves) |
| `window.onbeforeunload` | `on_quit = (): ...` |
| `requestAnimationFrame` | `draw` itself; with `redraw_on_input()`, `request_redraw()` or `redraw_after(s)` asks for a frame |

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
| `urljoin(base, link)`, `urlsplit(url)` | `url_join(base, link)`, `parse_url(url)` (`u.host`, `u.port`, `u.path`...) |
| `s[:4]`, `f"{s:.4}"` | `first(s, 4)` or `"{s:.4}"` (characters; `s[..4]` counts bytes, and can cut an `é` in two) |
| `re.search(r"\d+", s)` | `s.find(regex(r"\d+"))` (a `Match?`: `m.text`, `m.groups`) |
| `Counter(ws)`, `defaultdict(list)` | a map: a missing key starts at zero when changed (`counts[w] += 1`, `groups[k].push(x)`); reading one, `m[k]`, is an error: `m.get(k) ?? 0` |
| `set()`, `{1, 2}`, `x in s` | `seen: Set[int]` (`{}` where a Set is expected), `{1, 2}`, `s.add(x)`, `x in s`; `unique(xs)` for an array without repeats |
| `collections.deque`, `heapq.heappush(pq, (d, v))` | `q: Deque[int]` with `q.push(x)` and `q.pop_front()`; `pq.heap_push((d, v))` and `pq.heap_pop()` on an array |
| `bisect.bisect_left(xs, x)`, `itertools.permutations(xs)`, `combinations(xs, k)` | `lower_bound(xs, x)` (or `bisect_left`), `permutations(xs)`, `combinations(xs, k)` |
| `math.gcd`, `math.isqrt`, `pow(b, e, m)` | `gcd(a, b)`, `isqrt(n)`, `pow_mod(b, e, m)`, `inv_mod(a, m)` |
| `" ".join(map(str, xs))`, `print(x, file=sys.stderr)` | `xs.join(" ")`, `eprint(x)` |
| `None`, `if x is None:` | `none`, `if x == none:`; `if let v = x:` gets what is inside |
| `match s:` with `case Rect(w, h) if w == h:`, `case n if n > 100:` | `match s:` with `.rect(w, h) if w == h:` (a variant of an enum, its fields by position), `_ as n if n > 100:`; `if let .rect(w, h) = s:` for one variant |
| `t[0]` (a tuple) | `t.0` |
| `global x` before `x = 1` or `x += 1` in a function | `global x` before `x = 1`; `x += 1`, `x.f = 1` and `xs[i] = 1` change the global without it |
| `max(xs, key=len)`, `sorted(xs, key=..., reverse=True)` | `max(xs, key = len)`, `sorted(xs, key = (x): x.age, descending = true)` |
| `try: ... except: ...` | a function gives back what went wrong as a value (`-> Config \| JsonError`), checked with `if r is JsonError:`, or passed on to the caller with `?` (`cfg = load(p)?`) |
| `def test_x(): assert ...` (pytest) | `test "x": assert(...)`, run with `sloppy test file.jo` |
| big integers: `2 ** 1000`, `int("123...")`, `math.factorial(100)` | `int` is 64 bits and wraps around (`checked_mul(a, b)` is none where it would); past that, `BigInt` keeps every digit: `bigint(2) ^ 1000`, `bigint("123...")`, `f *= i` from `f = bigint(1)`, with `+ - * / %`, comparisons, `print` and `pow_mod`, `gcd`, `isqrt` as for ints |

For contests and Advent of Code (reading all the input at once, the containers, binary search,
number theory): [Contests and Advent of Code](CONTESTS.md).

## Coming from Go

Tasks are goroutines that take turns on one thread: `spawn((): ...)` starts one, and one that
waits (a channel, a fetch, a connection, `sleep`) lets the others run. For the processor's cores,
`parallel_map` shares out work, and the compiler checks its functions for data races.

| Go | Sloppy |
|---|---|
| `go run main.go`, `go build` | `sloppy main.jo`, `sloppy build main.jo` (`--release` for faster code) |
| `go f(x)` | `t = spawn((): f(x))`; `t.wait()` is its result ([tasks and channels](LANGUAGE.md#tasks-and-channels)) |
| `ch := make(chan int)`, `make(chan int, 10)` | `ch = channel[int]()`, `channel[int](10)` |
| `ch <- v`, `v, ok := <-ch`, `close(ch)` | `ch.send(v)`, `if let v = ch.receive():` (none once closed and empty), `ch.close()` |
| `for v := range ch` | `loop v in ch:` |
| `sync.WaitGroup`, `errgroup` | `wait_all(tasks)`: their results, in order; or a group, `g = task_group()`, `g.spawn((): ...)`, `g.wait()` (false if one panicked: the others are cancelled, `g.why()` says what) |
| a worker pool over fetches, `errgroup` with `SetLimit(8)` | `rs = net.fetch_all(urls, at_once = 8, retries = 2)`: the answers in order, each failed or busy one asked again |
| goroutines for CPU work | `parallel_map(xs, f)`, `parallel_range(n, f)` and `parallel_update(xs, f)` run `f` on every core and give back its results, in order |
| `sync.Mutex` | not needed: tasks take turns, and between two waits nothing else runs; `parallel_map`'s function cannot change a variable it shares (the compiler says so: return values instead), and a count the threads share is an `Atomic` (`done = atomic(0)`, `done.add(1)`) |
| `select` | `select:` with arms `ch.receive() as v:`, `ch.send(x):`, `t.wait() as r:` (a task has ended), `stopping():` (ctrl-c), `after 2.0:` and `else:`; one channel alone: `ch.receive(wait = 2.0)`, `ch.send(x, wait = 2.0)` |
| a nil channel in a `select` (`ch = nil` once it is closed) | the channel in an optional, set to none: an arm on `none` is never ready (`a: Channel[int]? = ch`, then `a = none`) |
| `runtime.Gosched()` | `yield_now()` |
| "all goroutines are asleep - deadlock!" | the same: every task waiting on what none will do is told, with where each waits |
| `context.WithTimeout`, cancelling | `net.fetch(url, wait = 5.0)` (and `fetch_start`, `fetch_all`): status 0 and `r.why` when the time runs out; `net.fetch_cancel(f)` stops one |
| `ctx.Done()`, `cancel()` | `t.cancel()`: the task's waits (sleep, a channel, select, the network's) end at once with nothing, and `cancelled()` is true in it, for it to clean up and end; a group's `g.cancel()` cancels every one |
| `signal.NotifyContext(ctx, os.Interrupt)`, graceful shutdown | `loop not stopping(): ...`: ctrl-c and SIGTERM make `stopping()` true (and end the `sleep` and `net.wait` of a task that has asked it); `on_quit = (): ...` runs as the program ends. A task that goes on after main has ended is told; a second ctrl-c ends the program |
| a goroutine dump (SIGQUIT) | `report_tasks()`: what each task waits for, where, and where it was spawned; `task_count()` |
| `if err != nil { return err }` | `x = f()?`: a failure (an `error struct`, or none) goes back to the caller as it is |
| `errors.New`, a type implementing `error` | `error struct LoadError:` with the fields the caller needs; the function returns `Config \| LoadError`, and the caller checks `if r is LoadError:` |
| `func save() error` | `save = () -> void \| SaveError:`; `save()?` passes the error on |
| `defer f.Close()` | `defer f.close()`: runs as the block ends, by a `return` or a `?` too |
| `v, ok := m[k]`, `m[k]++` | `if let v = m.get(k):`, `m[k] += 1` (a missing key starts at zero) |
| `append(xs, x)`, `len(xs)`, `xs[1:3]` | `xs.push(x)`, `xs.len()`, `xs[1..3)` |
| structs and methods | `struct Box:` and functions taking one: `area = (b: Box) -> f64: b.w * b.h` is called `b.area()` |
| `fmt.Printf("%-10s %5.2f\n", s, x)` | `print("{s:<10} {x:5.2f}")` |
| `flag.Bool("words", false, "count words")` | a struct of the options, `opts = parse_args[Options]("what it does")`, the comments as the help |
| `encoding/json`, struct tags | `from_json[Item](s)` (fields by name), `to_json(x)`, `parse_json(s)` for any shape; a JSON name that is a keyword is a field with `_` after it (`when_` is `"when"`) |
| `bufio.Scanner` over a file | `if let f = open_file(p):` then `loop let line = f.read_line():` |
| `regexp.MustCompile(expr)` | `regex(r"...")`, made once and used for every text |
| `url.Parse`, `base.ResolveReference(ref)` | `parse_url(s)` (`u.host`, `u.port`, `u.path`), `url_join(base, link)` |
| `http.HandleFunc`, `http.ListenAndServe` | `import http`, `http.get("/todos/:id", handler)`, `http.serve(8080)` ([writing a server](#writing-a-server)) |
| middleware, `rs/cors`, `gziphandler` | `http.before(f)` (may answer early) and `http.after(f)`, `http.cors(["https://example.com"])`; gzip is on (`http.gzip = false`) |
| `bcrypt.GenerateFromPassword`, `subtle.ConstantTimeCompare` | `crypto.hash_password(pw)` and `crypto.check_password(pw, stored)` (PBKDF2-SHA256), `crypto.constant_time_equal(a, b)` |
| gorilla/websocket, a goroutine per connection | `http.websocket(r)` in a route; `p = net.accept(wait = 1.0)`, a task for each with `net.receive([p], wait = 30.0)`; `net.close(p, 4001, "the room is full")` |
| `httptest.NewServer` | the server in the same program: `http.listen(port, host = "127.0.0.1")`, `spawn((): http.serve(port), background = true)`, then `net.fetch` ([as above](#writing-a-server)) |
| `go test`, `func TestX(t *testing.T)` | `test "x": assert(...)` blocks, run by `sloppy test file.jo` (`sloppy test file.jo x`: only those named so) |
| a small static binary | `sloppy build --release tool.jo`: one static executable (no libc; hello world is about 150 KB) |
| `GOOS=windows GOARCH=amd64 go build` | `sloppy build tool.jo --target windows` (`linux`, `linux-arm64`, `macos`, `wasm`), from any system; Linux, ARM and macOS builds are all named `tool` unless `-o` says otherwise, so give each its own: `--target macos -o tool-mac` |

## Coming from curses or bubbletea

`import term` is the terminal as curses, tcell or bubbletea give it, with the loop the program's
own: draw everything into the screen (`term.clear()`, `term.put(...)`), `term.flush()` (only what
changed goes out), then wait for `term.read_event()`. Keys come as an `Event` whose `name` is as
bubbletea's `msg.String()`: `"ctrl+c"`, `"up"`, `"enter"`, `"a"`.

| curses / tcell / bubbletea | Sloppy |
|---|---|
| `curses.wrapper(main)`, `initscr()` with `cbreak()`, `noecho()`, `keypad(True)`; `tcell.NewScreen()` with `Init()`; `tea.NewProgram(m, tea.WithAltScreen())` | `term.start()`: raw keys, the terminal's own screen, the cursor hidden; put back as it was by `term.stop()` or however the program ends (a panic, ctrl-c, SIGTERM too) |
| `stdscr.getmaxyx()`, `screen.Size()`, `tea.WindowSizeMsg` | `w, h = term.size()` (columns, rows); a resize is an event of kind `.resize`, the screen resized already |
| `stdscr.addstr(y, x, s, attr)`, `screen.SetContent(x, y, r, nil, style)` | `term.put(x, y, s, fg = term.RED, style = term.BOLD)`: x first, and it gives the column after |
| `stdscr.refresh()`, `screen.Show()` | `term.flush()`: only the cells changed, in one write |
| `stdscr.clear()`, `screen.Clear()` | `term.clear()` (each frame: only what changed is written anyway) |
| `stdscr.getch()`, `get_wch()`, `screen.PollEvent()`, `tea.KeyMsg` | `e = term.read_event()`: `e.key` (`.char`, `.up`, `.f5`...), `e.text`, `e.ctrl`, `e.alt`, `e.shift`, `e.name` (`"ctrl+up"`) |
| `stdscr.timeout(100)`, `nodelay(True)`, `tea.Tick` | `term.read_event(wait = 0.1)` (none: nothing came), or a task that ticks while main waits for keys |
| `curses.mousemask(ALL_MOUSE_EVENTS)`, `screen.EnableMouse()`, `tea.WithMouseCellMotion()` | `term.start(mouse = true)`: `.press`, `.release`, `.drag`, `.wheel_up`... with `e.button`, `e.x`, `e.y` (`mouse_moves = true`: `tea.WithMouseAllMotion()`) |
| `screen.EnablePaste()`, `tea.KeyMsg` with `Paste` | a paste is one event of kind `.paste`, its text in `e.text` (on by itself) |
| `init_pair(1, COLOR_RED, COLOR_BLACK)`, `color_pair(1)`; `tcell.ColorRed`; lipgloss's `Color("205")`, `Color("#ff8000")` | `fg = term.RED, bg = term.BLACK` on each call; `term.color(205)`, `term.color(hex(0xff8000))` |
| `A_BOLD \| A_UNDERLINE`, `A_REVERSE`, `A_DIM` | `term.BOLD \| term.UNDERLINE`, `term.REVERSE`, `term.DIM` (`ITALIC`, `STRIKE`) |
| `stdscr.border()`, `curses.textpad.rectangle`, lipgloss's borders | `term.box(x, y, w, h, title = "...", lines = .rounded)` (`.single`, `.double`, `.heavy`); `term.hline`, `term.vline` |
| `curs_set(1)` and `move(y, x)` | `term.set_cursor(x, y)` (shown after each flush), `term.hide_cursor()` |
| `wcwidth`, `runewidth.StringWidth`, `lipgloss.Width` | `term.text_width(s)`; `term.fit(s, 20)` cuts to 20 columns with a `…` |
| `KeyboardInterrupt` in `getch()`; `tea.Quit` on `"ctrl+c"` | ctrl-c asks the program to stop (`stopping()`, `on_quit`), ending it at its next `read_event` if it does not look; `term.start(ctrl_c_key = true)` to read it as `"ctrl+c"` |
| `curses.endwin()` before a shell command, then `refresh()` | `term.stop()`, `run_program(cmd, show = true)`, `term.start()` |
| tests with `teatest`, a `tcell.SimulationScreen` | `term.set_size(40, 10)`, draw, then `term.screen_text()` or `term.render()`; `term.decode(bytes)` for input |

## Coming from pygame

A pygame program owns its main loop: it reads events, moves things, draws onto the screen
Surface, flips it and waits for the clock. A Sloppy game has no loop of its own: `update` and
`draw` are called each frame, and the frame is shown after `draw` by itself. `sloppy new my_game
arcade` and `sloppy new my_game platformer` are whole games to start from (a title screen, a
score kept between runs, a level written as text).

```gdscript
window("Dodge", 800, 600)
player = Rect(380, 520, 40, 40)
rocks: Rect[]

update = (dt: f64):
    global player
    if key_down(.left): player.x -= 300 * dt         # speeds are per second: times dt
    if key_down(.right): player.x += 300 * dt
    player = player.clamp(Rect(0, 0, 800, 600))
    if every(1, 0.5): rocks.push(Rect(random(0, 780), -20, 20, 20))
    loop mut r in rocks: r.y += 200 * dt
    rocks.retain((r): r.y < 600)

draw = ():
    clear(rgb(0.1, 0.1, 0.15))
    rect(player, hex(0x40a0ff))
    loop r in rocks: rect(r, GRAY)
```

| pygame | Sloppy |
|---|---|
| `pygame.init()`, `set_mode((w, h))`, `while running:` with events, `clock.tick(60)`, `display.flip()` | `window("Title", w, h)`, then `update = (dt: f64):` and `draw = ():`: no loop, no events, no flip |
| `QUIT` | `on_quit = ():`, which the game calls as the window closes |
| `KEYDOWN`, `key.get_pressed()[K_LEFT]` | `key_pressed(.space)` (pressed this frame), `key_down(.left)` (held); `K_RETURN` is `.enter`, `K_ESCAPE` `.escape`, `K_a` `.a` |
| `mouse.get_pos()`, `mouse.get_pressed()`, `mouse.set_visible(False)` | `mouse_pos()`, `mouse_down(.left)` (`mouse_pressed`: this frame), `show_cursor(false)` |
| `display.set_caption(s)` | `set_title(s)` |
| `image.load(p).convert_alpha()` | `load_texture(embed("p.png"), false)` at the top of the file (false: sharp pixels, for pixel art) |
| `screen.blit(img, (x, y))` | `sprite(img, vec2(x, y))` in draw |
| `blit(sheet, pos, area)`, `subsurface` | `sheet = sprite_sheet(img, 16, 16)` and `draw_frame(sheet, i, center)`, or `sprite_region(img, src, center, size)` |
| `transform.flip`, `scale`, `rotate` | `draw_frame(..., flip_x = true)` (or a negative width in sprite's size), sprite's size argument, `angle =` (radians) |
| `img.get_width()`, `set_alpha(128)` | `img.width`, the tint's alpha: `sprite(img, pos, tint = rgba(1, 1, 1, 0.5))` |
| a `Surface((w, h))` drawn onto | `rt = render_target(w, h)`; in draw, `draw_to(rt)`, the drawing, `draw_to_screen()`, then `draw_target(rt, pos)` |
| `screen.fill(c)` | `clear(c)` at the top of draw; colors are 0 to 1, `rgb(1, 0.5, 0)`, or `hex(0xff8000)` |
| `draw.rect(s, c, r)`, `draw.rect(s, c, r, 2)`, `draw.circle`, `draw.line` | `rect(r, c)`, `rect_outline(r, 2, c)`, `circle(center, radius, c)` (`ring` for an outline), `line(a, b, width, c)` |
| `Rect.colliderect`, `collidepoint`, `center` | `overlaps(a, b)`, `contains(r, p)`, `center(r)` |
| `r.right`, `r.bottom`, `move`, `inflate`, `clamp`, `union`, `collidelist` | `right(r)`, `bottom(r)`, `r.move(v)`, `r.grow(2)` (each side out by 2), `r.clamp(bounds)`, `union(a, b)`, `first_overlap(r, rects)`; a Rect's fields are `x`, `y`, `w`, `h` |
| `sprite.Group`, `spritecollide(..., dokill=True)` | an array of structs, changed in a `loop mut e in enemies:`, then `enemies.retain((e): not e.dead)` |
| `math.Vector2` | `vec2`, `length(v)`, `normalize(v)`, `distance(a, b)`, `rotate(v, a)` (radians: `rotate(v, 90deg)`) |
| `mixer.Sound(p).play()`, `mixer.music.load(p)` | `jump = load_wav(embed("jump.wav"))` at the top, `play(jump)`; `play_music(load_music(embed("song.ogg")))`, or `play(snd, looping = true)` |
| `font.SysFont(None, 24).render(s)` and a blit | `text(s, pos, 24, color)` with the built-in font; `set_font(load_font(embed("font.ttf")))` for another |
| `time.get_ticks()`, `time.set_timer` | `elapsed()` (seconds), `if every(1, 2.0):` in update (true once each 2 s) |
| `random.randint(1, 6)`, `random.choice(xs)` | `random_int(1, 7)` (the top is left out), `random_item(xs)` |
| `open("level.txt").read()` | `str_from_bytes(embed("level.txt"))`: built into the game, so it works in a web page too; `read_file(path)` reads the disk (native builds) |
| a high score in a file | `save_value("best", best)` and `best = load_value("best", 0)` (or `save_data` / `load_data` for text): a file natively, the browser's storage on the web |
| a small Surface scaled up | `window("Title", 320, 180)` and `pixel_art()`; `full_resolution()` in draw before the HUD keeps its text sharp |
| `RESIZABLE`, `VIDEORESIZE`, `toggle_fullscreen()` | windows are resizable, and the game keeps its 2D units (`visible_rect()` is what shows); `toggle_fullscreen()` |
| `joystick.Joystick(0)` | `gamepad_down(.a)`, `left_stick()` (any pad, or the pad's number first) |

Also not as in Python: `round(5.7)` is `6.0` (`int(round(x))` for a whole number), and angles
are in radians. `xs.remove(x)` takes out the first element equal to x, as in Python, and
`xs.remove_at(i)` the one at index i (Python's `del xs[i]`).
To look at a frame without playing, or press keys at given frames: [Testing a
game](LANGUAGE.md#testing-a-game).

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
| `Instantiate`, `Destroy` | a function that makes the struct, pushed onto its array; `xs.remove_at(i)` or `xs.retain(...)` |
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
- [Contests and Advent of Code](CONTESTS.md): reading the input, integers, containers, binary
  search and number theory, for C++ and Python contest regulars.
- [The library](API.md): windows, input, drawing in 2D and 3D, sound, files and the rest.
- [The playground](https://sloppy-lang.org/playground/) has more examples, including two
  complete games.
- Building Sloppy from source, and working on the compiler: the
  [README](https://github.com/david-andrew/sloppy-lang#getting-started).
