#!/usr/bin/env python3
"""Measure compile work with one and four emit workers, including child instructions.

Unlike speedcheck, this exercises the normal fork threshold. Builds only, one at a
time. Diagnostic elapsed phase times are recorded, not treated as benchmark results
on a shared host. Set TMPDIR to choose scratch storage.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', default=str(root / 'bin/sloppy'))
    ap.add_argument('--base-compiler', help='optional earlier compiler command')
    ap.add_argument('--workers', type=int, choices=[1, 2, 3, 4], action='append')
    ap.add_argument('--repeat', type=int, default=3)
    ap.add_argument('--release', action='store_true', help='also measure --release builds')
    ap.add_argument('--env', action='append', default=[], metavar='NAME=VALUE',
                    help='environment override for the new compiler only; repeatable')
    ap.add_argument('--common-env', action='append', default=[], metavar='NAME=VALUE',
                    help='environment override for both compilers; repeatable')
    ap.add_argument('--json', type=Path, help='write measurements, commands and raw phase diagnostics')
    ap.add_argument('sources', nargs='*')
    args = ap.parse_args()
    if args.repeat < 1:
        ap.error('--repeat must be positive')
    def env_values(items):
        values = {}
        for item in items:
            key, sep, value = item.partition('=')
            if not sep or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', key):
                ap.error('environment overrides require NAME=VALUE')
            if key in ('SLOPPY_EMIT_WORKERS', 'SLOPPY_EMIT_FORCE'):
                ap.error('worker count and the normal fork threshold are controlled by parbench')
            values[key] = value
        return values
    overrides = env_values(args.env)
    common_overrides = env_values(args.common_env)
    counter = root / 'tools/icount'
    if not counter.exists():
        subprocess.run(['cc', '-O2', '-o', str(counter), str(root / 'tools/icount.c')], check=True)
    if not args.sources and not (root / 'bench/big.jo').exists():
        subprocess.run(['python3', 'tools/genbench.py', '2000', 'bench/big'], cwd=root, check=True)
    env = dict(os.environ, SLOPPY_LIB=str(root / 'lib'), SLOPPY_PAR_TIME='1')
    for key in ('SLOPPY_EMIT_FORCE', 'SLOPPY_RASTAT', 'SLOPPY_RADUMP'):
        env.pop(key, None)
    env.update(common_overrides)
    compilers = [('new', args.compiler)]
    if args.base_compiler:
        compilers.insert(0, ('base', args.base_compiler))
    report = {'host': os.uname().nodename, 'unit': 'G retired user instructions, including children',
              'common_environment_overrides': common_overrides,
              'note': 'Phase milliseconds are scheduling-sensitive diagnostics, not speedup measurements. '
                      'Default mode honors each source build block (compiler/main.jo selects release).',
              'measurements': []}
    with tempfile.TemporaryDirectory(prefix='sloppy-parbench-') as tmp:
        tmp = Path(tmp)
        (tmp / 'hello.jo').write_text('print("hi")\n')
        (tmp / 'game.jo').write_text('window("t", 320, 200)\ndraw = ():\n'
                                   '    clear(BLACK)\n    rect(1, 2, 3, 4, RED)\n'
                                   '    text("hi", vec2(3, 3), 12, WHITE)\n')
        sources = args.sources or ['bench/big.jo', 'compiler/main.jo',
                                  'examples/rebound/rebound.jo', 'examples/breakwater/breakwater.jo',
                                  str(tmp / 'hello.jo'), str(tmp / 'game.jo')]
        for source in sources:
            for flags in [[], ['--release']] if args.release else [[]]:
                for label, compiler in compilers:
                    for workers in args.workers or [1, 4]:
                        run_env = dict(env, **(overrides if label == 'new' else {}))
                        run_env['SLOPPY_EMIT_WORKERS'] = str(workers)
                        command = shlex.split(compiler) + ['build', source, '--time', '-o', str(tmp / 'program'), *flags]
                        samples = []
                        for _ in range(args.repeat):
                            p = subprocess.run([str(counter), *command], cwd=root, env=run_env,
                                               capture_output=True, text=True, timeout=600)
                            counted = re.search(r'^([\d.]+) G instructions(?:, ([\d.]+) G cycles)?$',
                                                p.stderr, re.MULTILINE)
                            if p.returncode or not counted:
                                raise SystemExit(f'cannot measure {shlex.join(command)}:\n{p.stderr}')
                            summary = re.search(r'emit: (\d+) workers,', p.stderr)
                            used = int(summary[1]) if summary else 1
                            emitted = len(re.findall(r'worker \d+\.\.\d+: emit ', p.stderr))
                            if (summary and (not 2 <= used <= workers or emitted != used)) or (not summary and emitted):
                                raise SystemExit(f'worker fallback or inconsistent counts: {shlex.join(command)}:\n{p.stderr}')
                            phases = {name: int(count) for name, count in
                                      re.findall(r'^PHASE (\w+) (\d+) instructions', p.stderr, re.MULTILINE)}
                            samples.append({'instructions_G': float(counted[1]), 'workers_used': used,
                                            'reported_phase_instructions': phases, 'stderr': p.stderr})
                        name = Path(source).name if str(source).startswith(str(tmp)) else source
                        row = {'source': name, 'flags': flags, 'compiler': label,
                               'workers_requested': workers, 'command': command,
                               'environment_overrides': overrides if label == 'new' else {},
                               'instructions_G': statistics.median(x['instructions_G'] for x in samples),
                               'workers_used': sorted(set(x['workers_used'] for x in samples)),
                               'samples': samples}
                        report['measurements'].append(row)
                        if args.json:
                            args.json.write_text(json.dumps(report, indent=2) + '\n')
                        print(f'{label:4} {name:44} {"release" if flags else "default":7} '
                              f'{workers} requested / {row["workers_used"]} used: '
                              f'{row["instructions_G"]:.3f} G instructions', flush=True)
    if not args.json:
        print('Use --json PATH to retain raw SLOPPY_PAR_TIME/--time diagnostics and optional PHASE counters.')


if __name__ == '__main__':
    main()
