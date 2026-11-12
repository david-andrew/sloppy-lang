#!/usr/bin/env python3
"""Release function-value/loop counts (instructions:u), IR and binary size.
Usage: python3 bench/fnvalues/measure.py --compiler PATH --scratch DIR
"""
import argparse, json, os, re, statistics, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--compiler', type=Path, default=ROOT / 'bin/sloppy')
p.add_argument('--scratch', type=Path, default=Path.home() / 'dev/tmp/fnvalues/after')
a = p.parse_args()
s = a.scratch.expanduser().resolve()
s.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, TMPDIR=os.environ.get('TMPDIR', str(s / 'tmp')),
           SLOPPY_LIB=str(ROOT / 'lib'), SLOPPY_EMIT_WORKERS='1', SLOPPY_THREADS='1', DISPLAY='', WAYLAND_DISPLAY='')
Path(env['TMPDIR']).mkdir(parents=True, exist_ok=True)
def run(cmd):
    return subprocess.run([str(x) for x in cmd], cwd=ROOT, env=env,
                          capture_output=True, text=True, check=True)
c = (ROOT / 'tools/icount.c').read_text().replace('%.3f G instructions', '%.0f instructions').replace('count / 1e9', '(double)count')
(s / 'icount.c').write_text(c)
run(['cc', '-O2', '-o', s / 'icount', s / 'icount.c'])
r = run([a.compiler.resolve(), 'build', ROOT / 'bench/fnvalues/fnvalues.jo', '--release', '--ir', '-o', s / 'fnvalues'])
(s / 'fnvalues.ir').write_text(r.stdout)
results = {'bytes': (s / 'fnvalues').stat().st_size, 'benchmarks': {}}
for name in ('reduce', 'count', 'each', 'any', 'all', 'map', 'named_map', 'filter', 'map_sum', 'sort_by', 'parallel_range'):
    counts, outputs = {}, {}
    for mode in ('hof', 'loop'):
        samples = []
        for _ in range(3):
            r = run([s / 'icount', s / 'fnvalues', name, mode])
            samples.append(int(re.search(r'(\d+) instructions', r.stderr)[1]))
            outputs[mode] = r.stdout
        counts[mode] = int(statistics.median(samples))
        counts[mode + '_samples'] = samples
    assert outputs['hof'] == outputs['loop'], (name, outputs)
    results['benchmarks'][name] = counts
    print(f"{name:16} hof {counts['hof']:12,d} loop {counts['loop']:12,d} {counts['hof']/counts['loop']:.3f}x", flush=True)
(s / 'counts.json').write_text(json.dumps(results, indent=2) + '\n')
print(f"binary {results['bytes']} bytes; IR/counts: {s}")
