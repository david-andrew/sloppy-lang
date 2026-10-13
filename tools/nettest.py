#!/usr/bin/env python3
"""Networking (lib/net.jo): a server and a client built from tests/net, talking over this machine's
loopback; with a browser at hand (Playwright's Chromium), also a web page's client.
usage: tools/nettest.py [path/to/sloppy]"""
import os, random, shutil, subprocess, sys, tempfile, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
tmp = tempfile.mkdtemp(prefix="sloppy-nettest-")
port = random.randrange(20000, 30000)        # (below the ports the system gives out for connections: 32768 up)
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"), NET_PORT=str(port))
exe = ".exe" if os.name == "nt" else ""
failed = 0

def build(name, *flags):
    out = os.path.join(tmp, name)
    subprocess.run([sloppy, "build", os.path.join(root, "tests", "net", name + ".jo"), "-o", out, *flags], check=True, env=env)
    return out

WANT_SERVER = ["listening", "server: joined", "server: got msg 1", "server: got msg 2", "server: got msg 3", "server: left"]
WANT_CLIENT = ["client: joined 1", "client: echo msg 1", "client: echo msg 2", "client: echo msg 3", "client: big 300000 7 7", "client: left"]

def check(name, got, want):
    global failed
    lines = [l.strip() for l in got.splitlines() if l.strip()]
    if lines != want:
        failed += 1
        print(f"FAIL {name}:\n  got:  {lines}\n  want: {want}")
    else: print(f"ok   {name}")

server = build("server") + exe
client = build("client") + exe
for host in ["localhost", "127.0.0.1"]:
    s = subprocess.Popen([server], stdout=subprocess.PIPE, text=True, env=env)
    time.sleep(0.5)
    c = subprocess.run([client], capture_output=True, text=True, env=dict(env, NET_HOST=host), timeout=60)
    s_out = s.communicate(timeout=60)[0]
    check(f"native client ({host})", c.stdout, WANT_CLIENT)
    check(f"native server ({host})", s_out, WANT_SERVER)
    port += 1
    env["NET_PORT"] = str(port)

# a web page's client, in a browser: the same, but as a game (messages arrive between frames)
shell = None
pw = os.path.expanduser("~/.cache/ms-playwright")
if os.path.isdir(pw):
    for d in sorted(os.listdir(pw)):
        if d.startswith("chromium_headless_shell"):
            for sub in os.listdir(os.path.join(pw, d)):
                p = os.path.join(pw, d, sub, "chrome-headless-shell")
                if os.path.exists(p): shell = p
if shell:
    page = build("web_client", "--target", "wasm") + ".html"
    s = subprocess.Popen([server], stdout=subprocess.PIPE, text=True, env=env)
    time.sleep(0.5)
    # (the page reads NET_PORT from its address)
    b = subprocess.Popen([shell, "--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0",
                          "file://" + page + f"?NET_PORT={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: s_out = s.communicate(timeout=30)[0]
    except subprocess.TimeoutExpired:
        s.kill()
        s_out = s.communicate()[0]
    b.kill()
    check("web client (in Chromium)", s_out, WANT_SERVER[:5] + ["server: got big ok", "server: left"])
    # rollback netplay through a relay: a native player and a web page's
    port += 1
    env["NET_PORT"] = str(port)
    host = build("np_host") + exe
    page = build("np_page", "--target", "wasm") + ".html"
    h = subprocess.Popen([host], stdout=subprocess.PIPE, text=True, env=env)
    time.sleep(0.5)
    b = subprocess.Popen([shell, "--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0",
                          "file://" + page + f"?NET_PORT={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: h_out = h.communicate(timeout=60)[0]
    except subprocess.TimeoutExpired:
        h.kill()
        h_out = h.communicate()[0]
    b.kill()
    check("netplay with a web page (in Chromium)", h_out, ["host: played true", "host: compared true, desync -1"])
    # a client-server game: a native server, a web page's client
    port += 1
    env["NET_PORT"] = str(port)
    srv = build("cs_server") + exe
    page = build("cs_page", "--target", "wasm") + ".html"
    h = subprocess.Popen([srv], stdout=subprocess.PIPE, text=True, env=env)
    time.sleep(0.5)
    b = subprocess.Popen([shell, "--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0",
                          "file://" + page + f"?NET_PORT={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: h_out = h.communicate(timeout=60)[0]
    except subprocess.TimeoutExpired:
        h.kill()
        h_out = h.communicate()[0]
    b.kill()
    check("client and server with a web page (in Chromium)", h_out, ["server: walked true"])
else: print("(no browser: the web client is not tried)")
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if failed else 0)
