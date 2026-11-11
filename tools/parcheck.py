#!/usr/bin/env python3
"""Compare serial and forced parallel output, including debug information.
Usage: tools/parcheck.py [--compiler bin/sloppy] [--target native|linux-arm64|macos]
                        [--reference-compiler path/to/earlier/compiler]
                        [--workers 2|3|4] [source.jo ...]
Builds only; it does not run the output. Use TMPDIR to choose scratch storage.
"""
import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--compiler', default=str(root / 'bin/sloppy'),
                    help='compiler command (for example "qemu-aarch64 /path/to/sloppy")')
    ap.add_argument('--reference-compiler',
                    help='also require serial output to match this earlier compiler command')
    ap.add_argument('--target', action='append', choices=['native', 'linux-arm64', 'macos'])
    ap.add_argument('--workers', type=int, choices=[2, 3, 4], default=4)
    ap.add_argument('sources', nargs='*')
    args = ap.parse_args()
    sources = args.sources or ['compiler/main.jo', 'bench/big.jo',
                              'examples/rebound/rebound.jo', 'examples/breakwater/breakwater.jo',
                              'examples/cube.jo', 'tests/t/floats.jo', 'tests/t/closures.jo']
    if 'bench/big.jo' in sources and not (root / 'bench/big.jo').exists():
        subprocess.run([sys.executable, 'tools/genbench.py', '2000', 'bench/big'], cwd=root, check=True)
    env = dict(os.environ, SLOPPY_LIB=str(root / 'lib'), SLOPPY_PAR_TIME='1')
    # These diagnostic modes intentionally disable workers.
    for name in ['SLOPPY_EMIT_FORCE', 'SLOPPY_RASTAT', 'SLOPPY_RADUMP']:
        env.pop(name, None)
    count = 0
    with tempfile.TemporaryDirectory(prefix='sloppy-parcheck-') as tmp:
        # Keep the output path fixed too (Mach-O has an ad hoc signature identifier).
        out = Path(tmp) / 'program'
        serial = Path(tmp) / 'serial'
        for target in args.target or ['native', 'linux-arm64', 'macos']:
            for flags in [[], ['--release'], ['-g'], ['--release', '-g']]:
                for src in sources:
                    cmd = shlex.split(args.compiler) + ['build', src, '--target', target, '-o', str(out)] + flags
                    outputs = []
                    reference = None
                    if args.reference_compiler:
                        ref_cmd = shlex.split(args.reference_compiler) + cmd[len(shlex.split(args.compiler)):]
                        out.unlink(missing_ok=True)
                        result = subprocess.run(ref_cmd, cwd=root,
                                                env=dict(env, SLOPPY_EMIT_WORKERS='1'),
                                                capture_output=True, text=True, timeout=600)
                        if result.returncode or not out.exists():
                            raise SystemExit(f'FAIL reference {target} {src} {flags}:\n{result.stderr}')
                        reference = out.read_bytes()
                    for workers in [1, args.workers]:
                        run_env = dict(env, SLOPPY_EMIT_WORKERS=str(workers))
                        if workers != 1:
                            run_env['SLOPPY_EMIT_FORCE'] = '1'
                        out.unlink(missing_ok=True)
                        result = subprocess.run(cmd, cwd=root, env=run_env, capture_output=True,
                                                text=True, timeout=600)
                        label = f'{target} {src} {" ".join(flags)}'.rstrip()
                        if result.returncode or not out.exists():
                            raise SystemExit(f'FAIL {label}, {workers} workers:\n{result.stderr}')
                        if workers != 1:
                            emitted = len(re.findall(r'worker \d+\.\.\d+: emit ', result.stderr))
                            summary = re.search(r'emit: (\d+) workers,', result.stderr)
                            # A run cannot split a single large function, so fewer workers
                            # than requested is valid, but every run must really emit.
                            used = int(summary[1]) if summary else 0
                            if not 2 <= used <= workers or emitted != used:
                                raise SystemExit(f'FAIL {label}: workers did not all emit (fallback?)\n{result.stderr}')
                        outputs.append(out.read_bytes())
                        if workers == 1:
                            if reference is not None and reference != outputs[0]:
                                offset = next((i for i, (a, b) in enumerate(zip(reference, outputs[0]))
                                               if a != b), min(len(reference), len(outputs[0])))
                                raise SystemExit(f'FAIL {label}: serial differs from reference at {offset}, '
                                                 f'lengths {len(reference)}, {len(outputs[0])}')
                            serial.write_bytes(outputs[0])
                    if subprocess.run(['cmp', '-s', str(serial), str(out)]).returncode:
                        offset = next((i for i, (a, b) in enumerate(zip(*outputs)) if a != b),
                                      min(map(len, outputs)))
                        raise SystemExit(f'FAIL {label}: different bytes at {offset}, lengths {list(map(len, outputs))}')
                    print(f'PASS {label}: {len(outputs[0])} identical bytes', flush=True)
                    count += 1
    print(f'{count} serial/parallel comparisons passed (up to {args.workers} workers)')


if __name__ == '__main__':
    main()
