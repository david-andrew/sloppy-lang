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
| Web pages | connect to a native server | through a relay | connect to a native server |

## Messages

`import net` sends messages (text or bytes) over WebSockets: `net.listen(port)` in a native
program, `net.connect(host, port)` from a native program or a web page, `net.receive()` each
frame for what happened. Messages arrive whole and in order. Native programs can also send UDP
datagrams (`net.udp`), which may be lost or come out of order but never wait for each other. See
[the library](api.html#networking).

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

**The tick must come out the same on every machine.** Sloppy's math is its own (no system
math library, no fused multiply-add), so the same code gives the same numbers on Linux, Windows,
macOS and in a web page. What breaks it is the game reading something that differs between
machines:
- `random()`: keep a seed in the game and draw from that (`hash(g.tick * 7 + i)` is one way);
- the clock (`time()`, `elapsed()`) or `dt`: a tick is always 1/60 s;
- anything outside the game: the window's size, the mouse in pixels (turn it into the input
  first), files, the order of a map filled from the network.

When it does break, the session finds out: each machine sends a hash of its game at ticks that
everyone's inputs are in for, and `s.desync` says the first tick at which two differed.

**Input delay.** An input takes effect `delay` ticks after it is made (2 by default, about
33 ms), which hides that much latency with no rollback at all. More delay means fewer and
shorter rollbacks; fighting games use 2 or 3.

**Waiting.** A session runs at most `max_ahead` ticks ahead of the inputs it has (then
`s.waiting` is true and the game holds still), and slows down a little when its clock is ahead
of the other's, so both keep pace.

## Client and server

The server runs the game; clients send their inputs and draw the worlds it sends back. Three
things hide the latency:
- **prediction**: a client applies its own input at once, so its own player answers without
  delay; when a world comes from the server, the inputs it has not answered yet are applied to
  it again (**reconciliation**), so the player ends up where the server says without jumping;
- **interpolation**: others are drawn a few ticks in the past, between two worlds from the
  server (`c.view()`), so they move smoothly however unevenly the worlds arrive;
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
take it there. The game need not be deterministic.

## Ticks, not frames

Both kinds play in ticks of 1/60 s. A screen may show 144 frames a second, or drop a frame, so
count ticks apart from frames:

```gdscript
spare = 0.0
update = (dt: f64):
    spare = min(spare + dt, 0.1)
    loop spare >= 1.0 / 60.0:
        spare -= 1.0 / 60.0
        s.play(read_pad())
```

## Trying it on one machine

Run the game twice (two windows), as two players on this machine's addresses: examples/duel
takes `PLAYER=0` and `PLAYER=1`. A real network is slower and loses things: `s.lag(100, 20,
0.05)` adds 100 ms (and up to 20 more) to what this session sends and drops 5% of it, and
examples/duel and examples/arena take `LAG=100`. For tests, `netplay.Link` is a network
simulated in one program, with its own clock: two sessions over it play the same way every
time (tests/t/rollback.jo, tests/t/clientserver.jo).

## Web pages

A web page cannot use UDP or wait for others to connect. It connects over WebSockets to a
native program: a client-server game's server, or for rollback, a relay
(`netplay.relay(port)`, which a native player can run while playing) that passes packets
between the players in a room (`s.join_relay(host, port, room)`). A page served over https
can only reach `wss://` servers: put a proxy with a certificate (Caddy, for one) in front of
the server. WebSockets run over TCP, where a lost packet holds up those after it, so a page's
connection is not as smooth as UDP on a bad network; WebRTC, which browsers can use without
that, is on the [roadmap](https://github.com/david-andrew/sloppy-lang/blob/master/docs/ROADMAP.md).
