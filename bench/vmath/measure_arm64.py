#!/usr/bin/env python3
"""Compare ARM64 release guest instruction counts using QEMU's plugin API.

Example: --before ~/dev/tmp/neon/sloppy-before --after bin/sloppy
         --plugin-include ~/.pixi/envs/cross/include/qemu-aarch64
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--before', type=Path, required=True)
ap.add_argument('--after', type=Path, default=ROOT / 'bin/sloppy')
ap.add_argument('--plugin-include', type=Path, required=True)
ap.add_argument('--qemu', default=os.environ.get('SLOPPY_ARM64_RUN', 'qemu-aarch64'))
ap.add_argument('--scratch', type=Path, default=Path.home() / 'dev/tmp/neon')
ap.add_argument('--output', type=Path)
args = ap.parse_args()
scratch = args.scratch.expanduser().resolve()
scratch.mkdir(parents=True, exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
env = dict(os.environ, TMPDIR=str(scratch / 'tmp'), SLOPPY_LIB=str(ROOT / 'lib'),
           SLOPPY_EMIT_WORKERS='1', DISPLAY='', WAYLAND_DISPLAY='',
           SLOPPY_NO_AUDIO='1', SDL_AUDIODRIVER='dummy')


def run(cmd):
    return subprocess.run(list(map(str, cmd)), env=env, cwd=ROOT,
                          capture_output=True, text=True, check=True)


plugin = scratch / 'insn.so'
glib_flags = shlex.split(run(['pkg-config', '--cflags', 'glib-2.0']).stdout)
run(['cc', '-shared', '-fPIC', '-O2', *glib_flags, '-I', args.plugin_include,
     ROOT / 'bench/vmath/insn.c', '-o', plugin])
qemu = shlex.split(args.qemu)
results = {'host': os.uname().nodename, 'qemu': run(qemu + ['--version']).stdout.splitlines()[0],
           'counter': 'QEMU plugin: sum executed translated-block guest instruction counts',
           'N': 1024, 'R': 256, 'compilers': {}, 'kernels': {}}
executables = {}
for label, compiler in [('before', args.before), ('after', args.after)]:
    compiler = compiler.expanduser().resolve()
    exe = scratch / ('vmath-arm64-' + label)
    run([compiler, 'build', ROOT / 'bench/vmath/vmath.jo', '--release',
         '--target', 'linux-arm64', '-o', exe])
    executables[label] = exe
    results['compilers'][label] = {'path': str(compiler),
                                  'sha256': hashlib.sha256(compiler.read_bytes()).hexdigest()}
for mode in ['add', 'mul', 'dot', 'lerp', 'norm4', 'mv', 'mm',
             'cross', 'norm3', 'particle', 'vertex']:
    counts, outputs = {}, {}
    for label, exe in executables.items():
        # Keep argv[0] identical: even scanning a one-byte-longer filename adds
        # guest instructions during startup. Programs execute sequentially.
        runnable = scratch / 'vmath-arm64-run'
        shutil.copyfile(exe, runnable)
        runnable.chmod(0o755)
        r = run(qemu + ['-plugin', str(plugin), str(runnable), mode])
        counts[label] = int(re.search(r'guest instructions: (\d+)', r.stderr)[1])
        outputs[label] = r.stdout.strip()
    if outputs['before'] != outputs['after']:
        raise RuntimeError(f'{mode}: output differs: {outputs}')
    counts['output'] = outputs['after']
    results['kernels'][mode] = counts
    print(f"{mode:10} {counts['before']:12,d} -> {counts['after']:12,d} "
          f"{100 * (counts['after'] / counts['before'] - 1):+.2f}%", flush=True)
output = args.output or scratch / 'arm64-measurements.json'
output.write_text(json.dumps(results, indent=2) + '\n')
