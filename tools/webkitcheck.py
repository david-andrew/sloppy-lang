#!/usr/bin/env python3
"""Safari's engine: Playwright's WebKit, in a container (localhost/sloppy-webkit, built from
tools/webkit/Containerfile the first time; Playwright's WebKit wants Ubuntu's libraries). Checks:
- invite codes between pages: WebKit to WebKit, and with Chromium both ways, the reply pasted
  20 s later, through a TURN relay (pages on one machine cannot reach each other otherwise: the
  container cannot look up their .local names, and one public address does not loop back);
- a WebKit page and a native program, each inviting in turn;
- the examples gallery's games as an iPhone held sideways: no errors (screenshots kept in the
  work directory, printed at the end).
The relay is coturn in a container (sloppy-turn), started if it is not running.
usage: tools/webkitcheck.py [path/to/sloppy]"""
import os, shutil, subprocess, sys, tempfile, time

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(root, "bin", "sloppy")
IMAGE = "localhost/sloppy-webkit"
TURN = "turn:127.0.0.1:3479,sloppy,secret"
GALLERY = ["aces/aces", "breakwater/breakwater", "cube", "duel/duel", "dunes/dunes", "netpong/netpong",
           "physics", "physics3d", "rebound/rebound", "scene3d", "shapes", "tiles"]
tmp = tempfile.mkdtemp(prefix="sloppy-webkit-")
failed = 0

def podman(*a, **kw): return subprocess.run(["podman", *a], **kw)

if podman("image", "exists", IMAGE).returncode != 0:
    print("building", IMAGE, "(once: a few minutes)", flush=True)
    podman("build", "-t", IMAGE, os.path.join(root, "tools", "webkit"), check=True)
running = podman("ps", "--format", "{{.Names}}", capture_output=True, text=True).stdout.split()
if "sloppy-turn" not in running:
    if podman("container", "exists", "sloppy-turn").returncode == 0: podman("start", "sloppy-turn", check=True, capture_output=True)
    else:
        podman("run", "-d", "--name", "sloppy-turn", "--network=host", "docker.io/coturn/coturn", "-n", "--listening-port=3479",
               "--listening-ip=127.0.0.1", "--relay-ip=127.0.0.1", "--external-ip=127.0.0.1", "--min-port=49400", "--max-port=49450",
               "--user=sloppy:secret", "--realm=sloppy.test", "--lt-cred-mech", "--no-tls", "--allow-loopback-peers", "--log-file=stdout",
               check=True, capture_output=True)
    time.sleep(1)

env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
def build(src, out, *flags):
    subprocess.run([sloppy, "build", os.path.join(root, src), "-o", out, *flags], check=True, env=env, capture_output=True)

page = os.path.join(tmp, "invite_page.html")
build("tests/net/invite_page.jo", page, "--target", "wasm")
peer = os.path.join(tmp, "invite_peer")
build("tests/net/invite_peer.jo", peer)
gdir = os.path.join(tmp, "gallery")
os.makedirs(gdir)
for g in GALLERY:
    build(f"examples/{g}.jo", os.path.join(gdir, os.path.basename(g) + ".html"), "--target", "wasm")

def run(*a, extra_env=()):
    cmd = ["podman", "run", "--rm", "--security-opt", "label=disable", "--network", "host", "-v", f"{tmp}:{tmp}",
           "-v", f"{os.path.join(root, 'tools', 'webkit')}:/opt/pw/t:ro"]
    for k, v in extra_env: cmd += ["-e", f"{k}={v}"]
    return subprocess.run(cmd + [IMAGE, "node", "/opt/pw/t/pages.mjs", *a], capture_output=True, text=True, timeout=300)

def report(r):
    global failed
    out = r.stdout.strip() or "FAIL: " + (r.stderr.strip()[-600:] or "no output")
    print(out)
    failed += sum(1 for l in out.splitlines() if l.startswith("FAIL"))

relay = f"SLOPPY_RTC_RELAY_ONLY=1&TURN={TURN}"
for a, b in [("webkit", "webkit"), ("webkit", "chromium"), ("chromium", "webkit")]:
    report(run("pages", a, b, page, extra_env=[("Q", relay), ("REPLY_DELAY", "20000")]))
for who in ["page", "native"]:
    d = os.path.join(tmp, "native-" + who)
    os.makedirs(d)
    n = subprocess.Popen([peer], stdout=subprocess.PIPE, text=True,
                         env=dict(env, DIR=d, ROLE="join" if who == "page" else "invite", TURN=TURN, SLOPPY_RTC_RELAY_ONLY="1"))
    report(run("native", who, page, d, extra_env=[("Q", relay)]))
    try: n.communicate(timeout=30)
    except subprocess.TimeoutExpired: n.kill()
report(run("gallery", gdir))
print(f"screenshots: {gdir}")
sys.exit(1 if failed else 0)
