#!/usr/bin/env python3
"""Compare host instructions compiling ARM64 debug programs; fail above 1% per input."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--before', type=Path, required=True)
ap.add_argument('--after', type=Path, default=ROOT / 'bin/sloppy')
ap.add_argument('--scratch', type=Path, required=True)
ap.add_argument('--output', type=Path)
a = ap.parse_args()
scratch = a.scratch.expanduser().resolve()
scratch.mkdir(parents=True, exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
env = dict(os.environ, TMPDIR=os.environ.get('TMPDIR', str(scratch / 'tmp')), SLOPPY_LIB=str(ROOT / 'lib'),
           SLOPPY_EMIT_WORKERS='1', DISPLAY='', WAYLAND_DISPLAY='')

def run(cmd):
    return subprocess.run(list(map(str, cmd)), cwd=ROOT, env=env,
                          capture_output=True, text=True, check=True)

source = (ROOT / 'tools/icount.c').read_text().replace('%.3f G instructions', '%.0f instructions')
source = source.replace('count / 1e9', '(double)count')
(scratch / 'icount.c').write_text(source)
run(['cc', '-O2', scratch / 'icount.c', '-o', scratch / 'icount'])
if not (ROOT / 'bench/big.jo').exists():
    run(['python3', 'tools/genbench.py', '2000', 'bench/big'])
results = {'host': os.uname().nodename, 'counter': 'perf_event_open instructions:u',
    'samples': 3, 'emit_workers': 1, 'compilers': {}, 'builds': {}}
compilers = [('before', a.before.expanduser().resolve()), ('after', a.after.expanduser().resolve())]
for label, compiler in compilers:
    results['compilers'][label] = {'path': str(compiler),
        'sha256': hashlib.sha256(compiler.read_bytes()).hexdigest()}
worst = 0
for target in ['linux-arm64', 'macos']:
    for src in ['bench/big.jo', 'compiler/main.jo', *[
            f'examples/{game}/{game}.jo' for game in ['rebound', 'breakwater', 'aces', 'dunes']]]:
        entry = {}
        # Alternate the two compilers; use the same source, library and output filename.
        for _ in range(3):
            for label, compiler in compilers:
                r = run([scratch / 'icount', compiler, 'build', src, '--target', target,
                         '-o', scratch / 'program'])
                entry.setdefault(label + '_samples', []).append(
                    int(re.search(r'(\d+) instructions', r.stderr)[1]))
        for label, _ in compilers:
            entry[label] = statistics.median(entry[label + '_samples'])
        entry['change_percent'] = (entry['after'] / entry['before'] - 1) * 100
        worst = max(worst, entry['change_percent'])
        results['builds'][target + ' ' + src] = entry
        print(target, src, entry['before'], '->', entry['after'],
              f"{entry['change_percent']:+.3f}%", flush=True)
results['worst_regression_percent'] = worst
(a.output or scratch / 'compile.json').write_text(json.dumps(results, indent=2) + '\n')
if worst > 1:
    raise SystemExit(f'compile instructions regressed {worst:.3f}% (limit 1%)')
