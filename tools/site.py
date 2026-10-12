#!/usr/bin/env python3
"""Build Sloppy's website into build/site: a home page, the docs (from the Markdown files) and the
playground. Static files only: serve the directory anywhere (GitHub Pages: .github/workflows).
usage: tools/site.py [output-dir]          (needs bin/sloppy, for the playground)"""
import base64, zlib, html, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apidoc

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "build", "site")
here = os.path.join(root, "tools", "site")
REPO = "https://github.com/david-andrew/sloppy-lang"

# ---- Markdown (the subset the docs use) ----

def slug(text):
    s = re.sub(r"<[^>]+>", "", text).lower()
    s = re.sub(r"[^a-z0-9 _-]", "", s).strip().replace(" ", "-")
    return re.sub(r"-+", "-", s) or "section"

LINKS = {"docs/TUTORIAL.md": "tutorial.html", "TUTORIAL.md": "tutorial.html",
         "docs/TUTORIAL_REBOUND.md": "tutorial-rebound.html", "TUTORIAL_REBOUND.md": "tutorial-rebound.html", "docs/TUTORIAL_BREAKWATER.md": "tutorial-breakwater.html", "TUTORIAL_BREAKWATER.md": "tutorial-breakwater.html", "docs/LANGUAGE.md": "language.html", "LANGUAGE.md": "language.html", "docs/API.md": "api.html",
         "API.md": "api.html", "docs/REPORT.md": "report.html", "REPORT.md": "report.html", "docs/START.md": "start.html",
         "START.md": "start.html", "docs/GRAPHICS.md": "graphics.html", "GRAPHICS.md": "graphics.html"}

# a table row's cells, as GitHub splits them: at each | that is not escaped (\|, which stands
# for a | in the cell, code included)
def table_cells(line):
    cells, cur, k = [], "", 0
    t = line.strip()
    if t.startswith("|"): t = t[1:]
    if t.endswith("|") and not t.endswith("\\|"): t = t[:-1]
    while k < len(t):
        if t[k] == "\\" and k + 1 < len(t) and t[k + 1] == "|":
            cur += "|"
            k += 2
            continue
        if t[k] == "|":
            cells.append(cur.strip())
            cur = ""
        else: cur += t[k]
        k += 1
    cells.append(cur.strip())
    return cells

def inline(t):
    # code spans first (their contents are literal)
    parts = re.split(r"(`[^`]+`)", t)
    outp = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            outp.append("<code>" + html.escape(p[1:-1]) + "</code>")
            continue
        p = html.escape(p, quote=False)
        def link(m):
            label, url = m.group(1), m.group(2)
            base, hash_, anchor = url.partition("#")
            if base in LINKS: url = LINKS[base] + hash_ + anchor
            elif base and not re.match(r"^(https?:|mailto:)", url) and not base.endswith(".html"):
                # a file in the repository (from docs/, ../x is x)
                if base.startswith("../"): base = base[3:]
                kind = "/blob/master/" if re.search(r"\.(md|jo|py|js)$", base) else "/tree/master/"
                url = REPO + kind + base + hash_ + anchor
            return f'<a href="{url}">{label}</a>'
        p = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, p)
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", p)
        p = re.sub(r"(?<!\w)_(?!\s)([^_]+?)(?<!\s)_(?!\w)", r"<em>\1</em>", p)
        outp.append(p)
    return "".join(outp)

