#!/usr/bin/env python3
"""Count ARM64 software frame 120 with QEMU; only a scratch library is instrumented.

Build insn.so with measure_arm64.py first. No target libc or display is required.
"""
import argparse
import hashlib
import importlib.util
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
ap.add_argument('--scratch', type=Path, required=True)
ap.add_argument('--plugin', type=Path, required=True)
ap.add_argument('--qemu', default='qemu-aarch64')
ap.add_argument('--objdump', default='aarch64-linux-gnu-objdump')
ap.add_argument('--games', nargs='+', choices=['aces', 'dunes', 'breakwater', 'rebound'],
                default=['aces', 'dunes', 'breakwater', 'rebound'])
ap.add_argument('--frame', type=int, default=120)
ap.add_argument('--output', type=Path)
a = ap.parse_args()
scratch = a.scratch.expanduser().resolve()
scratch.mkdir(parents=True, exist_ok=True)
(scratch / 'tmp').mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location('profile_games', ROOT / 'bench/games/profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
lib = scratch / 'lib'
if lib.exists():
    shutil.rmtree(lib)
shutil.copytree(ROOT / 'lib', lib)
osjo = lib / 'core/os.jo'
osjo.write_text(osjo.read_text().replace('time_ns = () -> int:',
    'time_ns = () -> int: 12345\n\n__gp_real_time_ns = () -> int:', 1))
win = lib / 'game/window.jo'
s = win.read_text()
s += '''
__gp_marker = 0
@noinline
__gp_begin = ():
    global __gp_marker
    __gp_marker = 1
@noinline
__gp_end = ():
    global __gp_marker
    __gp_marker = 2
'''
s = s.replace('__run_frame = (dt: f64, update: (f64) -> void, draw: () -> void):',
    '__run_frame = (dt: f64, update: (f64) -> void, draw: () -> void):\n'
    f'    if __frame_count == {a.frame}: __gp_begin()', 1)
s = s.replace('    __maybe_screenshot()\n',
    f'    if __frame_count == {a.frame}: __gp_end()\n    __maybe_screenshot()\n', 1)
win.write_text(s)
env = dict(os.environ, TMPDIR=os.environ.get('TMPDIR', str(scratch / 'tmp')), SLOPPY_LIB=str(lib),
    SLOPPY_EMIT_WORKERS='1', DISPLAY='', WAYLAND_DISPLAY='', SLOPPY_NO_AUDIO='1',
    SDL_AUDIODRIVER='dummy', SLOPPY_THREADS='1', SLOPPY_SOFTWARE='1',
    SLOPPY_WINDOW='320x180', SLOPPY_SCALE='1', SLOPPY_SOFT_SCALE='0.5',
    SLOPPY_SEED='12345', SLOPPY_FRAMES=str(a.frame + 2))
results = {'host': os.uname().nodename, 'frame': a.frame,
    'counter': 'QEMU translated-block guest instructions between marker entries',
    'window': '320x180', 'soft_scale': 0.5, 'compilers': {}, 'games': {}}
for label, compiler in [('before', a.before), ('after', a.after)]:
    compiler = compiler.expanduser().resolve()
    results['compilers'][label] = {'path': str(compiler),
        'sha256': hashlib.sha256(compiler.read_bytes()).hexdigest()}
    for game in a.games:
        exe = scratch / 'game-run'
        source = ROOT / profile.GAMES[game]
        r = subprocess.run([str(compiler), 'build', str(source), '--target', 'linux-arm64',
            '-o', str(exe)], env=env, capture_output=True, text=True, check=True)
        shutil.copyfile(exe, scratch / f'{game}-{label}')
        symbols = subprocess.run([a.objdump, '-t', str(exe)],
            capture_output=True, text=True, check=True).stdout
        markers = [int(re.search(r'^([0-9a-f]+).*\b' + name + '$', symbols, re.M)[1], 16)
            for name in ['__gp_begin', '__gp_end']]
        state = scratch / 'state'
        shutil.rmtree(state, ignore_errors=True)
        state.mkdir()
        png = state / 'last.png'
        runenv = dict(env, SLOPPY_INPUT=profile.INPUT[game],
            SLOPPY_SAVE_DIR=str(state / 'saves'), SLOPPY_SCREENSHOT=str(png))
        print('RUN', label, game, flush=True)
        r = subprocess.run(shlex.split(a.qemu) + ['-plugin',
            f'{a.plugin.resolve()},begin={markers[0]},end={markers[1]}', str(exe)],
            cwd=source.parent, env=runenv, capture_output=True, text=True, timeout=1800)
        (scratch / f'{game}-{label}.log').write_text(r.stdout + r.stderr)
        r.check_returncode()
        count = int(re.search(r'guest instructions: (\d+)', r.stderr)[1])
        digest = hashlib.sha256(png.read_bytes()).hexdigest()
        if count <= 0 or 'guest frame markers: 1/1' not in r.stderr:
            raise RuntimeError(f'{game}: empty sample or missing/repeated frame markers')
        result = results['games'].setdefault(game, {})
        result[label] = count
        result[label + '_png_sha256'] = digest
        if label == 'after' and digest != result['before_png_sha256']:
            raise RuntimeError(f'{game}: rendered output differs')
        print('DONE', label, game, count, digest, flush=True)
        (a.output or scratch / 'games.json').write_text(json.dumps(results, indent=2) + '\n')
