#!/usr/bin/env python3
"""Tests of lib/term.jo through a pseudo-terminal: keys and the mouse sent as a terminal sends them
and the events the program reads, the terminal's settings and screen put back after an exit, a
panic, a crash, ctrl-c and SIGTERM, a resize, what a flush writes, and a task running while
another waits for a key.

usage: tools/termtest.py [compiler]   (Linux and macOS)"""
import codecs, fcntl, os, select, shutil, signal, struct, subprocess, sys, tempfile, termios, time, unicodedata

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))

PROGRAM = r'''
import term

log = env("TT_LOG") ?? ""
said = ""
note = (s: str):
    global said
    said += s + "\n"
    write_file(log, said)

on_quit = (): print("on_quit ran")

# (each flush, then what the program drew, for the test's terminal to be compared with)
shown = env("TT_SCREEN") ?? ""
flushed = () -> int:
    n = term.flush()
    if len(shown) > 0: write_file(shown, term.screen_text())
    n

ticks = 0
ticker = ():
    loop ticks < 1000:
        ticks += 1
        paint()
        sleep(0.05)

paint = ():
    loop y in 0..term.size().1:
        term.put(0, y, "row {y} of the screen, the same each time {ticks}")
    flushed()

main = ():
    ok = term.start(mouse = true, ctrl_c_key = env("TT_CTRLC") != none)
    note("started {ok} {term.size()}")
    if env("TT_TASK") != none: spawn(ticker, background = true)
    paint()
    loop:
        e = term.read_event() ?? break
        note("{e}")
        if e.name == "q": break
        if e.name == "e": exit(3)
        if e.name == "p": panic("on purpose")
        if e.name == "s":
            p: *int = null
            print(p[0])
        if e.name == "b":
            n = 0
            loop: n += 1
        if e.name == "x":
            term.put(5, 3, "X")
            note("flushed {flushed()}")
        if e.name == "w":
            term.put(0, 5, "日本語 and é")
            note("flushed {flushed()}")
        if e.name == "r":
            term.stop()
            note("stopped")
            sleep(0.3)
            term.start(mouse = true)
            note("started again")
            paint()
        if e.kind == .resize: paint()
    note("end")
'''

failed = 0
passed = 0


class Terminal:
    """what a terminal shows of the bytes written to it: the characters only (the cursor moved by
    CUP, CUF, CUB, CUU, CUD, CR and LF; ED 2 and the alternate screen clear it; colors and modes
    passed over)"""

    def __init__(self, w=80, h=24):
        self.resize(w, h)
        self.dec = codecs.getincrementaldecoder("utf-8")("replace")
        self.pending = ""

    def resize(self, w, h):
        self.w, self.h = w, h
        self.cells = [[" "] * w for _ in range(h)]
        self.x = self.y = 0

    def text(self):
        return "\n".join("".join(c for c in row if c is not None) for row in self.cells)

    def feed(self, b):
        s = self.pending + self.dec.decode(b)
        self.pending = ""
        i = 0
        while i < len(s):
            c = s[i]
            if c == "\x1b":
                j = i + 1
                if j >= len(s):
                    self.pending = s[i:]
                    return
                if s[j] == "[":
                    k = j + 1
                    while k < len(s) and not ("@" <= s[k] <= "~"):
                        k += 1
                    if k >= len(s):
                        self.pending = s[i:]
                        return
                    self.csi(s[j + 1:k], s[k])
                    i = k + 1
                elif s[j] == "]":
                    k = s.find("\x07", j)
                    if k < 0:
                        self.pending = s[i:]
                        return
                    i = k + 1
                else:
                    i = j + 1
                continue
            if c == "\r": self.x = 0
            elif c == "\n": self.y = min(self.y + 1, self.h - 1)
            elif c >= " ": self.put(c)
            i += 1

    def csi(self, p, f):
        ns = [int(x) if x.isdigit() else 0 for x in p.lstrip("?").split(";")] if p else []
        n = ns[0] if ns and ns[0] > 0 else 1
        if f == "H":
            self.y = min(max((ns[0] if ns and ns[0] else 1) - 1, 0), self.h - 1)
            self.x = min(max((ns[1] if len(ns) > 1 and ns[1] else 1) - 1, 0), self.w - 1)
        elif f == "C": self.x = min(self.x + n, self.w - 1)
        elif f == "D": self.x = max(self.x - n, 0)
        elif f == "A": self.y = max(self.y - n, 0)
        elif f == "B": self.y = min(self.y + n, self.h - 1)
        elif f == "J" and p == "2": self.cells = [[" "] * self.w for _ in range(self.h)]
        elif f in "hl" and p == "?1049": self.cells = [[" "] * self.w for _ in range(self.h)]

    def put(self, c):
        o = ord(c)
        if unicodedata.combining(c) or unicodedata.category(c) in ("Mn", "Me", "Cf") or 0xFE00 <= o <= 0xFE0F or 0x1F3FB <= o <= 0x1F3FF:
            px = self.x - 1
            if px >= 0 and self.cells[self.y][px] is None: px -= 1
            if px >= 0: self.cells[self.y][px] += c
            return
        wide = unicodedata.east_asian_width(c) in ("W", "F")
        if self.x >= self.w: return
        row = self.cells[self.y]
        # (a wide character's half written over: the other half blank)
        if row[self.x] is None and self.x > 0: row[self.x - 1] = " "
        if self.x + 1 < self.w and row[self.x + 1] is None: row[self.x + 1] = " "
        row[self.x] = c
        if wide and self.x + 1 < self.w:
            row[self.x + 1] = None
            if self.x + 2 < self.w and row[self.x + 2] is None: row[self.x + 2] = " "
        self.x += 2 if wide else 1