def markdown(src):
    lines = src.split("\n")
    out, toc = [], []
    i = 0
    para = []
    seen = set()

    def flush():
        nonlocal para
        if para:
            # (the lines as one text: code spans and emphasis may go on to the next line; two
            # trailing spaces: a line break, \x01 until then)
            text = "\n".join(l.rstrip() + ("\x01" if l.endswith("  ") and k < len(para) - 1 else "") for k, l in enumerate(para))
            text = inline(text).replace("\x01\n", "<br>").replace("\n", " ")
            out.append("<p>" + text.strip() + "</p>")
            para = []

    def lists(i):
        # a list starting at line i (bullets or numbers, nested by indentation)
        items, kind = [], None
        base = len(lines[i]) - len(lines[i].lstrip())
        while i < len(lines):
            l = lines[i]
            m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l)
            if not m or len(m.group(1)) < base:
                if l.strip() and items and len(l) - len(l.lstrip()) > base:
                    items[-1][1].append(l.strip())
                    i += 1
                    continue
                break
            ind = len(m.group(1))
            if ind > base:
                sub, i = lists(i)
                items[-1][2].append(sub)
                continue
            kind = kind or ("ol" if m.group(2)[0].isdigit() else "ul")
            items.append([m.group(3), [], []])
            i += 1
        h = f"<{kind}>" + "".join("<li>" + inline(" ".join([t] + more)) + "".join(subs) + "</li>" for t, more, subs in items) + f"</{kind}>"
        return h, i

    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            flush()
            lang = l[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            # Sloppy code is fenced as gdscript: GitHub has no grammar for Sloppy, and GDScript's
            # (Godot's language) is the closest it has; here it gets Sloppy's own highlighting
            cls = "sloppy" if lang in ("sloppy", "gdscript") else lang or "plain"
            out.append(f'<pre><code class="{cls}">' + html.escape("\n".join(body)) + "</code></pre>")
            # a whole program (the tutorial's steps start with "# step"): a link that opens it in
            # the playground (its share-link form: #code=<deflated, base64url>)
            if cls == "sloppy" and body and body[0].startswith("# step"):
                out.append(f'<p class="play"><a href="{play_link("\n".join(body))}">Run it in the playground</a></p>')
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", l)
        if m:
            flush()
            n = len(m.group(1))
            text = inline(m.group(2))
            s = slug(m.group(2))
            while s in seen: s += "-"
            seen.add(s)
            if n in (2, 3): toc.append((n, s, re.sub(r"<[^>]+>", "", text)))
            out.append(f'<h{n} id="{s}"><a class="anchor" href="#{s}">{text}</a></h{n}>')
            i += 1
            continue
        if re.match(r"^<(p|h[1-6]|div|img|a|table|details|picture)\b", l):
            # raw HTML: as it is (until an empty line), images relative to the site's root
            flush()
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i])
                i += 1
            out.append(re.sub(r'src="assets/', 'src="../assets/', "\n".join(block)))
            continue
        if l.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(table_cells(lines[i]))
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.match(r"^:?-+:?$", c) for c in r)]
            t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</tbody></table>")
            continue
        if re.match(r"^\s*([-*]|\d+\.)\s+", l) and not re.match(r"^\s*-{3,}\s*$", l):
            flush()
            h, i = lists(i)
            out.append(h)
            continue
        if l.startswith(">"):
            flush()
            q = []
            while i < len(lines) and lines[i].startswith(">"):
                q.append(lines[i][1:].strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(q)) + "</p></blockquote>")
            continue
        if re.match(r"^\s*-{3,}\s*$", l):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if not l.strip():
            flush()
            i += 1
            continue
        para.append(l)
        i += 1
    flush()
    return "\n".join(out), toc

# a program in the playground (its share-link form: #code=<deflated, base64url>), from docs/
def play_link(code):
    z = zlib.compressobj(9, zlib.DEFLATED, -15)
    return "../playground/#code=" + base64.urlsafe_b64encode(z.compress(code.encode()) + z.flush()).decode().rstrip("=")

