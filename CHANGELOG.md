# Changelog

## Unreleased

- A phone held upright, playing a game made wider than tall: a note over it to turn the phone
  sideways (the game goes on under it; `sideways_hint(false)` for a game laid out for both ways).
- Thick `polyline`s (and `rect_rounded_outline`) are one band through their points: the bends
  had gaps, which made a rounded outline's corners a fan of spikes. Bends are mitred, a sharp
  one's point cut off at three times the thickness.
- Safari's engine checked: `tools/webkitcheck.py` runs Playwright's WebKit in a container. Invite
  codes work WebKit to WebKit, with Chromium both ways and with a native program (the reply
  pasted in 20 s later), and the gallery's games run as an iPhone with no errors. Real iPhones
  are not tried yet.

## 0.20.0

- Aces (examples/aces, in the gallery): biplanes in a dogfight, Red against Blue, up to six a
  side, players and the computer. Invite a friend, then more (each their own invite); the one
  who invites chooses the sides and starts, and passes on what goes between the others. Flown
  with the mouse, keys, a gamepad or two thumbs on a phone.
- netplay: `s.stand_in(p, input)` plays for a player who left, so the others play on (the game
  makes the input mean "the computer flies it"). The host takes in the inputs it passes on, so it
  has all anyone has of a player's; `s.stands_in(p)` says whether this machine does.
- `camera3d` takes an up direction (a camera that banks with a plane); 3D sound pans with it.
- Menus: a row is as wide as its label needs (a long label ran into its value), and a menu's
  values stay in one column.

## 0.19.1

- Invite codes between web pages work in Firefox: a page gave up while its friend was still
  pasting the reply in (Firefox's ICE stops for good after some seconds unanswered; Chrome's
  says failed and recovers, but the page closed it at once). A joining page whose ICE gave up
  starts again with the same certificate, ICE name and password (what its reply code holds),
  and a failure before connecting is waited out (20 s for the inviter, 10 minutes for the
  joiner). Tested Firefox and Chromium in every pairing with the reply pasted 0, 30 and 90 s
  later (tools/rtc_pages.mjs, in nettest.py).

## 0.19.0

From a 3D kart racer (a spline track, drifting, AI karts, a minimap, names over karts):
- `world_to_screen(vec3)` and `screen_ray` were off whenever the window was not the design area's
  shape (they took the design area for the whole picture, which 3D fills): names drifted off the
  karts, and picking missed.
- `"a" + panic("x")` and `"{panic("x")}"` (what never comes back, taken as a value) crashed the
  compiler; and after the error "recursive function needs an explicit return type", a second,
  wrong one (`cannot format a value of type void`) followed at its use.
- `SLOPPY_INPUT` presses a gamepad's buttons and moves its sticks and triggers (`5:pad_a+`,
  `6:lstick=1x0`, `lt=1`), for testing pad controls with no pad; what it cannot read, it says
  with every kind of item (touches were left out).
- Smooth paths (lib/game/curves.jo): `spline` and `spline_points` through points (Catmull-Rom),
  `path_length`, `point_along`, and `nearest_on_path` (how far round a track a kart is, for laps
  and positions; a point ahead to steer for).
- A chase camera: `update(cam, kart.pos, dt, heading = kart.yaw)` swings a follow camera round
  behind a vehicle, smoothly (`cam.chase`: how quickly).
- `play_at(..., looping = true)`: an engine heard where its kart is (with `move_sound`).
- `vec3 + vec2` says how a ground point goes into 3D (`vec3(p.x, 0, p.y)`).
- `custom_mesh` turns a triangle wound against its normals to face where they point (a road
  wound clockwise was invisible from above, with nothing saying why); its docs say which side
  is the front. `draw_mesh(..., double_sided = true)` draws both sides.
- Two menus drawn in one frame (one ended, another begun) took no input in the second: each
  menu keeps its own state now, and the frame's input is read once for all of them.

From a tower defense for phones (a grid, waves, towers built by tapping):
- `hud_hovered()` with a finger: the first tap on the world after one on a button was taken as
  the button's (the lifted finger leaves the pointer there), and a tap landing on a button was
  the world's that frame; it looks where the pointer is now. A button no longer stays lit after
  the finger lifts.
- A `loop mut` over a global array whose body calls a function that adds to it, removes from it
  or replaces it (itself or through what it calls) is an error naming the function; it looped
  over what was added, or wrote to an element of an emptied array. The Breakwater tutorial had
  one (a hit that ended the run emptied the bolts being looped over).
- `Pool[T]` and `Handle`: things that come and go (enemies, bullets), each found again by a
  handle that stays its own while others are removed, and says so once its thing is gone (a
  homing shot keeps its target); `pool[h].hp -= 1`, `pool.items` to loop over, `retain`.
- A struct given to a function along with a `mut` argument it is part of (`f(p, p.items[0])`), or
  part of a global the function changes, changed under the function as it wrote the other: it is
  passed as a copy then (the value it was, as everywhere else).
- `camera2d_fit(world, on)`: a world area shown as large as it fits in part of the screen (a
  board above the buttons on a phone held upright); START.md has the recipe.
- `visible_rect()` gives a `Rect` (`.w` is its width, `.h` its height), as the hud functions
  and `contains` take; it was a vec4 whose `.w` was the height.
- A struct that holds itself (`a: A`) is an error where it is declared, used or not; made with
  its defaults (`l: A`), it crashed the compiler (found by the error fuzzer).
- A struct field named by a keyword (`build: Rect`, `when: f64`) says so, as other names do.
- `SLOPPY_STATS=log` writes its summary every 2 seconds, as documented (it was every 120 frames);
  `fps()` gives the frames so far before its first half-second measure (it was 0).
- A circle is one square whose pixels are in or out by their distance from its center: its edge
  is smooth on every renderer (the software one too), and 2000 small circles draw 50 times faster
  there (18.6 ms, now 0.33). `segments = n` still draws a polygon. Lines, rings and arcs have
  smooth sides the same way (a band whose pixels are in or out by their distance from its middle). Ellipses and rings reuse
  their points (a circle of radius 1, made once for each number of segments).

- Rollback for three or four over invite codes, with no server: the others play over the host
  alone (`s.over([host, -1, -1])`), who passes on what goes between them.

## 0.18.0

- `net.invite()`, `net.invite_code(p)`, `net.join_invite(code)`, `net.accept_reply(p, reply)`:
  two games connect straight to each other with no server, the players passing two short codes
  (a chat message): web pages and native programs alike, on one network or across the internet.
  Native programs speak WebRTC now (lib/rtc.jo: ICE, DTLS 1.2, SCTP, data channels, in Sloppy),
  tested against Chromium both ways, OpenSSL, and on arm64 and Windows. Netpong's Invite a friend
  and Join a friend use them, from the website's page too.
From a persona making online two-player games with no server (tag with rollback, Connect Four
with chat):
- A rollback game that read `net.receive()` itself (to see its friend leave) took the session's
  packets over invite codes, and play stalled (Duel did): the session's packets are marked and
  stay its own; the game's own messages on the same peer (a chat, "again?") are the game's.
- A program's end (quit, its window closed, exit, a page closed) tells its peers at once; they
  waited 15 s of silence.
- A joining game waits for the inviter to paste the reply in for up to 10 minutes while that game
  answers (it gave up after 30 s); the inviter's 30 s start when the reply comes.
- What a failed connection says: a code with a character changed ("that code does not match the
  game that made it", not TLS words), a game that never answered (not "a network that allows no
  path"), an invite pasted where a reply goes, a reply pasted into Join a friend; on the Join
  screen the reason is the headline. `net.code_kind(code)`: "invite", "reply" or "".
- Codes broken across lines (a chat app wrapping them) are read whole.
- `s.over(peers)` with one peer short says how it goes (`[-1, friend]`).
- `sloppy new my_game online`: two players anywhere with no server, from the start (invite
  screens, rollback netplay, practice alone, touch).
- `chain([tween(...), tween(...)])`: tweens one after another, as one (`value()`, `done()`); and
  `done(tweens)` for a set started together (a match-3 persona's wish: the next move once all the
  falling pieces have landed).
- `struct Rematch: pass`: a struct with no fields (a message that is only its name); `pass` was
  refused. `zeros[int](rows, cols)` makes zeros of another type (`int[,]`). `rect(r, color)`
  and `rect_outline(r, thickness, color)` take a `Rect`, as the hud functions do.
- A warning where a netplay session's tick calls `random()`, `time()`, `elapsed()` and the like:
  each machine would get another game (a desync found only later, at run time).
- `Msg(Move(3))` with `Msg` a union says a Move is a Msg as it is (it was "unknown function");
  `from_text` reading a union says what it found (`expected a Move | Chat, found 'Mvoe'`).
- Native invite peers send much faster: sending n messages in a frame took time growing as n
  squared (20,000: 3.7 s, now 19 ms; 100,000 never all arrived, now in 5 s); at most 128 chunks
  go unacknowledged, so a big message no longer floods the other side (5 MB: 13 s, now 1.2 s;
  over 16 MB hung, 17 MB now arrives in 5 s). AES (tables) and GCM's GHASH (64-bit halves)
  are 10 times faster.
- `elapsed()` before the window opened was the machine's uptime (`s.silent(p)` was -656821);
  `s.problem`'s "not heard from" clears when the player is back.
- `net.turn_server(url, user, password)`: invites also offer a path through a TURN relay, for
  players whose networks allow no straight path (some mobile data, schools, offices); native
  programs speak TURN too (allocations, permissions, refreshes). Tested with coturn, relay only,
  native to native and native to Chromium both ways. `crypto.md5`, which TURN's credentials use.
- A native program's invite peer whose game went without a word (switched off, its network
  gone) is `.left` after 15 s of silence, with why; it waited for ever.
- `net.join_invite` takes a link with the code in it (`…?invite=code`) as well as the code;
  `page_url()` is a web page's own address, to make one. Netpong's invite is such a link: opened,
  the game joins by itself in a browser; from a computer, it links to the game on sloppy-lang.org,
  so a friend plays with nothing to install.
- `import invite`: the Invite a friend and Join a friend screens for any game (a link to send,
  a code back, copy, share and paste, on phones too, and why when nothing connected): a menu
  calls `invite.start()` or `invite.join()`, and draw shows `invite.screen()` until it gives the
  other player. `invite.from_link()` joins at once from an invite link.
- Netpong uses `invite`'s screens too.
- Duel (the rollback example) starts on a menu: Invite a friend plays anyone, anywhere, with no
  server (rollback over invite codes), on a phone too (steer toward a finger, a Fire button);
  it is on the website's examples page.
- `s.over(peers)`: rollback netplay over `net` peers, so over invite codes too: two players, in
  web pages or native programs, play a rollback game with no server.
- `import crypto`: SHA-1, SHA-256, HMAC, AES-128-GCM, P-256 ECDH and ECDSA, self-signed
  certificates, and `random_bytes` from the operating system (the start of WebRTC in native
  programs, for games that connect a desktop build and a web page with no server).
- Smooth edges natively, as in a web page: through Vulkan (Linux, Windows) the screen is drawn
  with 4 samples a pixel (MSAA), so shapes, lines and 3D edges are no longer jagged.
  `SLOPPY_MSAA=1` turns it off. (Not yet through Metal on macOS.)
- On a phone, a `hud_text_field` tapped brings up the phone's keyboard (in a web page there
  was no way to type before), with a Paste button at its end while it has it; the game fits
  above the keyboard. `ui_text_field` takes pastes too.
- `share(text)` opens the system's menu for sending text to another app (a phone's: a chat,
  Messages, mail) where `can_share()`; in a web page. `set_clipboard` in a phone's browser,
  refused outside a tap, is done at the end of the next one.
- Netpong plays on a phone: the paddle follows a finger (or the mouse held down), Back and
  Leave buttons where Escape was the only way, Share and Copy for the invite, the address typed
  into a text field, and the long codes shown in two lines.
- A native game hosting web pages (`net.listen`) refused about half of the browsers' connections
  since invite codes came: their base64 replaced the library's, and the WebSocket handshake's
  answer was written in the URL alphabet.
- A top-level `__x = ...` (a name the library uses for its own state) makes the program's or
  module's own `__x`, where it changed the library's without a word: a game's `__B64` broke
  `base64_encode`, and lib/rtc.jo's broke WebSocket servers.
- `when TARGET == "wasm": x = 1` on one line at the top level (as after `if`), where it was an
  error ("expected newline").
- A web page's error says what went wrong in Firefox and Safari too (it showed only where).
- Invite codes tested with Firefox as well (tools/nettest.py with SLOPPY_FIREFOX).
- A slice compared with `==` (`xs[1..4) == ys`) read the wrong memory and stopped the program.

From a creative coder (p5.js and Shadertoy: a flow field with trails, a shader piece with
post-processing, a step sequencer):
- `post_effects()` with `draw_to` and `draw_to_screen` drew a black screen: drawing back to the
  screen now goes under the effects.
- `noise()` in a shader drew other values than on the CPU (its hash was 64 bits, a shader's
  integers 32): noise is 32-bit now, the same on the CPU, Vulkan, the software renderer and the
  web. A shader with an integer that does not fit 32 bits is an error.
- `hash21` (the shader helper) hashes integers, not `fract(sin(...))`, which drew square seams
  on NVIDIA; it hashes the cell its point is in.
- `draw(prog, mesh, params)` with params of another type than the shader's functions take is
  an error, where prog is a global made by `make_shader(shader(vs, fs))`.
- `noise(x)` and `noise(x, y, z)`, beside `noise(x, y)`; `remap(x, a, b, c, d)` (p5's map) and
  `inverse_lerp`; `random_normal(mean, sd)`.
- GLSL's `sin`, `cos`, `floor`, `ceil`, `fract`, `pow`, `step`, `smoothstep` and `mix` (with a
  vector t) on vec2, vec3 and vec4, `abs`, `min` and `max` on vec4, on the CPU and in shaders.
- Errors for p5's and Shadertoy's habits: `TWO_PI`, `width`, `color(...)`, `stroke`,
  `strokeWeight`, `background`, `mouseX`, `mouseIsPressed`, `frameCount`, `beginShape`,
  `line(x1, y1, x2, y2)`, `text(s, x, y)`, `fill(r, g, b)`, `push()`, `map(x, a, b, c, d)`,
  `atan(y, x)`, `random(xs)`, `iTime`, `gl_FragColor`; `"void main() { ... }"` says the braces
  need doubling (it said "unexpected indentation"); a shader that reads a global says how to
  give it the value.
- Warnings for `hsv(200, ...)` (a hue goes from 0 to 1) and `rgba(0, 0, 0, 10)` (alpha too).
- START has "Coming from p5.js, Processing or Shadertoy", with a Shadertoy-style shader.

From an idle game (numbers past 1e300, a shop that scrolls, saves, offline progress, a chart):
- `log10` is exact at powers of ten (`log10(1000.0)` was 2.9999999999999996, so `floor` gave
  2) and as precise as C's elsewhere; `log2` is exact at powers of two; `{x:g}` follows.