def check(ok, what, detail=""):
    global failed, passed
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {what}" + (f"\n{detail}" if detail else ""))


class Run:
    """the program on a terminal of its own, which this side writes keys to and reads"""

    def __init__(self, exe, d, extra=None, rows=24, cols=80, args=(), ready=None):
        self.master, self.slave = os.openpty()
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        self.cooked = termios.tcgetattr(self.slave)
        self.log = os.path.join(d, "events.txt")
        if os.path.exists(self.log): os.remove(self.log)
        e = dict(env, TT_LOG=self.log, TT_SCREEN=os.path.join(d, "screen.txt"), **(extra or {}))
        # (its own session, with this terminal as its controlling one: ctrl-c and resizes reach it)
        self.p = subprocess.Popen([exe, *args], stdin=self.slave, stdout=self.slave, stderr=self.slave, env=e, start_new_session=True,
                                  preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
        self.out = b""
        self.term = Terminal(cols, rows)
        self.screen = os.path.join(d, "screen.txt")
        self.wait_for(lambda: ready(self) if ready else b"\x1b[?1049h" in self.out and self.lines() >= 1, "the program to start")

    def read(self, t=0.05):
        end = time.time() + t
        while True:
            r, _, _ = select.select([self.master], [], [], max(0.0, end - time.time()))
            if r:
                try:
                    b = os.read(self.master, 65536)
                except OSError:
                    return
                if not b: return
                self.out += b
                self.term.feed(b)
            elif time.time() >= end:
                return

    def lines(self):
        try:
            return len(open(self.log, encoding="utf-8").read().splitlines())
        except OSError:
            return 0

    def events(self):
        try:
            return open(self.log, encoding="utf-8").read().splitlines()
        except OSError:
            return []

    def wait_for(self, cond, what, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            self.read(0.02)
            if cond(): return True
        raise AssertionError(f"timed out waiting for {what}; events: {self.events()}; output: {self.out[-400:]!r}")

    def send(self, b, events=1):
        n = self.lines()
        os.write(self.master, b)
        if events: self.wait_for(lambda: self.lines() >= n + events, f"an event for {b!r}")

    def end(self, timeout=10):
        end = time.time() + timeout
        while self.p.poll() is None and time.time() < end:
            self.read(0.02)
        self.read(0.1)
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
            return None
        return self.p.returncode

    def same_screen(self, what):
        """the terminal shows what the program drew"""
        self.read(0.2)
        try:
            want = open(self.screen, encoding="utf-8").read()
        except OSError:
            want = ""
        got = self.term.text()
        check(got == want, f"{what}: the terminal shows what was drawn", f"terminal:\n{got}\nprogram:\n{want}")
        return got

    def restored(self, what):
        """the terminal's settings and screen as they were before the program"""
        now = termios.tcgetattr(self.slave)
        check(now == self.cooked, f"{what}: the terminal's settings put back", f"before {self.cooked}\nafter  {now}")
        tail = self.out[max(self.out.rfind(b"\x1b[?1049h"), 0):]
        check(b"\x1b[?1049l" in tail and b"\x1b[?25h" in tail, f"{what}: its screen and cursor put back", repr(self.out[-300:]))

    def close(self):
        if self.p.poll() is None:
            self.p.kill()
            self.p.wait()
        os.close(self.master)
        os.close(self.slave)


def main():
    d = tempfile.mkdtemp(prefix="sloppy-term-")
    src = os.path.join(d, "tt.jo")
    open(src, "w").write(PROGRAM)
    exe = os.path.join(d, "tt")
    r = subprocess.run([sloppy, "build", src, "-o", exe], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL the test program does not build\n" + r.stderr)
        sys.exit(1)

    # keys, as terminals send them, and what the program reads
    t = Run(exe, d)
    keys = [(b"a", "key a"), (b"A", "key A"), (b"\xc3\xa9", "key é"), (b"\xe6\x97\xa5", "key 日"), (b"\xf0\x9f\x98\x80", "key 😀"),
            (b" ", "key space"), (b"\r", "key enter"), (b"\t", "key tab"), (b"\x1b[Z", "key shift+tab"), (b"\x7f", "key backspace"),
            (b"\x1b[3~", "key delete"), (b"\x1b", "key escape"), (b"\x1b[A", "key up"), (b"\x1b[B", "key down"), (b"\x1b[C", "key right"),
            (b"\x1b[D", "key left"), (b"\x1bOA", "key up"), (b"\x1b[H", "key home"), (b"\x1b[F", "key end"), (b"\x1b[1~", "key home"),
            (b"\x1b[4~", "key end"), (b"\x1b[5~", "key page_up"), (b"\x1b[6~", "key page_down"), (b"\x1b[2~", "key insert"),
            (b"\x1bOP", "key f1"), (b"\x1bOS", "key f4"), (b"\x1b[15~", "key f5"), (b"\x1b[24~", "key f12"), (b"\x1b[1;5P", "ctrl+f1"),
            (b"\x01", "key ctrl+a"), (b"\x1a", "key ctrl+z"), (b"\x1c", "key ctrl+\\"), (b"\x00", "key ctrl+space"), (b"\x1bx", "key alt+x"),
            (b"\x1b\x01", "key ctrl+alt+a"), (b"\x1b[1;5A", "key ctrl+up"), (b"\x1b[1;2C", "key shift+right"), (b"\x1b[1;3D", "key alt+left"),
            (b"\x1b[1;6B", "key ctrl+shift+down"), (b"\x1b[3;5~", "key ctrl+delete"), (b"\x1b[13;2u", "key shift+enter"),
            (b"\x1b[27;5;105~", "key ctrl+i"), (b"\x1b[<0;10;5M", "mouse press 1 at 9,4"), (b"\x1b[<0;10;5m", "mouse release 1 at 9,4"),
            (b"\x1b[<2;1;1M", "mouse press 3 at 0,0"), (b"\x1b[<32;11;5M", "mouse drag 1 at 10,4"), (b"\x1b[<64;3;3M", "mouse wheel_up 0 at 2,2"),
            (b"\x1b[<65;3;3M", "mouse wheel_down 0 at 2,2"), (b"\x1b[<16;4;4M", "mouse press 1 at 3,3"),
            (b"\x1b[200~two\r\nlines\x1b[201~", "paste 9 bytes")]
    for seq, want in keys:
        t.send(seq)
        got = t.events()[-1]
        check(got.endswith(want), f"key {seq!r}", f"expected {want!r}, got {got!r}")
    # (several in one read, and a paste in pieces)
    t.send(b"\x1b[A\x1b[Bz", 3)
    check(t.events()[-3:] == ["key up", "key down", "key z"], "three keys in one read", str(t.events()[-3:]))
    t.send(b"\x1b[200~pie", 0)
    time.sleep(0.2)
    t.send(b"ces\x1b[201~")
    check(t.events()[-1] == "paste 6 bytes", "a paste in two pieces", t.events()[-1])
    t.same_screen("after the keys")

    # a resize: the event, and the screen drawn again at the new size
    fcntl.ioctl(t.master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
    t.term.resize(100, 30)
    os.kill(t.p.pid, signal.SIGWINCH)
    t.wait_for(lambda: t.events()[-1] == "resize 100x30", "the resize event")
    t.wait_for(lambda: b"row 29 of" in t.out, "the screen drawn at the new size")
    t.same_screen("after a resize")

    # a flush writes what changed: one cell
    t.out = b""
    t.send(b"x", 2)
    flushed = int(t.events()[-1].split()[-1])
    t.read(0.1)
    check(flushed < 40 and b"X" in t.out, "a flush of one cell changed", f"{flushed} bytes: {t.out!r}")
    t.send(b"x", 2)
    check(t.events()[-1] == "flushed 0", "a flush with nothing changed writes nothing", t.events()[-1])
    t.send(b"w", 2)
    t.read(0.1)
    check("日本語".encode() in t.out, "wide characters written", repr(t.out[-200:]))
    t.same_screen("after a cell changed, and wide characters")

    # stop and start again: the terminal as it was in between
    t.send(b"r", 1)
    t.wait_for(lambda: t.events()[-1] == "stopped", "stop")
    between = termios.tcgetattr(t.slave)
    check(between == t.cooked, "term.stop() puts the settings back", f"{between}")
    t.wait_for(lambda: t.events()[-1] == "started again", "start again")
    t.send(b"k")
    check(t.events()[-1] == "key k", "keys after starting again", t.events()[-1])
    t.same_screen("started again")
    t.send(b"q", 2)
    code = t.end()
    check(code == 0, "q ends it", f"exit {code}")
    t.restored("its end")
    check(b"on_quit ran" in t.out[t.out.rfind(b"\x1b[?1049l"):], "on_quit's output after the screen is put back", repr(t.out[-200:]))
    t.close()

    # how it ends: exit(), a panic, a crash, ctrl-c, SIGTERM, ctrl-c twice while busy
    for key, what, want in [(b"e", "exit(3)", 3), (b"p", "a panic", 101), (b"s", "a crash", 101), (b"\x03", "ctrl-c", 130),
                            (None, "SIGTERM", 143), (b"b", "ctrl-c twice while it computes", 130)]:
        t = Run(exe, d)
        if key is None:
            os.kill(t.p.pid, signal.SIGTERM)
        else:
            t.send(key, 0 if key == b"\x03" else 1)
        if key == b"b":
            time.sleep(0.3)
            os.write(t.master, b"\x03")
            time.sleep(0.3)
            check(t.p.poll() is None, "one ctrl-c does not end a program that never waits")
            os.write(t.master, b"\x03")
        code = t.end()
        check(code == want, f"{what}: its exit code", f"expected {want}, got {code}; {t.out[-300:]!r}")
        t.restored(what)
        if want == 101:
            after = t.out[t.out.rfind(b"\x1b[?1049l"):]
            check(b"panic:" in after, f"{what}: the message after the screen is put back", repr(t.out[-300:]))
        t.close()

    # ctrl-c as a key
    t = Run(exe, d, {"TT_CTRLC": "1"})
    t.send(b"\x03")
    check(t.events()[-1] == "key ctrl+c", "ctrl-c as a key", t.events()[-1])
    t.send(b"q", 2)
    check(t.end() == 0, "ctrl-c as a key: q ends it")
    t.restored("ctrl-c as a key")
    t.close()

    # a task runs while another waits for a key
    t = Run(exe, d, {"TT_TASK": "1"})
    t.out = b""
    t.read(0.6)
    frames = t.out.count(b"\x1b[?2026h")
    check(frames >= 4, "a task draws while main waits for a key", f"{frames} frames in 0.6 s")
    t.send(b"j")
    check(t.events()[-1] == "key j", "a key read with a task running", t.events()[-1])
    t.same_screen("with a task drawing")
    t.send(b"q", 2)
    check(t.end() == 0, "with a task: q ends it")
    t.restored("with a task")
    t.close()

    # the example: a file browser
    files = os.path.join(d, "files")
    r = subprocess.run([sloppy, "build", os.path.join(root, "examples", "files.jo"), "-o", files], env=env, capture_output=True, text=True)
    check(r.returncode == 0, "examples/files.jo builds", r.stderr)
    if r.returncode == 0:
        top = os.path.join(d, "tree")
        os.makedirs(os.path.join(top, "alpha"), exist_ok=True)
        open(os.path.join(top, "alpha", "inner.txt"), "w").write("inside\n")
        open(os.path.join(top, "beta.txt"), "w").write("hello from beta\nsecond line\n")
        open(os.path.join(top, "日本.txt"), "w", encoding="utf-8").write("こんにちは\n")
        t = Run(files, d, args=[top], ready=lambda r: "inner.txt" in r.term.text())
        shows = lambda *xs: lambda: all(x in t.term.text() for x in xs)
        os.write(t.master, b"\x1b[B")
        t.wait_for(shows("hello from beta", "second line"), "the second file's preview")
        os.write(t.master, "/日".encode())
        t.wait_for(shows("/日", "日本.txt", "こんにちは"), "the filter")
        os.write(t.master, b"\r")
        t.wait_for(shows("1 of 3 matching '日'"), "the filter typed")
        os.write(t.master, b"\x1b")
        t.wait_for(shows("3 of 3"), "the filter cleared")
        os.write(t.master, b"\x1b[<0;3;3M")          # (a click on the first row, chosen already: opened)
        t.wait_for(shows("/alpha", "inner.txt", "inside", "1 of 1"), "a click opening the directory")
        os.write(t.master, b"\x7f")
        t.wait_for(shows("3 of 3", "alpha/", "beta.txt"), "backspace going up")
        lines = t.term.text().splitlines()
        check(lines[1].startswith("┌") and lines[-1].startswith("3 of 3"), "the file browser's frame", t.term.text())
        os.write(t.master, b"q")
        check(t.end() == 0, "the file browser: q ends it")
        t.restored("the file browser")
        t.close()

    shutil.rmtree(d, ignore_errors=True)
    print(f"{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
