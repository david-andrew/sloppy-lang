# Playing together over a network

Sloppy has three ways for players on different machines to play one game. Which one fits
depends on the game:

| | Messages (`import net`) | Rollback (`netplay.session`) | Client and server (`netplay.server`, `netplay.client`) |
|---|---|---|---|
| What travels | whatever the game sends | each player's input, every tick | inputs to the server, the world back |
| Who runs the game | the game decides (often one host) | every machine runs all of it | the server |
| Feels | as fast as the network | local: others' moves shown at once, corrected a few frames later at worst | one's own moves at once; others a little in the past |
| Players | any | 2 to 4 | many |
| Good for | turn-based games, chat, lobbies, simple games | fighting, sports, action games for a few | shooters, many players, keeping cheating out |
| Example | examples/netpong | examples/duel | examples/arena |
| Web pages | connect to a native server, or straight to another game with invite codes | invite codes, or through a relay, then straight to each other (WebRTC) | connect to a native server |

## Messages

`import net` sends messages (text or bytes) over WebSockets: `net.listen(port)` in a native
program, `net.connect(host, port)` from a native program or a web page, `net.receive()` each
frame for what happened. Messages arrive whole and in order. Native programs can also send UDP
datagrams (`net.udp`), which may be lost or come out of order but never wait for each other. See
[the library](API.md#networking).

**With no server at all: invite codes.** `net.invite()` makes a peer and `net.invite_code(p)` a
code (120 to 250 characters: a box to paste one into needs `max_chars` of 400) for the player to
send their friend any way they like: a chat message. The friend's game joins with it, `net.join_invite(code)`, and its `net.invite_code(p)`
is a reply code to send back, which the first game takes with `net.accept_reply(p, reply)`. The
two games then connect straight to each other (WebRTC: the browser's own in a web page, Sloppy's
in a native program), web pages and native programs alike, on one Wi-Fi or across the internet;
after that the peer is as any other. Nothing runs anywhere but the two games: a public STUN server
(Google's, `rtc.rtc_stun_servers`) only tells each game how it looks from the internet. Most home
networks connect so; some (mobile data, many schools' and offices') let no outside connection in,
and need a relay: a TURN server, which passes the two games' packets on. `net.turn_server("turn:host:3478",
user, password)`, before inviting, offers a path through one (your own, coturn, or a service's: some
have a free tier; its password goes into every copy of the game), used only when no straight path
works. `net.invite(reliable = false)` sends messages that may be lost or come in another order but
never wait: a fast game's state. `net.code_kind(code)` says what a pasted code is ("invite",
"reply", or "" for neither: cut short, or something else). A game that ends (quit, its window
closed, a page closed) tells its peers so at once; one that vanishes (switched off, its network
gone) is `.left` after 15 s of silence. A message may be up to 16 MB. `import invite` has the
screens for all this (below).

A screen of one's own, whole (the inviter's side and the friend's in one program):

```gdscript
import net

p = -1                                  # the friend, once there is an invite or a join
mine = ""                               # this side's code, to send
pasted = ""                             # theirs, pasted in
connected = false

update = (dt: f64):
    global connected, mine
    if p >= 0 and len(mine) == 0: mine = net.invite_code(p)     # ("" for a moment)
    loop e in net.receive():
        if e.kind == .joined: connected = true
        else if e.kind == .left: print("no: {net.why(e.peer)}")
        else if e.kind == .message: print("they said {e.text}")

draw = ():
    global p, pasted
    clear()
    if connected:
        if hud_button(Rect(40, 40, 200, 44), "Say hello"): net.send(p, "hello")
        return
    if p < 0:
        if hud_button(Rect(40, 40, 200, 44), "Invite"): p = net.invite()
        pasted = hud_text_field(Rect(40, 100, 700, 44), pasted, "code", 400, "or their code here")
        if hud_button(Rect(40, 160, 200, 44), "Join") and net.code_kind(pasted) == "invite": p = net.join_invite(pasted)
        return
    text("Send them: {mine}", vec2(40, 40), 16)          # (and set_clipboard(mine), or a Copy button)
    if net.code_kind(mine) == "invite":
        pasted = hud_text_field(Rect(40, 100, 700, 44), pasted, "reply", 400, "their reply here")
        if hud_button(Rect(40, 160, 200, 44), "Connect"): net.accept_reply(p, pasted)
```

**The screens, ready made: `import invite`.** Invite a friend shows a link to send (it opens the
game in a browser: the page's own address in a web page, the `web_page` given on a computer),
with Copy and, on phones, Share; Join a friend takes a pasted link or code (a Paste button on a
phone) and shows the reply to send back; both say why when nothing connected, and Back leaves.
A game's menu opens them, and draw shows them until the friend is connected:

```gdscript
import net
import invite

friend = -1
invite.from_link()                      # opened from an invite link: Join a friend, at once
draw = ():
    if invite.active():
        if let c = invite.screen("My Game", "https://example.com/mygame/"):
            friend = c.peer             # connected; c.inviter: this side invited
        return
    ...
    if ui_button("Invite a friend"): invite.start()
    if ui_button("Join a friend"): invite.join()
```

Until the friend is connected, `net.receive()` leaves their events to the screens; after that,
everything from them is the game's. examples/duel and examples/netpong use them, and
`sloppy new my_game online` starts from a small game that does (two players, rollback, a
practice mode).

Netpong's Invite a friend and Join a friend show the whole of it, with the codes copied to the
clipboard and pasted back.

**Rooms: a matchmaking server instead of the reply code.** With `invite.server(url)` (a
server of your own, tools/rendezvous.jo: [how to run one](MATCHMAKING.md)), Invite a friend opens
this computer's room instead: a short code ("KX7P4") and a link with it (`?room=KX7P4`), kept, so
they are the same after a refresh or a restart (New code makes another). Friends type the code into
Join a friend, or open the link, and nothing comes back: their game and the host's pass the invite
and the reply through the server, and then connect straight to each other as before. A friend who
comes while the host's game is not open is told so, and joins once it is. The screen keeps
Invite with a code instead, and says so when the server cannot be reached.

```gdscript
invite.server("wss://match.example.org")        # (web pages and native builds alike)
invite.from_link()                              # (?room=... too)
...
if ui_button("Invite friends"): invite.start(players = 4)      # a room for 4, this side too
```

A room lets in several friends, one by one: the first comes from `invite.screen` as before, the
others from `invite.arrivals()` (each frame, in the game's lobby); `invite.room_busy(true)` makes
those who come wait, told why, while a fight is on; `invite.room_code()` is the code to show in a
lobby, and `invite.close_room()` closes it. `SLOPPY_SERVER` (a page's `?server=`) points any game
that uses `import invite` at a server, for trying one; examples/aces uses rooms.

A game with a lobby of its own opens the room with `invite.open_room()` instead: no screen, the
lobby shows `room_code()` (big, to read out), `room_link(web_page)` and `room_status()` (which
also says why it could not open), and friends come by `arrivals()`. `invite.start_codes()` is
Invite with a code instead, from the lobby's own button.

**Play with anybody.** `invite.anybody()` asks the server for a public room of the game: one
with space (whose host is not busy), or, when there is none, a new one this side hosts. Its
screen says how it goes, and gives the host `Invited(-1, true)` at once (nobody yet: the others
come by `arrivals()`, as to a room), and the others the host, as Join a friend does. A host's
`room_busy(true)` (a fight on) sends those who come to another room; one waiting in a public room
whose host leaves is found another. Aces starts a public room's fight by itself after 30 s, the
computer filling the sides, so nobody waits long for a full room.

**A browser with WebRTC turned off** (Firefox's `media.peerconnection.enabled = false`, a privacy
setting; some privacy extensions) cannot connect to anyone. `net.webrtc_missing()` says so, in
words for players ("" where WebRTC works, and always in native programs); `net.invite` and
`net.join_invite` then fail with it as `net.why`, and every one of the invite screens shows it
(with how to turn it on in Firefox) instead of trying.

**Aces's lobby** shows both sides, the same on every player's screen: the host keeps each
player's side, and sends the sides (who flies which plane, their names and insignias) to everyone
twice a second; a friend's Switch side asks the host, which moves them if that side has room.
Plane i is on side i % 2, so the players on each side take its planes in order and the computer
the rest. A name or insignia changed during a fight goes to the host, which tells everyone: it is
only drawn, never part of the game the tick plays.

What players need to know, a game should show them: the host's screen gives its address,
`net.local_address()` (as 192.168.1.20), and the one joining types it; both on the same network
(the same Wi-Fi or router), and on one computer, `localhost`. examples/netpong does this, with a
"How to play together" screen. Over the internet, the host's router has to pass the port on to
it (port forwarding), or both connect to a server with a public address.

A web page cannot listen, and a page served over https (as from a website) may only reach `wss://`
servers or `localhost`; native builds reach `wss://` servers too (TLS, with the server's
certificate checked against the authorities the system trusts). For trying a game with pages
alone, `tools/netpong_relay.py` (Python, no Sloppy needed) serves Netpong's page over plain http
on the network and passes messages between two pages, the first of which hosts: a pattern for
any game's own relay.

## Rollback

Every machine runs the whole game from the same start, and only the inputs travel. A remote
input that has not arrived when its tick comes is predicted (the player's last input, repeated);
when it arrives and was different, the game goes back to that tick and plays the ticks since
again, which with Sloppy's value semantics is a copy of the game kept for each tick.

```gdscript
import netplay

struct Pad:                             # one player's input for one tick
    x = 0
    fire = false
struct Game:                            # everything play depends on
    ...
tick = (g: Game, pads: Pad[]) -> Game:  # one tick of play (the same for the same inputs)
    ...

s = netplay.session(Game(), tick, players = 2, me = to_int(env("PLAYER") ?? "0") ?? 0)
s.udp(4400 + s.me, [("192.168.1.20", 4400), ("192.168.1.21", 4401)])
```

Then once a tick, `s.play(pad)` with this machine's input, and draw `s.state`.

**With invite codes, and no server.** `s.over(peers)` plays over peers from `net`: `peers[p]`
is player p's, and this machine's own entry is not used. With invite codes (see Messages
above), two players connect straight to each other from web pages and native programs alike:

```gdscript
# player 0 invites; the packets may be lost (newer ones carry the same inputs again)
friend = net.invite(reliable = false)
s = netplay.session(Game(), tick, players = 2, me = 0)
s.over([-1, friend])
# player 1, with the code: host = net.join_invite(code) ... s.over([host, -1])
```

For more players, one hosts: it invites each of the others (an invite and a reply
each), tells each its number in a message of the game's ("you are 2"), and plays over all of
them, `s.over([-1, a, b])`; the others play over the host alone, `s.over([host, -1, -1])`, and the
host passes on what goes between them (tests/net/np_three.jo does this; Aces does it for up to
twelve, in examples/aces).

**When a player leaves**, the session would wait for their inputs. `s.stand_in(p, input)` has
this machine play for them from then on: their inputs that reached it are kept, and `input` is
theirs for every tick after, sent to the others as theirs. A game makes that input mean "the
computer flies it" (a field the tick reads). Only a machine that had everything the leaver sent
anyone can do it: the host (all of it passed through the host), or either of two players. A
page that closes may not be reported as gone for half a minute: a player `s.silent(p)` for some
seconds can be taken as gone (Aces waits 8), but only while the game lasts: after it, a player
reading the results, or back in the lobby, plays no more ticks and sends nothing.

The session's packets on those peers are its own (marked, so the game's `net.receive()` leaves
them); the game sends and reads its own messages on the same peers as ever (a chat, "again?"),
and their `.joined` and `.left` are the game's, to say "connected" or "your friend left". Until the other player connects,
the session runs `max_ahead` ticks and waits.

**The tick must come out the same on every machine.** Sloppy's math is its own (no system
math library, no fused multiply-add), so the same code gives the same numbers on Linux, Windows,
macOS and in a web page. What breaks it is the game reading something that differs between
machines:
- `random()`: keep a seed in the game and draw from that (`hash(g.tick * 7 + i)` is one way);
- the clock (`time()`, `elapsed()`) or `dt`: a tick is always 1/60 s;
- anything outside the game: the window's size, the mouse in pixels (turn it into the input
  first), files, the order of a map filled from the network;