# the library page, from the library's sources (tools/apidoc.py): topics, each with its example,
# then every function as a signature and what it does; a search box narrows it down
def api_page():
    topics = apidoc.collect()
    out, toc = [], []
    out.append('<h1 id="the-library">The library</h1>')
    out.append(f'<p>{inline(apidoc.INTRO)}</p>')
    out.append('<div class="api-search"><input type="search" id="api-q" placeholder="Search the library (draw_mesh, split, gamepad...)" '
               'autocomplete="off" spellcheck="false"><span id="api-n"></span></div>')
    out.append('<div class="topics">')
    group = None
    for t in topics:
        if t["group"] != group:
            if group: out.append('</div>')
            group = t["group"]
            out.append(f'<div class="topic-group"><h4>{group}</h4>')
        out.append(f'<a href="#{t["id"]}">{html.escape(t["title"])}</a>')
    out.append('</div></div>')
    ids = set()
    for t in topics:
        toc.append((2, t["id"], t["title"]))
        out.append(f'<section class="topic" id="{t["id"]}"><h2><a class="anchor" href="#{t["id"]}">{html.escape(t["title"])}</a></h2>')
        if t["intro"]: out.append(f'<p class="intro">{inline(t["intro"])}</p>')
        if t["example"]:
            src = f'{REPO}/blob/master/{t["example_file"]}'
            out.append(f'<div class="example"><pre><code class="sloppy">{html.escape(t["example"])}</code></pre>'
                       f'<p class="play"><a href="{play_link(t["example"])}">Run it in the playground</a></p></div>')
        for m in t["modules"]:
            out.append('<div class="module">')
            if m["name"]:
                out.append(f'<h3 class="mod"><a href="{REPO}/blob/master/{m["path"]}">{m["name"]}</a></h3>')
            if m["header"]:
                out.append('<div class="about">')
                for kind, text in m["header"]:
                    out.append(f'<pre><code class="sloppy">{html.escape(text)}</code></pre>' if kind == "code" else f'<p>{inline(text)}</p>')
                out.append('</div>')
            for st, items in m["sections"]:
                out.append('<div class="sec">')
                if st: out.append(f'<h4>{html.escape(st)}</h4>')
                for e in items:
                    eid = "fn-" + re.sub(r"[^A-Za-z0-9_]", "", e["name"])
                    attr = f' id="{eid}"' if eid not in ids and eid != "fn-" else ""
                    ids.add(eid)
                    sigs = "\n".join(e["sigs"])
                    doc = f'<p>{inline(e["doc"])}</p>' if e["doc"] else ""
                    out.append(f'<div class="entry"{attr}><pre><code class="sloppy">{html.escape(sigs)}</code></pre>{doc}</div>')
                out.append('</div>')
            out.append('</div>')
        out.append('</section>')
    out.append('<p class="api-none" hidden>Nothing in the library matches that.</p>')
    out.append(API_SCRIPT)
    return "\n".join(out), toc

API_SCRIPT = """<script>
(() => {
  const q = document.getElementById("api-q"), n = document.getElementById("api-n");
  const entries = [...document.querySelectorAll(".entry")];
  for (const e of entries) e.dataset.text = e.textContent.toLowerCase();
  const run = () => {
    const words = q.value.toLowerCase().split(/\\s+/).filter(w => w);
    document.body.classList.toggle("searching", words.length > 0);
    let shown = 0;
    for (const e of entries) {
      const ok = words.every(w => e.dataset.text.includes(w));
      e.hidden = !ok;
      if (ok) shown++;
    }
    for (const el of document.querySelectorAll(".sec, .module, .topic"))
      el.hidden = words.length > 0 && !el.querySelector(".entry:not([hidden])");
    document.querySelector(".api-none").hidden = !(words.length && !shown);
    n.textContent = words.length ? `${shown} found` : "";
  };
  // (?q=words: the page searched for them, as a link)
  const given = new URLSearchParams(location.search).get("q");
  if (given) q.value = given;
  q.addEventListener("input", () => {
    run();
    const u = new URL(location.href);
    if (q.value) u.searchParams.set("q", q.value); else u.searchParams.delete("q");
    history.replaceState(null, "", u);
  });
  if (q.value) run();
})();
</script>"""

# ---- pages ----

def nav(here_page, prefix):
    items = [("Get started", "docs/start.html"), ("Tutorials", "docs/tutorial.html"), ("Language", "docs/language.html"),
             ("Library", "docs/api.html"), ("Playground", "playground/")]
    tutorials = {"docs/tutorial.html", "docs/tutorial-rebound.html", "docs/tutorial-breakwater.html"}
    on = lambda p: p == here_page or (p == "docs/tutorial.html" and here_page in tutorials)
    links = "".join(f'<a class="{"on" if on(p) else ""}" href="{prefix}{p}">{n}</a>' for n, p in items)
    # (on a narrow screen the links fold into a menu: the button opens it)
    return (f'<nav class="top"><a class="brand" href="{prefix}index.html"><img src="{prefix}icon-64.png" alt="">Sloppy</a>'
            f'<button class="menu" aria-label="Menu" aria-expanded="false" onclick="this.setAttribute(\'aria-expanded\', this.parentNode.classList.toggle(\'open\'))">'
            f'<span></span><span></span><span></span></button>'
            f'<div class="links">{links}<a class="gh" href="{REPO}">GitHub</a></div></nav>')

