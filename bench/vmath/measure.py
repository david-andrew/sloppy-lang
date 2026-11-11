#!/usr/bin/env python3
"""Retired user instructions, three samples. Scratch defaults to ~/dev/tmp/simd."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--compiler', type=Path, default=ROOT / 'bin/sloppy')
ap.add_argument('--label', default='after')
ap.add_argument('--scratch', type=Path, default=Path.home() / 'dev/tmp/simd')
args = ap.parse_args()
scratch = args.scratch.expanduser().resolve()
if args.compiler.resolve() == scratch / args.label:
    ap.error('the output label must differ from the compiler path')
scratch.mkdir(parents=True, exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
env = dict(os.environ, TMPDIR=str(scratch / 'tmp'), SLOPPY_LIB=str(ROOT / 'lib'),
           SLOPPY_EMIT_WORKERS='1', SLOPPY_NO_AVX='1', DISPLAY='', WAYLAND_DISPLAY='',
           SLOPPY_NO_AUDIO='1', SDL_AUDIODRIVER='dummy')


def run(cmd):
    return subprocess.run(list(map(str, cmd)), env=env, cwd=ROOT,
                          capture_output=True, text=True, check=True)


def f32_values(output):
    output = re.sub(r'vec[234]', '', output)
    numbers = re.findall(r'[-+]?(?:[0-9]*[.])?[0-9]+(?:[eE][-+]?[0-9]+)?', output)
    return [struct.pack('f', float(x)) for x in numbers]


# Keep the project's counter; change only its printed precision in this scratch copy.
src = (ROOT / 'tools/icount.c').read_text()
src = src.replace('%.3f G instructions', '%.0f instructions')
src = src.replace('count / 1e9', '(double)count')
(scratch / 'icount.c').write_text(src)
run(['cc', '-O2', scratch / 'icount.c', '-o', scratch / 'icount'])
run(['cc', '-O2', '-ffp-contract=off', ROOT / 'bench/vmath/vmath.c',
     '-lm', '-o', scratch / 'vmath-c'])
r = run([args.compiler.resolve(), 'build', ROOT / 'bench/vmath/vmath.jo',
         '--release', '--ir', '-o', scratch / args.label])
(scratch / (args.label + '.ir')).write_text(r.stdout)
results = {
    'label': args.label, 'compiler': str(args.compiler.resolve()),
    'compiler_binary_sha256': hashlib.sha256(args.compiler.read_bytes()).hexdigest(),
    'revision': run(['git', 'rev-parse', 'HEAD']).stdout.strip(),
    'cc': run(['cc', '--version']).stdout.splitlines()[0],
    'host': os.uname().nodename, 'counter': 'perf_event_open instructions:u',
    'samples': 3, 'N': 1024, 'R': 256, 'kernels': {},
}
for mode in ['add', 'mul', 'dot', 'lerp', 'norm4', 'mv', 'mm',
             'cross', 'norm3', 'particle', 'vertex']:
    counts, outputs = {}, {}
    for name, exe in [('sloppy', scratch / args.label), ('c', scratch / 'vmath-c')]:
        samples = []
        for _ in range(3):
            r = run([scratch / 'icount', exe, mode])
            samples.append(int(re.search(r'(\d+) instructions', r.stderr)[1]))
            outputs[name] = r.stdout.strip()
        counts[name] = int(statistics.median(samples))
        counts[name + '_samples'] = samples
    if f32_values(outputs['sloppy']) != f32_values(outputs['c']):
        raise RuntimeError(f'{mode}: C output differs: {outputs}')
    counts['outputs'] = outputs
    results['kernels'][mode] = counts
    print(f"{mode:10} {counts['sloppy']:12,d} {counts['c']:12,d} "
          f"{counts['sloppy']/counts['c']:.3f}x {outputs}", flush=True)
(scratch / (args.label + '.json')).write_text(json.dumps(results, indent=2) + '\n')
