#!/usr/bin/env python3
"""Bake the default SDF font atlas used by Sloppy's text rendering: ASCII 32..126 in its first
cells, then Latin-1 (accented letters: é, ñ, ü, ...), common punctuation (€, curly quotes,
dashes, ...), Greek, and what science and maths write (− √ ≈ ≤ ∞ ∑ ∫ ∂, arrows, sub- and
superscript digits, ✓ ✗). Characters Noto Sans lacks come from Noto Sans Math, then Noto Sans
Symbols 2 (all under the SIL Open Font License, as Noto Sans).
Output: lib/game/assets/font.png (grayscale SDF atlas) + font.txt (metrics; its third line is
the code point of each cell after the ASCII ones)."""
import sys, math
from PIL import Image, ImageDraw, ImageFont

FONT = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf"
FALLBACKS = ["/usr/share/fonts/google-noto/NotoSansMath-Regular.ttf", "/usr/share/fonts/google-noto/NotoSansSymbols2-Regular.ttf"]
OUT = sys.argv[2] if len(sys.argv) > 2 else "lib/game/assets/font"
CELL = 48          # output cell size
SCALE = 4          # supersampling factor for the distance computation
SPREAD = 6.0       # distance (output pixels) mapped to the full 0..255 range
PX = 34            # font size in output pixels

font = ImageFont.truetype(FONT, PX * SCALE)
try: font.set_variation_by_name("Medium")
except Exception: pass
fallbacks = [ImageFont.truetype(f, PX * SCALE) for f in FALLBACKS]

# (whether a font draws the character, not its missing-glyph box)
def has(f, ch):
    m = f.getmask(ch)
    n = f.getmask(chr(0x10FFFD))
    return m.getbbox() is not None and (bytes(m) != bytes(n) or m.size != n.size)

def font_for(ch):
    if has(font, ch): return font
    for f in fallbacks:
        if has(f, ch): return f
    return font
ascent, descent = font.getmetrics()
H = CELL * SCALE
INF = 1e9

def edt(inside, w, h):
    """distance (in hi-res px) from each pixel to the nearest pixel whose state differs"""
    # 8SSEDT: grid of offset vectors
    g = [[(0, 0) if not inside[y][x] else (INF, INF) for x in range(w)] for y in range(h)]
    def d2(p): return p[0] * p[0] + p[1] * p[1]
    def cmp(grid, x, y, ox, oy):
        nx, ny = x + ox, y + oy
        if 0 <= nx < w and 0 <= ny < h:
            o = grid[ny][nx]
            c = (o[0] + ox, o[1] + oy)
            if d2(c) < d2(grid[y][x]): grid[y][x] = c
    for y in range(h):
        for x in range(w):
            cmp(g, x, y, -1, 0); cmp(g, x, y, 0, -1); cmp(g, x, y, -1, -1); cmp(g, x, y, 1, -1)
        for x in range(w - 1, -1, -1): cmp(g, x, y, 1, 0)
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            cmp(g, x, y, 1, 0); cmp(g, x, y, 0, 1); cmp(g, x, y, -1, 1); cmp(g, x, y, 1, 1)
        for x in range(w): cmp(g, x, y, -1, 0)
    return [[math.sqrt(d2(g[y][x])) for x in range(w)] for y in range(h)]

# (ASCII first: the cells of 32..126 are their code - 32, as wayland.jo's title bar assumes)
CODES = list(range(32, 127)) + list(range(161, 256)) + [0x2018, 0x2019, 0x201C, 0x201D, 0x2013, 0x2014,
    0x2026, 0x2022, 0x20AC, 0x2122]
# Greek, capitals and small (no capital final sigma: 0x3A2)
CODES += list(range(0x391, 0x3A2)) + list(range(0x3A3, 0x3AA)) + list(range(0x3B1, 0x3CA))
# − √ ≈ ≠ ≤ ≥ ∞ ∑ ∫ ∂ ∝ ⋅ ∇ ∈, arrows, ⁰ ⁴-⁹ ⁺ ⁻ (¹ ² ³ are Latin-1's), ₀-₉, ′ ″, ✓ ✗
CODES += [0x2212, 0x221A, 0x2248, 0x2260, 0x2264, 0x2265, 0x221E, 0x2211, 0x222B, 0x2202, 0x221D, 0x22C5, 0x2207, 0x2208,
    0x2190, 0x2191, 0x2192, 0x2193, 0x2194, 0x2070] + list(range(0x2074, 0x207C)) + list(range(0x2080, 0x208A)) + [0x2032, 0x2033, 0x2713, 0x2717]
CODES = list(dict.fromkeys(CODES))
cols = 16
rows = (len(CODES) + cols - 1) // cols
atlas = Image.new("L", (cols * CELL, rows * CELL), 0)
metrics = []
baseline = int(CELL * 0.76)
for i, code in enumerate(CODES):
    ch = chr(code)
    img = Image.new("L", (H, H), 0)
    d = ImageDraw.Draw(img)
    f = font_for(ch)
    adv = f.getlength(ch) / SCALE
    # draw so that the baseline is at `baseline` and the glyph starts at x = SPREAD
    x0 = SPREAD * SCALE
    d.text((x0, baseline * SCALE), ch, font=f, fill=255, anchor="ls")
    px = img.load()
    inside = [[px[x, y] > 127 for x in range(H)] for y in range(H)]
    outside = [[not v for v in row] for row in inside]
    dout = edt(inside, H, H)     # distance to ink for outside pixels
    din = edt(outside, H, H)     # distance to background for inside pixels
    cell = Image.new("L", (CELL, CELL))
    cp = cell.load()
    for y in range(CELL):
        for x in range(CELL):
            sx, sy = x * SCALE + SCALE // 2, y * SCALE + SCALE // 2
            dist = (dout[sy][sx] - din[sy][sx]) / SCALE   # positive inside the glyph
            v = 128 + dist / SPREAD * 127
            cp[x, y] = max(0, min(255, int(round(v))))
    atlas.paste(cell, ((i % cols) * CELL, (i // cols) * CELL))
    metrics.append(adv)
    print(f"\rglyph {i + 1}/{len(CODES)}", end="", file=sys.stderr)
atlas.save(OUT + ".png", optimize=True)
with open(OUT + ".txt", "w") as f:
    f.write(f"{CELL} {cols} {rows} {baseline} {SPREAD} {PX} {ascent / SCALE:.2f} {descent / SCALE:.2f}\n")
    f.write(" ".join(f"{a:.3f}" for a in metrics) + "\n")
    f.write(" ".join(str(c) for c in CODES[95:]) + "\n")
print("\ndone", file=sys.stderr)