# the install command for the system the page is seen on (all of them without JavaScript)
INSTALL_SYSTEMS = [
    ("linux", "Linux", "curl -fsSL https://sloppy-lang.org/install | bash",
     "In a terminal, on x86-64. Installs to <code>~/.sloppy</code>; the command works at once."),
    ("windows", "Windows", "irm https://sloppy-lang.org/install.ps1 | iex",
     "In PowerShell, on Windows 10 or 11 (x64). Installs to <code>%LOCALAPPDATA%\\sloppy</code>; the command works at once."),
]

def install_box(prefix):
    tabs = "".join(f'<button data-os="{k}">{n}</button>' for k, n, _, _ in INSTALL_SYSTEMS)
    panes = ""
    for k, n, cmd, note in INSTALL_SYSTEMS:
        code = f'<div class="cmd"><pre><code>{html.escape(cmd)}</code></pre><button class="copy" title="Copy">Copy</button></div>'
        panes += f'<div class="pane" data-os="{k}">{code}<p>{note.format(prefix=prefix)}</p></div>'
    return f'''<div class="install-box" data-os="linux"><div class="tabs">{tabs}</div>{panes}
<p class="phone">On a phone or tablet? Sloppy installs on a computer; here, <a href="{prefix}playground/">try it in the browser</a>.</p>
<p class="mac">Sloppy does not run on macOS yet. Its programs run in any browser, though: write and run them in <a href="{prefix}playground/">the playground</a>.</p></div>'''

INSTALL_SCRIPT = """<script>
(() => {
  const ua = navigator.userAgent, p = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || "";
  const phone = /Android|iPhone|iPad|iPod/.test(ua) || (/Mac/.test(p) && navigator.maxTouchPoints > 1);
  const mac = !phone && (/Mac/.test(p) || /Mac OS X/.test(ua));
  const os = /Win/.test(p) || /Windows/.test(ua) ? "windows" : "linux";
  for (const box of document.querySelectorAll(".install-box")) {
    box.classList.add("js");
    box.dataset.os = os;
    if (phone) box.classList.add("on-phone");
    if (mac) box.classList.add("on-mac");
    for (const b of box.querySelectorAll(".tabs button")) b.onclick = () => { box.dataset.os = b.dataset.os; };
    for (const b of box.querySelectorAll("button.copy")) b.onclick = () => {
      navigator.clipboard.writeText(b.parentNode.querySelector("code").textContent).then(() => {
        b.textContent = "Copied"; setTimeout(() => { b.textContent = "Copy"; }, 1500);
      });
    };
  }
})();
</script>"""

SITE = "https://sloppy-lang.org"
DESCRIPTION = ("A small, statically typed language for making games that feels like Python and runs like C. "
               "It compiles in milliseconds, to a native Linux or Windows executable or a single web page.")

# what chat apps and social sites show for a link (Open Graph, and Twitter's cards); the
# image is assets/social.png (1200x630)
def preview_meta(title, description, path):
    t, d = html.escape(title, quote=True), html.escape(description, quote=True)
    return (f'<meta name="description" content="{d}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="Sloppy">'
            f'<meta property="og:title" content="{t}"><meta property="og:description" content="{d}">'
            f'<meta property="og:url" content="{SITE}/{path}">'
            f'<meta property="og:image" content="{SITE}/social.png"><meta property="og:image:width" content="1200">'
            f'<meta property="og:image:height" content="630">'
            f'<meta property="og:image:alt" content="sloppy: a simple game dev language">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#2f6a7a">')

