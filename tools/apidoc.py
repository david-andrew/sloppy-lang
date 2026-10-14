#!/usr/bin/env python3
"""Generate docs/API.md from the standard library: its public functions, structs, enums and
constants, with the comment lines just above them, by topic. Each topic has an example program
(docs/api/<name>.jo; the tests run or compile them all). tools/site.py builds the website's
library page from the same data (collect())."""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (group, id, title, modules, example, what it is about); a module may be (module, names) for
# only those names of it
TOPICS = [
    ("Basics", "builtins", "Built-in functions", [], "builtins",
     "Part of the language itself: printing, stopping with an error, and a few functions the compiler knows."),
    ("Basics", "arrays", "Arrays", ["core/array"], "arrays",
     "`T[]` is a growable array. Arrays are values: assigning one or passing it to a function gives a copy "
     "(shared until one of them changes). Functions can be called as `f(xs, y)` or `xs.f(y)`."),
    ("Basics", "strings", "Strings", ["core/str"], "strings",
     "`str` is text, in UTF-8. `\"{x}\"` puts a value in a string; `\"{x:.2}\"` rounds it to two decimals "
     "(more ways: [the language](LANGUAGE.md#2-lexical-structure)). Strings are values, like arrays."),
    ("Basics", "regex", "Regular expressions", ["std/regex"], "regex",
     "`regex(r\"...\")` makes a pattern once; `s.find(r)`, `s.find_all(r)`, `s.matches(r)`, `s.replace(r, \"$1\")` "
     "and `s.split(r)` use it. Raw strings (`r\"\\d+\"`) keep the backslashes as they are."),
    ("Basics", "maps", "Maps", ["core/map"], "maps",
     "`{K: V}` maps keys to values, in the order they were added."),
    ("Basics", "math", "Math and random numbers", ["core/math"], "math",
     "For vectors and matrices, see [colors, vectors and matrices](#colors-vectors-and-matrices)."),
    ("Basics", "system", "Files, time and the system", ["core/os", "std/path", "std/date"], "system",
     "In a web page, files are the ones the page was given, and `env` reads its address's parameters."),
    ("Data", "json", "JSON, CSV and base64", ["std/json", "std/csv", "std/base64"], "json",
     "`to_json(value)` and `from_json[T](text)` turn any value (a struct, an array, a map...) into JSON and back; "
     "`parse_json` reads JSON of any shape as a `Json` to look inside."),
    ("Data", "saving", "Saving, and values as text", ["std/save", "std/text"], "saving",
     "`save_value` and `load_value` keep any value (settings, a saved game) as text that reads back even "
     "after its structs gain or lose fields."),
    ("Data", "threads", "Threads", ["std/thread"], "threads", ""),
    ("Data", "numeric", "Numeric arrays", ["std/nd"], "numeric",
     "Elementwise operators (`.+ .* .^`...), `f.(xs)` and n-dimensional arrays are part of the language: "
     "see [arrays for numeric work](LANGUAGE.md#8-arrays-for-numeric-work). These are the functions on them."),
    ("Games", "window", "The window, the game loop and input", ["game/window", "game/stats"], "window",
     "A program that defines `update(dt: f64)` or `draw()` opens a window and calls them every frame. "
     "More on windows, screen sizes and the game loop: [the language](LANGUAGE.md#12-programs-and-the-game-loop)."),
    ("Games", "controls", "Controls and gamepads", ["game/controls", "game/gamepad"], "controls", ""),
    ("Games", "draw2d", "Drawing in 2D", ["game/draw2d", "game/font", "game/screen", ("game/softgl", ["soft_rendering"])], "draw2d", ""),
    ("Games", "sprites", "Images, sprites and tilemaps", ["game/image", "game/jpeg", "game/sprites", "game/tilemap"], "sprites", ""),
    ("Games", "vmath", "Colors, vectors and matrices", ["game/vmath"], "colors",
     "`vec2`, `vec3`, `vec4`, `ivec2` and `mat4` are built-in types, with `+ - *` and fields `.x .y .z .w` "
     "(and swizzles: `v.xz`). Colors are `vec4`s: red, green, blue and alpha, from 0 to 1."),
    ("Games", "draw3d", "3D", ["game/draw3d", "game/camera3d"], "draw3d", ""),
    ("Games", "models", "Models (glTF)", ["game/gltf"], None, ""),
    ("Games", "sound", "Sound and music", ["game/audio", "game/vorbis"], "sound", ""),
    ("Games", "gpu", "GPU programs", ["game/gpu"], "gpu", ""),
    ("Games", "gpuarray", "GPU arrays", ["game/gpuarray"], "gpuarray", ""),
    ("Games", "gpubuffer", "GPU buffers and compute", ["game/gpubuffer"], "gpubuffer",
     "For programs that keep their data on the GPU: buffers of any struct, functions run once per element "
     "(`compute`, `dispatch`) and draws the GPU decides (`draw_indirect`). Through Vulkan these run on the GPU; "
     "elsewhere on the CPU, so programs work everywhere."),
    ("Games", "menus", "Menus", ["game/ui"], "menus", ""),
    ("Games", "paths", "Paths", ["game/paths"], "paths", ""),
    ("Games", "helpers", "Particles, noise, easing and collisions", ["game/gameutil"], "helpers", ""),
    ("Games", "physics", "2D physics", ["physics"], "physics",
     "A module (`import physics`): rigid bodies (circles, boxes, convex polygons) that collide, bounce, slide and stack, "
     "joined by pins, rods, ropes and springs. Distances are in the screen's units with y down, as in drawing. See [examples/physics.jo](https://github.com/david-andrew/sloppy-lang/blob/master/examples/physics.jo)."),
    ("Games", "physics3d", "3D physics", ["physics3d"], "physics3d",
     "A module (`import physics3d`): rigid bodies (spheres, boxes, capsules) and a level's triangles, joints (ball, hinge, "
     "rod, rope, spring), rays, and a character controller that walks slopes and steps. Meters, y up. See [examples/physics3d.jo](https://github.com/david-andrew/sloppy-lang/blob/master/examples/physics3d.jo)."),
    ("Games", "net", "Networking", ["net"], "networking",
     "A module (`import net`): messages between programs over WebSockets, so a native build and a web page "
     "can play together (a server is a native program; a web page connects to one: [examples/netpong](https://github.com/david-andrew/sloppy-lang/tree/master/examples/netpong)), "
     "and UDP datagrams between native programs."),
    ("Games", "netplay", "Netplay", ["netplay"], "netplay",
     "A module (`import netplay`): players on different machines in one game. With rollback (`session`), only inputs "
     "travel, and a late one is made up for by playing the last ticks again; with a server (`server`, `client`), the "
     "server runs the game and clients predict their own moves and draw others a little in the past. Sloppy's math is its own (no system math "
     "library, no fused multiply-add), so a tick comes out the same on Linux, Windows, macOS and the web. See [examples/duel](https://github.com/david-andrew/sloppy-lang/tree/master/examples/duel) and [examples/arena](https://github.com/david-andrew/sloppy-lang/tree/master/examples/arena), "
     "and [playing over a network](MULTIPLAYER.md) for choosing between them."),
]
# the library's own machinery (the runtime, the OS and graphics layers, the prompt...): not listed
INTERNAL = {"core/rt", "core/fmt", "core/windows", "core/macos", "game/dl", "game/cocoa", "game/x11", "game/wayland", "game/wlclient", "game/dmabuf", "game/vk", "game/vkgl",
            "game/gl", "game/softgl", "std/backtrace", "std/snapshot", "std/repl", "std/watch"}