- a global the tick changes: it is not part of the game, so a rollback does not put it back
  (keep it in the game's struct);
- a global the tick reads that is not the same everywhere: a setting, `env(...)`, a difficulty
  chosen on one machine (put it in the game's struct, the same for all, before the first tick).

The compiler warns where the tick given to `netplay.session`, or a function of the program's it
calls, takes random numbers, reads the clock or the input, or changes a global. (An `Rng` kept in
the game, `g.rng.next_float()`, is the same everywhere.)

A tick may be played several times (each rollback plays it again), so it must do nothing but
compute the game: a sound or particles started in it would start again. Start them in `update`
from what changed in `s.state` since the last frame.

`s.ping(p)` is the round trip to player p and back, in milliseconds, to show players (a
client's is `c.ping`). It is from an input made to the answer's arrival, so it includes the
frame each side waits before it plays and sends: two machines on one computer show about 16 ms.

When it does break, the session finds out: each machine sends a hash of its game at ticks that
everyone's inputs are in for, and `s.desync` says the first tick at which two differed. That,
and other trouble (packets from another build of the game that cannot be read, two machines
with the same `me`, a player not heard from for 5 seconds), is in `s.problem` and said once on
stderr. A debug build (not `--release`) also writes its game at that tick, as JSON, to
`netplay-desync-<tick>-p<me>.json`: the two machines' files differ where the games went apart.
Test with a different `SLOPPY_SEED` for each machine: screenshot runs
(`SLOPPY_SCREENSHOT`) seed `random()` alike and step by exactly 1/60 s, which hides those two
mistakes.

**Input delay.** An input takes effect `delay` ticks after it is made (2 by default, about
33 ms), which hides that much latency with no rollback at all. More delay means fewer and
shorter rollbacks; fighting games use 2 or 3, and more for a far player: about half the ping in
ticks, `s.delay = clamp(int(s.ping(other) / 2.0 / 16.7), 2, 6)`. `s.delay` may be changed at
any time (from the ping once it is known, or a setting): a longer delay gives the ticks between
the same input, a shorter one plays the inputs made meanwhile in turn.

**Waiting.** A session runs at most `s.max_ahead` ticks ahead of the inputs it has (10; then
`s.waiting` is true and the game holds still), and slows down a little when its clock is ahead
of the other's, so both keep pace. Set it after making the session, as `delay`. Inputs made
while it waits are not lost: each change of input is played in turn on the ticks after (a
button tapped during a wait still hits).

A machine that stops for a moment (a 0.3 s hitch: a disk, another program) catches up on the
ticks it missed only as far as `dt` goes, which is never more than 0.1 s (a game playing a tick
for each 1/60 s of it); the rest of the time is lost, and the others, who went on, wait a few
frames for it and then run a little slower until both agree again.

**Replays and spectators.** The ticks below `s.confirmed()` have everyone's inputs for good, and
`s.inputs_at(t)` gives them; taken as they come, they are a replay: the game played again from
its start, tick by tick, comes out the same (and the same on another machine, so a spectator can
be sent them).

```gdscript
saved = 0
replay: Pad[][]
update = (dt: f64):
    s.play(read_pad())
    loop saved < s.confirmed():
        replay.push(s.inputs_at(saved))
        saved += 1
```

Played again: `g = Game()`, then `loop pads in replay: g = tick(g, pads)`. A desync shows up
here too: two machines' replays are the same inputs, and the tick at which their games differ
can be found by playing each.

**Local players.** Two players on one keyboard, or a keyboard and a gamepad, give each player
actions of their own, declared for their number: `action("p2 punch", [.key(.k), .button(.x)],
player = 1)` is the K key, and gamepad 1's X.

## Client and server

The server runs the game; clients send their inputs and draw the worlds it sends back. Three
things hide the latency:
- **prediction**: a client applies its own input at once, so its own player answers without
  delay; when a world comes from the server, the inputs it has not answered yet are applied to
  it again (**reconciliation**), so the player ends up where the server says without jumping;
- **interpolation**: others are drawn a little in the past (`c.interpolation`, 0.1 s), between
  two worlds from the server (`c.view()`), so they move smoothly however unevenly the worlds
  arrive;
- **lag compensation**: each input says which tick its player was seeing, and the game's
  `apply` gets that world too, so a shot hits what the shooter saw.

```gdscript
import netplay

apply = (w: World, player: int, input: Pad, seen: World) -> World: ...    # one player's input
step = (w: World) -> World: ...                                          # the rest of a tick

srv = netplay.server(World(), apply, step)      # (a native program)
srv.listen(4600)                                # once a tick: srv.update(); srv.joined, srv.left

c = netplay.client(World(), apply)
c.connect("game.example.com", 4600)             # once a tick: c.play(pad); draw c.state and c.view()
```

The server's world is the truth: a client cannot move its player anywhere its inputs would not
take it there, and the server applies at most one input of each player a tick (a few more after
a pause, to catch up), so sending more moves no faster. The game need not be deterministic.

A client predicts with `apply` only: what moves a player belongs in `apply` (in `step`, the
client's own player would wait for the server). `random()` in `apply` makes the client's guess
and the server's differ, which shows as flicker: draw it from something both have. Add each
player to the world when `srv.joined` names them, and take them out on `srv.left`.
`c.connected()` turns false, and `c.problem` says why, when the client cannot connect, the
server closes the connection (with its reason: `net.close(p, 4001, "the room is full")` on the
server), or nothing comes from it for 5 seconds. With `c.reconnect = true` a client connects
again by itself when the connection is lost or the server goes away or restarts (after 1, 2,
4... up to 30 seconds), not when the server closed it on purpose; the server sees a new player
then, with the same hello. A server without a window calls `srv.run()`: `srv.update()` 60 times
a second, on time (a loop of `update` and `sleep(1.0 / 60.0)` ticks a little slower than the
clients, and their inputs wait in a queue: lag).

```gdscript
srv = netplay.server(World(), apply, step)
srv.listen(4600)
srv.run()                       # (or each tick in a game's own update: srv.update())
```

What a player is called, or a token to know them by when they come back, goes with the
connection: `c.connect(host, 4600, hello = "{name} {token}")`, and the server reads
`srv.hello(p)` (empty for a moment after `p` joins: it comes with the first world).
`c.disconnect()` leaves; `c.connect(...)` again joins again with the same client.

The game's own messages (a chat line, "round over", the scores) go on the same connection, as
text, in order: `srv.say(p, text)` to one player, `srv.say_all(text)` to everyone, read by the
client in `c.messages` after each `c.play`; `c.say(text)` to the server, read in `srv.messages`
(who sent each, and what) after each `srv.update()`.

To try a slow network on one machine, `srv.lag(100, 20)` and `c.lag(100, 20)` hold what each
side sends 100 ms, and up to 20 ms more at random (in order, as TCP keeps it).
`srv.waiting(p)` says how many of p's inputs wait to be applied: 1 or 2 is right; more is lag.

The world goes to every client as its text (`to_text`), compressed, every `srv.send_every`
ticks (2: 30 a second): a few hundred bytes for a small arena. Keep what does not need to
travel (effects, sounds) out of it, or in the client only. A screenshot run
(`SLOPPY_SCREENSHOT`) of a connected client keeps to real time, as the server does.

Bullets and other things moved in `step` are not predicted: the client sees them when the
server's world shows them, half a round trip and the interpolation later. For a shot that
must show at once, draw its flash in the client when the button is pressed, and let the
server's world bring the bullet.

### Other tick rates

A game that needs fewer ticks (a strategy game, a slow arena: 20 or 30 a second) or more (up to
120) says so on the server: `srv.run(20)`, or `srv.ticks_per_second = 20` for a server ticking in
its own loop. The worlds carry it to the clients (`c.ticks_per_second`), and each client calls
`c.play` once a tick at that rate (as below, with `1.0 / c.ticks_per_second` for `1.0 / 60.0`).
`c.view()` is meant to be drawn every frame: between two plays it goes on by the time since the
last, so others move smoothly at 60 frames a second with a server at 20. `c.interpolation` is in
seconds: at least the time between two worlds (`srv.send_every` ticks: `srv.send_every = 1` at 20
a second), and more on an uneven network.

### Several games on one port

One server can hold many games, each a `netplay.server` of its own, behind one http server on
one port (its pages, its API and the games' WebSockets together). Without `srv.listen`, a server
is fed by hand: `srv.join(p)`, `srv.receive(p, data)` and `srv.leave(p)` from the program's own
`net.receive_server()` loop, and what it has to send comes from `srv.outgoing()`:

```gdscript
import http
import net
import netplay

rooms: {str: netplay.Server[World, Pad]}       # a game each, by its name
room_of: {int: str}                             # each player's room

http.get("/play/:room", (r: http.Request) -> http.Response: http.websocket(r))
http.files("/", "public")
http.listen(8080)
next = time()
loop not stopping():
    http.answer()
    loop e in net.receive_server():
        if e.kind == .joined:
            name = net.handshake(e.peer).path[len("/play/")..]
            if not rooms.has(name): rooms[name] = netplay.server(World(), apply, step)
            if [loop _, r in room_of: if r == name: r].len() >= 8:
                net.close(e.peer, 4001, "the room is full")
                continue
            rooms[name].join(e.peer)
            room_of[e.peer] = name
        else if let name = room_of.get(e.peer):
            if e.kind == .message: rooms[name].receive(e.peer, e.data)
            else:
                rooms[name].leave(e.peer)
                room_of.remove(e.peer)
    # (every room's tick, 60 a second, on time)
    if time() >= next:
        next = max(next + 1.0 / 60.0, time() - 0.25)
        loop name in [loop n, _ in rooms: n]:
            rooms[name].update()
            loop p in rooms[name].joined: rooms[name].world.pos[p] = 0
            loop p in rooms[name].left: rooms[name].world.pos.remove(p)
            loop o in rooms[name].outgoing(): net.send(o.0, o.1)
            if rooms[name].world.pos.len() == 0 and rooms[name].tick > 60: rooms.remove(name)
    net.wait(max(next - time(), 0.0))
```

A client joins a room by its address: `c.connect("wss://game.example.com/play/red", 0)`. A
task for each room works too (its server fed through a channel); the loop above is the
simplest, and costs no more.

### What goes over the wire

For a bot or a client in another language: a WebSocket, binary messages, each starting with a
byte that says what it is.

- From the server, `2` then `you tick ack rate ` in ASCII (four numbers, each followed by a
  space: this player's number, the world's tick, the sequence number of this player's last
  input applied, the server's ticks a second), then the world as `to_text` writes it (Sloppy's
  text for values, as `World(pos={1: 3}, hits=0)`), compressed with raw deflate (RFC 1951, no
  zlib header: Python's `zlib.decompress(data, -15)`).
- From the server, `3` then UTF-8 text: `srv.say`.
- From the client, `1` then UTF-8 text: its hello, once its first world has come.
- From the client, `3` then UTF-8 text: `c.say`.
- From the client, an input: `(seq=12, seen=340, input=Pad(dx=1, fire=false))` as text (no
  leading byte; a struct's name may be left out, `(dx=1, fire=false)`). `seq` counts the
  client's inputs from 1, `seen` is the tick of the world it was drawing (-1 for none: no lag
  compensation). One a tick, at the server's rate: more wait in a queue and are dropped past 8.

## Ticks, not frames

Both kinds play in ticks of 1/60 s (a client-server game at the server's rate:
`c.ticks_per_second`). A screen may show 144 frames a second, or drop a frame, so count ticks
apart from frames:

```gdscript
spare = 0.0
update = (dt: f64):
    global spare
    spare = min(spare + dt, 0.1)
    loop spare >= 1.0 / 60.0:
        spare -= 1.0 / 60.0
        s.play(read_pad())
```

## Trying it on one machine

Run the game twice (two windows), as two players on this machine's addresses: examples/duel
takes `PLAYER=0` and `PLAYER=1`. A real network is slower and loses things: `s.lag(100, 20,
0.05)` adds 100 ms (and up to 20 more) to what this session sends and drops 5% of it, and
examples/duel takes `LAG=100`. For tests, `netplay.Link` is a network
simulated in one program, with its own clock: two sessions over it play the same way every
time (tests/t/rollback.jo, tests/t/clientserver.jo).

## Web pages

A web page cannot use UDP or wait for others to connect. It connects over WebSockets to a
native program: a client-server game's server, or for rollback, a relay
(`netplay.relay(port)`, which a native player can run while playing) that passes packets
between the players in a room (`s.join_relay(host, port, room)`; each still gives its own
`me`: the relay does not hand out numbers, and two with the same one are told so). A page served over https
can only reach `wss://` servers: put a proxy with a certificate (Caddy, for one) in front of
the server.

WebSockets run over TCP, where a lost packet holds up those after it. So pages in a rollback
room also connect straight to each other with WebRTC: they tell each other how to through the
relay, and from then on their packets go between them as over UDP (unordered, never resent,
never held up), not through the relay (`s.direct(p)` says whether player p's do). A STUN
server tells each page its address as others see it: `join_relay` uses Google's public one,
and takes `stun = "stun:..."` for another or `""` for none (then only pages on the same
network reach each other). Pages that cannot reach each other (some company and phone
networks) keep playing through the relay; so does a native player with a page.