def page(title, body, here_page, prefix, extra_head="", description=DESCRIPTION):
    path = "" if here_page == "index.html" else here_page
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>{preview_meta(title, description, path)}
<link rel="icon" href="{prefix}icon-32.png"><link rel="stylesheet" href="{prefix}style.css">{extra_head}
</head><body>{nav(here_page, prefix)}
{body}
<footer>Sloppy &middot; <a href="{REPO}">source on GitHub</a> &middot; <a href="{prefix}docs/report.html">measured results</a> &middot; <a href="{REPO}/blob/master/CHANGELOG.md">changes</a> &middot; <a href="{REPO}/blob/master/LICENSE">MIT license</a></footer>
<script src="{prefix}highlight.js"></script>
<script>for (const c of document.querySelectorAll("pre code.sloppy")) c.innerHTML = sloppyHighlight(c.textContent, 0).replace(/\\n$/, "");</script>
{INSTALL_SCRIPT if "install-box" in body else ""}
</body></html>
"""

DOCS = [("start.html", "docs/START.md", "Getting started", "Start"),
        ("tutorial.html", "docs/TUTORIAL.md", "Make a game", "Tutorials"),
        ("tutorial-rebound.html", "docs/TUTORIAL_REBOUND.md", "Make an arcade game", "Tutorials"),
        ("tutorial-breakwater.html", "docs/TUTORIAL_BREAKWATER.md", "Make a 3D shooter", "Tutorials"),
        ("language.html", "docs/LANGUAGE.md", "The language", "Reference"),
        ("api.html", "docs/API.md", "The library", "Reference"),
        ("graphics.html", "docs/GRAPHICS.md", "Graphics and the GPU", "Reference"),
        ("report.html", "docs/REPORT.md", "Measured results", "More")]
DOC_DESCRIPTIONS = {
    "start.html": "Install Sloppy, a simple game dev language, and write your first program and game.",
    "tutorial.html": "Make a small platformer in Sloppy, step by step: moving, jumping, platforms, a camera, menus, saving, glow and music.",
    "tutorial-rebound.html": "Make a small arcade game in Sloppy, step by step: angles, many things at once, chain reactions, upgrades and synthesized sound.",
    "tutorial-breakwater.html": "Make a small 3D first-person shooter in Sloppy, step by step: mouse look, walls, shots as rays, enemies that fire back, waves, light and sound.",
    "language.html": "The Sloppy language: types, functions, structs and unions, numeric arrays, modules, parallelism, the game loop and calling C.",
    "api.html": "Everything in Sloppy's standard library: strings, maps, math, files, threads, windows, input, 2D and 3D drawing, shaders and audio.",
    "graphics.html": "How Sloppy draws through Vulkan, OpenGL, WebGL or a software renderer, how shaders written in Sloppy reach each, and computing on the GPU.",
    "report.html": "Measured results for Sloppy's design goals: compile speed, program speed against C, and executable size."}

def build_docs():
    os.makedirs(os.path.join(out, "docs"), exist_ok=True)
    for k, (name, src, title, _) in enumerate(DOCS):
        text = open(os.path.join(root, src)).read()
        # (<!-- install --> ... <!-- /install -->: the commands, on GitHub; here, the one for this system)
        text = re.sub(r"<!-- install -->.*?<!-- /install -->", lambda m: install_box("../"), text, flags=re.S)
        body, toc = api_page() if name == "api.html" else markdown(text)
        pages, group = "", None
        for n, _, t, g in DOCS:
            if g != group:
                pages += f'<div class="group">{g}</div>'
                group = g
            pages += f'<a class="{"on" if n == name else ""}" href="{n}">{t}</a>'
        tocs = "".join(f'<a class="h{n}" href="#{s}">{t}</a>' for n, s, t in toc)
        # the pages before and after this one, in reading order
        steps = ""
        if k > 0: steps += f'<a class="prev" href="{DOCS[k - 1][0]}"><span>Previous</span>{DOCS[k - 1][2]}</a>'
        if k + 1 < len(DOCS): steps += f'<a class="next" href="{DOCS[k + 1][0]}"><span>Next</span>{DOCS[k + 1][2]}</a>'
        # (on a narrow screen the side bar is folded away behind its button)
        side = (f'<aside><button class="side-toggle" onclick="this.parentNode.classList.toggle(\'open\')">{html.escape(title)}<span>Contents</span></button>'
                f'<div class="side"><div class="pages">{pages}</div><div class="toc">{tocs}</div></div></aside>')
        main = f'<div class="doc">{side}<main>{body}<div class="steps">{steps}</div></main></div>'
        here_page = "docs/" + name
        open(os.path.join(out, "docs", name), "w").write(page(f"{title} | Sloppy", main, here_page, "../", description=DOC_DESCRIPTIONS[name]))

HOME = """
<section class="hero">
  <div>
    <h1><span>sloppy</span>: a simple game dev language</h1>
    <p class="lead">A small, statically typed language that feels like Python and runs like C. One command
    compiles and runs your program in milliseconds, as a native Linux or Windows executable or as a single web page.</p>
    {install}
    <div class="buttons"><a class="btn primary" href="playground/">Try it in your browser</a>
    <a class="btn" href="docs/start.html">Get started</a><a class="btn" href="docs/tutorial.html">Make a game</a><a class="btn" href="docs/language.html">The language</a></div>
  </div>
  <div class="art"><img class="logo" src="logo-512.png" alt="a white clover blossom">
  <pre><code class="sloppy">pos = vec2(400, 300)