# what the compiler itself provides: (topic, section, name, signatures, what it does)
BUILTINS = [
    ("builtins", "", "print", ["print(values...)"], "prints the values, separated by spaces, and a line break"),
    ("builtins", "", "assert", ["assert(ok: bool, message: str = \"\")"], "stops the program (with the message, and where) if `ok` is false"),
    ("builtins", "", "panic", ["panic(message: str)"], "stops the program, with the message and where each function on the way was called"),
    ("builtins", "", "fill", ["fill[T](x: T, n: int) -> T[]"], "an array of `n` copies of `x`"),
    ("builtins", "", "sqrt", ["sqrt(x: f64) -> f64", "sqrt(x: f32) -> f32"], "the square root"),
    ("builtins", "", "embed", ["embed(path: str) -> u8[]"], "a file's contents, read when the program is compiled and kept in it (the path is relative to the source file)"),
    ("builtins", "", "bytes", ["bytes(s: str) -> u8[]"], "a string's bytes (UTF-8)"),
    ("builtins", "", "str_from_bytes", ["str_from_bytes(b: u8[]) -> str"], "a string of these bytes"),
    ("builtins", "", "size_of", ["size_of(T) -> int", "align_of(T) -> int"], "how many bytes a value of type T takes, and its alignment"),
    ("builtins", "", "int", ["int(x)", "i32(x)", "u8(x)"], "a number as a whole number of that type (a float is cut toward zero: int(3.7) is 3); "
     "text is read with `to_int(s)`, and a one-character string in single quotes is its code (`u8('A')` is 65)"),
    ("builtins", "", "f64", ["f64(x)", "f32(x)"], "a number as a float of that size (f32 and f64 also mix by themselves)"),
    ("builtins", "", "str", ["str(x)"], "any value as text, as `print` shows it"),
    ("arrays", "Built in", "len", ["len(xs: T[]) -> int"], "how many elements"),
    ("arrays", "Built in", "push", ["push(xs: mut T[], x: T)"], "adds `x` at the end"),
    ("arrays", "Built in", "pop", ["pop(xs: mut T[]) -> T"], "removes the last element and gives it back"),
    ("arrays", "Built in", "insert", ["insert(xs: mut T[], i: int, x: T)"], "puts `x` in at index `i`, moving the ones after it along"),
    ("arrays", "Built in", "remove", ["remove(xs: mut T[], i: int) -> T"], "takes out the element at `i` and gives it back"),
    ("arrays", "Built in", "extend", ["extend(xs: mut T[], ys: T[])"], "adds all of `ys` at the end"),
    ("arrays", "Built in", "clear", ["clear(xs: mut T[])"], "removes every element"),
    ("arrays", "Built in", "truncate", ["truncate(xs: mut T[], n: int)"], "keeps the first `n` elements"),
    ("arrays", "Built in", "resize", ["resize(xs: mut T[], n: int)"], "makes it `n` long: new elements are zero"),
    ("arrays", "Built in", "reserve", ["reserve(xs: mut T[], n: int)", "cap(xs: T[]) -> int"], "makes room for `n` elements without growing again; `cap` is the room there is"),
]

