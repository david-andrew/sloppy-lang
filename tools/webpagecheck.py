#!/usr/bin/env python3
"""A web build's page from the build block's head and page_files: the head file's tags in the
page's <head> after the title (its own icon and viewport in place of the page's), and the
directory's files beside the page, as a single page, with --wasm-file and in a zip. Also the
mistakes: a missing head file, page_files that is not a directory, and a page file named as
the page.
usage: tools/webpagecheck.py [path/to/sloppy]
"""
import os, pathlib, shutil, subprocess, sys, tempfile, zipfile

root = pathlib.Path(__file__).resolve().parent.parent
sloppy = str(pathlib.Path(sys.argv[1]).resolve()) if len(sys.argv) > 1 else str(root / "bin/sloppy")
env = dict(os.environ, SLOPPY_LIB=str(root / "lib"))
failed = 0


def check(what, ok, detail=""):
    global failed
    if not ok:
        failed += 1
        print(f"FAIL {what} {detail}")


def build(d, *extra, out="game.html"):
    return subprocess.run([sloppy, "build", str(d / "game.jo"), "--target", "wasm", "-o", str(d / "out" / out), *extra],
                          capture_output=True, text=True, env=env, timeout=300)


work = pathlib.Path(tempfile.mkdtemp(prefix="webpage", dir=os.environ.get("TMPDIR")))
try:
    d = work / "game"
    (d / "web" / "icons").mkdir(parents=True)
    (d / "out").mkdir()
    (d / "game.jo").write_text('build:\n    name = "Sky Game"\n    head = "head.html"\n    page_files = "web"\nprint("hello")\n')
    head = ('<meta name="description" content="A game in the sky">\n'
            '<meta property="og:image" content="preview.png">\n'
            '<link rel="icon" href="icons/icon-192.png">\n'
            '<link rel="manifest" href="site.webmanifest">\n'
            '<meta name="theme-color" content="#123456">')
    (d / "head.html").write_text(head)
    (d / "web" / "preview.png").write_bytes(b"\x89PNG preview")
    (d / "web" / "icons" / "icon-192.png").write_bytes(b"\x89PNG icon")
    (d / "web" / "site.webmanifest").write_text('{"name": "Sky Game"}')
    (d / "web" / ".hidden").write_text("left out")
    files = {"preview.png": b"\x89PNG preview", "icons/icon-192.png": b"\x89PNG icon", "site.webmanifest": b'{"name": "Sky Game"}'}

    def page_ok(what, page):
        h = page[:page.index("</head>")]
        check(what + ": title", "<title>Sky Game</title>" in h)
        check(what + ": head after the title", h.index("<title>") < h.index('name="description"'))
        for line in head.splitlines(): check(what + ": head line", line in h, line)
        check(what + ": its own icon, not the page's", 'href="data:,"' not in h and h.count('rel="icon"') == 1)
        check(what + ": the page's viewport", h.count('name="viewport"') == 1)

    # one page: the files beside it
    r = build(d)
    check("single build", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        page_ok("single", (d / "out" / "game.html").read_text())
        for name, b in files.items(): check(f"single: {name}", (d / "out" / name).read_bytes() == b)
        check("single: hidden files left out", not (d / "out" / ".hidden").exists())
    # --wasm-file: the module too
    shutil.rmtree(d / "out"); (d / "out").mkdir()
    r = build(d, "--wasm-file")
    check("wasm-file build", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        page_ok("wasm-file", (d / "out" / "game.html").read_text())
        check("wasm-file: module", (d / "out" / "game.wasm").exists())
        for name, b in files.items(): check(f"wasm-file: {name}", (d / "out" / name).read_bytes() == b)
    # a zip: index.html and the files in it
    r = build(d, out="game.zip")
    check("zip build", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        z = zipfile.ZipFile(d / "out" / "game.zip")
        page_ok("zip", z.read("index.html").decode())
        for name, b in files.items(): check(f"zip: {name}", z.read(name) == b)
    # a head with its own viewport, and no icon: the page's icon stays, its viewport goes
    (d / "head.html").write_text('<meta name="viewport" content="width=600">')
    r = build(d)
    if r.returncode == 0:
        h = (d / "out" / "game.html").read_text()
        check("own viewport", h.count('name="viewport"') == 1 and 'content="width=600"' in h and 'href="data:,"' in h)
    else: check("own viewport build", False, r.stderr)
    # with no head and no page_files: the page as before
    (d / "game.jo").write_text('print("hello")\n')
    r = build(d, out="plain.html")
    check("plain build", r.returncode == 0, r.stderr)
    if r.returncode == 0:
        h = (d / "out" / "plain.html").read_text()
        check("plain: the default icon and viewport", 'href="data:,"' in h and h.count('name="viewport"') == 1)
    # mistakes
    for src, want in [('build:\n    head = "nope.html"\nprint(1)\n', "cannot read the head file"),
                      ('build:\n    page_files = "head.html"\nprint(1)\n', "is not a directory"),
                      ('build:\n    page_files = 3\nprint(1)\n', "build option 'page_files' is a directory in quotes")]:
        (d / "game.jo").write_text(src)
        r = build(d)
        check(f"error '{want}'", r.returncode != 0 and want in r.stderr, r.stderr[-300:])
    (d / "web" / "game.html").write_text("x")
    (d / "game.jo").write_text('build:\n    page_files = "web"\nprint(1)\n')
    r = build(d)
    check("a page file named as the page", r.returncode != 0 and "page's own name" in r.stderr, r.stderr[-300:])
finally:
    shutil.rmtree(work, ignore_errors=True)
print("web page from the build block: " + ("ok" if failed == 0 else f"{failed} failed"))
sys.exit(1 if failed else 0)
