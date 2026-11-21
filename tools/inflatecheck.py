#!/usr/bin/env python3
"""inflate on streams made by an independent encoder (Python's zlib): every level 0-9 and each
strategy (stored, fixed and dynamic blocks; matches 32768 back, the farthest), zlib's wrapper,
inputs of each kind; the same streams cut short (none, always) and with bytes changed (never a
crash or a hang; none where zlib finds them damaged, its bytes where it reads them). Each also
through an Inflater stepped a little at a time, which must agree. Native, and wasm under node when
node is here.
usage: tools/inflatecheck.py [path/to/sloppy]
"""
import os, pathlib, random, shutil, subprocess, sys, tempfile, zlib

root = pathlib.Path(__file__).resolve().parent.parent
sloppy = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "bin/sloppy"
env = dict(os.environ, SLOPPY_LIB=str(root / "lib"), DISPLAY="", WAYLAND_DISPLAY="")
r = random.Random(1950)

def inputs():
    yield "empty", b""
    yield "one", b"a"
    yield "short", b"hello hello hello hello hello world"
    yield "zeros", bytes(200000)
    yield "random", bytes(r.getrandbits(8) for _ in range(100000))
    yield "few_values", bytes(r.choice(b"abcd") for _ in range(100000))
    words = "the of and to in is was for on that with as by at from his her it an were are which this".split()
    yield "text", " ".join(r.choice(words) + ("\n" if r.random() < 0.1 else "") for _ in range(40000)).encode()
    yield "runs", b"".join(bytes([r.getrandbits(8)]) * r.randrange(1, 600) for _ in range(500))
    # (a window of random bytes, then it again: matches exactly 32768 back)
    w = bytes(r.getrandbits(8) for _ in range(32768))
    yield "far", w + w + w[:1000]
    yield "all_bytes", bytes(range(256)) * 300

def streams():
    pack = lambda c, data: c.compress(data) + c.flush()
    for name, data in inputs():
        for level in range(10):
            yield f"{name}_l{level}", data, pack(zlib.compressobj(level, zlib.DEFLATED, -15), data)
        for sname, strat in [("fixed", zlib.Z_FIXED), ("huff", zlib.Z_HUFFMAN_ONLY), ("rle", zlib.Z_RLE), ("filt", zlib.Z_FILTERED)]:
            yield f"{name}_{sname}", data, pack(zlib.compressobj(6, zlib.DEFLATED, -15, 9, strat), data)
        yield f"{name}_mem1", data, pack(zlib.compressobj(9, zlib.DEFLATED, -15, 1), data)
        yield f"{name}.zlib", data, pack(zlib.compressobj(6), data)
        # (flushed every 1000 bytes: empty stored blocks between the pieces)
        c = zlib.compressobj(6, zlib.DEFLATED, -15)
        yield f"{name}_flush", data, b"".join(c.compress(data[i:i + 1000]) + c.flush(zlib.Z_SYNC_FLUSH) for i in range(0, len(data), 1000)) + c.flush()

def zread(z, name):
    try:
        d = zlib.decompressobj(15 if name.endswith(".zlib") else -15)
        out = d.decompress(z)
        return out if d.eof else None
    except zlib.error:
        return None

def run(work, kind, cmd, files):
    lines = []
    for i in range(0, len(files), 400):
        out = subprocess.run(cmd + files[i:i + 400], capture_output=True, text=True, env=env, timeout=600)
        if out.returncode != 0:
            print(f"{kind}: the check program failed\n{out.stdout[-2000:]}{out.stderr[-2000:]}")
            return None
        lines += out.stdout.splitlines()
    return dict((l.split(": ")[0], l.split(": ")[1]) for l in lines)

def check(work, kind, cmd, cases):
    files = [f for f, _ in cases]
    res = run(work, kind, cmd, files)
    if res is None: return 1
    bad = 0
    for f, want in cases:
        line = res.get(f, "missing")
        got = None
        if line.startswith("ok"):
            got = open(f + ".out", "rb").read() if os.path.exists(f + ".out") else b""
        problems = []
        if "same" not in line: problems.append(f"stepped: {line}")
        if got != want: problems.append("none" if got is None else "zlib reads none" if want is None else "other bytes")
        if os.path.exists(f + ".out"): os.remove(f + ".out")
        if problems:
            bad += 1
            if bad <= 20: print(f"{kind} {os.path.basename(f)}: {', '.join(problems)}")
    print(f"{kind}: {len(cases)} streams, {'ok' if bad == 0 else f'{bad} FAILED'}")
    return bad

with tempfile.TemporaryDirectory(prefix="sloppy-inflate-") as work:
    cases = []
    for name, data, z in streams():
        f = os.path.join(work, name)
        open(f, "wb").write(z)
        cases.append((f, data))
        # (cut short at a few places: none)
        for k, n in enumerate(sorted({1, len(z) // 2, len(z) - 1} - {0}) if len(z) > 1 else []):
            g = os.path.join(work, f"{name}_cut{k}") + (".zlib" if name.endswith(".zlib") else "")
            open(g, "wb").write(z[:n])
            # (zlib's checksum after the stream is not read: cut there, the stream is whole)
            cases.append((g, zread(z[2:n], "") if name.endswith(".zlib") else zread(z[:n], name)))
        # (bytes changed: what zlib makes of it)
        if "_l6" in name or "_fixed" in name:
            for k in range(12):
                b = bytearray(z)
                for _ in range(r.randrange(1, 4)):
                    if b: b[r.randrange(len(b))] = r.getrandbits(8)
                g = os.path.join(work, f"{name}_bad{k}")
                open(g, "wb").write(bytes(b))
                cases.append((g, zread(bytes(b), name)))
    # (random bytes: not deflate)
    for k in range(200):
        g = os.path.join(work, f"noise{k}")
        b = bytes(r.getrandbits(8) for _ in range(r.randrange(0, 300)))
        open(g, "wb").write(b)
        cases.append((g, zread(b, g)))
    prog = str(root / "tools/inflatecheck.jo")
    subprocess.run([str(sloppy), "build", "--release", prog, "-o", f"{work}/check"], check=True, env=env)
    bad = check(work, "native", [f"{work}/check"], cases)
    if shutil.which("node"):
        subprocess.run([str(sloppy), "build", "--release", "--target", "wasm", prog, "-o", f"{work}/check.html"], check=True, env=env)
        bad += check(work, "wasm", ["node", str(root / "tools/runwasm.js"), f"{work}/check.html"], cases)
    else:
        print("(no node: the wasm check skipped)")
    sys.exit(1 if bad else 0)