def signature(line):
    """the declaration up to the ':' that starts the body (depth-aware)"""
    depth = 0
    for i, c in enumerate(line):
        if c in "([{": depth += 1
        elif c in ")]}": depth -= 1
        elif c == ":" and depth == 0 and i > 0:
            return line[:i]
    return line

def header_of(lines):
    """a module's first comment: paragraphs of prose, and examples (lines indented 3 or more)"""
    header = []
    for l in lines:
        if l.startswith("#"): header.append(l[1:].rstrip())
        else: break
    blocks, para, code = [], [], []
    def end_para():
        if para: blocks.append(("text", " ".join(para)))
        para.clear()
    def end_code():
        while code and not code[-1].strip(): code.pop()
        if code: blocks.append(("code", "\n".join(code)))
        code.clear()
    for h in header:
        if h.startswith("   ") and h.strip():
            end_para()
            code.append(h[3:])
        elif not h.strip():
            if code: code.append("")
            else: end_para()
        else:
            end_code()
            para.append(h.strip())
    end_para()
    end_code()
    return blocks

def entries_of(path, only=None):
    """[(section, name, signature, what it does)] of a module's public declarations"""
    lines = open(path, encoding="utf-8").read().splitlines()
    out, comment, seen = [], [], set()
    section = ""
    in_when = False        # (declarations one level into a top-level `when` count too)
    body = None            # (a struct's fields or an enum's variants, as written: the lines under it)
    for l in lines:
        s = l.rstrip()
        if body is not None:
            if s.startswith("    ") and not s.startswith("     "):
                t = s[4:]
                if not t.startswith(("#", "_")): body.append(t)
                continue
            body = None
        if s and not s.startswith((" ", "#")):
            in_when = s.startswith(("when ", "else"))
            if in_when: continue
        if in_when and s.startswith("    ") and not s.startswith("     "):
            s = s[4:]
            if s.startswith("extern"): s = "    " + s
        if s.startswith("#"):
            # (lines indented 3 or more after the # are an example: kept as code)
            if s.startswith("#   ") and s.strip("# "):
                comment.append("\0" + s[4:].rstrip())
                continue
            c = s.lstrip("# ").rstrip()
            m = re.fullmatch(r"-{3,}\s*(.*?)\s*-{3,}", c)
            if m:
                section = m.group(1)
                comment = []
            else: comment.append(c)
            continue
        m = re.match(r"(struct|enum|const|type)\s+([A-Za-z_]\w*)(.*)", s)
        f = re.match(r"(?:extern\s+)?(\([^)\s]+\)|[A-Za-z_]\w*)(\[[^\]]*\])?\s*=\s*\(", s)
        if not s.startswith(" ") and (m or f):
            name = m.group(2) if m else f.group(1)
            if not name.startswith("_") and (only is None or name in only):      # (private, and the runtime's __ names)
                sig = s
                if f and not m: sig = signature(s)
                elif m.group(1) == "struct": sig = s.split(":")[0]
                elif m.group(1) == "const": sig = re.sub(r"\s+#.*$", "", s)
                if sig.strip() not in seen:
                    seen.add(sig.strip())
                    prose = " ".join(c for c in comment if c and not c.startswith("\0"))
                    code = [c[1:] for c in comment if c.startswith("\0")]
                    out.append((section, name, sig.strip(), prose, [], code))
                    if m and m.group(1) in ("struct", "enum") and s.endswith(":"): body = out[-1][4]
        if not s.startswith("#"):
            comment = []
    return out