- Charts label big numbers as 4B, 2T and 1e+25 (they wrote out every digit, and past about
  1e40 drew nothing at all), and tiny ones as 2e-06; `Chart(log_y = true)` puts y on a log scale.
- A `hud_button` (or any hud_ box) clipped out of sight with `clip` takes no clicks: rows of a
  scrolling list out of view were bought.
- `to_json` writes infinity and NaN as `Infinity`, `-Infinity` and `NaN` (as Python's json does),
  and `parse_json`, `from_json` and `to_float` read them; they were written as null, which
  `from_json` then refused.
- `min(a, b)` and `max(a, b)` take any type with its own `<`, as `min(xs)` did.
- A float literal too large for a float (`1e400`) is an error; it was infinity.
- `is_finite(x)` and `is_inf(x)`, beside `is_nan`.
- A `str` of the program's own for its type (`str = (b: Big) -> str: ...`) is how the type
  shows: in `print`, in `"{x}"`, inside arrays and other structs; `to_text`, `to_json` and
  saves still write its fields. `str(5)` beside it is still the conversion.
- `short_number(x)`: 999, 1.23K, 45.6M, 789B, 1.00T, then 1.23e+15.
From a match-3 puzzle game (a Phaser developer: tweens, cascades, specials, levels, touch):
- `sloppy test` on a game whose top calls `window(...)` runs its tests with no window, so with
  no display (it stopped at "cannot open a window").
- A `const` nothing uses is checked too: `const X = no_such(3)` was accepted.
- Changing a loop's element inside a function that runs later (`steps.then(0.1, (): g.scale =
  0.0)`) says to change it by its position, `xs[i]`; the advice before led to changing a copy.
- Errors for Phaser's and JavaScript's habits: `async`/`await`, `new Promise`, `this.tweens`,
  `this.time`, `this.add`, `game.config`, `scene.start`, `Phaser.Math`, `Array(8)`,
  `for (let i = 0; ...)`, `for (const g of gems)`, `let [a, b] = ...`, `const {x} = g`, labelled
  loops and `break outer`, `xs.push(1, 2, 3)` (`extend`), `xs.map((x, i): ...)`.
- `SLOPPY_INPUT` takes fingers: `5:touch1=400x300` puts finger 1 down (or moves it), `9:touch1-`
  lifts it; the first finger is the mouse too, as on a phone, so touch controls can be tested
  without one.
- START's JavaScript table has Phaser's tweens, scenes and chains of animations.
- Netpong explains itself: "How to play together" (the same network, one hosts, the other joins
  the address its screen shows, localhost on one computer); the host's screen shows this
  computer's address in large type. `net.local_address()` gives it; `net.stop_listening()`.
- `tools/netpong_relay.py` (Python, on Netpong's page of the website too): run it, and open the
  address it prints in two browsers on the same Wi-Fi; the first hosts. No Sloppy needed.
- A screenshot run of a program that uses `net` keeps to real time, as one using netplay did.
- Netpong on the website said only "could not reach": a web page cannot host, and one served
  over https reaches only a host on the same computer or a wss:// one. The game and its page say
  so now, and `net.why(peer)` in a web page gives the reason (an https page and a ws:// address
  fail at once with it, not after a wait; nothing answering says so).
- `hud_scroll(r, content_height)`: a list taller than its box, scrolled by the wheel and a bar;
  `hud_tooltip(text)`: a box of text beside the mouse, kept on the screen.
- `download_file(path)`: in a web page, the browser downloads a file the program wrote (a
  picture from `save_png`, an exported save); elsewhere it is already on disk.
- `loop i in 0.. and name, cost in items:` unpacks each pair (or more) while counting.
- A warning for `draw_to(rt)` in draw with no `draw_to_screen()` after it (the screen stayed
  blank).
- Windows: a Vulkan screenshot run with `SLOPPY_HEADLESS=1` opens no window (over ssh, where
  there is no desktop); `tools/gpucheck.ps1` is the Windows GPU check.
- `use big`: numbers past 1.8e308 (`big(1.5, 400)`), a mantissa and a power of ten, with
  arithmetic, comparison, `min`, `max`, `sort`, `pow`, `log10`, and saving as for numbers.
- `hud_text_field` pastes (ctrl+V, cmd+V), and keeps a clip it is drawn inside (a scrolling
  list's); a `hud_button`'s label shrinks to fit.
- `load_value` copies a save it cannot read to `name.bad` before falling back to the default,
  so the next save does not lose it.
- `audio_started()`: whether sound has begun (a web page's waits for a first click).
- Errors for JavaScript's habits: `JSON`, `localStorage`, `setInterval`, `setTimeout`, `btoa`,
  `isFinite`, `Number`, `toExponential`, `toLocaleString`; `Date.now()` points to `unix_time()`;
  `loop (k, v) in pairs`, `const xs = [...]` then `xs.push`, `"v is " + v`, `xs.reduce(f, 0)`,
  an `if` without `else` as a function's value, a map literal with values of several types, and
  an enum compared with a number each say what to write; `on_close` (and the like) points to
  `on_quit`, in one warning, not two; `[0..xs.len()]` warns that it includes xs.len().
- START has "Coming from JavaScript"; LANGUAGE has time away for an idle game, and says each
  frame starts black and a window may be scaled.
- Overloads are tried faster: a vector argument rules out the others at once (games compile
  about 1% faster).

From someone coming from Scratch (a catch game with clones, costumes, backdrops and a high-score
list; a maze with walls by color, a key, a door and a pen trail):
- START has a "Coming from Scratch" table: forever, clones, broadcasts, wait, touching,
  costumes, backdrops, the pen, say and ask, each as it is written here.
- A second `update`, `draw` or `main` is an error: only the first ran.
- Errors for Scratch's habits: `forever:`, `set x to 0`, `change x by 1`, `loop until`, and
  `create_clone`, `broadcast`, `say`, `touching`, `pick_random`, `go_to`, `glide`, costumes and
  the rest name the way it is done here.
- Clearer errors for `score > 10 and < 20`, `key_pressed(.1)`, `key_down(right)`, a function
  with nothing under it, `load_texture(cat1.png)`, `score = score + 1` before a first value,
  `Score` used as `score`, a color with no name (`BROWN`), `text("Score:", score, pos)`,
  `play("meow.wav")`, `embed("Cat1.png")` for cat1.png, `xs.add(x)` on `xs = []`, and a
  variable of whole numbers (or of text, `"0"`) given a fraction (or a number).
- An indented line that matches no line above it is told every place it could go.
- New warnings: `y == 650` in update, where y moves by fractions; `input()` in update or draw;
  a top-level `loop:` that never ends in a game; drawing in update with no draw.
- A warning is not shown twice when the compiler goes on to the next error.
- A frame natively starts black, as on the web: a draw with no `clear()` left a trail of the
  frames before (a picture kept from frame to frame is a render target).
- `sloppy build` at a terminal says what it made (`made apples.html`).

## 0.17.0

From a deck-building card game (a fanned hand, drag and drop, enemies' intents, a run of fights):
- A function field never given one (`on_click: () -> void`, left out) stopped the program with
  "memory access at 0x0" and sometimes no line: calling it now says which and where, and
  building the struct without it warns.
- `loop name, n, cost in items:` unpacks three or more names, as two did.
- `t.1()` calls a tuple's function element.
- `Actions`: steps one after another, each a wait after the one before
  (`turn.then(0.4, (): enemy_attack(0))`, `turn.update(dt)`, `turn.busy()`).
- `rect_rounded`, `rect_rounded_outline` and `ellipse`; `hud_text_field(..., hint = "seed")`.
- A tween read back from text keeps an ease (linear): it stopped the program when updated.
- `sloppy check` on a file of definitions alone (a module others use) no longer says each of
  its functions is never called; run, such a file gets one warning that nothing in it runs.

From a visual novel (dialogue, choices, portraits, music, save slots, Japanese text):
- A loaded font's missing characters are drawn with the built-in font (Latin and accents in a
  Japanese font drew nothing), else as `?`.
- `wrap_text` and `text_wrapped` break lines between Chinese, Japanese and Korean characters
  (they only broke at spaces), keeping 。、」 at the end of a line.
- `text(..., chars = n)` and `text_wrapped(..., chars = n)` draw the first n characters where
  the whole text puts them: dialogue that types itself out.
- `story(script)`: a story written as Ren'Py writes one (`label`, `character`, lines, `menu`
  with conditions, `$ trust += 1`, `if`/`elif`/`else`, `jump`, `call`/`return`, and commands
  such as `show mira happy` for the game), stepped through with `st.next()` and `st.choose(i)`;
  `st.save()` and `st.load(s)` keep its place, even after the script changes elsewhere.
- `sloppy new tale story`: a story game to start from (its script as Ren'Py's, a dialogue box,
  choices, portraits, its place kept between runs). `sloppy new a/b` makes `a` too.
- `on_quit`'s last line may give a value (`on_quit = (): save_value(...)`): it is dropped.
- `text_rich(s, pos, size, color, width, chars)`: `[color=yellow]...[/color]`, `[b]...[/b]` and
  `[i]...[/i]` where they are in the text, wrapped to a width, typed out with chars.
- `img.resized(w, h)` (a thumbnail), `free_texture(t)`, `xs.get(i)` (an element or none).
- `"{i}plans"` and `"{color=#ff0}gold{/color}"`: the errors say how to write the braces as
  text (they said "unknown name 'i'" and "`#` starts a comment").
- `sloppy watch` with its input not a terminal (run from a script, or with `< /dev/null`)
  restarted the game on every change, losing its state: it reloads in place now.
- A script (no `update` or `draw`) that makes a texture or loads a font opens no window: it
  draws with the software renderer, as `render_image` does.
- Screenshot runs play no sound: the mixer keeps to the frames' clock, so fades and
  `audio_time()` are the same every run.
- `UiStyle` and `HudStyle` (`ui_style`, `hud_style`) are in the API reference.
- A `ui_` menu shown again (back from Settings to the title) has the item it was left on
  chosen, not its first.
- `load_font` makes its glyphs on all cores: 0.2 s to 0.08 s for a font.
- `load_font` reads OpenType fonts with PostScript outlines (.otf, CFF), CJK ones too (Noto Sans
  CJK, the Japanese, Chinese and Korean font most systems have): it stopped with "not supported".

From an online arena (2-4 players, native and browser clients, a lobby, reconnects):
- `srv.run()` ticks a server 60 times a second on time. The loop the docs showed (`update`,
  then `sleep(1/60)`) ticked a little slower than the clients, whose inputs then piled up:
  150 ms of lag on one machine. A server also takes one extra input now and then from a client
  that is ahead, so a slight difference in clocks cannot build up.
- `c.connect(host, port, hello = "...")` and `srv.hello(p)`: a name or token sent with the
  connection. `c.disconnect()`; `connect` again works with the same client.
- `srv.lag(ms, jitter)` and `c.lag(ms, jitter)` simulate a slow network; `srv.waiting(p)` says
  how many of a player's inputs wait.
- Worlds travel compressed: a quarter of the bytes.
- A web page's `env("JOIN")` reads `?join=` too (URL parameters in any letters): the arena
  example said `?join=` and was ignored.
- A screenshot run of a connected client keeps to real time (as fast as possible, it sent its
  inputs faster than the server took them).
- A warning when a program uses a library struct's own `__` field (`c.__peer`).
- `net.why(peer)` says why a connection failed ("no machine named 'x' was found", "refused:
  nothing is listening on port 4600 there", "no answer in 10 seconds"), and netplay's
  "could not connect to the server" says it too.
- `SLOPPY_INPUT` keys type punctuation as a US keyboard does (shift+period is `>`).
- `text(..., mono = true)` (and `text_width`, `text_centered`): every character in a cell of
  one width, so `"{name:<12} {score:>5}"` columns line up with the built-in font.
- The game's hook as it ends is `on_quit = ():` (it was `quit`, which replaced the library's
  `quit()` that closes the window).

- `from_text`, `from_json` and `load_value` read structs nearly twice as fast (field names and
  numbers are read where they are, not copied first); `csv_rows` is 30% faster.

## 0.16.0

From data analysis (a CSV of 200k sales, group-bys, a regression, charts):
- `render_image(w, h, draw)`: a picture drawn with the 2D functions, exactly w x h pixels, from
  a script with no window or display (`save_png` it: a chart).
- Charts: `c = Chart(title = ..., x_label = ...)`, then `c.line(xs, ys, "name")`, `c.points`,
  `c.bars(labels, values)`, `c.histogram(values, bins)`; axes with round ticks, a grid and a
  legend. `draw_chart(c, rect)` in a game's draw, `chart_image(c, w, h)` for a picture.
- `r.next_normal(mean, sd)`: normally distributed numbers from a seeded `Rng`.
- `from_csv[T](text)`: each row a struct, its columns by the header's names, numbers checked
  (an empty one or NA is NaN, or none in an optional); 200,000 rows in 0.7 s with 47 MB. Blank
  lines no longer make rows.
- A matrix prints a row a line with its columns lined up (6 significant digits, the middle of a
  large one left out); `to_text` and lists keep the exact one-line form.