update = (dt: f64):
    pos += input_axis() * f32(300 * dt)

draw = ():
    clear(rgb(0.08, 0.08, 0.12))
    circle(pos, 24, rgb(1.0, 0.6, 0.2))
    text("arrow keys", vec2(20, 20), 24, WHITE)</code></pre></div>
</section>
<section class="features">
  <div class="feature"><h3>Instant compiles</h3><p>About 250,000 lines a second. Hello world compiles and runs in about 10 ms; there is no build system, options live in the source.</p></div>
  <div class="feature"><h3>Fast programs</h3><p>Release builds run within about 1.5&times; of gcc -O2, with bounds checks on. <code>parallel_map</code> uses every core; GPU arrays run on the GPU.</p></div>
  <div class="feature"><h3>Easy</h3><p>Type inference everywhere, indentation syntax, closures, partial application, generics without ceremony, unions, value semantics with no garbage collector.</p></div>
  <div class="feature"><h3>Made for games</h3><p>Windows, input, 2D drawing, a 3D renderer with shadows and bloom, shaders written in Sloppy, audio, pixel art and any screen shape, all built in.</p></div>
  <div class="feature"><h3>Runs anywhere it lands</h3><p>Native programs are static executables with no dependencies; web builds are one HTML file. Graphics drivers are optional: there is a software renderer.</p></div>
  <div class="feature"><h3>Self-hosted</h3><p>The compiler is written in Sloppy and compiles itself, even in this site's playground, where it runs as WebAssembly.</p></div>
</section>
<section class="showcase">
  <a href="rebound/"><img src="assets/rebound.png" alt="Rebound: a shield arcs around a glowing core; a chain of blasts runs through a line of turrets"></a>
  <div>
    <h2>Rebound</h2>
    <p>A complete arcade game in one file of Sloppy. Turn the shield to catch the turrets' bolts and send
    them back: blasts set off the turrets beside them, catches near the shield's edge bank off to other
    turrets, and every few turrets you choose an upgrade. Menus, settings, a saved best score, and sound
    made by the built-in synthesizer.</p>
    <div class="buttons"><a class="btn primary" href="rebound/">Play it</a><a class="btn" href="playground/#example=rebound">Change it in the playground</a>
    <a class="btn" href="https://github.com/david-andrew/sloppy-lang/blob/master/examples/rebound/rebound.jo">Read the source</a></div>
  </div>
