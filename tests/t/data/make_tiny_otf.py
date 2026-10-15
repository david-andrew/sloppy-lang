#!/usr/bin/env python3
"""Write tiny.otf: a minimal OpenType font with PostScript (CFF) outlines for tests/t/font_cff.jo.
Glyphs: 0 .notdef, 1 'I' (a rectangle: stems, hlineto/vlineto), 2 'O' (two cubic curves:
rrcurveto, hvcurveto), 3 'L' (a hint mask with implicit vstems, a local and a global
subroutine), 4 space; 1000 units per em."""
import struct, os

def num(v):
    # a Type 2 charstring number
    if -107 <= v <= 107: return bytes([v + 139])
    if 108 <= v <= 1131: v -= 108; return bytes([v // 256 + 247, v % 256])
    if -1131 <= v <= -108: v = -v - 108; return bytes([v // 256 + 251, v % 256])
    return b"\x1c" + struct.pack(">h", v)

def cs(*items):
    out = b""
    for x in items:
        if isinstance(x, int): out += num(x)
        else: out += x                             # an operator's bytes
    return out

RMOVETO, HLINETO, VLINETO, RLINETO, RRCURVETO, HVCURVETO = b"\x15", b"\x06", b"\x07", b"\x05", b"\x08", b"\x1f"
HSTEM, VSTEM, HSTEMHM, HINTMASK = b"\x01", b"\x03", b"\x12", b"\x13"
CALLSUBR, CALLGSUBR, RETURN, ENDCHAR = b"\x0a", b"\x1d", b"\x0b", b"\x0e"

def index(items, off_size=4):
    out = struct.pack(">HB", len(items), off_size)
    if not items: return struct.pack(">H", 0)
    o = 1
    offs = [o]
    for it in items:
        o += len(it); offs.append(o)
    out += b"".join(struct.pack(">I", x)[4 - off_size:] for x in offs)
    return out + b"".join(items)

def dint(v): return b"\x1d" + struct.pack(">i", v)   # a DICT number, always 5 bytes

charstrings = [
    cs(ENDCHAR),
    # 'I': a width first (500 - nominal 0: dropped), stems, then a rectangle by alternating lines
    cs(400, 0, 700, HSTEM, 100, 200, VSTEM, 100, 0, RMOVETO, 700, 200, -700, VLINETO, ENDCHAR),
    # 'O': a ring of two cubic curves, the second by hvcurveto
    cs(500, 0, RMOVETO, -400, 0, 0, 700, 400, 0, RRCURVETO, 400, 0, 0, -700, -400, HVCURVETO, ENDCHAR),
    # 'L': a hint mask after hstemhm, its vstems implicit; the up stroke a local subroutine, the
    # across one a global one
    cs(0, 700, HSTEMHM, 100, 200, HINTMASK, b"\xc0", 100, 0, RMOVETO, -107, CALLSUBR, -107, CALLGSUBR, 0, -700, RLINETO, ENDCHAR),
    cs(ENDCHAR),
]
local_subrs = [cs(0, 700, RLINETO, RETURN)]
global_subrs = [cs(200, 0, RLINETO, RETURN)]

def cff():
    header = bytes([1, 0, 4, 4])
    names = index([b"Tiny"])
    strings = index([])
    gsubrs = index(global_subrs)
    chars = index(charstrings)
    lsubrs = index(local_subrs)
    private = dint(len(dint(0) + b"\x13")) + b"\x13"       # Subrs: right after the private dict
    def top(cs_off, priv_off):
        return dint(cs_off) + b"\x11" + dint(len(private)) + dint(priv_off) + b"\x12"
    top_len = len(index([top(0, 0)]))
    base = len(header) + len(names) + top_len + len(strings) + len(gsubrs)
    cs_off = base
    priv_off = cs_off + len(chars)
    return header + names + index([top(cs_off, priv_off)]) + strings + gsubrs + chars + private + lsubrs

advances = [500, 400, 1000, 700, 300]
n_glyphs = len(charstrings)
head = struct.pack(">IIIIHHqqhhhhHHhhh", 0x10000, 0x10000, 0, 0x5F0F3CF5, 0, 1000, 0, 0, 0, 0, 1000, 1000, 0, 8, 2, 0, 0)
hhea = struct.pack(">Ihhh" + "H" + "hhh" + "hhh" + "hhhhh" + "H", 0x10000, 800, -200, 0, 1000, 0, 0, 1000, 1, 0, 0, 0, 0, 0, 0, 0, n_glyphs)
maxp = struct.pack(">IH", 0x5000, n_glyphs)
hmtx = b"".join(struct.pack(">Hh", a, 0) for a in advances)
# cmap format 4: ' ' -> 4, 'I' -> 1, 'L' -> 3, 'O' -> 2
segs = [(32, 32, 4 - 32), (73, 73, 1 - 73), (76, 76, 3 - 76), (79, 79, 2 - 79), (0xFFFF, 0xFFFF, 1)]
n = len(segs)
f4 = struct.pack(">HHHHHHH", 4, 16 + 8 * n, 0, 2 * n, 2, 1, 0)
f4 += b"".join(struct.pack(">H", s[1]) for s in segs) + b"\0\0"
f4 += b"".join(struct.pack(">H", s[0]) for s in segs)
f4 += b"".join(struct.pack(">h", ((s[2] + 32768) % 65536) - 32768) for s in segs)
f4 += b"\0\0" * n
cmap = struct.pack(">HHHHI", 0, 1, 3, 1, 12) + f4
tables = {b"CFF ": cff(), b"cmap": cmap, b"head": head, b"hhea": hhea, b"hmtx": hmtx, b"maxp": maxp}
out = struct.pack(">IHHHH", 0x4F54544F, len(tables), 0, 0, 0)
offset = 12 + 16 * len(tables)
body = b""
for tag in sorted(tables):
    data = tables[tag]
    out += tag + struct.pack(">III", 0, offset + len(body), len(data))
    body += data + b"\0" * ((4 - len(data) % 4) % 4)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiny.otf"), "wb").write(out + body)
