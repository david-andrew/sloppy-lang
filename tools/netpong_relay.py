#!/usr/bin/env python3
"""Netpong for two web pages on one network, with nothing but Python (3.8 or later) installed.

Run it on one computer:   python3 netpong_relay.py
It prints an address to open in a web browser: on this computer, and on the other player's
computer or phone on the same Wi-Fi. The first page to connect hosts, the second joins, and this
program passes their messages between them (it serves the game's page too, over plain http, which
lets the page reach this computer; a page from https:// could not).

The page is netpong.html next to this file if there is one (`sloppy build netpong.jo -o
netpong.html`), else the one on sloppy-lang.org, fetched once. Options: --port N (47200),
--page FILE. A Sloppy build of Netpong can join it too: Join a game, and this computer's address.

What it tells the pages: "host" or "guest" when they connect, "j" (to the host) when the other
player comes, "l" when the other player leaves; every other message goes on to the other player.
"""
import argparse, base64, hashlib, os, socket, struct, sys, tempfile, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE_URL = "https://sloppy-lang.org/examples/netpong/index.html"
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

players = []                 # the connected pages (at most two): the first is the host
lock = threading.Lock()


def local_address():
    """this computer's address on its network: a datagram socket aimed at a public address (no
    packet is sent) and the address it would send from"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 53))
        return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()


def load_page(path):
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [path, os.path.join(here, "netpong.html")]:
        if p and os.path.exists(p):
            return open(p, "rb").read()
    cache = os.path.join(tempfile.gettempdir(), "netpong-page.html")
    # (a copy from today: newer ones of the game come with the website)
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400:
        return open(cache, "rb").read()
    print(f"fetching the game's page from {PAGE_URL} ...")
    page = urllib.request.urlopen(PAGE_URL, timeout=60).read()
    open(cache, "wb").write(page)
    return page


class Player:
    def __init__(self, conn):
        self.conn = conn
        self.send_lock = threading.Lock()

    def send(self, payload, opcode=1):
        """one frame to the page (a server's frames are not masked)"""
        n = len(payload)
        head = bytes([0x80 | opcode])
        if n < 126: head += bytes([n])
        elif n < 65536: head += bytes([126]) + struct.pack(">H", n)
        else: head += bytes([127]) + struct.pack(">Q", n)
        with self.send_lock:
            try: self.conn.sendall(head + payload)
            except OSError: pass

    def recv_exact(self, n):
        b = b""
        while len(b) < n:
            part = self.conn.recv(n - len(b))
            if not part: raise ConnectionError
            b += part
        return b

    def frames(self):
        """(opcode, payload) for each message the page sends, until it closes"""
        message, op0 = b"", 0
        while True:
            b0, b1 = self.recv_exact(2)
            op, n = b0 & 15, b1 & 127
            if n == 126: n = struct.unpack(">H", self.recv_exact(2))[0]
            elif n == 127: n = struct.unpack(">Q", self.recv_exact(8))[0]
            mask = self.recv_exact(4) if b1 & 128 else b"\0\0\0\0"
            data = bytes(c ^ mask[i & 3] for i, c in enumerate(self.recv_exact(n)))
            if op == 8: return
            if op == 9:
                self.send(data, 10)
                continue
            if op == 10: continue
            if op != 0: op0, message = op, b""
            message += data
            if b0 & 0x80:
                yield op0, message
                message = b""


def other_of(p):
    with lock:
        for q in players:
            if q is not p: return q
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"        # (a WebSocket's switch must be HTTP/1.1's)

    def log_message(self, *a): pass

    def do_GET(self):
        if self.headers.get("Upgrade", "").lower() == "websocket":
            return self.websocket()
        host = self.headers.get("Host") or f"localhost:{self.server.server_port}"
        if "join=" not in self.path:
            # (the page joins this relay by itself: its address in ?join=)
            self.send_response(302)
            self.send_header("Location", f"/?join=ws://{host}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.server.page)))
        self.end_headers()
        self.wfile.write(self.server.page)

    def websocket(self):
        key = self.headers.get("Sec-WebSocket-Key", "")
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.wfile.flush()
        p = Player(self.connection)
        with lock:
            full = len(players) >= 2
            if not full: players.append(p)
            role = "host" if not full and len(players) == 1 else "guest"
            host = players[0] if len(players) == 2 else None
        if full:
            p.send(b"full")
            return
        p.send(role.encode())
        print(f"a player connected from {self.client_address[0]}: {role}")
        if host is not None: host.send(b"j")
        try:
            for op, msg in p.frames():
                q = other_of(p)
                if q is not None: q.send(msg, op)
        except (ConnectionError, OSError):
            pass
        with lock:
            if p in players: players.remove(p)
            rest = list(players)
            players.clear()          # (the other goes back to its title: both start over)
        print(f"a player left ({self.client_address[0]})")
        for q in rest: q.send(b"l")
        self.close_connection = True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=47200)
    ap.add_argument("--page", default="")
    args = ap.parse_args()
    try:
        page = load_page(args.page)
    except OSError as e:
        sys.exit(f"could not get the game's page ({e}): give one with --page netpong.html")
    try:
        server = ThreadingHTTPServer(("", args.port), Handler)
    except OSError as e:
        sys.exit(f"port {args.port} is taken ({e}): another relay or a Netpong hosting here? --port picks another")
    server.daemon_threads = True
    server.page = page
    ip = local_address()
    print(f"Netpong relay, on port {args.port}. In a web browser, open:")
    print(f"  on this computer:                  http://localhost:{args.port}")
    if ip: print(f"  on another one, or a phone, on the same Wi-Fi:  http://{ip}:{args.port}")
    else: print("  (this computer seems to be on no network: only pages on it can join)")
    print("The first page to open it hosts, the second joins. If a window asks whether Python may")
    print("use the network, allow it. Ctrl+C stops.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