- `not mask` works element by element (NumPy's `~mask`); `NAN`; `variance` of whole numbers;
  `max(a, b, c)` and `min(a, b, c)`.
- Fixes: a `soa` array indexed with a mask or an array of indexes gave garbage (now a soa array
  of those elements); Vulkan stopped (`vkAllocateMemory failed`) drawing 100,000 shapes in a
  frame on a GPU without resizable BAR; the software renderer drew text blurred (its edge twice
  as soft as the GPU's); a `[loop ...]` with its body on the next line was reported at column 1.

From a roguelike (a dungeon, field of view, monsters that chase, items, saves):
- `field_of_view(grid, cell, radius)` (shadowcasting: what a cell sees past walls) and
  `line_cells(a, b)`; `path_step`, `path_distance` and `path_field` (a Dijkstra map) on grid
  cells (`ivec2`), with `taken = [...]` cells a step avoids (other monsters).
- The number pad: `Key.kp0` to `Key.kp9`, `kp_period`, `kp_plus`, `kp_minus`, `kp_star`,
  `kp_slash`, with NumLock on or off, on Linux (X11 and Wayland), Windows, macOS and the web.
- Typed text (`text_input()`, `hud_text_field`) follows the keyboard's layout on Linux: on
  Wayland it assumed a US keyboard (an AZERTY "a" typed "q"; AltGr and accented keys typed
  nothing), and on X11 only ASCII was typed.
- `quit = ():` runs as the game ends (its window closed, a page closed): the place to save.
- `delete_data(name)` forgets saved data (a game over), in a web page too.
- `if let t = e and t != "":` binds and tests at once; `'a' + i` is a character code as
  `i + 'a'` is (single quotes: no warning); `c in "aeiou"` for a character (a byte).

From command-line scripts (a build runner, a file renamer, a log reader, a duplicate finder):
- `parse_args[Options]("what it does")` reads the command line into a struct: `bool` fields are
  flags (`--verbose`, `-v`, `-vq`), others take a value (`--out x`, `--out=x`, `-o x`; numbers
  checked, enums by name), the last list field gets the other arguments, and `--help` is made
  from the fields and their defaults. A mistake is said with that help, and exit code 2.
  `read_args[T](words)` does the same without exiting, for tests.
- `run_program` and `run_shell` take `show = true` (the program's output shows as it runs,
  after what was printed before it) and `cwd = "dir"` (where it runs).
- `open_file(path)`, then `loop let line = f.read_line():` reads a file of any size a line at a
  time (96 MB in 0.5 s with 23 MB of memory); `f.read_bytes(n)`, `f.close()`.
- `main = () -> int` gives the exit code (in a web build, one other than 0 ends the program).
  A function whose last line is `exit(...)` or a panic (`die(msg)`) ends every path through it:
  `if ok: return x` then `die("...")` needs no value.
- `sloppy test file.jo words` runs only the tests with one of the words in their names; a test
  that calls `exit()` fails instead of passing.
- Text past ASCII: format widths (`"{name:<12}"`) and `pad_start`/`pad_end` count characters,
  not bytes; `upper`, `lower` and `capitalize` know accented Latin, Greek and Cyrillic letters;
  regex `\w` and `\b` take letters of any script.
- `file_error()`: why the last file operation that failed did ("permission denied", "no such
  file or directory", "the directory is not empty"), on Linux, macOS and Windows.
- `regex_error(pattern)`: what is wrong with a pattern a user typed, without stopping.
- `rename_file(a, b, replace = false)` fails when `b` is there, checked as it moves (no race
  between a check and the rename).
- `parse_date("2026-10-14T08:15:03+02:00")` reads ISO dates and times (a Date, or none).
- `sha256(bytes or text)`, `abs_path(path)`; `if let` in a comprehension
  (`[loop s in fields: if let n = to_float(s): n]`).
- `glob` leaves out hidden names (`.git`, `.env`) unless the pattern starts them with a dot, as
  the shell does, and `glob("src/*.jo")` lists one directory instead of walking all below it.
- `is_dir` is true for a directory that cannot be read; a CSV's byte order mark is not part of
  its first column's name; printed strings show `\r` and control characters as escapes.
- An untyped parameter with a default (`loud = false`) takes the default's type when a call
  leaves it out (it said "cannot infer type parameter"). `'{'` is a brace.
- The run cache (`sloppy-cache` in the temporary directory) stays under 500 MB.
- A warning for `@lib("libc.so.6")` in a Windows build (and a DLL in a Linux or macOS one): the
  program stopped when it called the function.

## 0.15.0

From a strategy game (1000+ units, flow fields, spatial hashes, save/load):
- A `soa` array in a saved struct lost the whole save: it was written as its inner arrays and
  could not be read back, and `load_value` gave the default without a word. soa arrays print
  and save as the array of their elements now, and read back; `load_value` says on stderr when
  what is kept does not read. Generic functions can take `soa T[]`.
- `from_text[S](f(x))` failed: the call's type arguments were taken by the call inside its
  argument.
- `parallel_range` and the other parallel helpers cost 0.4 ms a call on an idle machine and
  2-4 ms on a busy one (the caller waited for every worker thread to wake, even with nothing
  left to do): 0.004 ms now; the caller waits for the work, not the threads.
- `path_grid`'s flood is 10x faster (2.1 ms to 0.2 ms for a 128 x 128 grid); its docs say what
  it keeps (256 goals) and when it forgets them.
- `SLOPPY_SOFTWARE=1` with no display runs without a window (a benchmark with SLOPPY_FRAMES and
  SLOPPY_STATS failed to open one); a screenshot run's mouse starts in the middle of the window
  (in the corner, a game scrolling at the screen's edge scrolled); `SLOPPY_COPIES` with
  `sloppy game.jo` reports the game's copies, not the compiler's.
- Clearer errors: `{int}` for a set (a map to bool), `T` in a function that does not name its
  type parameters, a soa array's `mut` element in a combined loop; `mouse_button_pressed`,
  `get_mouse_position`, `is_key_down`, `delta_time` and the like name what Sloppy calls them.
- A game's own interface, placed anywhere and worked with the mouse or a finger: `hud_button`,
  `hud_panel`, `hud_bar`, and `hud_hovered()` so that a click on the interface is not also a
  click on the world behind it (the `ui_*` menus are a centered column, for menus).
- `Heap[T]`, a priority queue: `h.push(x, priority)`, `h.pop()` gives the least first (A*'s
  open list, events by time).
From a level editor (painting, layers, objects with properties, undo, save and load):
- `hud_text_field` (takes the keyboard when clicked, gives it back on Enter, Escape or a click
  elsewhere), `hud_checkbox`, and `hud_button(..., selected = true)` for tools and tabs;
  `ui_typing()` says a text field has the keyboard, so a game's letter shortcuts wait.
- SLOPPY_INPUT: `text=` with spaces runs to the next item (it took the rest of the line), and
  ctrl+letter or alt+letter types nothing (a scripted ctrl+z typed a "z").
- `to_json(x, 2)` keeps arrays of numbers on one line (a level's rows were one number a line).
- `loop mut` over `g.enemies` with `respawn(g)` in it says the call takes all of `g`; changing a
  character of a string says how; `has_point`, `mouse_scroll`, `text_size`, `get_ticks`,
  `str_to_int`, `list_files`, `erase`, `input_text`, `deep_copy` name what Sloppy calls them.
- Docs: saving to a file the player names (`write_file(path, to_text(x))`), thin lines at the
  software renderer's half resolution; examples/tiles.jo without needless `f32(...)`.
- Docs: what soa arrays have and do not have, and that reading a whole element reads every
  field; what a parallel call costs; `time()` for measuring code.

- Lines between tiles in web pages, flickering as the camera moved (seen on a scaled laptop
  screen): with the page's antialiasing, pixels along a tile's edge were shaded at their
  centers, outside the tile, so the texture was read past it, from the next tile in the
  tileset. The 2D shader reads within what each pixel covers now (centroid), and a part of a
  texture is read a little inside its edges (half a texel for smooth textures, which blend the
  next texel in).
- runtests: a test that runs out of time in the Wine or arm64 container is stopped there too
  (stopping `podman exec` left the program running inside, for hours).

From a music toy (a step sequencer and rhythm game):
- `play(s, delay = seconds)` starts a sound to the sample, and `audio_time()` is the mixer's
  clock: notes land on the beat whatever the frame rate (they started with the next frame's mix,
  up to a frame late).
- The mixer's soft clip made a signal just past 1.0 quieter than one just under it (1.01 came
  out 0.77, 0.99 as 0.99): a smooth knee from 0.75 now, louder never quieter.
- Fades change the volume every sample (they stepped once a mix call, which clicked).
- Without a sound device (or with SLOPPY_NO_AUDIO), sounds still end and fades finish: the
  mixer runs by the frames' time (voices piled up, `is_playing` stayed true).
- `note_freq` stops with a message for a name that is not a note (it gave 0); `midi_freq(n)`.
- `mtof`, `midi_to_freq`, `load_sound`, `play_sound` name `midi_freq`, `load_wav`, `play`;
  a keyword as an argument's name (`play(s, when = 0.1)`) says so.
- `Dir(n)` gives a simple enum's variant by its number, the other way from `int(Dir.east)`,
  checked when the program runs (`Key(int(Key.n1) + i)` for the number keys).
- `SLOPPY_INPUT` turns the mouse wheel (`3:wheel=1`); screenshot runs are the size asked for on
  a scaled Wayland display (the compositor's scale came at a different time each run).
- Docs: `dt` is at most 0.1 s (a clock reads `elapsed()` or `audio_time()`), `Sound(samples)`
  for synthesis, how the mix pans and limits, `melody`'s step in beats.

## 0.14.0

- Debug builds (the default) run array and reference-counting code faster on x86-64, arm64
  (macOS, Linux) and the web: making an
  array unique before a write and adding or dropping a reference are done inline when they can
  be (an unshared array, no threads running), and through a stub that keeps every register when
  not, so the register allocator never sees a call. nbody 1.8x, fannkuch 1.6x, sieve 1.4x and
  the swarm game benchmark 1.15-1.2x faster, with compile time unchanged (the IR stays one call
  each; release builds already inlined these). On arm64 (measured under qemu) nbody 1.8x and
  fannkuch 3x; in web pages (node) nbody 1.4x and swarm 1.3x.

- `sloppy test`: a failing test says FAILED under its name, with why indented below it and
  "in this test" for the test's own line (it said "panic:" and "the top level of").

From a 2D physics puzzle (a slingshot and cut-the-rope game with joints and sensors):
- A fast body met a wall at some speeds without a contact: the sweep that keeps fast bodies
  from passing through put it just off the surface, so no contact came and the speed it kept
  carried it back each step, held there and moving again later. It stops a little into the
  surface now, and the contact takes its speed (or bounces it).
- `bounce = 0` no longer rebounds (it came back at 30-150 px/s): after the positions move, the
  contacts are solved again aiming at the bounce alone (Box2D's relax pass), so the speed that
  pushed overlap out is not kept.
- `w.separated()`: the pairs that stopped touching in the last step (a body leaving a sensor).
- `m[k] = .wood` and `m.get(k, .ground)` for a map of an enum (the shorthand said the enum had
  no such variant).
- A function ending in a `match` whose arms give a value and none says the match is what the
  function gives back, and how to give back nothing.
- `SLOPPY_FRAMES=n` without a screenshot runs n frames and exits.
- Docs: 2D units (mass is density times area / 100; what an impulse is), how friction and bounce
  combine, that fast bodies are swept, that circles roll on (damping stops them), `add_body`'s
  frame at the center of mass, `outlines` for bodies of parts, `physics.box_part` with its
  module's name.

From publishing a game to the web (a one-button runner, tested in a phone-sized browser):
- `touches()`: every finger on a touch screen (the first is still the mouse), for on-screen
  buttons; `touch_input()` says the last input was a finger.
- `toggle_fullscreen()` from a tap works: browsers allow fullscreen only as a finger lifts (or in
  a click or key), so a request made while the finger is down is made then.
- A page's sound stops while its tab is hidden (its game gets no frames), and starts again when
  it is shown.
- A panic in a page shows where, as a native program does (`in update (game.jo:12)`, `called
  from ...`): the page reads the browser's wasm frames against a table of the program's calls
  in the module (about 0.7% of its size).
- The page says "loading…" while it downloads, and asks for no favicon when the game has none.
- `sloppy new`'s arcade game pauses when the window loses the focus (a click outside an itch.io
  frame).
- `save(...)` and `load(...)` suggest `save_data` and `load_data`; `window_visible`, `is_mobile`
  and other guesses name `window_focused`, `touches` and `touch_input`; a name's first word
  suggests the names it starts.
- `sloppy build --help` (and check, test, fmt, new, watch) shows the usage.
- START: phones (touch, orientation, fullscreen), focus, where saved data is kept, sound in
  hidden tabs, and that reading a missing map key is an error while `+=` starts it at zero.

From a first 3D game (a third-person collect-and-dodge game, built from the docs alone):
- A warning for `q1 * q2` on quaternions (values from `quat_*` functions and variables made
  from them): `*` multiplies the parts of the vec4s one by one; `quat_mul` turns. `q * v` and
  `m * v` (vec3) say `quat_rotate`, `transform_point` and `transform_dir`.
- A third-person camera: `follow_camera()`, with `flat_forward`/`flat_right` for walking where
  it looks and `pull_in` to keep it out of walls (after a `sphere_cast`).
- `Shake.offset3d(right)`: the screen shake for a 3D camera, in meters.
- `physics3d.terrain_triangles(size, divisions, height)`: the ground of a `terrain_mesh`, for
  `add_mesh`; `terrain_mesh` says where it lies (centered, `size` across).
- One yaw for the cameras and the 3D template (0 looks along -z, more turns left), and the
  directions written down in one place (draw3d: models face +z, `facing` turns -z).
- Docs: `draw_mesh` with alpha below 1 is see-through; physics layers and masks
  (`set_layers`); `OrbitCamera.drag_left`'s comment was cut off in the library list.
- The color warning leaves values a little above 1 alone (`rgb(3, 3, 3)`, brighter than white,
  for a flash in 3D); it is for 0-255 colors.
- `physics3d.world()` suggests `World`, the module's own name (it suggested `words`), and a
  name that starts a longer one suggests it (`poly`: `polygon`).
- A `[loop ...]` with its expression on the next line says it goes on the colon's line.
- The first scripted mouse position (`SLOPPY_INPUT`'s `mouse=`) is where the mouse is, not a
  move from (0, 0).

From a game jam (a twin-stick shooter built from the docs alone):
- `screen_to_world` and `world_to_screen` in `update` use the last `camera2d` (the transform is
  reset at the start of each frame, so in `update` they ignored the camera): aiming at the mouse
  works where it is read.
- `tilemap_move` says once when a box starts inside a solid tile (most often a floor tile left
  solid), and `tile_layer`'s doc says every tile is solid until `set_tile_shape` says otherwise.
- A warning when values given in order stop one or two fields short of a struct's number, text
  or struct field without a default (`P(1)` for `P(x, y)`: y would be zero unnoticed).
- A warning for `random(1, 6)` (a number with a fraction: `random_int(1, 7)` is a die). The
  `random_int(1, 6)` warning has a quiet form for when 1 to 5 is meant: `random_int(1, 5 + 1)`.
- `def move(self):` inside a struct says structs have no methods, and how the function is
  written instead.
- `SLOPPY_INPUT` takes spaces between items as well as commas, and reports a mouse position it
  cannot read (`mouse=900x2zz` was the mouse at y 0).
- `text`, `text_centered` and `text_wrapped` take `shadow =` (a color drawn under the text, to
  read over a busy scene); the library list's first-game section has the camera (mouse in the
  world), particles and screen shake.
- A variable given a value and never used, named as a global of a file this one does not
  `use`, says so and which file to `use` (the assignment made a variable of its own instead of
  changing the global).
- A name or function the program has in a file this one does not `use` (only in a file that
  file uses) says which file to `use`; `print(limit)` said to put it in quotes.
- The same warning at the same place is printed once (a generic function checked for several
  types printed it for each).

From a second pass with someone who had not programmed before:
- Warnings: a variable given a value and never used (`scor = score + n` in a function, with the
  global it was likely meant to be); a function nothing calls; drawing in `update` (the screen is
  cleared before `draw`); `clear` after drawing in `draw`; `sleep` in `update` or `draw`;
  `score += "1"` (the character code, not 1). The `random_int` warning only for the usual dice
  and percent ranges (`random_int(1, 6)`, `(1, 100)`), not for every range.
- Clearer errors: `print(hello)` (text goes in quotes); `enum Mode = ...`; `draw:` and
  `draw = :` without `()`; `repeat 5:`; `thorns = Rect[]` for an empty typed array; a text
  compared with a number; a string with no closing quote followed by more code, at its line.
- `polygon` draws concave shapes (a star, an L) correctly; it filled them as if convex.
- The built-in font has accented letters (é, ñ, ü, ß, Æ: all of Latin-1) and common punctuation
  (curly quotes, dashes, …, •, €, ™); they showed as `?`.
- An index past the end says when it is the length (the last is index n - 1) or the array is
  empty; a slice out of bounds is shown as written (`s[1..9]`, not `[1..10)`), with the last
  index; a missing map key reads as a sentence.
- The playground keeps more than one program: a menu of your programs (new, rename, delete),
  each saved as it is edited. Choosing an example no longer replaces what you wrote: an example
  becomes a program of yours when you edit it.
- Docs: the timer number in `every(1, 2.0)`; a tutorial section on many moving things (a
  struct, `loop mut`, `retain`).

## 0.13.0

From a teacher preparing a first programming class:
- `input(prompt)`, `input_int(prompt)` and `input_float(prompt)`: a line typed by the user, and
  numbers, asked again until what was typed is one.
- Web pages read standard input: in a browser, a box asks for each line (showing what the
  program printed last), so programs that ask questions work in the playground; under node,
  the real standard input.
- A web page (a debug build: the playground's) stops a loop that runs 5 seconds without a break,
  with a message, and shows what the program printed before it; the page hung.
- A warning for `random_int(1, 6)` (a die): the upper end is left out.
- Clearer errors: printing an empty `[]`; text and a number added (`age + 1` with age read as
  text); a character's code compared with text, or added to text; `print(hello world)`; a
  function that only prints used for its value; `(x: int) x * 2` without its `:`; a function
  whose last line makes a variable instead of giving it back; a line indented to no level
  above; an array of mixed kinds; a string without its closing quote; `!` on none at run time;
  "an int" for "a int".
- The REPL: `:type print` (and the other built-ins, `len` of an array) says what they are;
  `:quit`, `:exit` and `:doc` work.
- docs/TEACHING.md: running it in a class, programs that ask questions, an order to teach things
  in, the usual mistakes, and grading with `sloppy test`.

- Rebound: choosing an upgrade with the mouse no longer turns the shield toward the card (it
  stays where it was until the pointer moves), and the arena waits half a second, the shield
  free to turn, before the bolts move on.

From a performance-minded C programmer:
- Release builds: a temporary value the optimizer made could take what an earlier, larger
  function had known of the same slot (that it was some constant) and be replaced by it. Found
  by the unsigned division above; it could have hit any function after a larger one.
- Release builds vectorize integer sums over a loop (and `&`, `|`, `xor`), with partial sums in
  a vector added together after: 5x faster with AVX2, 3x with SSE2.
- `SLOPPY_COPIES=1`: each copy of a shared array of 64 KB or more (or a size given) is told with
  the line that changed it, to find hidden copies and the frame spikes they make.
- `sort_by`/`sorted_by` work out each element's key once (it was twice a comparison): 1.5x
  faster with a cheap key, much more with a costly one.
- `sloppy check` lowers the program too (without making code), so it finds what a build would:
  a `loop mut` that resizes its array, data races, shader errors (it passed such programs).
- `s = s + x` on text or an array is written `s += x` by the compiler: it adds to the end in
  place instead of copying all of s (a loop of them took time growing with the square).
- Release builds divide unsigned integers by a constant with a multiply (6x faster; `str(i)`
  and `"{i}"` 2.6x faster, as fast as C's snprintf).
- The CPU path of compute functions (OpenGL, the web, no GPU) copies its parameters once per
  run of ids instead of once per id: 9x faster, and no longer slower with more threads.
- A warning when arithmetic on a narrow type is widened right after (`n: int = a + a` with
  `a: u8` is worked out as a u8, so 200 + 200 is 144); an unknown attribute (`@inline`) is an
  error; `_ = f()` drops a value on purpose; `q->x`, `*p` and a loop after a loop's colon say what
  to write instead.
- LANGUAGE: a Performance section (copies, allocation, the loops release builds speed up,
  narrow numbers, profiling).

From a first try at multiplayer:
- A client-server game's server applies at most one input of each player a tick over time (a
  few more after a pause): a client that sent two a tick moved twice as fast.
- `s.problem` (rollback) and `c.problem` (client) say what is wrong, once on stderr too:
  packets that cannot be read (another build of the game), two machines with one player number,
  a player or the server not heard from for 5 seconds, the games differing (`s.desync`), no
  connection; `c.connected()` turns false when the server is gone.
- A module's function named as a library one (`cm.step`) can be given where a function goes.
- `s.udp` in a web page: a warning when building, and a message that says to use a relay.
  `?STUN=` in a page's address is the empty text (it was "1"; `?stats` alone is still on).
- MULTIPLAYER: what a tick must not do (globals, sounds: a rollback plays it again), testing with
  different seeds, what a client predicts with, a server without a window, losing the server.

From a game jam entry shipped to the browser:
- Web pages bigger than 4 MB are compiled off the main thread: above 8 MB (a few music tracks
  embedded) Chrome and Edge refused to start them.
- `-o game.zip` or `-o game.html` builds the web page, and `-o game.exe` the Windows program,
  without `--target` (it wrote a Linux program under that name); `--target web` is `wasm`; the
  output's directory is made if it is not there.
- Web pages let go of the keys held when the page loses the focus (a click outside an itch.io
  frame left the player walking), and try to start the sound at every key until it runs (Safari).
- Warnings: a web page that saves without a name of its own (pages on one site share their
  storage); `read_file("...")`/`read_bytes("...")` in a web page (it has no disk: `embed`).
- `window_focused()`: false while the player is in another window or tab (a game may pause),
  on every system and in web pages.
- `load_wav` given an Ogg file says to use `load_ogg` or `load_music`; a missing map key says
  which key it was nearly (`assets["playr.png"]`: did you mean player.png?).
- START: shipping to itch.io, and what to leave out of a Windows download.

From a Python programmer's scripts:
- `sloppy file.jo` keeps each program's build apart by its path: two `main.jo` in two
  directories, run at once, no longer run each other (or fail to write); the build is written
  beside and put in place, so a copy still running is not written over; builds not run for a
  week are removed. `args()[0]` is the program as it was named (`tool.jo`).
- `main()` called by the file itself (at its end, or in an `if`) runs once, there.
- Files: `make_dirs`, `delete_dir`, `rename_file`, `copy_file`, `append_file`, `file_time`,
  `walk_dir` (every file under a directory) and `glob("src/**/*.jo")`, on every system;
  `run_shell("ls *.jo | wc -l")` runs a command line through the shell.
- A warning for `{4}` in text (a regular expression's repeat puts the number 4 there instead:
  `{{4}}` or `r"..."`); `sloppy test` on a file without tests, or with pytest's `test_` functions,
  says how a test is written instead of "0 tests passed".
- Errors for Python's habits: `with open(...)`, `global`, `assert x, "msg"`, comprehensions and
  generators, `import re`/`sys`/`os`/`json`/..., `os.path.join`, `Counter`, `defaultdict`,
  `open`, `sys.argv`, `t[0]` on a tuple, `m.groups()`, `"{:.2f}".format(x)`, `"%.2f" % x`,
  `{x!r}`, a ternary in braces, `range(3)`, `set()`, `", ".join(ints)`, `regex("\d+")`, a
  module's function without its name, `isinstance`, `xs.index`, `isdigit`, `partition`,
  `splitlines`; no `?T16` in messages. The "nothing calls load" warning is gone, and
  `updated()` is no longer taken for a misspelled `update`.
- START: Scripts and tools, and a Coming from Python table.
- The 3D tutorial (Breakwater) without casts that are not needed (`f32(...)`, its `v3`), with
  `facing` for aiming, and a note on `import physics3d` for a bigger game.

From a Unity developer's first 3D game:
- Physics: `mass =` on every `add_...` (instead of the density's), `w.set_mass(b, m)`, in 2D
  and 3D; physics3d's header says what a density of 1000 weighs. `w.contacts()` forgets a body
  removed after the step, so reading the rest of them no longer stops the game.
- Rotations: `quat_euler(pitch, yaw, roll)`, `facing(dir)` and `quat_facing(dir)` (turn a
  model's front, -z, toward a direction), `quat_inverse`, `quat_from_mat4`, `scaling(2.0)`.
- Post effects (bloom, grading) leave the 2D drawn after the 3D (a HUD, text) as drawn, as
  Unity's overlay UI; a 2D game's are on all of it as before (`include_hud = true` for a 3D
  game's HUD too).
- A warning for an angle in degrees where radians go (`rotation_y(45)`: `45deg`).
- Errors for Unity's and C#'s habits: `transform.position`, `Input.GetKey`, `Mathf.Clamp`,
  `Debug.Log`, `GameObject`, `Instantiate`/`Destroy`, `GetComponent`, `Physics.Raycast`,
  `SceneManager`, `Quaternion`, `new List<T>()`/`new Color(...)`, `foreach (...)`/`switch
  (...)`/`while (...) {`, `void Start()`, `float speed = 5`, `public` fields, braces for a block,
  `(): int:`, `$"..."`, `v.normalized`/`v.magnitude`, `vec3.up`, `xs.Add`/`Remove`, a field of a
  physics Body (`b.velocity`: ask the world), `w.pos(b).y = 3` (a copy: `set_pos`),
  `gems.remove(g)` (remove takes a position), and Unity's collision callbacks (a warning).

- 2D physics: bodies of several shapes, `w.add_body(pos, [.circle(vec2(-40, 0), 15),
  physics.box_part(vec2(0, 0), vec2(80, 8))])`, held together as one (mass, center and turning
  inertia from all of them); `add_polygon` with a concave outline (an L, a U, a star) cuts it
  into convex parts instead of taking its convex hull; `w.outlines(b)` gives each part's.
- 2D physics: rays (and the sweep of fast bodies, which uses one) look only at bodies whose
  bounds the ray crosses: a scene of 300 bodies steps 1.7x faster.

- Errors: a color written as text (`"yellow"`: `YELLOW`, `rgb(...)` or `hex("#ff8800")`); an
  int variable given a fraction (`time_left = 30`, then `-= dt`: write `30.0`); a constant
  changed (make it a variable, rather than `let`); no compiler-made names or `?T` in
  "cannot infer" errors.

- `enemies = []` at the top level takes its type from what a function pushes into it, as a
  local array does (it needed `enemies: Enemy[] = []`).

## 0.12.0

For newcomers (from a first-time programmer working through the tutorial):
- New warnings: a value made and dropped on a line of its own (`x == 6` for `x = 6`, `speed +
  1`, `if hit: true` for `return true`); `got / total * 100` with whole numbers (0 for 3 of 4);
  `Draw = ():` or `updte = (dt: f64):` near the name the game calls, which then never runs.
- `update` and `draw` give nothing back: their last line is a statement (a value there was a
  type mismatch reported at `update =`).
- Drawing outside a frame (`circle(...)` on a line of the top level) says to draw in `draw`
  instead of crashing on a null pointer.
- Clearer errors: an enum's variant without its dot (`if screen == title`, `key_pressed(space)`,
  `screen = play`, `screen = .title` with no type to go by); a function where its result was
  meant (`play(sfx_coin)`, `input_axis * 400`); a missing `,` at the end of a line in a list; a
  quote inside text; a line one space too deep; `rect(...)` where `Rect(...)` was meant; an
  Image given for a Texture; `xs.add`/`xs.delete`; a variable made in `update` used in
  `draw`; `x = []` at the top level (the type of what is pushed later is suggested); a call
  that may give none (`to_float(load_data("best"))`: `?? ""` says what to use then) and an
  optional compared with `<` (said with the line that made it).
- Fewer words from compilers in errors: "no version of 'rect' takes 4 arguments" (said of all
  of them, not of the last one tried) for "no matching overload"; a value that may be none says
  what to do instead of "unwrap it".
- `draw()` inside `draw` (or `update(dt)` inside `update`) is an error: the game calls them.
  A menu left without `ui_end()` frame after frame stops with a message saying so.
- `melody("H4 ...")` stops with what a note is, instead of leaving the note out; a note without
  its octave (`"C"`) is in octave 4.
- The tutorial explains what it uses as it comes (functions giving back a value, arrays, `loop
  i < n`, enums and `.play`, `??`, where variables live) and shows a picture drawn with
  `sprite`; START's first program is simpler; the library's page starts with what a first
  game needs.
- A menu (ui_begin) no longer gives the focus to the item the pointer happens to rest on when
  it opens; only a move onto an item takes it.

Compiling:
- Up to five errors are reported at once: after an error in a function, the compiler checks the
  program again without that function's body for the next one (only when there are errors:
  a program that compiles is checked once, as before).
- Machine code is made on several processors (on Linux and macOS, for x86-64): after a program
  is lowered, forked workers each make the code of a run of its functions, release builds'
  loop versioning and hoisting with it, and the compiler joins them in order. The program is
  the same bytes as before. 10% off building bench/big.jo and the compiler on a busy 8-core
  machine; more on an idle one. `SLOPPY_EMIT_WORKERS=1` makes it all here.

Language and library:
- Tiled maps as Tiled saves them by default: `load_tiled("maps/level1.tmx", embed_dir("assets"))`
  reads XML maps (.tmx) as well as JSON ones, with tilesets in files of their own (.tsx, .tsj)
  and their images, each found next to the file that names it. CSV and XML layer data too.
- 2D physics: a body moving more than half its size in a step is swept along its path, so a
  fast bullet no longer passes through a thin wall between two steps.
- `embed_dir("assets")`: every file under a directory built into the program, as a map from
  its path there (`assets["sfx/hit.wav"]`).
- Effects on 2D drawing (LÖVE's `setShader`): `use_effect(fx, params)` runs a fragment function
  of your own for what is drawn until `no_effect()`, with `fx = make_shader(shader(effect_vs,
  my_fs))`; `base_color(p, u)` gives what the pixel would have been. On every renderer. Uniform
  structs may hold structs on OpenGL too, and `shader()` takes a generic vertex function.
- `ui_text_field("Name", name)`: a line of text typed into a menu (letters and space type
  there instead of moving through the menu; long text shows its end); `without_last_char(s)`
  (a backspace that takes a whole UTF-8 character).
- A parameter's default value may use earlier parameters (`h: f64 = w`, `label = "w={w}"`).
- `loop k, mut v in m` (as `loop mut k, v in m`); `name = (...): ...` at the top level for a
  variable of a function type declared above gives it a new value (it was a second definition);
  `xs[-1]` and `s[-3..]` are errors pointing to `end` (they panicked when run); a warning for a
  division of whole-number literals that gives 0 (`3 / 4 * 100`).
- Web builds can call JavaScript: the build block's `js = "glue.js"` goes into the page and sets
  the program's `extern` functions on `sloppy.env` (`sloppy.text(p, n)` reads text).
- A union passed where a function has an overload for each of its members calls the one for
  what it holds (`loop mut m in mobs: m.step(dt)` with `step` for `Walker` and for `Flyer`; `mut`
  ones change it in place), and a field every member has is read from whichever it is (`m.pos`).
- A warning for a variable whose fields or elements are changed but whose value is never read:
  a copy changed for nothing (`if let e = enemies.find(...): e.hp -= 5`, `first = xs[0]` then
  `first.hp = 9`), the habit of languages where objects are shared.
- From a JavaScript web-game developer pass: `net.send` of text sends a WebSocket text message;
  a panic in a web game shows over the canvas; a web build warns about `sleep`; a multi-line
  lambda followed by more arguments (`f(():\n    a(), 5)`) works; `hex("#ff8000")` (CSS colors,
  with alpha as `#rrggbbaa`); `find_index`; messages for a keyword as a name (`build = ...`),
  `throw`, `export`, `delete`, `typeof`, `import {...} from`, `[a, b] = xs`, `[...xs]`,
  `Array<int>`, C's `for (;;)`, `x = null`, `Date.now()`, `clear("#ff0000")`, a file name where
  its bytes go (`load_texture("hero.png")`: `embed`), `sort` with a comparison (`sort_with`), and
  JavaScript's array and map methods (`every`, `some`, `at`, `shift`, `m.set`, `m.size`...).
- `loop mut x in xs` whose body adds, removes or replaces elements of xs is an error (they were
  visited or skipped as the array changed under the loop); `xs.retain((x): keep)` keeps some in
  place. Assigning to a field of a narrowed optional or union (`x.hp = 7` after `if x is Enemy`,
  for globals and fields) works (only `-=` and the like did), as does `x!.f = v`.
- `Atomic`: a number parallel code changes together (`atomic(0)`, `add`, `get`, `set`,
  `compare_swap`, `set_max`): counts of work done, a flag that stops the other threads.
- `sin` and `cos` of an `f32` (shader code) give an `f32`, computed with shorter polynomials
  (30% faster; the same f32 but for a last-bit difference in 1 of 10000).
- The software renderer is about 3 times faster in games with post effects (Rebound: 45 to 14
  ms a frame in a debug build, 29 to 9 in a release one): bloom's blur and the final composite
  work on its pixels directly, other full-screen passes call their fragment function per pixel
  without rasterizing a triangle, and clears copy instead of looping.
- 2D physics: `weld` (two bodies as one), `slider` (along a line, with limits and a motor: a
  piston, a lift) and `wheel` (a car's: sprung along its suspension, turning, with a motor);
  `joint_translation`; `set_motor` and `set_limits` work on sliders too.
- A web build warns where the program calls what does nothing in a browser (`net.udp`,
  `net.listen`, `tcp_connect`, `tcp_listen`: library functions marked `@no_web("why")`).
- `clip(pos, size)` shows 2D drawing only inside a rectangle until `no_clip()` (LÖVE's
  scissor; screen units, not moved by `translate` or `camera2d`; per render target and frame;
  3D is not clipped), on every renderer.
- `text_wrapped(s, pos, width, size, color, align)` draws text broken into lines at spaces, each
  to the left, centered or to the right (LÖVE's `printf`), and gives the height it took;
  `wrap_text` gives the lines and `text_height` how tall text is. `text_centered` centers each
  line of text with line breaks, `text_width` is that of the widest line, and it works before
  there is a window (it stopped the program with a shader error).
- A row or column of a `T[,]` goes where a `T[]` is expected (`argmax(m[0, ..])`, a function of
  the program's own).
- Matrix products are 6 to 7 times faster (no bounds checks inside; big ones are shared among
  the threads).
- `xs[mask]` and `xs[idxs]` pick elements, as in NumPy (a `bool[]` mask, an `int[]` of
  indexes: `xs[xs .> 0.5]`, `xs[argsort(xs)]`); `xs[mask] = v` and `xs[idxs] = vs` set them.
- `random()` outside parallel code gives the same numbers whether or not a parallel job ran
  (the threads' generators come from the seed, and the main thread uses its own while it helps
  with a job; the software renderer's jobs had moved Rebound's turrets). `x ^ 2.0` is `x * x`
  (3x faster for `xs .^ 2`). `xs * 2.0`, `xs + 1.0`, `xs < 2.0` and `xs ^ 2` on number arrays
  point to `.*`, `.+`, `.<` and `.^`.
- From a LÖVE-developer pass: `update = (dt):` with dt untyped works (the compiler panicked);
  `[Kind.a, .b]` takes the enum from its first element (also as a generic function's argument);
  an `if` choice in a string's braces (`"{if w: 'x' else: 'y'}"`); messages for `#xs`, `..` on
  text, `local`, `{x = 1}`, `~=`, `tostring`, `pairs`, `require`, an `if ... else` right after a
  comprehension's colon; a warning for `keypressed` and the other callbacks nothing calls.
- From a NumPy-user pass: `random()` in parallel code no longer races on one generator (each
  worker thread has its own; `rng(seed + k)` for the same numbers each run); `sum` of floats is
  pairwise (ten million 0.1s make 1000000.0, as NumPy's do); NaN sorts last and makes `max`,
  `min` and `median` NaN; `variance`, `percentile`, `quantile`, `argmax`, `argmin`, `argsort`,
  `cumsum`, `diff`, `prod`, `histogram`, `covariance`, `correlation`, `solve`, `inverse`, `det`,
  `trace`, `diag`, `outer`.
- Removing from a map takes constant time (it rebuilt the map: 10,000 removals from 100,000
  entries took 10 s; now under 1 ms): a removed entry stays in place, marked gone, until half
  are gone. Loops, `keys`, `values`, `len` and printing see only what is there; the debuggers'
  printers (gdb, lldb, Visual Studio) too. Maps are equal with the same keys and values, in any
  order (`==` compared their insides).
- `@cabi` functions called on threads C made (pthreads, a library's callbacks) can allocate:
  once one is called, the allocator tells threads apart by their stacks and gives C's a state
  of their own, taken in turns (several at once crashed).
- `x: T` for a struct with default field values starts with them (as `T()` would), and so does
  a field left out whose own struct has defaults; they were zero, unlike a map's new entries.
- TCP in `import net`: `tcp_connect` (waiting up to a timeout), `tcp_listen`, `tcp_accept`,
  `tcp_send`, `tcp_receive` (waiting up to `wait` for the first bytes), `tcp_closed`,
  `tcp_close`: for tools and servers speaking other programs' protocols (HTTP and the like).
- Maps are faster: a slot keeps half of its entry's hash, so other entries are passed over
  without reading them, and a new key is probed for once (5M int keys: inserting 0.66 s, was
  0.80; looking them up 0.22 s, was 0.31).
- Bytes and bits (lib/std/bytes.jo): `get_le`/`get_be` (and signed), `put_le`/`put_be`,
  `append_le`/`append_be` for numbers in byte arrays; `popcount`, `leading_zeros`,
  `trailing_zeros`, `rotate_left`/`rotate_right`, `byte_swap`; `bytes_from(p, n)` and
  `str_from_c(p)` for C's memory. `reserve` for maps.
- C: `@lib(NAME)` takes a constant; a function value given where C wants a callback says it
  must be a top-level `@cabi` function; `malloc`/`free`/`memcpy` get hints. LANGUAGE.md gains a
  Pointers part with a worked example (qsort with a callback, an out-parameter), what threads C
  makes may run, and how shifts count.
- A warning when `import x` takes a file beside the program while the library has a module x.
- `x == v` with `x: T?` and `v: T` for any T with `==` (it was int only; none is never equal).
- `ivec2(x, y)` and `ivec3` take ints (as `i32(x)` makes them).
- Messages for Godot habits: `extends`, `signal`, a function written inside a struct, `randf`,
  `Color`, `Vector3`, `deg2rad`, `Basis`, `xs.size()`; a warning when `_process`/`_ready` are
  defined and nothing calls them; a function of the wrong type names the parameter that differs.
- `sloppy check` checks `update` and `draw` against what the game loop calls.
- A program's own `insert`, `push`, `len` (and the other built-in array and string functions)
  with an array or string first are used for its calls, where they were ignored.
- `x as f64` between a whole number and a float is an error that says `f64(x)` converts
  (`as` kept the bits); `f64_bits`, `f64_from_bits`, `f32_bits`, `f32_from_bits` for the bits.
- C functions: a `str` parameter is passed as C's `char *` (the bytes, ending in a zero; it
  passed the string's header); an array parameter is an error pointing to `data(xs)`. What C's
  stdio holds (`printf`) is written out when the program ends (it was lost in a pipe or file).
- Regular expressions: `regex(pattern)`, then `s.find(r)`, `find_all`, `matches` (all of the
  text), `contains`, `replace` (with `$1`, or a function of the match), `split`. Groups,
  classes, `\d \w \s \b`, `^ $` at lines, counted, greedy and lazy repeats, `(?i)`; matching
  takes time in proportion to the text (no runaway backtracking), works on characters, and
  skips ahead to where a match can start (a search for a word in 4 MB: 37 ms; Python's: 95).
- A warning for `{hits / shots:.1%}` with whole numbers (the fraction is dropped before it is
  formatted).
- Map comprehensions: `{loop w in words: w: len(w)}` (with `if` filters and nested loops, as in
  brackets).
- `TextError`'s fields are `message`, `line` and `column`, as `JsonError`'s are.
- `{x=}` in a string shows `x=` and then the value (Python's debugging form); a `#` in a format
  puts `0x`, `0b` or `0o` before the digits (`{255:#06x}` is `0x00ff`).
- `a, b = xs` unpacks an array of exactly that many elements (2 to 4; another length panics):
  `key, value = line.split("=", 1)`.
- `words` and `split` with a one-byte separator are about twice as fast (44 MB of text: 8 million
  words in 0.41 s, was 0.78; Python's split takes 0.44).
- Dates: `now()` and `date(t)` give a `Date` (year, month, day, hour, minute, second,
  weekday, offset) in the computer's time zone or UTC, `unix_time()` is the wall clock,
  `unix_time(d)` goes back, `date_text`, `month_name`, `weekday_name`, `utc_offset`. Time zones
  come from the system's zone file (or TZ), with daylight saving time past its table from the
  POSIX rule; Windows asks the system, a web page the browser.
- Paths: `file_name`, `dir_name`, `extension`, `without_extension`, `join_path`;
  `is_symlink`.
- Messages for more habits from other languages: `(x) => x * 2`, `===`/`!==`, a C-style
  `loop i = 0; ...`, backtick strings, `try:`/`except:`, `null` for a missing value, `{x: 1}`
  as an object, `m.key` on a map, `console.log`, `Math.random()`, `set[str]`, `ljust`/`zfill`;
  calling a function on a value that may be none says to unwrap it; a binary file given as
  source says so.
- `assert(x + 1 == 4)` fails with its condition: `assertion failed: x + 1 == 4`.
- `split(s, sep, max)` (Python's maxsplit), `count(s, sub)`, `pad_start`/`pad_end`,
  `capitalize`, `max_by`/`min_by`.
- LANGUAGE.md: an operator precedence table; narrowing after panic and exit; loops over an
  array that changes inside them.
- `is` with a member of an optional union (`f() is A` where f gives `A | B | none`), and with a
  union of some of a union's members (`r is AB`, `type AB = A | B`), narrowing too; `x is A or
  x is B` narrows x to `A | B`.
- At the top level, a global declared after `if r == none: panic(...)` sees r narrowed
  (`s: str = r`), as a function's variables do.
- `sloppy check` checks the test blocks too (only `sloppy test` did).
- `x ^ -n` on integers truncates like `/` (`2 ^ -1 == 0`; `0 ^ -1` panics), where it gave 1.
- `{7:>05}` pads with zeros, as Python does (an alignment ignored the 0).
- `sort` and `sorted` compare with `<` directly instead of through a function value, copy runs
  already in order as they are, and sort largest-first by reversing around the ascending sort
  (still stable): 2 million ints sort in 295 ms in a release build (was 430; C's qsort: 295).
- An error inside a generic function the program defines is followed by notes for the calls
  that made it, innermost first, with the types it was made for
  (`a.jo:13:20: note: in summarize(xs: P[]), called here`).
- Fixed: `assert(ok, "x is {x}")` (a message with something in it) crashed in debug builds when
  `ok` was true.
- `print` and `write` to a file or a pipe are collected and written in large pieces (a million
  lines: 0.25 s, 12 times faster); to a terminal each line goes at once, in one write. Standard
  error, reading input, each frame of a game, `sleep` and the program's end write out what was
  collected first; `flush_output()` does it by hand. `is_terminal()` says where output goes.
- `is_dir(path)` and `file_size(path)`; `read_file` of a directory is none (it was "").
- `exit(code)` ends narrowing as `return` does (`if r is int: exit(r)`, then `r` is the rest).
- Errors: casting a union (`x as int` on an `int | str` gave its bits; `is` narrows), and
  `s as *u8` on a string or an array (it gave the header's address; `data(s)` is what C wants);
  hints for comparing a union with one of its members.
- `@noinline`: release builds call the function rather than copy it into its callers.
- Formats `{x:e}`, `{x:.3E}`, `{x:g}` (as Python's), and `d` and `s` accepted; a format the
  library does not know is an error (`{x:.3z}` printed the number as if it were not there).
- A `@cabi` function can be given straight to a C function's callback parameter.
- `"-" * 40` is forty dashes (it was the character code of `-` times 40), and `3 * "="` works
  as in Python. `find` and `find_byte` look at eight bytes at a time (about 4 times faster on
  long text).
- `sloppy test` runs each test in a process of its own (Linux, macOS): a failing one is reported
  and the rest still run, then "N passed, M failed" and exit status 1.
- Debuggers (`-g`) show the program's globals, top-level variables included; gdb's printer shows
  an empty string as `""` (it failed with a Python error) and keeps to `print elements`.
- Release builds divide by a constant with a multiply (6.6 times faster histogram binning), and
  a loop over a string's bytes by index has no bounds checks, as one over an array has.
- A `match` statement on an enum or a union names each variant or has `_:`, as a match giving
  a value did (the language reference said so; a state added later is not left out quietly).
- Messages for habits from Unity and C#: `new T(...)`, `switch`, `yield`, `x?.f`,
  `struct B(A)`, a field read from a union of structs, a library module used without `import`.

Games:
- Physics: bodies joined by a joint no longer collide with each other (2D and 3D, as in Box2D),
  and 2D pins and rods take out their stretch from the positions after each step instead of by
  extra speed: a heavy weight on a chain of light links swings and stays on it (the last link,
  overlapping the weight, pushed it away and the chain flew apart, up to 1e13 px).
- `Animator`: plays a model's animations by name (`anim.play(robot, "Run")`, again: it goes
  on), fades from one to the next, plays one once (`finished`), `passed(t)` for events such as
  footsteps, and `pose(...)` to draw with.
- Physics: a sensor keeps reporting a body that falls asleep inside it, and does not wake it
  (2D and 3D; its contact vanished, and came back as new when it woke). `overlap_sphere`,
  `overlap_box` and `w.overlaps(character)`: the bodies, sensors too, in a shape or around a
  character (trigger zones, pickups); in 2D `overlap_circle` and `overlap_box`. A character on a moving platform is carried along and
  turned with it (`standing_on`); only lifts carried it.
- `move_toward` for numbers and vec3 (it was vec2 only); `OrbitCamera.drag_left = false` leaves
  the left button to the game; `?stats` in a page's address shows the overlay (only
  `?SLOPPY_STATS` did); docs: cylinder_mesh stands on its base, physics3d's `ground`, rays pass
  through sensors, fast bodies can pass through thin walls (no continuous collision yet).
- `show_cursor(false)` hides the mouse pointer over the window while it still moves (a
  crosshair drawn by the game); with `mouse_lock` the two keep track of each other (Linux X11
  and Wayland, Windows, macOS, the web).
- `tile_layer` keeps rows of spaces (open sky above a level); only the empty line after the
  opening quote and the closing quote's line are left out. Rows of spaces at the top were
  dropped, moving the tiles up against positions read from the same text.
- Screenshot runs (`SLOPPY_SCREENSHOT`) ignore the desktop's keys, mouse and typing, so they
  are the same each time on a machine with a display; only `SLOPPY_INPUT` gives them input.
- 3D particles: `Particles3D` with `emit` (in a cone around a direction), `update` and `draw`
  (glowing sparks that add up, or blended smoke and dust), soft dots facing the camera.
- `time_scale(s)`: update gets dt times s (slow motion, 0 pauses the game while it still
  draws and takes input); `frame_time()` is the scaled dt.
- Audio fades: `fade_volume(id, v, seconds)`, `fade_out(id, seconds)` (stops at the end) and
  `crossfade(old, sound_or_music, seconds)` from one loop or song to the next.
- Fixed: `set_fixed_rotation` did not keep spheres, capsules (3D) and circles (2D) from turning
  when they slid with friction; such a body now never turns, whatever hits it.
- `screen_ray(mouse_pos())`: the ray from the 3D camera through a point on the screen, for
  picking with a raycast. `angle_difference`, `turn_toward` and `approach_angle` turn the
  short way round. `find_animation` says (once) when a model has no clip of that name, and
  which it has.
- `SLOPPY_INPUT`'s mouse moves count as the pointer moving (`mouse_delta`, drags, mouse look).
- The 3D reference says which way things face (y up; a turn about y takes +z toward +x; glTF
  models face +z), and START.md how Unity's and Godot's ideas map to Sloppy's.
- Gamepads on macOS, through Apple's GameController framework (Xbox, PlayStation, Switch Pro
  and MFi controllers), with the same layout and functions as elsewhere.

Shipping:
- `sloppy build --target macos -o Game.app` makes an app bundle: the program, an Info.plist
  (its name in the Dock and the menu bar) and the build block's icon, signed (ad hoc) as a whole.

## 0.11.0

Games:
- Physics: limits and motors on 2D pins and 3D hinges (`lower`, `upper`, `motor_speed`,
  `max_torque`; `set_motor`, `set_limits`, `joint_angle`): doors that stop, wheels that drive,
  elbows that bend one way. Joints are solved more times each step, so chains and limits hold
  stiffer.
- 2D physics: `w.circle_cast(a, b, radius)`, the same in 2D.
- Physics: a body's handle is not the next body's when one is removed and another takes its place
  (it was: a stale handle moved the new body). Using a removed body's handle panics, `w.alive(b)`
  says false; a removed joint's (or one whose body went) does nothing, and `w.joint_alive(j)`
  says so.
- 3D physics: `w.sphere_cast(a, b, radius)`, a ray with thickness: where a ball moved from a to b
  first touches something (thick bullets, a camera kept out of walls, the ground under feet).
- Netplay: web pages in a rollback room connect straight to each other with WebRTC; their
  packets then go as over UDP (unordered, never resent, never held up behind a lost one) instead
  of through the relay's WebSockets. The relay passes on how they connect; a STUN server
  (`join_relay(..., stun = ...)`) finds their addresses; `s.direct(p)` says which players are
  reached straight. Pages that cannot reach each other keep to the relay.
- Netplay: `s.ping(p)` and a client's `c.ping`, the round trip in milliseconds (examples/duel and
  examples/arena show it).
- `world_to_screen(p)`: where a 3D point appears on the screen (none behind the camera), for names
  and health bars over heads; in 2D, where a world position appears under the camera.
- Fixed: 3D drawn after 2D in the same frame (a label drawn after each enemy) covered what was
  drawn before with the sky; only the last 3D drawn showed. Each later batch now goes over the
  earlier ones, and their shadows stay.
- `ui_choice("Level", ["forest", "cave", "tower"], level)`: one of several, in a menu.
- The software renderer draws small meshes on one thread: waking the others for each
  `draw_mesh` cost more than it saved (40 small cubes a frame: 10 times faster; Breakwater: twice).
- `ui_slider` moves by whole steps (0.8, less two steps, is 0.6, not 0.6000000000000001).
  `master_volume()` says what it was set to.
- `capsule_mesh(radius, height)`: the shape of physics3d's capsules and characters.
- `draw_line3d(a, b, color)` and `draw_grid3d()`: lines and a ground grid in 3D, for seeing paths,
  rays and distances while making a game.
- `random_direction()` (and `random_direction_3d()`), `random_point(low, high)`,
  `random_in_circle(center, radius)` and `random_color()`.
- `SLOPPY_INPUT` scripts the mouse too: `3:mouse_left+`, `2:mouse=400x300`; an item it cannot
  read is reported instead of ignored.
- Physics (2D and 3D): bodies at rest go to sleep, with all they touch, and are left out of each
  step until something touches, pushes or moves them, or what they rest on goes (`w.sleeping(b)`;
  `World(sleep = false)` keeps all awake). A settled pile of 200 boxes steps 15 times faster.

Language and library:
- `random()` differs from run to run: it starts from the clock (it always started from the same
  seed). `seed_random(n)` makes the numbers the same every run, as do `SLOPPY_SEED=n` and screenshot
  runs (`SLOPPY_SCREENSHOT`).
- Fixed: `xs[f(i)].v += d`, a vector (or a type with its own operators) at an index that is a
  call, failed to compile ("invalid expression"); the index is now computed once.
- `chr(c)` is the character with code point c, as in Python (`chr(233)` is "é"; it was one byte,
  which made text typed into a web page or a Windows console wrong past ASCII); `byte_str(b)` is a
  one-byte string. `split(s, "")` gives characters, not bytes. The language reference has a part on
  text: bytes, characters, and how wide text is drawn.
- `mut` in combined loops: `loop i in 0.. and mut e in enemies: e.hp -= i` changes the elements
  themselves while counting.
- `read_line()` reads a line typed in (or piped in), none when the input has ended, and
  `read_stdin()` all of it; `read_file("/dev/stdin")` reads a pipe. `input`, `raw_input` and
  `readline` point to `read_line`.
- `random_item(xs)` and `shuffle(xs)` (and `r.next_item(xs)`, `r.shuffle(xs)` with an `Rng`);
  `choice`, `randint` and `uniform` point to them. `draw_cube`, `draw_sphere` and `light` point to
  what draws them.
- `to_json(value)` and `from_json[T](text)` for any value: structs as objects by field name
  (fields left out keep their defaults, unknown ones are skipped), arrays, tuples and vectors as
  lists, maps, optionals as null, enums by name. `csv_rows(text)` and `to_csv(rows)` read and
  write CSV (quoted fields too). `median`, `std_dev`, `mean` of ints, `unique` and `group_by`.
- `round` is right for 0.49999999999999994 (it gave 1.0) and says how it rounds halves (away
  from zero; Python's goes to the even one).
- `pow` is within an ulp (fdlibm's; it was exp(y * log(x)), several ulps off for big results):
  `pow(2.0, 0.5) == sqrt(2.0)`.
- Sorting keeps equal elements in their order (sort by name, then by score, and the names stay in
  order within a score), and takes `descending = true`; `sorted_by(xs, key)` is a sorted copy.
- Tuples compare element by element (`sorted` of `(score, name)` pairs; `max`, `<`). `>`, `<=`
  and `>=` come from a struct's `<` (they were errors without their own definitions).
- `loop x in xs: if x > 0: n += 1` on one line: an `if` after a colon on the same line is the
  statement (it was an if expression, wanting an else).
- `split(s)` splits at spaces, as `words(s)` does; `tween(0, 10, 0.5)` goes through the
  fractions (with whole numbers it gave an int tween).
- `first(xs, n)` and `last(xs, n)`: the first or last n, or all when there are fewer.

Errors and hints:
- A warning for `s[0] + "!"`: it adds a byte and a character's code, not text.
- Comparing an optional with `none` narrows it, as `is` does: after `if x == none: return`, or
  inside `if x != none:` (and `x != none and x > 0`), `x` is its value. `x is not T` is
  `not (x is T)`. `x!` on a variable known to have its value is that value.
- Raw strings take either quote: `r'{"a": 1}'`. A string whose braces hold only a string
  (`'{"a": 1}'`, meant as JSON) is an error that says how to write braces; an unterminated
  interpolation and a bad one say so too.
- `int("5")` is an error (it was 53, the character's code): `to_int("5")` reads the number.
  (`int('5')` in single quotes, as character arithmetic writes it, is still the code.)
- A function that calls itself without its result type written (`fact = (n: int): ... fact(n - 1)`)
  says to write it, instead of "operator * is not defined for int and void".
- Assigning a global declared below the function is an error (it was a warning): a global
  added further down the file would quietly change what the function does.
- Hints for `x if c else y` in arguments, `n // 2`, `xs.map(str)`, `sort(key = ...)`,
  `circle(100, 100, ...)` (a position is one vec2), `draw_text`, `draw_rect`, `.copy()`; the
  panic for `xs[-1]` mentions `xs[end]`; `max`, `min`, `first` and `last` of an empty array say so.
- A warning for `hits / shots * 100.0` and other divisions of whole numbers that become floats
  (the fraction is gone before: 3 / 4 is 0).
- Hints for Python's `xs[:2]`, `a if c else b`, `if xs:` and `if n:`, for `score += 0.5` with an
  int score (make it `score = 0.0`), and for a color (vec4) given where a vec3 is wanted (`.rgb`).
- Comparing an optional with a value (`env("X") != ""`) says how: `(x ?? default) == value`
  or `if let`.
- The REPL's `:type f` of a function shows its versions and their notes.
- A struct's function field taking `self` says that structs have no methods and how to write one;
  an indentation error in a file that mixes tabs and spaces says so.
- Key names from other libraries (`.esc`, `.return`, `.left_ctrl`, `.left_arrow`) say which variant is
  meant (`.escape`, `.enter`, `.ctrl`, `.left`).

Compiling:
- The library's functions are read only when a program uses them (the lexer passes over their
  bodies): building an empty program takes 37% less work, small games 2 to 5% less, which more
  than pays for the library's growth in this release.

Shipping:
- `--target wasm -o game.zip` (for itch.io) deflates the page: a third of the size.
- `can_quit()` is false in a web page, where `quit()` cannot close anything; the arcade
  template's title menu leaves its Quit button out there.
- A macOS build shows the build block's icon in the Dock.
- `SLOPPY_INPUT` works in web pages too (`page.html?SLOPPY_INPUT=5:space+`), types letters,
  digits and spaces it presses into `text_input()`, and takes `9:text=ACE`.
- `--help`, `sloppy new` and START.md name every target; START.md says what a macOS build needs
  on a Mac, and what a Windows build's `.pdb` is.

Editor:
- The language server reads what has arrived before answering: a request the editor cancelled
  since is answered "cancelled", and one about a document changed since "content modified", so
  typing fast in a big program no longer queues up checks of old text.

Docs:
- The tutorial, the templates (`sloppy new`) and the library's examples leave out the `f32(...)`
  they did not need: f32 and f64 mix by themselves (`pos += input_axis() * 400 * dt`).
- The library reference lists each struct's fields and each enum's variants (`Key`'s names), and
  its headings are where they belong; `tanh` is with the math.
- `SLOPPY_INPUT` is described in full; enum matches, and that `loop c in s` gives bytes, are in
  the language reference; examples are linked on GitHub (the release does not include them).

## 0.10.0

Language:
- **Error messages that say what to write.** Habits from other languages get Sloppy's way
  instead of "expected end of statement": `def`, `fn`, `class`, `for`, `while`, `elif`, `var`,
  `let mut`, `:=`, `&&`, `||`, `!`, `i++`, `**`, `x => ...`, `lambda`, `c ? a : b`, braces, `//`
  comments, f-strings, `print "x"`, `len xs`, a missing `,` or `:`. Names from them get Sloppy's
  (`True`, `None`, `float`, `string`, `.append`, `.length`, `strip`, `parseInt`...), and the
  editor's quick fixes change them. A call that does not fit shows the function's parameters
  and the first argument that is wrong (`circle(100, 100, 20, RED)` is about `center`); with the
  program's own function and the library's of the same name, the program's is the one meant. A
  name used after its block ended says where it was made; `x(1)` with a variable `x`, `xs.len`
  without `()`, `p.hp` on a `P?`, `"n=" + n`, `0 < x < 10`, `[0] * 5`, `[0.0..1.0)`, `if v:` on
  an optional, `int("42")`, `key_down("space")` and `.left_arrow`, `x = "one"` after `x = 1`, a
  match without some variants (they are named), a wrong `update` or `draw` (reported there, not
  in the library) each say what to do.
- An error inside a library function made for the program's types (`sort` of structs without
  `<`, `max` of them) is reported at the program's call, with the library's line in parentheses
  and, for a struct without the operator, how to define it.
- New errors: `-> void` is kept (a function that says so and returns a value is an error; it
  used to return the value); assigning a constant (inside a function this made a variable that
  hid it); top-level code reading a global above the line that gives it its value (it was
  zero); a function named as a statement without being called (`update` for `update()`).
- Fixed: `a[f()]` where `f` grows the global array `a` read freed memory (the index is now
  evaluated first); an `if let` whose branches are statements, at the end of a function, was
  taken for the function's value.
- A warning for `s.trim()`, `xs.sorted()`, `normalize(v)` and the library's other functions
  that give a new value, called as a statement (it does nothing; `s = s.trim()` keeps it).
- A warning for colors written from 0 to 255 (`rgb(255, 128, 0)`; colors go from 0 to 1).
- Errors in an interpolation inside a string inside an interpolation point at the right place.
- `import name` in a file called name.jo is the library's module, not the file itself.

Tools:
- `sloppy run game.jo` runs a program, as `sloppy game.jo` does; a mistyped command says which
  one was meant (`sloppy bulid`). Panics name operators in the call stack (`[] (indexing)`, not
  `XX`), a missing map key says how to ask for one that may be missing, and a slice out of
  bounds shows the range as `[a..b)`.
- **Variables in debuggers on Windows**: `sloppy build -g` puts the variables and their types in
  the PDB (CodeView: S_LOCAL records with where each is, type records with their hashes), so
  Visual Studio, WinDbg, cdb and VS Code's C/C++ debugger show every frame's variables.
  `lib/debug/sloppy.natvis` shows strings as text, arrays and maps as their elements and
  optionals as their value or `none`; VS Code's F5 loads it. A function that saves registers
  now says where in its unwind codes (`.pdata`), so callers' variables held in them are right
  too. A program that panics with a debugger attached stops there. `tools/dbgtest.py` checks
  what cdb shows on Windows.
- `sloppy new <dir> platformer`: a 2D platformer to start from (a level written as text,
  slopes, platforms to jump up through, coins, a camera that follows), also in the gallery and
  the playground.

Games:
- **2D physics** (`import physics`): rigid bodies (circles, boxes, convex polygons) that
  collide, bounce, slide and stack, with friction, bounciness, density, damping and collision
  layers; `.fixed` and `.moving` bodies (floors, platforms); joints: pins, rods, ropes and
  springs, and dragging with the mouse; contacts after each step (new ones, how hard), sensors,
  raycasts, bodies at a point, a debug drawing. Pixels with y down, as drawing. Stepping is
  deterministic (a fixed internal step and order), for replays and rollback. examples/physics.jo
  (in the gallery and the playground): a pyramid, a bridge of planks, a wrecking ball.
- **3D physics** (`import physics3d`): rigid bodies (spheres, boxes, capsules) that collide,
  roll, slide and stack (box against box by separating axes and clipping, so piles and pyramids
  stand), a level's triangles (`add_mesh`, `physics3d.triangles(model_data)`, kept in a tree of
  boxes), joints (ball, hinge, rod, rope, spring), contacts, rays (bodies and triangles), and a
  character controller (`w.character`, `w.walk`): a capsule that walks up slopes and steps,
  slides down steeper slopes, stops at walls, keeps to the ground going down, jumps, and
  shoves dynamic bodies out of its way (a heavy one stops it).
  Deterministic stepping. examples/physics3d.jo: a yard to walk around and throw balls in.
  `sloppy new <dir> 3d` walks with it (steps, slopes, jumping), and its crates are knocked about
  by shots.
- **Rollback netplay** (`import netplay`): players on different machines play one game as if it
  ran on each alone. Only inputs travel; a missing remote input is predicted (the last one,
  repeated), and when the real one differs the game goes back and plays the ticks since again.
  Input delay, waiting when too far ahead, slowing down when ahead of the other's clock,
  inputs resent until acknowledged (loss is fine), hashes of confirmed ticks to catch
  machines whose games differ (`s.desync`), simulated latency, jitter and loss (`s.lag`, and
  `netplay.Link` for two sessions in one program). Over UDP (`s.udp`) or any transport
  (`s.outgoing()`, `s.receive(bytes)`), and through a relay over WebSockets, the way web pages
  play (`netplay.relay(port)` in a native program, which may itself be a player;
  `s.join_relay(host, port, room)`). examples/duel: two ships, over a LAN, in two windows, or
  with a web page.
- **Client and server netcode** (`netplay.server`, `netplay.client`): an authoritative server
  over WebSockets (native and web clients); the client's own inputs applied at once
  (prediction) and again on each world from the server that has not answered them yet
  (reconciliation); others drawn between two worlds a few ticks in the past (`c.view()`);
  lag compensation (`apply` gets the world the player was seeing). examples/arena: any number
  of players with lasers; tested with a web page's client in Chromium.
- **UDP** in `net`: `net.udp(port)`, `net.udp_send`, `net.udp_receive` (Linux, macOS, Windows).
- `net.receive(peers)` and `net.receive_server()`: the events of some peers only, for parts of a
  program that each have peers of their own.
- **Saving any value**: `save_value("settings", settings)` and `load_value("settings",
  Settings())` keep a value as text; `to_text(x)` and `from_text[T](text)` (a `T` or a
  `TextError` with the line and column) do it with a string. The text is what print shows
  (`Settings(volume=0.8, keys={"jump": 32}, mode=hard)`); fields go by name, so a field added
  since keeps its default and one removed is skipped, and saves from an older version still
  load. Numbers, strings, arrays, maps, optionals, tuples, structs, enums, unions and vectors.
- **GPU time in the frame statistics**: through Vulkan, the overlay (`show_stats()`,
  `SLOPPY_STATS=1` or `log`) shows the GPU's time for the frame and for each zone, from
  timestamps among the frame's commands; the 3D scene, its shadows and post-processing are zones
  of their own.
- **Slopes and one-way platforms in tilemaps**: `set_tile_shape(map, id, shape)` with
  `.platform` (landed on from above, passed through from below and the sides), `.slope(left,
  right)` (a floor rising or falling across the tile: `.slope(0, 1)`, gentle ones over two
  tiles), `.empty` or `.solid` (every tile, until set). `tilemap_move` walks a box up and down
  slopes, keeping it on the floor going down, and drops it through platforms with `drop =
  true`. In Tiled, a tile's custom property `shape` (`platform`, `slope 0 1`...).
- **Tweens**: `tween(from, to, seconds, ease)` for numbers, positions and colors, with `delay`
  and `once`, `repeat` or `pingpong`; `update`, `value`, `done`, `restart`, `retarget`. More
  easing curves: `linear`, `ease_in`, cubic, sine, back, `ease_out_elastic`, `ease_out_bounce`.

Docs:
- **Playing over a network** (docs/MULTIPLAYER.md, on the site): messages, rollback or a
  server and which fits a game, keeping a tick the same on every machine, ticks apart from
  frames, trying it on one machine, web pages.

## 0.9.0

Tools:
- **Packages**: `name = package("git URL" [, "tag, branch or commit"])` (or a directory) in the
  build block; `import name` loads the package's main file, `import 'name/file.jo'` another. The
  first build pins each to a commit in `sloppy.lock` beside the program and fetches it once,
  with git, into a cache, so builds after are the same and need no network. `sloppy add <url>`
  writes the line and fetches it. A package's own packages come along.
- **An examples gallery** on the website (sloppy-lang.org/examples): each game, example and
  `sloppy new` template, with its picture, to play in the browser or change in the playground.
- `run_program(program, args)`: run a program, wait for it, its exit code and output.
- **Variables in debuggers**: `sloppy build -g` (Linux on x86-64 and arm64, macOS) adds every function's
  parameters and locals with their types and where they are while it runs, and how each frame
  is made (`.debug_frame`), so gdb and lldb show the variables of every frame on the stack. A
  variable of a `-g` build lives on to the end of its function and stays where calls keep it.
  `lib/debug` has printers for gdb and lldb: strings as text, arrays and maps as their
  elements, optionals as their value or `none`, an enum with fields as its variant. In VS Code,
  F5 (**Sloppy: Debug File**) builds with `-g` and debugs through CodeLLDB or the C/C++
  extension, stopping where the program panics. `tools/dbgtest.py` checks what gdb and lldb
  show; the fuzzer also compares `-g` builds.
- **Quick fixes** (the language server's code actions, Ctrl+. in VS Code) for errors that say
  what to change: a misspelled name ("did you mean"), `loop mut` for a loop variable changed, a
  parameter changed made `mut`, a number of another type converted (or `2.0` written `2`).

Games:
- **Networking**: `import net`, then `net.listen(port)` (a server), `net.connect(host, port)`,
  `net.send(peer, msg)`, `net.send_all(msg)` and `net.receive()` each frame (peers joining and
  leaving, their messages, whole and in order). Over WebSockets: a web page and native programs
  play together, a native program being the server; on Linux, macOS, Windows and in browsers.
  examples/netpong: Pong for two over the network. `tools/nettest.py` checks a server and
  clients (and a web page's client, in a browser) in CI.
- A camera that follows (`follow(cam, target, dt, speed, deadzone)`) and a screen shake
  (`Shake`: `add` trauma, `update`, `offset`); sounds from a place (`play_at` in 2D, from a
  listener, and in 3D, from the camera; `move_sound` for one playing; `set_pan`).
- **Zones in the frame statistics**: `zone("physics")` ... `zone_end()` (or `zone("physics", f)`)
  times a part of the frame; the overlay (`show_stats()`, SLOPPY_STATS=1) lists each zone,
  nested, with its average and longest time over the last frames, and SLOPPY_STATS=log prints
  them. `update` and `draw` are zones already. Off, a zone costs a check.

Errors:
- An argument of the wrong type is pointed at, not the call.
- A function's final expression has its own line in backtraces and debuggers.

## 0.8.1

Fixed:
- The library's 3D example called `sun()` with the direction its light goes; it takes the
  direction toward the sun (now said where it is defined).
- The software renderer drew a faint box behind small text (16 px and less).

Faster:
- **arm64 code keeps values in registers** (macOS and Linux arm64): linear-scan allocation over
  the same lifetimes as on x86-64, callee-saved registers for values living across calls, x0-x7
  for those that live between calls; comparisons branch on the flags, constant operands are
  immediates, float constants are read from a literal pool. Under emulation, the compiler
  compiles itself in 8.5 s instead of 13.2 s, and is 4.4 MB instead of 6.6 MB.

Tools:
- **`sloppy fmt`**: code laid out one way: blocks indented by four spaces, one space around
  binary operators and after commas and colons, none inside brackets; line breaks, strings and
  comments stay (a comment after code keeps its column). Only spaces change, and only where
  the compiler reads the same tokens afterwards (the spaces it pays attention to, as in
  `[a -b]` and `x xor= 1`, included), else the file is left alone. `--check` lists what would
  change; `-` formats standard input. The language server formats (`textDocument/formatting`),
  and the VS Code extension formats on save.
- **`sloppy new <directory> [kind]`**: a project to start from, which runs as it is: `game` (the
  smallest: a window, update and draw), `arcade` (a 2D arcade game: a title menu, a score, a best
  score kept, sounds, particles, a pause menu), `3d` (first person: mouse look, walking and
  jumping among crates, shooting orbs) or `program` (for the terminal, with a test).
- Language server: symbols across the workspace's files (VS Code's Ctrl+T). The extension:
  **Sloppy: New Project** (`sloppy new` from the command palette).
- `tools/fuzz.py --arm64`: each random program also built for arm64 and run under qemu (each
  night in CI).

## 0.8.0

Platforms:
- **The interactive prompt and `sloppy watch` on macOS and Linux arm64.** The prompt compiles
  each input with the arm64 code generator, linked to the running session (far calls through
  veneers). On macOS the inputs' code goes into MAP_JIT memory (Apple silicon runs code made at
  run time only from there), the session starts without address space randomization (as
  debuggers start programs) so it is where its code was linked, and C functions an input uses
  for the first time are found when first called. A game run by `sloppy watch` on macOS keeps all
  its code in such a region, put there at start by a loader in its executable (a signed page
  cannot be patched), and takes patches through a copier outside it; files are watched by when
  they were last written. Every test of both runs on GitHub's arm64 Linux and macOS runners.
- `__code_sync(p, n)` for machine code written at run time (arm64: the caches).

Fixed:
- arm64: the prompt's jump buffer was too small for arm64's `__setjmp` (168 bytes), which wrote
  past it into the heap.
- macOS: a stack overflow in the prompt's input, or in anything running in a copy made by fork,
  killed it without a word (the copy's thread had no alternate signal stack).
- An error message about a type made of aliases of aliases (`(F, F) -> int` with
  `F = (G, G) -> int`...) took exponential time: type names are cut short past 150 parts.

Tools:
- CI checks compile speed against the commit before (`tools/speedcheck.py`: instructions
  counted, debug and release, the compiler, bench/big.jo and the games; above 1% fails).
- The fuzzers run each night with new seeds (.github/workflows/nightly.yml): programs built four
  ways, broken programs, GPU compute functions and fragment shaders on Mesa.

## 0.7.1

Editor (the extension is 0.4.0, now on the VS Code Marketplace and Open VSX both, published by
each release):
- Names are coloured by what they are: the language server sends semantic tokens (variables,
  parameters, fields, functions, structs, enums and their members, modules, constants as
  read-only, the standard library's names), and the grammar colours names before it answers.
- Fixed: inlay hints repeated (`x: int: int: int`) in a file whose program had errors; the
  brackets of `[a..b)` and `(a..b]` marked as unmatched; `(a..b]` running on into the next lines.
- Rename: an alias (`from m import x as y`) renames its binding and its uses; renaming to a
  keyword, or to a name that would change what other names mean, is refused; uses in open files
  that import the file are renamed too (and found by Find References).
- Names with non-ASCII letters work in every feature; signature help, hover and completion read
  strings as the compiler does; the outline finds `f=(x: int)` and multi-line signatures, and
  nothing inside strings; doc comments above `@attributes` show on hover; a generic function's
  hints only where all its instances agree.
- Files changed on disk (not in the editor) are checked again; closing a file keeps the errors
  other open files have for the files they share; new unsaved files get the language features.
- The extension: a server that fails to start no longer leaves requests waiting; restarting
  cannot start two servers; errors from an older version of a file are dropped; Run and Test stop
  when saving fails; Install Sloppy works on Linux arm64 and macOS too.
- Highlighting: octal numbers, `<<` and `<<=`, `ivec3`/`ivec4`, `f[int](x)`, interpolations as
  code; indentation after a line ending in `:` with a `#` in a string.

macOS: OpenGL at a Retina screen's full resolution (window sizes and the pointer in pixels, the
scale followed as the window moves between screens).

## 0.7.0

Platforms:
- **macOS on Apple Silicon** (`--target macos`, the default when the compiler runs on a Mac;
  the installer sets it up as on Linux, with no Xcode): Mach-O executables written by the
  compiler itself, with dyld binding the C functions they use and an ad hoc code signature, so
  they can be made on Linux too. The library's system calls go through libSystem; threads
  (`parallel_map` and the rest) are pthreads. Games open a Cocoa window (keyboard, mouse, wheel,
  mouse look, clipboard, fullscreen), draw with OpenGL 4.1 (or the software renderer) and play
  sound through AudioQueue. Every test and render test passes on a Mac, the compiler compiles
  itself there to the same bytes, and the language server works; CI runs all of it on a GitHub
  macOS runner, with a game on its screen. Not yet: Metal, Retina resolution (windows are drawn
  at one pixel per point), the interactive prompt and `sloppy watch`.
- **Linux on arm64** (`--target linux-arm64`, the default when the compiler runs on arm64; the
  installer has it too): a new code generator (compiler/arm64.jo), x86-64 system call numbers
  translated for arm64, C libraries loaded through arm64's ld.so, crash backtraces from arm64's
  registers. Every test passes there, and the compiler compiles itself on arm64 to the same
  bytes; CI runs the tests on an arm64 machine. Not yet: register allocation (values live in the
  frame, so the code is slower), the interactive prompt and `sloppy watch`.
- `ARCH` (`"x86_64"`, `"arm64"` or `"wasm32"`) beside `TARGET` (now also `"macos"`), for `when`.
- `@variadic(n)` on an `extern`: a C function with n fixed parameters, then C's `...` (macOS
  passes the others on the stack).

Graphics:
- `ivec3` and `ivec4` (i32 vectors, as `ivec2`), and compute functions over a 3D grid:
  `f(id: ivec3, params)` with `dispatch(compute(f), ivec3(w, h, d), params)` (groups of 4 by 4 by
  4 on the GPU).
- Shaders on OpenGL and the web: integer `+ - *` wrap on overflow as on the CPU (they are
  written through unsigned numbers; NVIDIA's GLSL compiler assumed signed results never
  overflow and simplified hash-like code wrongly). Found by tools/gpufuzz.py.
- Shaders: the smallest integer `/ -1` (and `% -1`) and `abs` of the smallest integer give
  what the CPU gives (itself, 0, itself); GLSL and SPIR-V leave them undefined, and Intel's
  OpenGL driver gave other values. Found by tools/gpufuzz.py on an Intel UHD 620, where every
  test and render test now passes with Vulkan and OpenGL.
- Web games take touch: the first finger is the mouse with its left button held, so dragging
  moves it (Rebound's shield follows a finger; before, only the first touch registered), and the
  page no longer scrolls or zooms under the game.

Docs:
- A new page, **Graphics and the GPU** (docs/GRAPHICS.md): the four renderers and when each
  runs, how shader functions reach each of them, what is the same and what differs, the three
  ways of computing on the GPU, and the switches for choosing and troubleshooting.

## 0.6.0

Graphics:
- **Vulkan.** Games draw through Vulkan 1.3 on Linux and Windows where the driver has it
  (OpenGL otherwise, or with `SLOPPY_VULKAN=0`), set up as current GPUs work best (after Mason
  Remaley's mr_gpu): every texture in one bindless array, buffers read by address, vertices
  fetched by the shader, dynamic rendering, per-frame upload memory, memory in large blocks.
  Frames are the same as with OpenGL; the CPU's time per frame is lower (Breakwater: 2.0 ms
  instead of 2.8). `SLOPPY_VK_VALIDATE=1` turns on the Khronos validation layer.
- The compiler turns shader functions into SPIR-V itself (as well as GLSL), so no shader
  compiler is needed; tools/spirvtest.py checks every module.
- Pipelines are kept between runs (a cache per program in `~/.cache/sloppy`, checked against
  the device and a hash): Breakwater's take 1-10 ms to make at start instead of 70 on NVIDIA.
  `SLOPPY_VK_PIPELINE_CACHE=0` leaves it out.
- **GPU buffers and compute functions** (lib/game/gpubuffer.jo): `gpu_buffer(xs)` keeps an array
  of plain data (numbers, bools, vectors and structs of them) on the GPU; a compute function
  `f(id: int, params)`, written in Sloppy, runs once per element with
  `dispatch(compute(f), n, params)`, reading and writing buffers by index (`u.bugs[id] = b`,
  `u.bugs[id].pos += v`), with atomics (`atomic_add`, `atomic_min`, `atomic_compare_exchange`...).
  Over a grid, `f(id: ivec2, params)` runs once per cell: `dispatch(k, ivec2(w, h), params)`.
  Shaders read buffers among their uniforms; buffers can be a mesh's vertices (`gpu_mesh`) or a
  draw's instances; `draw_indirect` draws as many as a compute function decided (`DrawArgs`),
  and `draw_indirect_count` takes how many draws there are from a buffer too. Compute
  functions can read textures. Barriers are automatic. Without Vulkan, buffers are CPU memory
  and compute functions run on every core, so the same program works with OpenGL, the software
  renderer and on the web.
- Subgroup operations in compute functions (`subgroup_add`, `subgroup_inclusive_add`,
  `subgroup_exclusive_add`, `subgroup_min`, `subgroup_max`, `subgroup_and/or/xor`,
  `subgroup_any/all`, `subgroup_elect`, `subgroup_broadcast_first`, `subgroup_size`): across the
  invocations the GPU runs together (32 on NVIDIA), 1 at a time on the CPU, so programs written
  for any size give the same results everywhere.
- GPU arrays run as Vulkan compute programs (with no window too), their `sum`, `min` and `max`
  on the GPU as with OpenGL.
- Shaders and compute functions follow the CPU's rules for numbers: unsigned division,
  remainders, shifts, comparisons, `min`, `max` and `clamp`; narrow integer types wrapping (`abs`
  too); float to integer conversions saturating; shifts by 32 or more; every compound
  assignment (`%=`, `>>=`, `and=`...) with its target and indexes computed once, before the
  right side; `ivec2(vec2(...))` converting each component; `i32(bool)`. (GPU arithmetic stays
  32-bit.)
- Arrays of arrays (`f32[2][3]`) work in shaders on OpenGL and the web (GLSL ES has none: they
  are kept in structs there). `fwidth()` in fragment shaders.
- Fixes: `-(-1.5)` in a shader broke GLSL (it read `--`); `mat4` takes integer vectors among
  its parts; a texture deleted, made again or given other sampling after a draw that uses it no
  longer changes that draw, and things released between frames wait for the frame that may
  still use them; a user struct named Texture is plain data.

Language:
- Type arguments at a call: `zero[int]()`, `gpu_buffer[Bug](100)`, `empty[str[]]()` (`T[]`
  written inside the brackets is the array type).
- `b[i].f = v` and `b[i].f += v` for types defining `[]` and `[]=` (a GpuBuffer, in compute
  functions too): the element is read, changed and written back. `b[f(x)] += v` computes the
  index once.
- `min`, `max`, `clamp` (and `abs` for signed ones) keep an integer type: `min(x, 5)` with
  `x: i32` is an `i32`, `max(a, b)` of two `u8` a `u8` (mixed types still take `int`'s). Ties
  between the library's overloads go to the one more arguments match exactly.
- Integer literals must fit: `x: u64 = -1` is an error like `x: u32 = -1`, as is a literal
  above 64 bits. Overloads rank integer types before `f64` before `f32` (`choose(-1)` with
  `u64` and `f64` overloads takes `f64`; it was ambiguous), and leave out what a call cannot
  match (`f(300)` with `f(x: i8)` and `f(x: i16)` is the `i16` one).
- Float to integer conversions saturate at the range of the type converted to (`u8(300.0)` is
  255, `i8(-200.0)` is -128, `u64(-1.0)` is 0); before, only `int` did. Signed division wraps
  like the rest of integer arithmetic (the smallest integer `/ -1` is itself, `% -1` is 0;
  native programs used to stop). `x %= y` on floats is `x % y`.
- Generic types are also worked out from what the result must be: `x: int = make((v): v + 1)`
  types the lambda's `v`, `f: () -> int = zero` picks `zero[int]`, and a lambda returning a
  member of a generic union makes that member. A generic function that expands without end
  stops with an error (found by its chain of instantiations: deep finite types and many
  instances are fine).
- `match` narrows a field (`match b.x:`) or a global in each arm, as it does a local variable;
  a closure using a name narrowed by `is` captures the variable itself, so it sees later
  changes and may assign it.

Memory safety and data races (from reviews of the compiler):
- An argument read from a global, a variable closures share, a capture, a `g!`, an operand of
  string or array `+` and `==`, or a part of `"...{x}..."` stays alive through the call, even
  if the callee (or a later argument) gives its variable another value; it used to be freed
  under the callee. (Where the callee cannot change that global, no reference is taken.)
- An element passed as `mut` (`hit(enemies[i])`) is written where it is, so while the call runs
  nothing may move or share its array: the same call can no longer also be given the array
  (`attach(nodes[0], nodes)`) or an element inside it, nor can a global array the function
  changes; the compiler says so. Where the function may call a function value that could
  resize the array, the element is passed as a copy and written back after the call.
- The data race check of `parallel_map` and the others covers partial applications
  (`f(k, _)`), calls of function values inside the function, `__fmt` functions and narrowed
  globals; a function kept in a variable is refused, since the compiler cannot see which it is.
  A function handing the function it is given on to them is marked `@parallel`, and such
  functions can only be called directly.
- On the CPU, negating an integer vector gave wrong components (it went through floats), and
  swizzles out of order (`v.zx`) read and wrote the wrong components (assigning one wrote past
  the vector). A swizzle naming a component twice cannot be assigned to (`v.xx = ...`).

Other fixes:
- Maps: keys that are unions, optionals or arrays work (they hashed wrongly), `-0.0` and `0.0`
  are one key as they are equal, and `remove` keeps the other entries in insertion order.
- Windows: a float given to a C function among its first four arguments also goes in the
  integer register (as varargs functions like `sprintf` read it); a @cabi function called from
  C may take more than four arguments; @cabi functions sign-extend narrow integers C passes.
- Editor: an unsaved change to a file is seen at once in the other open files that use it, and
  references across files follow a used file as it is opened and closed.

Tools:
- tools/gpufuzz.py: random compute functions run on the CPU, the GPU and lavapipe, and random
  fragment shaders drawn by the software renderer, OpenGL and Vulkan, must agree (`--reduce`
  shrinks a failure).

Website and install:
- The website works on phones: the top links fold into a menu, and a docs page's contents into
  a bar under the title. The pages are grouped (start, tutorials, reference), with previous and
  next links at the bottom.
- The install command shown is the one for your system (Linux, Windows; on a Mac, the
  playground), with a copy button. A new **Getting started** page (docs/START.md): installing, a
  first program and game, sharing it, editors.
- The Linux installer links `sloppy` into `~/.local/bin` when that is on the PATH (as on most
  systems), so the command works in the same terminal at once.
- **The library page, by topic** (arrays, strings, the window and input, 2D, 3D, sound...),
  each with a whole program to run in the playground (docs/api/; the tests build them), every
  function with its description, a search box (`?q=` links to a search), and the built-in
  functions (`print`, `push`, `pop`, `fill`, `embed`...), which were missing.

## 0.5.0

Games:
- **Breakwater** (examples/breakwater), a first-person shooter in one file: hold a platform at
  sea against waves of robots, with a shield that recharges, two weapons at a time (a pistol, a
  rifle, a shotgun, rockets, the robots' casters), grenades and melee; animated glTF robots and
  weapons by Quaternius (CC0). Play it at sloppy-lang.org/breakwater, or change it in the
  playground.
- A third tutorial, **Make a 3D shooter**: a small Breakwater in eight steps
  (docs/TUTORIAL_BREAKWATER.md): mouse look, cover, shots as rays, drones that fire back, waves.
- **Lowline** (examples/lowline): a glider down an endless valley, scoring for flying low.
- The playground keeps each game's files (icon, models) apart, and fetches large ones only when
  that game is chosen.

Library and language:
- **Controls players can change**: `action("jump", [.key(.space), .button(.a)])`, then
  `action_pressed("jump")`, `action_axis("left", "right")`...; `ui_controls()` in a menu lets the
  player rebind each action (press the new key or button), and the bindings are saved. Rebound
  has a Controls page. An array of shorthand values (`[.key(.space)]`) now takes its type from
  the parameter it is passed to. A long list of actions scrolls to fit the screen.
- **Several gamepads**: up to eight, each by its number (`gamepad_down(1, .a)`, `left_stick(1)`,
  `gamepads()`); without a number, any of them. Flight sticks and wheels: `joystick_button` and
  `joystick_axis` give a device's own inputs.
- **3D models**: `load_model` reads glTF 2.0 (.glb, or .gltf with its files): meshes placed by
  the scene's nodes, base colors, PNG and JPEG textures, vertex colors; `draw_model` draws one.
  `read_gltf` gives the model's data without the GPU (for collision, or to change it).
- **Animated models**: glTF skins (up to 64 joints, bent on the GPU) and their animations.
  `pose_at(model, find_animation(model, "Run"), time)` gives a pose (Blender's "Armature|Run"
  is found as "Run"), `blend_poses` fades from one to another, `turn_node` bends a joint (a
  spine aiming up), `node_transform` says where a joint is (to put a weapon in a hand);
  `draw_model(m, transform, pose = p)`. `draw_model` also takes `in_front` (a first-person
  weapon model).
- **JPEG**: `load_jpeg`, and `load_image`/`load_texture` read JPEG as well as PNG (baseline and
  progressive, any color sampling, grayscale, CMYK).
- 3D draws the camera cannot see are left out (meshes know their bounding sphere).
- **Paths over a grid** (lib/game/paths.jo): mark cells open or blocked, then `path_step(grid,
  from, to)` gives the next point to walk to round the walls (and `path_distance`): for enemies
  in 2D (tiles) or 3D (the ground's x and z).
- **Point lights** in 3D: `point_light(pos, color, radius)` for a frame (muzzle flashes, glowing
  shots, lamps); up to 8 light a frame, the ones nearest the camera.
- One mesh from many shapes: `add_box`, `add_cylinder` and `add_sphere` add a shape's vertices
  to an array (placed by a transform, in a color) for `custom_mesh`: a level or a robot drawn in
  one call. `draw_mesh(..., in_front = true)` draws over everything else (a first-person
  weapon that would poke into walls).
- Cameras for 3D: `orbit_camera` (drag to turn, the wheel to zoom) and `fly_camera` (WASD and
  the mouse), with gamepad sticks too; `camera3d(cam)` uses one.
- **Debugging on Windows**: `sloppy build` writes a PDB beside the program, and programs have
  unwind tables, so Visual Studio, WinDbg and RemedyBG show Sloppy functions, lines and call
  stacks (break at a function or a line, step through the source).
- The build block's `icon` is the window's icon on Linux too (X11); `PROGRAM_ICON` has its bytes.
- **The interactive prompt on Windows** (`sloppy` with no file), as on Linux: an input that has
  errors, panics, crashes or is stopped with ctrl-c leaves everything as it was before it.
- **Music that plays while it decodes**: `load_music` and `play_music` (Ogg Vorbis), for long
  tracks: no wait when they load, and little memory (`load_ogg` still decodes a sound whole).
- **Fonts**: `load_font` reads TrueType fonts (.ttf, .ttc) into sharp text at any size;
  `set_font` chooses the one `text` draws with. Text is UTF-8 now: accented letters, quotes,
  dashes and the euro sign in loaded fonts (characters a font lacks show as ?).
- A function that assigns a global declared further down its file gets a warning (it changes
  that global; `let x = ...` makes the function's own). A top-level `x = 0` now runs where it
  is, like other initializers.

## 0.4.0

Games:
- **Rebound** (examples/rebound) is the example game now, in place of Lumen: a one-file arcade
  game where you turn a shield to catch turrets' bolts and send them back (chain blasts, bank
  shots, upgrades, a saved best score). Play it at sloppy-lang.org/rebound, or change it in the
  playground.
- A second tutorial, **Make an arcade game**: a small Rebound in eight steps (docs/TUTORIAL_REBOUND.md).
- **Ogg Vorbis**: `load_ogg` (music at a tenth of the size of WAV).
- **Sprite sheets and animations**: `sprite_sheet`, `animation`, `draw_anim`, and
  `load_aseprite` for Aseprite's JSON with its tags.
- **Tilemaps**: from text (`tile_layer`) or Tiled's JSON (`load_tiled`), drawn by what is on
  screen (`draw_tilemap`), with `tilemap_move` for boxes that stop at walls and floors
  (examples/tiles.jo).
- **JSON** (`parse_json`, `to_json`, and `get`/`at`/`as_*` that chain) and **base64**.
- Menus ignore input in the frame they open, so the key that opened one does not also work it
  (`ui_ready()` for a game's own keys).
- `arc` (part of a ring) and `melody_loop` (music that loops without a seam).
- The playground opens an example by link (`#example=rebound`) and has the files examples use,
  like icons.

Language:
- At the top level, assigning to a variable of a `use`d module (or the library's, like
  `ui_style`) changes it, as in a function; before, it quietly made a new variable.
- Enums are members of unions like other types (`E | str` could not hold an `E`), and `.v` and
  `.v(args)` work as arguments, also for a union parameter.
- A function literal in a call's arguments works in an `if`/`loop` header
  (`if xs.any((x): x > 2): ...`).

## 0.3.1

Windows: `sloppy watch`, crash reports, the software renderer. Saving (`save_data`), menus
(lib/game/ui.jo), program icons, itch.io zips, the first tutorial, and correctness fixes from an
outside review. Earlier versions: the GitHub releases page.