# how the sources' section markers read as headings ("" for none)
SECTION_TITLES = {"public API": "", "public input API": "", "state": "", "output": "Playing", "synthesis": "Making sounds",
                  "WAV files": "WAV files", "colors (vec4 rgba in 0..1)": "Colors", "quaternions (vec4: x, y, z, w)": "Quaternions",
                  "mesh generators": "Meshes", "frame post-processing": "", "`sloppy test` support": ""}

def section_title(s):
    s = SECTION_TITLES.get(s, s)
    return s[:1].upper() + s[1:] if s else ""

def collect():
    """[{id, group, title, intro, example (code or None), modules: [{name, header, sections: [(title, [entry])]}]}],
    an entry being {name, sigs, doc}"""
    covered = set()
    topics = []
    for group, tid, title, mods, example, intro in TOPICS:
        t = {"id": tid, "group": group, "title": title, "intro": intro, "example": None, "modules": []}
        if example:
            t["example"] = open(os.path.join(ROOT, "docs", "api", example + ".jo"), encoding="utf-8").read().rstrip("\n")
            t["example_file"] = f"docs/api/{example}.jo"
        built = [b for b in BUILTINS if b[0] == tid]
        if built:
            secs = {}
            for _, sec, name, sigs, doc in built: secs.setdefault(sec, []).append({"name": name, "sigs": sigs, "doc": doc})
            t["modules"].append({"name": "", "header": [], "sections": list(secs.items())})
        for mod in mods:
            mod, only = (mod if isinstance(mod, tuple) else (mod, None))
            covered.add(mod)
            path = os.path.join(ROOT, "lib", mod + ".jo")
            lines = open(path, encoding="utf-8").read().splitlines()
            sections = []
            for sec, name, sig, doc, body, code in entries_of(path, only):
                title_ = section_title(sec)
                if not sections or sections[-1][0] != title_: sections.append((title_, []))
                items = sections[-1][1]
                # overloads: one entry (the same name next to each other, one description or the same)
                if items and items[-1]["name"] == name and (not doc or not items[-1]["doc"] or doc == items[-1]["doc"]):
                    items[-1]["sigs"].append(sig)
                    items[-1]["doc"] = items[-1]["doc"] or doc
                else:
                    items.append({"name": name, "sigs": [sig], "doc": doc, "body": body, "code": code})
            # (sections of the same name further on join the first)
            merged = []
            for st, items in sections:
                same = [m for m in merged if m[0] == st]
                if same: same[0][1].extend(items)
                else: merged.append((st, items))
            if merged:
                t["modules"].append({"name": os.path.basename(mod) + ".jo", "path": f"lib/{mod}.jo",
                                     "header": header_of(lines) if only is None else [], "sections": merged})
        topics.append(t)
    # every module is in a topic, or the library's own
    for d in ["core", "std", "game"]:
        for f in sorted(os.listdir(os.path.join(ROOT, "lib", d))):
            m = f"{d}/{f[:-3]}"
            if f.endswith(".jo") and m not in covered and m not in INTERNAL:
                raise SystemExit(f"tools/apidoc.py: lib/{m}.jo is in no topic (TOPICS) and not INTERNAL")
    return topics

