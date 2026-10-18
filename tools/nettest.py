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

# wait (up to 15 s) until something listens on the port: a server started just before
def wait_port(p, limit=15.0):
    import socket
    end = time.time() + limit
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", p), timeout=0.5).close()
            return
        except OSError: time.sleep(0.1)

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
wait_port(port)
a = subprocess.Popen([player], stdout=subprocess.PIPE, text=True, env=env)
# (the second starts once the first is connected: the first to connect hosts)
first = a.stdout.readline()
b = subprocess.run([player], capture_output=True, text=True, env=env, timeout=40)
a_out = first + a.communicate(timeout=40)[0]
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
# WebRTC: the other game killed (no goodbye): found gone after some seconds of silence, and why
lost = build("rtc_lost") + exe
ld = os.path.join(tmp, "lost")
os.makedirs(ld, exist_ok=True)
a = subprocess.Popen([lost], stdout=subprocess.PIPE, text=True, env=dict(env, DIR=ld, ROLE="invite"))
b = subprocess.Popen([lost], stdout=subprocess.DEVNULL, env=dict(env, DIR=ld, ROLE="join"))
t0 = time.time()
while time.time() - t0 < 30 and not (os.path.exists(os.path.join(ld, "invite.joined")) and os.path.exists(os.path.join(ld, "join.joined"))): time.sleep(0.1)
time.sleep(1)
b.kill()
try: a_out = a.communicate(timeout=60)[0]
except subprocess.TimeoutExpired:
    a.kill()
    a_out = a.communicate()[0]
a_lines = [l for l in a_out.splitlines() if l.strip()]
if len(a_lines) == 2 and a_lines[0] == "invite: joined" and "stopped answering" in a_lines[1]: print("ok   WebRTC: the other game gone without a word is found gone")
else:
    failed += 1
    print(f"FAIL WebRTC: the other game gone without a word: {a_lines}")
