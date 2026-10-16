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

# tools/netpong_relay.py (Python): the first player hosts, the second is the guest, messages pass
port += 1
env["NET_PORT"] = str(port)
player = build("relay_player") + exe
dummy = os.path.join(tmp, "page.html")
open(dummy, "w").write("<html></html>")
r = subprocess.Popen([sys.executable, "-u", os.path.join(root, "tools", "netpong_relay.py"), "--port", str(port), "--page", dummy],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.0)
a = subprocess.Popen([player], stdout=subprocess.PIPE, text=True, env=env)
time.sleep(0.5)
b = subprocess.run([player], capture_output=True, text=True, env=env, timeout=40)
a_out = a.communicate(timeout=40)[0]
r.kill()
check("relay: the first player hosts", a_out, ["host: connected", "host: the other came", "host: got pong"])
check("relay: the second is the guest", b.stdout, ["guest: connected", "guest: got ping", "guest: the other left"])

# straight to each other (WebRTC), no server: one native program invites, another joins with its
# code, the first accepts the reply, and messages pass
peer = build("invite_peer") + exe
inv = os.path.join(tmp, "invite")
os.makedirs(inv, exist_ok=True)
a = subprocess.Popen([peer], stdout=subprocess.PIPE, text=True, env=dict(env, DIR=inv, ROLE="invite"))
b = subprocess.run([peer], capture_output=True, text=True, env=dict(env, DIR=inv, ROLE="join"), timeout=60)
a_out = a.communicate(timeout=60)[0]
check("WebRTC: a native program invites", a_out, ["accepted:true", "native:joined", "native got:ping from native", "native got:pong from native"])
check("WebRTC: a native program joins", b.stdout, ["native:joined", "native got:ping from native", "native got:pong from native"])

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
                          "file://" + page + f"?net_port={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: h_out = h.communicate(timeout=60)[0]
    except subprocess.TimeoutExpired:
        h.kill()
        h_out = h.communicate()[0]
    b.kill()
    check("client and server with a web page (in Chromium)", h_out, ["server: hello page", "server: walked true"])
    # two web pages, straight to each other (WebRTC): the relay passes on only how they connect
    port += 1
    env["NET_PORT"] = str(port)
    relay = build("rtc_relay") + exe
    page = build("rtc_page", "--target", "wasm") + ".html"
    r = subprocess.Popen([relay], stdout=subprocess.PIPE, text=True, env=env)
    time.sleep(0.5)
    pages = [subprocess.Popen([shell, "--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0",
                               f"--user-data-dir={tmp}/browser{p}", "file://" + page + f"?NET_PORT={port}&PLAYER={p}"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for p in range(2)]
    try: r_out = r.communicate(timeout=70)[0]
    except subprocess.TimeoutExpired:
        r.kill()
        r_out = r.communicate()[0]
    for b in pages: b.kill()
    check("two web pages over WebRTC (in Chromium)", r_out, [f"player {p}: played true, direct true, desync -1" for p in range(2)])
    # WebRTC between a web page and a native program, each inviting in turn (driven by node)
    if shutil.which("node"):
        page = build("invite_page", "--target", "wasm") + ".html"
        r = subprocess.run(["node", os.path.join(root, "tools", "rtc_webtest.mjs"), shell, page, peer, os.path.join(tmp, "rtcweb")],
                           capture_output=True, text=True, timeout=180)
        print(r.stdout.strip())
        if r.returncode != 0: failed += 1
    else: print("(no node: WebRTC with a web page is not tried)")
else: print("(no browser: the web client is not tried)")
# the same in Firefox, where SLOPPY_FIREFOX says where one is (on a display of its own if Xvfb is
# installed: headless, Firefox has no WebGL)
ff = os.environ.get("SLOPPY_FIREFOX")
if ff and shutil.which("node"):
    page = build("invite_page", "--target", "wasm") + ".html"
    r = subprocess.run(["node", os.path.join(root, "tools", "rtc_webtest.mjs"), ff, page, peer, os.path.join(tmp, "rtcff")],
                       capture_output=True, text=True, timeout=240)
    print(r.stdout.strip())
    if r.returncode != 0: failed += 1
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if failed else 0)
