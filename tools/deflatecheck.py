#!/usr/bin/env python3
"""deflate's output read by an independent decoder (Python's zlib), on inputs of each kind: empty,
tiny, random, repetitive, text, runs, and sizes around the block and stored-block limits. Also that
a Deflater stepped a little at a time gives the same bytes, and that inflate reads it all back.
Native, and wasm under node when node is here.
usage: tools/deflatecheck.py [path/to/sloppy]
"""
import os, pathlib, random, shutil, subprocess, sys, tempfile, zlib

root = pathlib.Path(__file__).resolve().parent.parent
sloppy = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "bin/sloppy"
env = dict(os.environ, SLOPPY_LIB=str(root / "lib"), DISPLAY="", WAYLAND_DISPLAY="")

def inputs():
    r = random.Random(1951)
    yield "empty", b""
    yield "one", b"a"
    yield "three", b"abc"
    yield "four", b"abab"
    yield "short", b"hello hello hello hello hello world"
    yield "zeros", bytes(300000)
    yield "random", bytes(r.getrandbits(8) for _ in range(200000))
    yield "random_small", bytes(r.getrandbits(8) for _ in range(70))
    # (random bytes from a few values: short matches everywhere)
    yield "few_values", bytes(r.choice(b"abcd") for _ in range(150000))
    words = "the of and to in is was for on that with as by at from his her it an were are which this".split()
    text = " ".join(r.choice(words) + ("\n" if r.random() < 0.1 else "") for _ in range(60000))
    yield "text", text.encode()
    line = b'Person(id=17, name="Eleni Papadakis", home=202, job=pilot, gold=307, alive=true)\n'
    yield "repeated", line * 4000
    rec = "".join(f"Entry(t={r.randrange(900000)}, from={r.randrange(20000)}, amount={r.randrange(500)}, price={r.uniform(0, 90):.3f}), " for _ in range(8000))
    yield "records", rec.encode()
    # (long runs and their ends; matches reaching the end of the input)
    yield "runs", b"".join(bytes([r.getrandbits(8)]) * r.randrange(1, 600) for _ in range(800))
    yield "ends_in_match", b"abcdefgh" * 40 + b"xyz" + b"abcdefgh" * 40
    # (sizes around 64 KB: the window, a stored block's most)
    for n in (32767, 32768, 32769, 65535, 65536, 65537):
        yield f"random_{n}", bytes(r.getrandbits(8) for _ in range(n))
    # (random bytes then text: stored blocks next to coded ones)
    yield "mixed", bytes(r.getrandbits(8) for _ in range(100000)) + text.encode()[:100000] + bytes(r.getrandbits(8) for _ in range(70000))

def check(work, kind, run):
    out = subprocess.run(run, capture_output=True, text=True, env=env, timeout=300)
    if out.returncode != 0:
        print(f"{kind}: the check program failed\n{out.stdout}{out.stderr}")
        return 1
    bad = 0
    lines = out.stdout.splitlines()
    for (name, data), line in zip(inputs(), lines):
        f = os.path.join(work, name)
        z = open(f + ".z", "rb").read()
        zs = open(f + ".zs", "rb").read()
        try:
            back = zlib.decompress(z, -15)
        except zlib.error as e:
            back = f"zlib: {e}".encode()
        problems = []
        if back != data: problems.append("zlib reads something else")
        if zs != z: problems.append("stepped differs from deflate")
        if "inflate same" not in line: problems.append("inflate reads something else")
        if problems:
            bad += 1
            print(f"{kind} {name}: {', '.join(problems)}  ({line})")
    if len(lines) != len(list(inputs())):
        print(f"{kind}: {len(lines)} results\n{out.stdout}{out.stderr}")
        bad += 1
    total = sum(len(d) for _, d in inputs())
    packed = sum(os.path.getsize(os.path.join(work, n + ".z")) for n, _ in inputs())
    print(f"{kind}: {len(lines)} inputs, {total} -> {packed} bytes, {'ok' if bad == 0 else f'{bad} FAILED'}")
    return bad

with tempfile.TemporaryDirectory(prefix="sloppy-deflate-") as work:
    names = []
    for name, data in inputs():
        open(os.path.join(work, name), "wb").write(data)
        names.append(os.path.join(work, name))
    prog = str(root / "tools/deflatecheck.jo")
    subprocess.run([str(sloppy), "build", "--release", prog, "-o", f"{work}/check"], check=True, env=env)
    bad = check(work, "native", [f"{work}/check"] + names)
    if shutil.which("node"):
        subprocess.run([str(sloppy), "build", "--release", "--target", "wasm", prog, "-o", f"{work}/check.html"], check=True, env=env)
        bad += check(work, "wasm", ["node", str(root / "tools/runwasm.js"), f"{work}/check.html"] + names)
    else:
        print("(no node: the wasm check skipped)")
    sys.exit(1 if bad else 0)