# rollback netplay over invite codes (s.over), the same way
npi = build("np_invite") + exe
npd = os.path.join(tmp, "np_codes")
os.makedirs(npd, exist_ok=True)
a = subprocess.Popen([npi], stdout=subprocess.PIPE, text=True, env=dict(env, DIR=npd, ROLE="invite"))
b = subprocess.run([npi], capture_output=True, text=True, env=dict(env, DIR=npd, ROLE="join"), timeout=90)
a_out = a.communicate(timeout=90)[0]
check("netplay over invite codes: player 0", a_out, ["player 0: joined true, played true, desync -1, chat 'hello from player 1'"])
check("netplay over invite codes: player 1", b.stdout, ["player 1: joined true, played true, desync -1, chat 'hello from player 0'"])
# rollback for three, over invite codes: the host invites two, and passes on what goes between them
n3 = build("np_three") + exe
n3d = os.path.join(tmp, "three")
os.makedirs(n3d, exist_ok=True)
h = subprocess.Popen([n3], stdout=subprocess.PIPE, text=True, env=dict(env, DIR=n3d, ROLE="host"))
f1 = subprocess.Popen([n3], stdout=subprocess.PIPE, text=True, env=dict(env, DIR=n3d, ROLE="friend", N="1"))
f2 = subprocess.run([n3], capture_output=True, text=True, env=dict(env, DIR=n3d, ROLE="friend", N="2"), timeout=120)
h_out = h.communicate(timeout=60)[0]
f1_out = f1.communicate(timeout=60)[0]
check("netplay for three through the host: the host", h_out, ["player 0: played true, desync -1, stood in true"])
check("netplay for three through the host: player 1", f1_out, ["player 1: played true, desync -1, stood in true"])
check("netplay for three through the host: player 2", f2.stdout, ["player 2: played true, desync -1"])
# two games through lib/invite.jo's screens (run with no window: the software renderer, no display)
ig = build("invite_game") + exe
igd = os.path.join(tmp, "invite_codes")
os.makedirs(igd, exist_ok=True)
genv = {k: v for k, v in env.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
genv.update(SLOPPY_SOFTWARE="1", SLOPPY_NO_AUDIO="1", SLOPPY_FRAMES="900", DIR=igd)
a = subprocess.Popen([ig], stdout=subprocess.PIPE, text=True, env=dict(genv, ROLE="invite"))
b = subprocess.run([ig], capture_output=True, text=True, env=dict(genv, ROLE="join"), timeout=90)
a_out = a.communicate(timeout=90)[0]
check("invite screens: the inviter", a_out, ["invite: connected, inviter true, screens up false", "invite got: hello from join"])
check("invite screens: the friend", b.stdout, ["join: connected, inviter false, screens up false", "join got: hello from invite"])

# rooms through a matchmaking server (tools/rendezvous.jo), with lib/invite.jo's screens: a host and
# two friends (one with the code typed in small letters, one with its link); a friend who comes
# before the host, who then opens the room with the code its computer kept; the host gone, and
# back; and the server out of reach
rv_bin = os.path.join(tmp, "rendezvous")
subprocess.run([sloppy, "build", os.path.join(root, "tools", "rendezvous.jo"), "-o", rv_bin], check=True, env=env)
port += 1
rv_port = port
def rendezvous(at):
    r = subprocess.Popen([rv_bin + exe], stdout=subprocess.DEVNULL, env=dict(env, PORT=str(at), ROOMS=os.path.join(tmp, f"rooms{at}.txt")))
    time.sleep(0.5)
    return r
rv = rendezvous(rv_port)
rg = build("room_game") + exe
renv = dict(genv, SLOPPY_FRAMES="1800", SLOPPY_SERVER=f"ws://127.0.0.1:{rv_port}")
def room_game(d, name, **kw):
    return subprocess.Popen([rg], stdout=subprocess.PIPE, text=True, env=dict(renv, DIR=d, NAME=name, SLOPPY_SAVE_DIR=os.path.join(d, name), **kw))
def output(p):
    try: return p.communicate(timeout=60)[0]
    except subprocess.TimeoutExpired:
        p.kill()
        return p.communicate()[0]
rd = os.path.join(tmp, "room")
os.makedirs(os.path.join(rd, "host", "room_game"))
h = room_game(rd, "host", ROLE="host", FRIENDS="2")
a = room_game(rd, "amy", ROLE="join")
b = room_game(rd, "bob", ROLE="join", LINK="1")
check("a room, three games: the host", output(h), ["host got: hello from amy", "host got: hello from bob"])
check("a room, three games: a friend with its code", output(a), ["amy got: hello from host"])
check("a room, three games: a friend with its link", output(b), ["bob got: hello from host"])
rd = os.path.join(tmp, "room_kept")
os.makedirs(os.path.join(rd, "host", "room_game"))
with open(os.path.join(rd, "host", "room_game", "invite_room"), "w") as f: f.write("KX7P4 0123456789abcdef0123")
a = room_game(rd, "amy", ROLE="join", ROOM="kx7p4", WAIT="1")
time.sleep(2)
h = room_game(rd, "host", ROLE="host")
check("a room: a friend who comes first waits", output(a), ["amy: told wait new", "amy got: hello from host"])
check("a room: its host opens it later, with the code its computer kept", output(h), ["host got: hello from amy"])
a = room_game(rd, "amy", ROLE="join", ROOM="KX7P4", WAIT="1")
time.sleep(2)
h = room_game(rd, "host", ROLE="host")
check("a room whose host has gone: the friend is told, and joins when it is back", output(a), ["amy: told wait host", "amy got: hello from host"])
output(h)
l = room_game(rd, "look", ROLE="look", SLOPPY_SERVER=f"ws://127.0.0.1:{rv_port + 1}")
check("a room with the server out of reach says so", output(l), ["look: true, said it cannot be reached"])
# play with anybody: the first to ask hosts a public room and the next two are put in it; one who
# asks while a public room is busy hosts another; and the server's side of it, spoken to directly
def made(path):
    t0 = time.time()
    while not os.path.exists(path) and time.time() - t0 < 20: time.sleep(0.05)
rd = os.path.join(tmp, "anybody")
os.makedirs(rd)
h = room_game(rd, "ann", ROLE="anybody", FRIENDS="2")
made(os.path.join(rd, "public.txt"))
a = room_game(rd, "ben", ROLE="anybody")
b = room_game(rd, "cat", ROLE="anybody")
check("play with anybody: the first hosts", output(h), ["ann: hosts the public room true", "ann got: hello from ben", "ann got: hello from cat"])
check("play with anybody: the next is put in its room", output(a), ["ben got: hello from ann"])
check("play with anybody: and the next", output(b), ["cat got: hello from ann"])
rd = os.path.join(tmp, "anybody_busy")
os.makedirs(os.path.join(rd, "eve"))
h = room_game(rd, "dot", ROLE="anybody", BUSY="1")
made(os.path.join(rd, "public.txt"))
time.sleep(1)
a = room_game(os.path.join(rd, "eve"), "eve", ROLE="anybody", BUSY="1")
check("play with anybody: one who asks while the room is busy hosts another", output(a), ["eve: hosts the public room true"])
output(h)
rp = build("rv_public") + exe
check("play with anybody: the server's public rooms", subprocess.run([rp], capture_output=True, text=True, env=dict(env, SLOPPY_SERVER=f"ws://127.0.0.1:{rv_port}"), timeout=60).stdout,
      ["a: public host", "b: true asking", "a: guest", "c: public host true", "b: true asking", "c: guest", "d: true"])
rv.kill()
port += 2
env["NET_PORT"] = str(port)

# TLS (lib/tls.jo) against OpenSSL's own server: a test authority made here (P-256, with an
# intermediate of P-384) and another of RSA; certificates for localhost of P-256, P-384 and RSA,
# which must be taken, and ones that must not: for another name, expired, from an authority not
# trusted; a server that asks for a key share again (P-256), one that asks for a certificate. Then
# TLS 1.2 (the version used read from SLOPPY_TLS_DEBUG's lines): ECDHE-ECDSA and ECDHE-RSA, with and
# without the extended master secret, refused when the server has only CBC suites or only TLS 1.1,
# and 1.3 chosen when the server speaks both. Then wss:// through a TLS proxy (Python's) in front
# of the WebSocket server, and a room through a matchmaking server behind it
# (OpenSSL's own, 1.1.1 or later: macOS's LibreSSL makes certificates differently)
def find_openssl():
    for o in [os.environ.get("SLOPPY_OPENSSL", ""), "/opt/homebrew/opt/openssl@3/bin/openssl", "/usr/local/opt/openssl@3/bin/openssl",
              shutil.which("openssl") or "", r"C:\Program Files\OpenSSL\bin\openssl.exe", r"C:\Program Files\Git\usr\bin\openssl.exe"]:
        if o and os.path.exists(o):
            v = subprocess.run([o, "version"], capture_output=True, text=True).stdout
            r = subprocess.run([o, "s_server", "-help"], capture_output=True, text=True)
            if v.startswith("OpenSSL ") and not v.startswith("OpenSSL 1.0") and "-tls1_3" in r.stdout + r.stderr: return o
    return None

openssl = find_openssl()
if openssl:
    td = os.path.join(tmp, "tls")
    os.makedirs(td)
    def ossl(*a):
        r = subprocess.run([openssl, *a], cwd=td, capture_output=True, text=True)
        if r.returncode != 0: raise SystemExit(f"openssl {' '.join(a)}: {r.stderr}")
    with open(os.path.join(td, "req.cnf"), "w") as f: f.write("[req]\ndistinguished_name = dn\nprompt = no\n[dn]\nCN = x\n")
    with open(os.path.join(td, "ext.cnf"), "w") as f:
        f.write("[root]\nbasicConstraints = critical, CA:TRUE\nkeyUsage = critical, keyCertSign, cRLSign\n"
                "[inter]\nbasicConstraints = critical, CA:TRUE, pathlen:0\nkeyUsage = critical, keyCertSign, cRLSign\nextendedKeyUsage = serverAuth\n"
                "[leaf]\nbasicConstraints = critical, CA:FALSE\nkeyUsage = critical, digitalSignature\nextendedKeyUsage = serverAuth\nsubjectAltName = DNS:localhost, IP:127.0.0.1\n"
                "[other]\nbasicConstraints = critical, CA:FALSE\nkeyUsage = critical, digitalSignature\nextendedKeyUsage = serverAuth\nsubjectAltName = DNS:other.test, DNS:*.other.test\n")
    with open(os.path.join(td, "ca.cnf"), "w") as f:
        f.write("[ca]\ndefault_ca = test\n[test]\ndatabase = index.txt\nnew_certs_dir = .\nserial = serial.txt\ndefault_md = sha256\npolicy = any\nunique_subject = no\n[any]\ncommonName = supplied\n")
    open(os.path.join(td, "index.txt"), "w").close()
    with open(os.path.join(td, "serial.txt"), "w") as f: f.write("1000\n")
    def key(name, kind):
        if kind.startswith("rsa"): ossl("genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:" + kind[3:], "-out", name + ".key")
        else: ossl("genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:" + kind, "-pkeyopt", "ec_param_enc:named_curve", "-out", name + ".key")
        ossl("req", "-new", "-config", "req.cnf", "-key", name + ".key", "-subj", f"/CN=Sloppy test {name}", "-out", name + ".csr")
    serial = [1]
    def cert(name, kind, signer, ext, md="-sha256"):
        key(name, kind)
        serial[0] += 1
        by = ["-signkey", name + ".key"] if signer is None else ["-CA", signer + ".pem", "-CAkey", signer + ".key", "-set_serial", str(serial[0])]
        ossl("x509", "-req", "-in", name + ".csr", *by, "-days", "3650", md, "-extfile", "ext.cnf", "-extensions", ext, "-out", name + ".pem")
    cert("root", "P-256", None, "root")
    cert("inter", "P-384", "root", "inter")
    cert("leaf_ec", "P-256", "inter", "leaf", "-sha384")
    cert("leaf_p384", "P-384", "root", "leaf")
    cert("rsaroot", "rsa3072", None, "root")
    cert("leaf_rsa", "rsa2048", "rsaroot", "leaf")
    cert("other", "P-256", "inter", "other", "-sha384")
    cert("stranger", "P-256", None, "root")
    cert("leaf_stranger", "P-256", "stranger", "leaf")
    key("expired", "P-256")
    ossl("ca", "-config", "ca.cnf", "-batch", "-notext", "-cert", "root.pem", "-keyfile", "root.key", "-startdate", "20200101000000Z",
         "-enddate", "20210101000000Z", "-extfile", "ext.cnf", "-extensions", "leaf", "-in", "expired.csr", "-out", "expired.pem")
    with open(os.path.join(td, "trusted.pem"), "w") as f: f.write(open(os.path.join(td, "root.pem")).read() + open(os.path.join(td, "rsaroot.pem")).read())
    fetch = build("tls_fetch") + exe
    tenv = dict(env, SLOPPY_CA_FILE=os.path.join(td, "trusted.pem"))
    def s_server(leaf, *more, chain=None):
        global port
        port += 1
        args = [openssl, "s_server", "-accept", f"127.0.0.1:{port}", "-cert", leaf + ".pem", "-key", leaf + ".key", "-www", "-quiet", *more]
        if chain: args += ["-cert_chain", chain + ".pem"]
        s = subprocess.Popen(args, cwd=td, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        return s, port
    cases = [("a P-256 certificate, through a P-384 authority", "leaf_ec", ["-tls1_3"], "inter", "200 true, TLS 1.3"),
             ("the same at 127.0.0.1 (its address in the certificate)", "leaf_ec", ["-tls1_3"], "inter", "200 true, TLS 1.3"),
             ("a server that asks for a P-256 key share instead (HelloRetryRequest)", "leaf_ec", ["-tls1_3", "-groups", "P-256"], "inter", "200 true, TLS 1.3"),
             ("a server that asks for this side's certificate", "leaf_ec", ["-tls1_3", "-verify", "1"], "inter", "200 true, TLS 1.3"),
             ("a P-384 certificate", "leaf_p384", ["-tls1_3"], None, "200 true, TLS 1.3"),
             ("an RSA certificate (RSA-PSS handshake, PKCS#1 chain)", "leaf_rsa", ["-tls1_3"], None, "200 true, TLS 1.3"),
             ("a certificate for another name is refused", "other", ["-tls1_3"], "inter", "no: the secure connection failed: localhost is not who it says: its certificate is for other names (other.test, *.other.test), not localhost"),
             ("an expired certificate is refused", "expired", ["-tls1_3"], None, "no: the secure connection failed: localhost is not who it says: its certificate has expired"),
             ("a certificate from an authority not trusted is refused", "leaf_stranger", ["-tls1_3"], None, "no: the secure connection failed: localhost is not who it says: it comes from Sloppy test stranger, an authority this computer does not trust"),
             ("TLS 1.2: a P-256 certificate (ECDHE-ECDSA)", "leaf_ec", ["-tls1_2"], "inter", "200 true, TLS 1.2"),
             ("TLS 1.2: an RSA certificate (ECDHE-RSA, RSA-PSS)", "leaf_rsa", ["-tls1_2"], None, "200 true, TLS 1.2"),
             ("TLS 1.2: P-256's key exchange, signed with RSA PKCS#1", "leaf_rsa", ["-tls1_2", "-groups", "P-256", "-sigalgs", "RSA+SHA256"], None, "200 true, TLS 1.2"),
             ("TLS 1.2 without the extended master secret", "leaf_ec", ["-tls1_2", "-no_ems"], "inter", "200 true, TLS 1.2"),
             ("TLS 1.2: a server that asks for this side's certificate", "leaf_ec", ["-tls1_2", "-verify", "1"], "inter", "200 true, TLS 1.2"),
             ("TLS 1.2: a certificate for another name is refused", "other", ["-tls1_2"], "inter", "no: the secure connection failed: localhost is not who it says: its certificate is for other names (other.test, *.other.test), not localhost"),
             ("TLS 1.2 with CBC suites only is refused, and says why", "leaf_ec", ["-tls1_2", "-cipher", "ECDHE-ECDSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA"], "inter", "no: the secure connection failed: the server ended the connection (handshake_failure: it found nothing in common with this side (TLS 1.3 or 1.2, AES-128-GCM, ECDHE with X25519 or P-256))"),
             ("a server of TLS 1.1 only is refused, and says why", "leaf_ec", ["-tls1_1"], "inter", "no: the secure connection failed: the server ended the connection (protocol_version: it speaks only TLS older than 1.2, which this side does not)"),
             ("a server of TLS 1.3 and 1.2: 1.3", "leaf_ec", [], "inter", "200 true, TLS 1.3"),
             ("without the test authority trusted, refused", "leaf_ec", ["-tls1_3"], "inter", "no: the secure connection failed: localhost is not who it says: it comes from Sloppy test root, an authority this computer does not trust")]
    # (an s_server that has not got an option, as -no_ems before OpenSSL 3, starts no server)
    shelp = subprocess.run([openssl, "s_server", "-help"], capture_output=True, text=True)
    shelp = shelp.stdout + shelp.stderr
    for k, (what, leaf, more, chain, want) in enumerate(cases):
        if any(o.startswith("-") and o not in shelp for o in more):
            print(f"(this openssl's s_server has not got {' '.join(o for o in more if o.startswith('-') and o not in shelp)}: TLS: {what} is not tried)")
            continue
        s, p = s_server(leaf, *more, chain=chain)
        url = f"https://{'127.0.0.1' if k == 1 else 'localhost'}:{p}/"
        cenv = tenv if k < len(cases) - 1 else env
        r = subprocess.run([fetch, url], capture_output=True, text=True, env=dict(cenv, SLOPPY_TLS_DEBUG="1"), timeout=60)
        s.kill()
        s.wait()
        got = r.stdout.strip()
        if r.stdout.startswith(url + ": 200"):
            versions = [l.split("open (")[1].rstrip(")") for l in r.stderr.splitlines() if "open (TLS" in l]
            got = got.split(" (")[0] + ", " + " ".join(versions)
        check("TLS: " + what, got, [f"{url}: {want}"])
    # wss:// through a TLS proxy in front of the WebSocket server (as Caddy is in front of one)
    import ssl, socket, threading
    def tls_proxy(listen, to):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        chain = os.path.join(td, "leaf_chain.pem")
        with open(chain, "w") as f: f.write(open(os.path.join(td, "leaf_ec.pem")).read() + open(os.path.join(td, "inter.pem")).read())
        ctx.load_cert_chain(chain, os.path.join(td, "leaf_ec.key"))
        ls = socket.socket()
        ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ls.bind(("127.0.0.1", listen))
        ls.listen(16)
        def pump(a, b):
            try:
                while True:
                    d = a.recv(65536)
                    if not d: break
                    b.sendall(d)
            except OSError: pass
            for x in (a, b):
                try: x.close()
                except OSError: pass
        def serve():
            while True:
                try: c, _ = ls.accept()
                except OSError: return
                try: tc = ctx.wrap_socket(c, server_side=True)
                except (OSError, ssl.SSLError):
                    c.close()
                    continue
                b = socket.create_connection(("127.0.0.1", to))
                threading.Thread(target=pump, args=(tc, b), daemon=True).start()
                threading.Thread(target=pump, args=(b, tc), daemon=True).start()
        threading.Thread(target=serve, daemon=True).start()
        return ls
    port += 1
    ws_port = port
    port += 1
    proxy = tls_proxy(port, ws_port)
    s = subprocess.Popen([server], stdout=subprocess.PIPE, text=True, env=dict(env, NET_PORT=str(ws_port)))
    time.sleep(0.5)
    c = subprocess.run([client], capture_output=True, text=True, env=dict(tenv, NET_HOST=f"wss://localhost:{port}"), timeout=60)
    s_out = s.communicate(timeout=60)[0]
    proxy.close()
    check("wss://, through a TLS proxy: the client", c.stdout, WANT_CLIENT)
    check("wss://, through a TLS proxy: the server", s_out, WANT_SERVER)
    port += 1
    rvs_port = port
    port += 1
    proxy = tls_proxy(port, rvs_port)
    rv = rendezvous(rvs_port)
    rd = os.path.join(tmp, "room_wss")
    os.makedirs(os.path.join(rd, "host", "room_game"))
    wenv = dict(SLOPPY_SERVER=f"wss://localhost:{port}", SLOPPY_CA_FILE=os.path.join(td, "trusted.pem"))
    h = room_game(rd, "host", ROLE="host", FRIENDS="1", **wenv)
    a = room_game(rd, "amy", ROLE="join", **wenv)
    check("a room through a matchmaking server at wss://: the host", output(h), ["host got: hello from amy"])
    check("a room through a matchmaking server at wss://: a friend", output(a), ["amy got: hello from host"])
    rv.kill()
    proxy.close()
    port += 1
    env["NET_PORT"] = str(port)
else: print("(no openssl with TLS 1.3: TLS is not tried against it)")
# net.fetch over plain HTTP, against a server here (Python's): methods, headers and a body, chunks,
# redirects (a 303, or a 302 after a POST, become a GET; a 307 keeps it), a big answer saved to a
# file as it comes, a 404 not saved
import http.server, threading, hashlib
BIG = bytes((i * 7) % 251 for i in range(3 << 20))
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def reply(self, code, body, headers=()):
        self.send_response(code)
        for k, v in headers: self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)
    def answer(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode() if n else ""
        if self.path == "/echo":
            self.reply(200, f"{self.command} [{self.headers.get('X-Test', '-')}] [{self.headers.get('Content-Type', '-')}] [{body}]".encode())
        elif self.path == "/chunked":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for part in [b"one ", b"two ", b"three"]: self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
            self.wfile.write(b"0\r\n\r\n")
        elif self.path == "/see-other": self.reply(303, b"", [("Location", "/echo")])
        elif self.path == "/moved": self.reply(302, b"", [("Location", "/echo")])
        elif self.path == "/again": self.reply(307, b"", [("Location", "/echo")])
        elif self.path == "/big": self.reply(200, BIG)
        elif self.path == "/cookies": self.reply(200, b"two", [("Set-Cookie", "a=1; Path=/"), ("Set-Cookie", "b=2; Path=/")])
        elif self.path == "/slow":
            time.sleep(1.0)
            self.reply(200, b"slow answer")
        else: self.reply(404, b"no such page")
    do_GET = do_POST = do_PUT = do_HEAD = answer
port += 1
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
fetcher = build("http_fetch") + exe
r = subprocess.run([fetcher], capture_output=True, text=True, env=dict(env, NET_PORT=str(port), NET_DIR=tmp), timeout=60)
httpd.shutdown()
check("net.fetch over HTTP", r.stdout, [
    "post: 200 POST [yes] [application/json] [{\"a\": 1}]",
    "put: 200 PUT [-] [text/plain; charset=utf-8] [plain words]",
    "chunked: 200 one two three",
    "303: 200 GET [-] [-] []",
    "302 after a POST: 200 GET [-] [-] []",
    "307: 200 POST [-] [text/plain; charset=utf-8] [z]",
    f"saved: 200 {len(BIG)} 0 {len(BIG)} true {len(BIG)} {hashlib.sha256(BIG).hexdigest()[:16]}",
    "404: 404 false no such page",
    "head: 200 0",
    "cookies: a=1; Path=/, b=2; Path=/ | a=1; Path=/ | b=2; Path=/",
    "started: none yet true",
    "frames while it came: true",
    "fetch_result: 200 slow answer",
    "two at once: 200 one two three, 200 slow answer"])
port += 1
env["NET_PORT"] = str(port)

# an HTTP server of lib/http.jo (tests/net/http_server.jo), spoken to as browsers and curl do:
# routes, JSON, keep-alive and HTTP/1.0's close, HEAD, chunked bodies and 100-continue, a body too
# big, cookies, a handler that panics, clients that send or read slowly while others are answered,
# files, server-sent events, a fetch made while it serves, WebSockets on its port (their handshake's
# path, query, cookies and origin; the close handshake; a message too big: 1009; a reader that
# stopped, let go), and SIGTERM, on_quit running
import socket, struct, http.client, http.server, threading, signal

def http_server_test(hs_exe, hport, upstream_port):
    global failed
    site = os.path.join(tmp, "http_site")
    os.makedirs(os.path.join(site, "site", "sub"), exist_ok=True)
    with open(os.path.join(site, "site", "index.html"), "w", newline="") as f: f.write("<p>index</p>\n")
    with open(os.path.join(site, "site", "a.txt"), "w", newline="") as f: f.write("a file\n")
    with open(os.path.join(site, "site", ".secret"), "w", newline="") as f: f.write("no\n")
    with open(os.path.join(site, "site", "sub", "index.html"), "w", newline="") as f: f.write("<p>sub</p>\n")
    with open(os.path.join(site, "site", "big.bin"), "wb") as f: f.write(bytes(20 << 20))
    srv = subprocess.Popen([hs_exe], stdout=subprocess.PIPE, text=True,
                           env=dict(env, NET_PORT=str(hport), NET_DIR=site, NET_UPSTREAM=f"http://127.0.0.1:{upstream_port}/slow"))
    wait_port(hport)
    def ok(what, cond, detail=""):
        global failed
        if cond: print(f"ok   http server: {what}")
        else:
            failed += 1
            print(f"FAIL http server: {what} {detail}")
    def req(method, path, body=None, headers={}):
        c = http.client.HTTPConnection("127.0.0.1", hport, timeout=10)
        c.request(method, path, body=body, headers=headers)
        r = c.getresponse()
        data = r.read()
        c.close()
        return r, data
    def raw(data, wait=2.0, until=None):
        s = socket.create_connection(("127.0.0.1", hport), timeout=wait)
        s.sendall(data)
        got = b""
        try:
            while True:
                d = s.recv(65536)
                if not d: break
                got += d
                if until and until in got: break
        except socket.timeout: pass
        s.close()
        return got
    try:
        r, d = req("GET", "/hello?name=ann%20b")
        ok("a route with a query", r.status == 200 and d == b"hello ann b", (r.status, d))
        r, d = req("GET", "/items/1")
        ok("a route's :id, answered JSON", r.status == 200 and d == b'{"id":1,"name":"first"}' and r.getheader("Content-Type") == "application/json", (r.status, d))
        r, d = req("GET", "/items/9")
        ok("404 as JSON from the handler", r.status == 404 and d == b'{"error":"no item 9"}', (r.status, d))
        r, d = req("POST", "/items", body=b'{"name": "second"}', headers={"Content-Type": "application/json"})
        ok("POST read with read_json: 201, Location", r.status == 201 and d == b'{"id":2,"name":"second"}' and r.getheader("Location") == "/items/2", (r.status, d))
        r, d = req("POST", "/items", body=b'{"name": ')
        ok("POST of broken JSON: 400 saying why", r.status == 400 and d == b'{"error":"the body is not what this takes: the text ends before name\'s value"}', (r.status, d))
        r, d = req("DELETE", "/items")
        ok("a method no route has: 405 with Allow", r.status == 405 and r.getheader("Allow") == "POST", (r.status, r.getheader("Allow")))
        r, d = req("GET", "/rest/a/b/c.txt")
        ok("*path: the rest of the path", d == b"rest=a/b/c.txt", d)
        r, d = req("GET", "/nothing/here")
        ok("no such route: 404", r.status == 404 and d == b"404 Not Found", (r.status, d))
        # keep-alive: three requests on one connection; HTTP/1.0 without keep-alive: closed after
        c = http.client.HTTPConnection("127.0.0.1", hport, timeout=10)
        socks, bodies = set(), []
        for k in range(3):
            c.request("GET", f"/hello?name={k}")
            r = c.getresponse()
            bodies.append(r.read())
            socks.add(id(c.sock))
        c.close()
        ok("keep-alive: three requests, one connection", bodies == [b"hello 0", b"hello 1", b"hello 2"] and len(socks) == 1, (bodies, len(socks)))
        got = raw(b"GET /hello HTTP/1.0\r\n\r\n")
        ok("HTTP/1.0: answered, Connection: close, closed", got.startswith(b"HTTP/1.1 200 OK\r\n") and b"Connection: close\r\n" in got and got.endswith(b"\r\n\r\nhello you"), got)
        got = raw(b"GET /hello HTTP/1.0\r\nConnection: keep-alive\r\n\r\n", wait=1.0)
        ok("HTTP/1.0 with keep-alive: kept", b"Connection: keep-alive\r\n" in got, got)
        got = raw(b"GET /hello HTTP/1.1\r\nHost: x\r\n\r\nGET /items/1 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        ok("two requests sent at once: both answered, in order", got.count(b"HTTP/1.1 200 OK") == 2 and got.index(b"hello you") < got.index(b'"first"'), got)
        r, d = req("HEAD", "/hello")
        ok("HEAD: the length, no body", r.status == 200 and r.getheader("Content-Length") == "9" and d == b"", (r.status, r.getheader("Content-Length"), d))
        got = raw(b"POST /echo HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n5\r\nhello\r\n6;x=y\r\n world\r\n0\r\n\r\n")
        ok("a chunked body", got.endswith(b"\r\n\r\nPOST 11 hello world"), got)
        s = socket.create_connection(("127.0.0.1", hport), timeout=5)
        s.sendall(b"POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nExpect: 100-continue\r\nConnection: close\r\n\r\n")
        first = s.recv(1000)
        s.sendall(b"12345")
        rest = b""
        while True:
            d = s.recv(1000)
            if not d: break
            rest += d
        s.close()
        ok("Expect: 100-continue", first == b"HTTP/1.1 100 Continue\r\n\r\n" and rest.endswith(b"POST 5 12345"), (first, rest))
        got = raw(b"POST /echo HTTP/1.1\r\nHost: x\r\nContent-Length: 5000000\r\n\r\n")
        ok("a body too big: 413", got.startswith(b"HTTP/1.1 413 Content Too Large\r\n"), got[:60])
        got = raw(b"NOT HTTP AT ALL\r\n\r\n")
        ok("not a request: 400", got.startswith(b"HTTP/1.1 400 Bad Request\r\n"), got[:60])
        # cookies
        c = http.client.HTTPConnection("127.0.0.1", hport, timeout=10)
        c.request("GET", "/login")
        r = c.getresponse()
        r.read()
        cookies = r.msg.get_all("Set-Cookie")
        ok("Set-Cookie, twice", r.status == 303 and cookies == ["sid=abc123; Path=/; Max-Age=3600; HttpOnly; SameSite=Lax", "theme=dark; Path=/; SameSite=Lax"], (r.status, cookies))
        c.request("GET", "/whoami", headers={"Cookie": "sid=abc123; theme=dark"})
        d = c.getresponse().read()
        c.close()
        ok("cookies read", d == b"sid=abc123 theme=dark", d)
        # a handler that panics: 500, and the server goes on
        r, d = req("GET", "/panic")
        r2, d2 = req("GET", "/hello")
        ok("a handler that panics: 500, the server goes on", r.status == 500 and r2.status == 200, (r.status, r2.status))
        # clients slow to send and to read, while another is answered at once
        half = socket.create_connection(("127.0.0.1", hport))
        half.sendall(b"GET /hello HTTP/1.1\r\nHost: x\r\n")
        lazy = socket.create_connection(("127.0.0.1", hport))
        lazy.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        lazy.sendall(b"GET /static/big.bin HTTP/1.1\r\nHost: x\r\n\r\n")
        time.sleep(0.3)
        t0 = time.time()
        r, d = req("GET", "/hello")
        dt = time.time() - t0
        ok("slow clients do not hold up others", r.status == 200 and dt < 0.5, f"{dt:.3f} s")
        half.close()
        lazy.close()
        # files
        r, d = req("GET", "/static/")
        ok("files: index.html for a directory", d == b"<p>index</p>\n" and r.getheader("Content-Type") == "text/html; charset=utf-8", (d, r.getheader("Content-Type")))
        r, d = req("GET", "/static/a.txt")
        tag = r.getheader("ETag")
        ok("files: a file, its type, ETag, Last-Modified", d == b"a file\n" and r.getheader("Content-Type") == "text/plain; charset=utf-8" and tag and r.getheader("Last-Modified", "").endswith(" GMT"), r.getheaders())
        r, d = req("GET", "/static/a.txt", headers={"If-None-Match": tag})
        ok("files: unchanged since: 304", r.status == 304 and d == b"", r.status)
        r, d = req("GET", "/static/a.txt", headers={"If-Modified-Since": r.getheader("Last-Modified") or "Sun, 06 Nov 1994 08:49:37 GMT"})
        r, d = req("GET", "/static/sub")
        ok("files: a directory without its /: 301 to it", r.status == 301 and r.getheader("Location") == "/static/sub/", (r.status, r.getheader("Location")))
        got = raw(b"GET /static/../http_server.jo HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        ok("files: .. refused", got.startswith(b"HTTP/1.1 400 "), got[:40])
        r, d = req("GET", "/static/.secret")
        ok("files: a name starting with a dot is not served", r.status == 404, r.status)
        r, d = req("GET", "/static/big.bin")
        ok("files: a big file, whole", len(d) == 20 << 20 and r.getheader("Content-Length") == str(20 << 20), len(d))
        # server-sent events: a stream, chunked
        r, d = req("GET", "/events")
        ok("server-sent events", r.getheader("Content-Type") == "text/event-stream" and d == b"event: time\ndata: tick\n\ndata: tock\n\n", d)
        # a fetch while serving: the upstream takes a second, the server answers meanwhile
        r, d = req("GET", "/fetch")
        t0 = time.time()
        r, d = req("GET", "/hello")
        dt = time.time() - t0
        ok("a fetch on its way holds up nothing", d == b"hello you" and dt < 0.3, f"{dt:.3f} s")
        got = b""
        while time.time() - t0 < 10 and got != b"200 upstream says hi":
            r, got = req("GET", "/fetched")
            time.sleep(0.1)
        ok("the fetch's answer, once it has come", got == b"200 upstream says hi", got)
        # WebSockets on the same port
        def ws_open(path, extra=b""):
            s = socket.create_connection(("127.0.0.1", hport), timeout=5)
            s.sendall(b"GET " + path + b" HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n" + extra + b"\r\n")
            head = b""
            while b"\r\n\r\n" not in head: head += s.recv(1)
            return s, head
        def ws_send(s, op, payload):
            mask = b"\x01\x02\x03\x04"
            n = len(payload)
            h = bytes([0x80 | op]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
            s.sendall(h + mask + bytes(b ^ mask[i & 3] for i, b in enumerate(payload)))
        def ws_recv(s):
            def take(n):
                b = b""
                while len(b) < n:
                    d = s.recv(n - len(b))
                    if not d: raise EOFError
                    b += d
                return b
            h = take(2)
            n = h[1] & 127
            if n == 126: n = struct.unpack(">H", take(2))[0]
            elif n == 127: n = struct.unpack(">Q", take(8))[0]
            return h[0] & 15, take(n)
        s, head = ws_open(b"/ws?room=4", b"Cookie: sid=abc123\r\nOrigin: http://example.test\r\n")
        ok("WebSocket: the handshake answered", head.startswith(b"HTTP/1.1 101 Switching Protocols\r\n") and b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n" in head, head)
        m1 = ws_recv(s)
        ws_send(s, 1, b"hi")
        m2 = ws_recv(s)
        ok("WebSocket: messages both ways", m1 == (1, b"welcome") and m2 == (1, b"echo hi"), (m1, m2))
        ws_send(s, 8, struct.pack(">H", 1000) + b"bye")
        m3 = ws_recv(s)
        try: eof = s.recv(10) == b""
        except OSError: eof = True
        s.close()
        ok("WebSocket: a close answered with its code, then the end", m3 == (8, struct.pack(">H", 1000)) and eof, (m3, eof))
        s, head = ws_open(b"/ws")
        ws_recv(s)
        ws_send(s, 2, bytes(2000))
        m = ws_recv(s)
        s.close()
        ok("WebSocket: a message too big: closed with 1009", m == (8, struct.pack(">H", 1009)), m)
        s, head = ws_open(b"/ws")
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        ws_recv(s)
        ws_send(s, 1, b"flood")
        time.sleep(3)
        s.close()
        # asked to stop (Windows has no SIGTERM to send: a request that asks): the loop ends, on_quit runs
        if os.name != "nt": srv.send_signal(signal.SIGTERM)
        else: req("GET", "/quit")
        out = srv.communicate(timeout=20)[0]
        lines = [l for l in out.splitlines() if l.strip()]
        lines = [l if "it took none of the last" not in l else l.split(" of the last")[0] + " of the last N bytes" + l.split(" bytes", 1)[1] for l in lines]
        want = ["listening", "server: ws joined /ws room=4 sid=abc123 origin=http://example.test", "server: ws left: closed",
                "server: ws joined /ws room=- sid=- origin=", "server: ws left: it sent a message bigger than the 1000 bytes taken",
                "server: ws joined /ws room=- sid=- origin=", "server: ws left: it took none of the last N bytes sent to it (a reader that stopped)",
                "server: stopped", "server: on_quit"]
        check("http server: what it printed (WebSockets' handshakes and ends; stopped by SIGTERM, on_quit)", "\n".join(lines), want)
    finally:
        if srv.poll() is None: srv.kill()

class Upstream(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/slow": time.sleep(1.0)
        body = b"upstream says hi"
        self.send_response(200)
        if self.path == "/cookies":
            self.send_header("Set-Cookie", "a=1; Path=/")
            self.send_header("Set-Cookie", "b=2; Path=/")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

port += 1
up_port = port
up = http.server.ThreadingHTTPServer(("127.0.0.1", up_port), Upstream)
threading.Thread(target=up.serve_forever, daemon=True).start()
port += 1
http_server = build("http_server") + exe
http_server_test(http_server, port, up_port)
up.shutdown()
port += 1
env["NET_PORT"] = str(port)

# the real thing, where SLOPPY_TEST_LIVE=1 (it needs the internet): https://sloppy-lang.org, and the
# matchmaking server behind Caddy, with its Let's Encrypt certificate; servers of TLS 1.2 only
# (an AWS load balancer's, ECDHE-RSA; npm's, ECDHE-ECDSA)
if os.environ.get("SLOPPY_TEST_LIVE") == "1":
    fetch = build("tls_fetch") + exe
    for url in ["https://sloppy-lang.org/", "https://httpbin.org/json", "https://registry.npmjs.org/"]:
        r = subprocess.run([fetch, url], capture_output=True, text=True, env=env, timeout=60)
        check("live: " + url, r.stdout.strip().split(" (")[0], [url + ": 200 true"])
    r = subprocess.run([rv_bin + exe, "check", "wss://matchmaking.sloppy-lang.org"], capture_output=True, text=True, env=env, timeout=60)
    check("live: wss://matchmaking.sloppy-lang.org", r.stdout.strip().split("\n")[-1], ["ok: a matchmaking server answers at wss://matchmaking.sloppy-lang.org"])

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
    # a web page's fetch (the browser's), from an HTTP server of lib/http.jo
    port += 1
    page = build("web_fetch", "--target", "wasm") + ".html"
    h = subprocess.Popen([http_server], stdout=subprocess.PIPE, text=True, env=dict(env, NET_PORT=str(port), NET_DIR=tmp))
    wait_port(port)
    b = subprocess.Popen([shell, "--no-sandbox", "--enable-unsafe-swiftshader", "--remote-debugging-port=0",
                          "file://" + page + f"?NET_PORT={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # (its lines as they come, for up to 30 seconds)
    import queue
    lines_q = queue.Queue()
    threading.Thread(target=lambda: [lines_q.put(l) for l in h.stdout], daemon=True).start()
    seen = []
    t0 = time.time()
    while time.time() - t0 < 30 and not any("page fetched" in l for l in seen):
        try: seen.append(lines_q.get(timeout=1).strip())
        except queue.Empty: pass
    b.kill()
    try:
        q = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        q.request("GET", "/quit")
        q.getresponse().read()
        h.wait(timeout=20)
    except (OSError, subprocess.TimeoutExpired): h.kill()
    check("a web page's fetch_start (in Chromium)", "\n".join(seen), ["listening", "server: page fetched 200 from the server"])
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
    # rooms through a matchmaking server with web pages (driven by node): the link the same after a
    # reload, a page joining by it, the host's page gone and back, a native program joining a
    # page's room, the server out of reach
    if shutil.which("node"):
        port += 1
        env["NET_PORT"] = str(port)
        rv = rendezvous(port)
        ui = os.path.join(tmp, "invite_ui")
        subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "invite_ui.jo"), "-o", ui, "--target", "wasm"], check=True, env=env)
        subprocess.run([sloppy, "build", os.path.join(root, "tests", "web", "invite_ui.jo"), "-o", ui + "_native"], check=True, env=env)
        r = subprocess.run(["node", os.path.join(root, "tools", "web_room.mjs"), shell, ui + ".html", str(port), ui + "_native" + exe, os.path.join(tmp, "webroom")],
                           capture_output=True, text=True, timeout=300, env=genv)
        rv.kill()
        print(r.stdout.strip())
        if r.returncode != 0: failed += 1
else: print("(no browser: the web client is not tried)")
# through a TURN relay only, where SLOPPY_TEST_TURN names a test server ("turn:host:port,user,password":
# coturn, run locally): two native programs, and a native program with a web page
turn = os.environ.get("SLOPPY_TEST_TURN")
if turn:
    tenv = dict(env, TURN=turn, SLOPPY_RTC_RELAY_ONLY="1")
    td = os.path.join(tmp, "turn")
    os.makedirs(td, exist_ok=True)
    a = subprocess.Popen([peer], stdout=subprocess.PIPE, text=True, env=dict(tenv, DIR=td, ROLE="invite"))
    b = subprocess.run([peer], capture_output=True, text=True, env=dict(tenv, DIR=td, ROLE="join"), timeout=60)
    a_out = a.communicate(timeout=60)[0]
    check("WebRTC through a TURN relay only: the inviter", a_out, ["accepted:true", "native:joined", "native got:ping from native", "native got:pong from native"])
    check("WebRTC through a TURN relay only: the one who joined", b.stdout, ["native:joined", "native got:ping from native", "native got:pong from native"])
    if shell and shutil.which("node"):
        page = build("invite_page", "--target", "wasm") + ".html"
        r = subprocess.run(["node", os.path.join(root, "tools", "rtc_webtest.mjs"), shell, page, peer, os.path.join(tmp, "rtcturn")],
                           capture_output=True, text=True, timeout=240, env=dict(tenv, RTC_PAGE_QUERY=f"SLOPPY_RTC_RELAY_ONLY=1&TURN={turn}"))
        print(r.stdout.strip().replace("WebRTC:", "WebRTC through a TURN relay only:"))
        if r.returncode != 0: failed += 1
# two web pages straight to each other by invite codes, the reply pasted in 20 s later (a page
# must wait for it): Chromium to Chromium, and with Firefox where SLOPPY_FIREFOX says where one is
if shell and shutil.which("node"):
    page = build("invite_page", "--target", "wasm") + ".html"
    pairs = [(shell, shell)]
    ffp = os.environ.get("SLOPPY_FIREFOX")
    if ffp: pairs += [(ffp, ffp), (ffp, shell), (shell, ffp)]
    for k, (inv, joi) in enumerate(pairs):
        r = subprocess.run(["node", os.path.join(root, "tools", "rtc_pages.mjs"), inv, joi, page, os.path.join(tmp, f"pages{k}")],
                           capture_output=True, text=True, timeout=240, env=dict(env, REPLY_DELAY="20000"))
        print(r.stdout.strip().split("\n")[0])
        if not r.stdout.startswith("ok"): failed += 1
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