INTRO = ("Everything here is there in every program, without imports. Functions can be called as `f(x, y)` or "
         "`x.f(y)`. Each topic starts with a whole program to try.")

def markdown(topics):
    out = ["# The library", "", "Generated by `tools/apidoc.py` from the library's sources (`lib/`). " + INTRO, ""]
    group = None
    for t in topics:
        if t["group"] != group:
            group = t["group"]
            out.append(f"**{group}:** " + " · ".join(f"[{x['title']}](#{slug(x['title'])})" for x in topics if x["group"] == group) + "  ")
    out.append("")
    for t in topics:
        out += [f"## {t['title']}", ""]
        if t["intro"]: out += [t["intro"], ""]
        if t["example"]: out += ["```gdscript", t["example"], "```", ""]
        for m in t["modules"]:
            if m["name"] and len(t["modules"]) > 1: out += [f"### {m['name']}", ""]
            for kind, text in m["header"]:
                out += (["```gdscript", text, "```", ""] if kind == "code" else [text, ""])
            for st, items in m["sections"]:
                if st: out += [f"#### {st}", ""]
                for e in items:
                    for k, sig in enumerate(e["sigs"]):
                        doc = f": {e['doc']}" if e["doc"] and k == 0 else ""
                        out.append(f"- `{sig.replace('|', '\\|')}`{doc}")
                    if e.get("code"):
                        out += ["  ```gdscript"] + [f"  {c}" for c in e["code"]] + ["  ```"]
                    if e.get("body"):
                        out += ["  ```gdscript", f"  {e['sigs'][0].rstrip(':')}:"] + [f"      {b}" for b in e["body"]] + ["  ```"]
                out.append("")
    return "\n".join(out) + "\n"

def slug(text):
    s = re.sub(r"[^a-z0-9 _-]", "", text.lower()).strip().replace(" ", "-")
    return re.sub(r"-+", "-", s)

if __name__ == "__main__":
    open(os.path.join(ROOT, "docs", "API.md"), "w", encoding="utf-8", newline="\n").write(markdown(collect()))
    print("wrote docs/API.md")
