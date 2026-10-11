#!/usr/bin/env python3
"""SPIR-V test: build every program with shaders (the examples, the render scenes, the library's
examples), keeping the SPIR-V the compiler makes for Vulkan (SLOPPY_SPIRV_DUMP), and check each
module with spirv-val (from SPIRV-Tools) as a Vulkan 1.3 driver with scalar block layout sees it.
usage: spirvtest.py   (skips, and passes, when spirv-val is not installed)"""
import glob, os, shutil, subprocess, sys, tempfile

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sloppy = os.path.join(root, "bin", "sloppy.exe" if os.name == "nt" else "sloppy")
val = shutil.which("spirv-val")
if not val:
    print("spirv-val not found: skipped")
    sys.exit(0)
programs = sorted(glob.glob(os.path.join(root, "examples", "*.jo")) + glob.glob(os.path.join(root, "examples", "*", "*.jo"))
                  + glob.glob(os.path.join(root, "tests", "render", "*.jo")) + glob.glob(os.path.join(root, "docs", "api", "*.jo")))
out = tempfile.mkdtemp(prefix="sloppy-spirv-")
env = dict(os.environ, SLOPPY_LIB=os.path.join(root, "lib"))
failed = 0
modules = 0
seen = set()
for src in programs:
    name = os.path.relpath(src, root)
    d = os.path.join(out, name.replace(os.sep, "_"))
    os.makedirs(d)
    r = subprocess.run([sloppy, "build", src, "-o", os.path.join(d, "prog")], env=dict(env, SLOPPY_SPIRV_DUMP=d), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {name}: build failed\n{r.stderr}")
        failed += 1
        continue
    for spv in sorted(glob.glob(os.path.join(d, "*.spv"))):
        data = open(spv, "rb").read()
        if data in seen: continue
        seen.add(data)
        modules += 1
        v = subprocess.run([val, "--target-env", "vulkan1.3", "--scalar-block-layout", spv], capture_output=True, text=True)
        if v.returncode != 0:
            print(f"FAIL {name}: {os.path.basename(spv)}\n{v.stdout}{v.stderr}")
            failed += 1
shutil.rmtree(out, ignore_errors=True)
print(f"{modules} SPIR-V modules from {len(programs)} programs, {failed} failed")
sys.exit(1 if failed else 0)
