#!/usr/bin/env python3
"""Check optional graphics dependencies in native debug binaries, without opening a window.

The compile-cost gate is tools/speedcheck.py. These small probes also catch unused shader
families becoming reachable before a slower timing regression makes that visible.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "linux" or not shutil.which("nm"):
        print("graphics reachability: needs Linux nm")
        return 0
    asset = json.dumps(str(ROOT / "tests/render/pbr_skin.gltf"))
    cases = [
        ("2d", 'window("t", 320, 200)\ndraw = ():\n    rect(1, 2, 3, 4, RED)\n    text("hi", vec2(3, 3))\n',
         [], ["__render3d", "__post_init", "__pbr_fs", "lit_vs_skin", "__sky_filter_fs", "__vg_warm_vertex"]),
        ("2d_post", 'post_effects()\ndraw = (): rect(1, 2, 3, 4, RED)\n',
         ["__post_init"], ["__render3d", "__pbr_fs", "lit_vs_skin", "__sky_filter_fs", "__vg_warm_vertex"]),
        ("classic", 'box = cube_mesh()\ndraw = (): draw_mesh(box)\n',
         ["__render3d"], ["__pbr_fs", "lit_vs_skin", "__sky_filter_fs", "__sky_image_fs", "__vg_warm_vertex"]),
        ("gltf_data", f'd = read_gltf(embed({asset}))\nif d is ModelData: print(d.meshes.len())\n',
         [], ["__render3d", "__pbr_fs", "lit_vs_skin", "__sky_filter_fs", "__vg_prime_pipeline"]),
        ("pbr", 'box = cube_mesh()\ndraw = (): draw_mesh(box, material = Material(roughness = 0.5))\n',
         ["__pbr_fs"], ["lit_vs_skin", "__sky_filter_fs", "__vg_warm_vertex"]),
        ("sky_image", 't = texture(image(16, 8, WHITE))\nsky_image(t)\nbox = cube_mesh()\ndraw = (): draw_mesh(box)\n',
         ["__sky_image_fs", "__sky_filter_fs"], ["__pbr_fs", "lit_vs_skin", "__vg_warm_vertex"]),
    ]
    env = dict(os.environ, SLOPPY_LIB=str(ROOT / "lib"), SLOPPY_EMIT_WORKERS="1")
    with tempfile.TemporaryDirectory(prefix="sloppy-reachability-") as tmp:
        for name, code, present, absent in cases:
            source = Path(tmp) / (name + ".jo")
            exe = Path(tmp) / name
            source.write_text(code)
            build = subprocess.run([str(ROOT / "bin/sloppy"), "build", str(source), "-o", str(exe)],
                                   env=env, capture_output=True, text=True)
            if build.returncode:
                raise RuntimeError(build.stdout + build.stderr)
            symbols = set(line.split()[-1] for line in subprocess.check_output(["nm", str(exe)], text=True).splitlines() if line.split())
            assert all(s in symbols for s in present), (name, "missing", present)
            assert not symbols.intersection(absent), (name, "unneeded", symbols.intersection(absent))
            print("ok", name)
    print(f"{len(cases)} graphics reachability probes passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
