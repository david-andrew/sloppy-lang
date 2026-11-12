#!/usr/bin/env python3
"""Generate original CC0 test fonts; requires fontTools. No third-party font outlines.
All advances are 600 units (space 300), at 1000 units/em. Each file is about 1 KB.
The separate fixtures pin legacy kern, GPOS pairs, classes, and extension lookups.
"""
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0

OUT = Path(__file__).resolve().parent
ORDER = ['.notdef', 'space', 'A', 'V', 'W', 'T', 'o', 'a', 'eacute']
SHAPES = {
    'A': [[(30, 0), (240, 700), (360, 700), (570, 0), (450, 0), (300, 520), (150, 0)]],
    'V': [[(20, 700), (150, 700), (300, 160), (450, 700), (580, 700), (360, 0), (240, 0)]],
    'W': [[(20, 700), (120, 700), (200, 180), (260, 500), (340, 500), (400, 180), (480, 700), (580, 700), (480, 0), (360, 0), (300, 300), (240, 0), (120, 0)]],
    'T': [[(20, 700), (580, 700), (580, 600), (360, 600), (360, 0), (240, 0), (240, 600), (20, 600)]],
    'o': [[(80, 0), (80, 480), (520, 480), (520, 0)], [(190, 100), (410, 100), (410, 380), (190, 380)]],
    'a': [[(100, 0), (100, 300), (400, 300), (400, 400), (100, 400), (100, 480), (510, 480), (510, 0)], [(210, 80), (400, 80), (400, 220), (210, 220)]],
    'eacute': [[(80, 0), (80, 480), (520, 480), (520, 0)], [(200, 550), (320, 700), (450, 700), (330, 550)]]}

def font():
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(ORDER)
    fb.setupCharacterMap({32:'space', **{ord(c):c for c in 'AVWToa'}, 233:'eacute'})
    glyphs = {}
    for name in ORDER:
        pen = TTGlyphPen(None)
        for contour in SHAPES.get(name, []):
            pen.moveTo(contour[0])
            for point in contour[1:]: pen.lineTo(point)
            pen.closePath()
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({g: (300 if g == 'space' else 600, 0) for g in ORDER})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({'familyName':'Sloppy Kerning Test', 'styleName':'Regular',
                       'copyright':'Original test outlines dedicated to the public domain (CC0-1.0).'})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    fb.font['head'].created = fb.font['head'].modified = 2082844800
    fb.font.recalcTimestamp = False
    return fb.font

def legacy(f, pairs):
    table = newTable('kern'); table.version = 0
    sub = KernTable_format_0(); sub.version = 0; sub.coverage = 1; sub.kernTable = pairs
    table.kernTables = [sub]; f['kern'] = table

f = font()
legacy(f, {('A','V'):-100, ('T','o'):-70, ('T','a'):-50, ('eacute','V'):-40})
f.save(OUT / 'kern.ttf')
for name, features in {
    'gpos-pairs': 'pos A V -120; pos T o -80; pos T a -60; pos eacute V -40;',
    'gpos-classes': '@L = [A T]; @R = [V W]; lookup Classes { pos @L @R -90; pos @L [o a] -70; } Classes; lookup Extra { pos A V -10; } Extra;',
    'gpos-extension': 'lookup Extended useExtension { pos A V -120; pos T o -80; pos T a -60; } Extended;',
    'gpos-extension-classes': '@L = [A T]; @R = [V W]; lookup Extended useExtension { pos @L @R -90; } Extended;',
    'gpos-values': 'pos A <10 0 -100 0> V <20 0 -30 0>; pos V <30 0 -200 0> A <40 0 -50 0>;',
}.items():
    f = font()
    addOpenTypeFeaturesFromString(f, 'languagesystem DFLT dflt; feature kern { ' + features + ' } kern;')
    legacy(f, {('A','V'):-999})  # GPOS takes precedence, including its zero/missing pairs.
    f.save(OUT / (name + '.ttf'))
    print(name, [(l.LookupType, [getattr(s, 'Format', None) for s in l.SubTable]) for l in f['GPOS'].table.LookupList.Lookup])
