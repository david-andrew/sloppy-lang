#!/usr/bin/env python3
"""Exercise synthetic VX spills and AAPCS64 calls under QEMU (no target libc needed)."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='neon-backend-') as tmp:
    driver = Path(tmp) / 'driver'
    guest = Path(tmp) / 'guest'
    subprocess.run([str(root / 'bin/sloppy'), 'build', 'tests/neon_backend.jo',
                    '-o', str(driver)], cwd=root, check=True)
    subprocess.run([str(driver), str(guest)], cwd=root, check=True)
    subprocess.run(shlex.split(os.environ.get('SLOPPY_ARM64_RUN', 'qemu-aarch64'))
                   + [str(guest)], check=True)
print('NEON register pressure and full-width call spills passed')