</section>
<section class="showcase flip">
  <a href="breakwater/"><img src="assets/breakwater.png" alt="Breakwater: robots advance across a platform at sea; a shielded warden is in the shotgun's sights"></a>
  <div>
    <h2>Breakwater</h2>
    <p>A first-person shooter in one file of Sloppy: hold a platform at sea against waves of robots.
    A shield that recharges, two weapons at a time from racks and fallen robots, grenades and melee.
    Animated glTF models (robots and weapons by Quaternius), shadows, bloom and synthesized sound;
    mouse, keyboard alone, or a gamepad.</p>
    <div class="buttons"><a class="btn primary" href="breakwater/">Play it</a><a class="btn" href="playground/#example=breakwater">Change it in the playground</a>
    <a class="btn" href="https://github.com/david-andrew/sloppy-lang/blob/master/examples/breakwater/breakwater.jo">Read the source</a></div>
  </div>
</section>
<section class="strip">
  <h2>Numbers, arrays, and the rest</h2>
  <pre><code class="sloppy">fib = (n: int) -> int:
    if n < 2: return n
    fib(n - 1) + fib(n - 2)

nums = [5 3 9 1]
nums.sort()
add = (a: int, b: int): a + b
print(nums.map((x): x * x), add(1, _)(41), fib(30))
print(nums .* 2.5 .+ 1, sqrt.([4.0 9.0]), [1 2; 3 4] * [1 0; 0 1])</code></pre>
  <p>Editors: <code>sloppy lsp</code> is a language server (and there is a <a href="https://marketplace.visualstudio.com/items?itemName=RedFoxLabs.sloppy">VS Code / Cursor extension</a>). An interactive prompt: run <code>sloppy</code> with no file.</p>
</section>
"""

def main():
    if os.path.exists(out): shutil.rmtree(out)
    os.makedirs(out)
    shutil.copy(os.path.join(here, "style.css"), out)
    for f in ["icon-32.png", "icon-64.png", "logo-512.png", "social.png"]: shutil.copy(os.path.join(root, "assets", f), out)
    shutil.copytree(os.path.join(root, "assets"), os.path.join(out, "assets"))
    shutil.copy(os.path.join(root, "tools", "playground", "highlight.js"), out)
    open(os.path.join(out, "index.html"), "w").write(page("Sloppy: a simple game dev language", HOME.replace("{install}", install_box("")), "index.html", ""))
    build_docs()
    os.makedirs(os.path.join(out, "playground"))
    subprocess.run([sys.executable, os.path.join(root, "tools", "playground.py"), os.path.join(out, "playground", "index.html")], check=True)
    # (the playground's title leads back to the site)
    pg = os.path.join(out, "playground", "index.html")
    t = open(pg).read().replace('<h1><span>Sloppy</span> playground</h1>', '<h1><a href="../" style="color:inherit"><span>Sloppy</span></a> playground</h1>', 1)
    t = t.replace('<title>Sloppy playground</title>', '<title>Sloppy playground</title><link rel="icon" href="../icon-32.png">'
                  + preview_meta("Sloppy playground", "Write and run Sloppy programs and games in your browser: the compiler itself runs here, as WebAssembly.", "playground/"), 1)
    open(pg, "w").write(t)
    # Rebound, to play (sloppy-lang.org/rebound/)
    os.makedirs(os.path.join(out, "rebound"))
    subprocess.run([os.path.join(root, "bin", "sloppy"), "build", os.path.join(root, "examples", "rebound", "rebound.jo"), "--target", "wasm",
                    "-o", os.path.join(out, "rebound", "index.html")], check=True, env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")))
    # Breakwater (sloppy-lang.org/breakwater/)
    os.makedirs(os.path.join(out, "breakwater"))
    subprocess.run([os.path.join(root, "bin", "sloppy"), "build", os.path.join(root, "examples", "breakwater", "breakwater.jo"), "--target", "wasm",
                    "-o", os.path.join(out, "breakwater", "index.html")], check=True, env=dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib")))
    # curl -fsSL .../install | bash
    shutil.copy(os.path.join(root, "tools", "install.sh"), os.path.join(out, "install"))
    # irm https://sloppy-lang.org/install.ps1 | iex
    shutil.copy(os.path.join(root, "tools", "install.ps1"), os.path.join(out, "install.ps1"))
    open(os.path.join(out, ".nojekyll"), "w").close()
    print(out)

main()
