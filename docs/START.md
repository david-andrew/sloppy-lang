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

fib = (n: int) -> int:
    if n < 2: return n
    fib(n - 1) + fib(n - 2)

loop i in [0..10):
    print("fib({i}) = {fib(i)}")
```

and run it:

```sh
sloppy hello.jo
```

(`sloppy run hello.jo` is the same.) Each run compiles the whole program, in a few milliseconds, and runs it. `sloppy` alone is an
interactive prompt, for trying things a line at a time.

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

Each is one file with nothing to install alongside it (`--target macos` and `--target linux`
make the same from any system too; a Windows build's `.pdb` beside it is for debuggers only).
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

## Where next

- [Make a game](TUTORIAL.md): a small platformer, built step by step. Then
  [an arcade game](TUTORIAL_REBOUND.md) and [a 3D shooter](TUTORIAL_BREAKWATER.md).
- [The language](LANGUAGE.md): everything Sloppy has, with examples.
- [The library](API.md): windows, input, drawing in 2D and 3D, sound, files and the rest.
- [The playground](https://sloppy-lang.org/playground/) has more examples, including two
  complete games.
- Building Sloppy from source, and working on the compiler: the
  [README](https://github.com/david-andrew/sloppy-lang#getting-started).
