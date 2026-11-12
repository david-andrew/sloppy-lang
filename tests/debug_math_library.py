#!/usr/bin/env python3
"""Custom math definitions must bypass debug helper specialization.

Run with TMPDIR set to scratch and --compiler pointing to the compiler to check.
Only a temporary library copy is changed.
"""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--compiler', type=Path, default=ROOT / 'bin/sloppy')
ap.add_argument('--target', choices=['native', 'linux-arm64'], default='native')
a = ap.parse_args()
compiler = a.compiler.resolve()
runner = (shlex.split(os.environ.get('SLOPPY_ARM64_RUN', 'qemu-aarch64'))
          if a.target == 'linux-arm64' else [])
with tempfile.TemporaryDirectory(prefix='debug-math-library-') as tmp:
    tmp = Path(tmp)
    lib = tmp / 'lib'
    shutil.copytree(ROOT / 'lib', lib)
    core = lib / 'core/math.jo'
    vectors = lib / 'game/vmath.jo'
    original_core = core.read_text()
    core.write_text(original_core.replace(
        'abs = (x: f32) -> f32:\n    if x < 0.0: return -x\n    x',
        'abs = (x: f32) -> f32: x + 7.0', 1).replace(
        'min = (a: f32, b: f32) -> f32:\n    if a < b: return a\n    b',
        'min = (a: f32, b: f32) -> f32: 42.0', 1))
    src = tmp / 'probe.jo'
    src.write_text('''v = abs(vec3(-1, -2, 3))
assert(v.x == 6.0 and v.y == 5.0 and v.z == 10.0)
v = min(vec3(1), vec3(2))
assert(v.x == 42.0 and v.y == 42.0 and v.z == 42.0)
print("core ok")
''')
    env = dict(os.environ, SLOPPY_LIB=str(lib), SLOPPY_EMIT_WORKERS='1')

    def check(expected):
        for flags in [[], ['-g'], ['--release']]:
            exe = tmp / 'probe'
            r = subprocess.run([str(compiler), 'build', str(src), *flags,
                                '--target', a.target,
                                '-o', str(exe)], env=env, capture_output=True, text=True)
            if r.returncode:
                raise RuntimeError(r.stderr)
            r = subprocess.run([*runner, str(exe)], env=env, capture_output=True, text=True)
            if r.returncode or r.stdout != expected:
                raise RuntimeError(f'{flags}: {r.stdout}{r.stderr}')
            print(f'PASS {expected.strip()} {flags}', flush=True)

    check('core ok\n')
    core.write_text(original_core)
    vectors.write_text(vectors.read_text().replace(
        'dot = (a: vec3, b: vec3) -> f32: a.x * b.x + a.y * b.y + a.z * b.z',
        'dot = (a: vec3, b: vec3) -> f32: 42.0', 1).replace(
        'mix = (a: vec3, b: vec3, t: f32) -> vec3: a + (b - a) * t',
        'mix = (a: vec3, b: vec3, t: f32) -> vec3: a + b * t', 1))
    src.write_text('''assert(dot(vec3(1), vec3(2)) == 42.0)
v = mix(vec3(1), vec3(3), f32(0.25))
assert(v.x == 1.75 and v.y == 1.75 and v.z == 1.75)
print("vectors ok")
''')
    check('vectors ok\n')
print('6 custom-library checks passed')
