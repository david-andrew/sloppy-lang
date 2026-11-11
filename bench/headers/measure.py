#!/usr/bin/env python3
"""Measure the nine header kernels in instructions, never wall time.

Usage: python3 bench/headers/measure.py [--compiler bin/sloppy] [--scratch DIR]
Artifacts and exact counts are written below --scratch (default ~/dev/tmp/hoist).
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--compiler', type=Path, default=ROOT / 'bin/sloppy')
ap.add_argument('--scratch', type=Path, default=Path.home() / 'dev/tmp/hoist')
args = ap.parse_args()
scratch = args.scratch.expanduser().resolve()
scratch.mkdir(parents=True, exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
env = dict(os.environ, TMPDIR=str(scratch / 'tmp'), SLOPPY_LIB=str(ROOT / 'lib'),
           SLOPPY_EMIT_WORKERS='1', DISPLAY='', WAYLAND_DISPLAY='')


def run(cmd):
    return subprocess.run([str(x) for x in cmd], env=env, cwd=ROOT,
                          capture_output=True, text=True, check=True)


# Keep the project's counter implementation; only print its count without rounding
# to 0.001G. The scratch copy leaves tools/icount.c unchanged.
src = (ROOT / 'tools/icount.c').read_text()
src = src.replace('%.3f G instructions', '%.0f instructions')
src = src.replace('count / 1e9', '(double)count')
(scratch / 'icount.c').write_text(src)
cc = os.environ.get('CC', 'cc')
run([cc, '-O2', '-o', scratch / 'icount', scratch / 'icount.c'])
run([cc, '-O2', '-o', scratch / 'headers-c', ROOT / 'bench/headers/headers.c'])
r = run([args.compiler.resolve(), 'build', ROOT / 'bench/headers/headers.jo',
         '--release', '--ir', '-o', scratch / 'headers-sloppy'])
(scratch / 'headers.ir').write_text(r.stdout)
for name in ('sloppy', 'c'):
    (scratch / f'{name}.asm').write_text(run(['objdump', '-d', scratch / f'headers-{name}']).stdout)

# Probe without starting any measured workload twice.
r = subprocess.run([str(scratch / 'icount'), '/bin/true'], env=env,
                   capture_output=True, text=True)
use_callgrind = 'perf_event_open' in r.stderr
if r.returncode and not use_callgrind:
    raise RuntimeError(r.stderr)
engine = 'callgrind' if use_callgrind else 'perf_event_open instructions:u'
results = {'counter': engine, 'samples': 3, 'kernels': {}}
for kernel in ('matrix', 'stencil', 'histogram'):
    for origin in ('param', 'local', 'global'):
        mode = f'{kernel}_{origin}'
        counts, outputs = {}, {}
        for name in ('sloppy', 'c'):
            samples = []
            for _ in range(3):
                exe = scratch / f'headers-{name}'
                if use_callgrind:
                    r = run(['valgrind', '--tool=callgrind', '--callgrind-out-file=' +
                             str(scratch / 'count.callgrind'), exe, mode])
                    m = re.search(r'^summary: (\d+)', (scratch / 'count.callgrind').read_text(), re.M)
                else:
                    r = run([scratch / 'icount', exe, mode])
                    m = re.search(r'(\d+) instructions', r.stderr)
                if not m:
                    raise RuntimeError(r.stderr)
                samples.append(int(m[1]))
                outputs[name] = float(r.stdout.strip())
            counts[name] = int(statistics.median(samples))
            counts[name + '_samples'] = samples
        if not math.isclose(outputs['sloppy'], outputs['c'], rel_tol=1e-10, abs_tol=1e-15):
            raise RuntimeError(f'{mode}: output mismatch: {outputs}')
        results['kernels'][mode] = counts
        print(f"{mode:18} Sloppy {counts['sloppy']:12,d}  C {counts['c']:12,d}  "
              f"{counts['sloppy'] / counts['c']:.3f}x", flush=True)
(scratch / 'counts.json').write_text(json.dumps(results, indent=2) + '\n')
print(f'{engine}; outputs match C in all nine cases; artifacts: {scratch}')
