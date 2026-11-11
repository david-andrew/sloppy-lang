#!/usr/bin/env python3
"""Audit emitted GLSL against WebGL2's guaranteed minimum resources, without a GPU.

Build library shaders, examples, render scenes, API examples and shader tests as Wasm.
Count declarations conservatively: one vec4 row per scalar/vector, matrix column or
array element (including nested structs). This bounds Appendix A packing; it is not
std140, and deliberately does not rely on a driver's dead-uniform elimination.
Usage: tools/webglbudget.py [--compiler PATH] [--json PATH] [source.jo ...]
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
QUAL = r"(?:(?:lowp|mediump|highp)\s+)?"
FIELD = re.compile(QUAL + r"(\w+)(?:\[(\d+)\])?\s+(\w+)(?:\[(\d+)\])?\s*;")


def audit(source):
    original = source
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    structs = dict(re.findall(r"struct\s+(\w+)\s*\{([^}]+)\}\s*;", source))

    def cost(ty, count=1):
        if ty in structs:
            rows = samplers = 0
            body = structs[ty]
            if FIELD.sub("", body).strip():
                raise ValueError(f"unsupported struct resource declaration: {body}")
            for ft, a, _, b in FIELD.findall(body):
                r, s = cost(ft, count * int(a or b or 1))
                rows += r
                samplers += s
            return rows, samplers
        if re.fullmatch(r"[iu]?sampler\w+", ty):
            return count, count
        if re.fullmatch(r"mat[234](?:x[234])?", ty):
            return int(ty[3]) * count, 0
        if re.fullmatch(r"float|int|uint|bool|[biu]?vec[234]", ty):
            return count, 0
        raise ValueError(f"unknown GLSL resource type: {ty}")

    vertex = bool(re.search(r"\bgl_Position\s*=", source))
    uniforms = samplers = varyings = attributes = 0
    resources = {}
    for ty, a, name, b in re.findall(r"^\s*uniform\s+" + FIELD.pattern, source, re.M):
        rows, tex = cost(ty, int(a or b or 1))
        uniforms += rows
        samplers += tex
        resources[name] = rows
    # Fail closed when the generated grammar changes rather than silently omit a declaration.
    uniform_lines = re.findall(r"^\s*uniform\b[^;]*;", source, re.M)
    if len(uniform_lines) != len(resources):
        raise ValueError("unsupported or duplicate uniform declaration")
    direction = "out" if vertex else "in"
    for ty, a, _, b in re.findall(r"^\s*(?:(?:flat|centroid)\s+)?" + direction + r"\s+" + FIELD.pattern, source, re.M):
        varyings += cost(ty, int(a or b or 1))[0]
    for loc, ty, a, _, b in re.findall(r"layout\s*\(location\s*=\s*(\d+)\)\s+in\s+" + FIELD.pattern, source):
        attributes = max(attributes, int(loc) + cost(ty, int(a or b or 1))[0])
    # Handwritten 2D shaders use named attributes without explicit locations.
    if vertex and not attributes:
        for ty, a, _, b in re.findall(r"^\s*in\s+" + FIELD.pattern, source, re.M):
            attributes += cost(ty, int(a or b or 1))[0]
    main = source[source.rfind("void main"):]
    name = re.search(r"\b(f_\w+)\(", main)
    identity = re.search(r"// sloppy shader: (.*)", original)
    counts = dict(uniforms=uniforms, samplers=samplers, varyings=varyings, attributes=attributes)
    # At most 16 samplers per stage also bounds the two-stage combined total by 32.
    limits = dict(uniforms=256 if vertex else 224, samplers=16, varyings=15, attributes=16)
    errors = [f"{key}: {counts[key]} > {limit}" for key, limit in limits.items() if counts[key] > limit]
    metadata = re.search(r"// sloppy resources: uniforms=(\d+) samplers=(\d+) varyings=(\d+) attributes=(\d+)", original)
    if metadata and tuple(map(int, metadata.groups())) != tuple(counts.values()):
        errors.append(f"compiler resource metadata disagrees with declarations: {metadata.groups()} != {counts}")
    return dict(name=identity[1] if identity else name[1] if name else "draw2d", stage="vertex" if vertex else "fragment", **counts, resources=resources, errors=errors)


def shaders(data):
    """Read complete generated sources from Wasm data, stopping at main's closing brace.

    Sloppy stores strings without a terminator; printable bytes after a source may
    belong to another string. Scanning through the end of main avoids counting those.
    """
    for start in re.finditer(rb"#version 300 es\n", data):
        main = data.find(b"void main", start.start())
        if main < 0:
            raise ValueError("shader has no main")
        opening = data.find(b"{", main)
        depth = 1
        end = opening + 1
        while depth:
            if end >= len(data):
                raise ValueError("unterminated GLSL main")
            depth += (data[end] == 123) - (data[end] == 125)
            end += 1
        yield data[start.start():end].decode("ascii") + "\n"


def programs():
    result = set()
    for pattern in ("examples/**/*.jo", "tests/render/*.jo", "tests/web/*.jo", "docs/api/*.jo", "lib/new/*.jo"):
        result.update(ROOT.glob(pattern))
    for p in (ROOT / "tests/t").glob("*.jo"):
        if any(word in p.read_text() for word in ("shader(", ".gpu")):
            result.add(p)
    return sorted(result)


def check_counter():
    # Independent packing fixtures: both legal array spellings, nested aggregates,
    # non-square matrices, samplers, centroid/flat varyings and matrix attributes.
    source = """#version 300 es
struct Inner { vec4[3] a; mat3x2 m; sampler2D t[2]; };
struct Outer { Inner[2] children; float scalar; };
uniform Outer u;
layout(location=2) in mat4 instance;
centroid out vec2 uv;
flat out ivec3 id;
void main() { gl_Position = vec4(0); }
"""
    counts = audit(source)
    assert [counts[k] for k in ("uniforms", "samplers", "varyings", "attributes")] == [17, 4, 2, 6], counts
    for declaration, key in (("uniform vec4 big[225];", "uniforms"),
                             ("uniform sampler2D t[17];", "samplers"),
                             ("in vec4 v[16];", "varyings")):
        result = audit(declaration + "\nvoid main() {}")
        assert any(e.startswith(key + ":") for e in result["errors"]), result
    try:
        audit("uniform mystery unknown;\nvoid main() {}")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown resource types must fail closed")


def main():
    check_counter()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compiler", default=str(ROOT / "bin/sloppy"))
    ap.add_argument("--json", type=Path)
    ap.add_argument("sources", nargs="*", type=Path)
    args = ap.parse_args()
    env = dict(os.environ, SLOPPY_LIB=str(ROOT / "lib"), SLOPPY_EMIT_WORKERS="1")
    results = []
    seen = set()
    failed = 0
    inputs = args.sources or programs()
    with tempfile.TemporaryDirectory(prefix="sloppy-webgl-") as tmp:
        library_env = env
        if not args.sources:
            # Private shader entries must be referenced inside their own module. Instrument
            # a scratch copy, leaving the checked-out library and shader bodies untouched.
            library = Path(tmp) / "lib"
            shutil.copytree(ROOT / "lib", library)
            calls = []
            for lib in sorted(library.rglob("*.jo")):
                original = lib.read_text()
                code = re.sub(r"#[^\n]*", "", original)
                pairs = sorted(set(re.findall(r"\bshader\(\s*(\w+)\s*,\s*(\w+)\s*\)", code)))
                if not pairs:
                    continue
                helper = f"__webgl_audit_{len(calls)}"
                calls.append(helper + "()\n")
                body = "".join(f"    s{i} = shader({v}, {f})\n    print(s{i}.vs, s{i}.fs)\n" for i, (v, f) in enumerate(pairs))
                lib.write_text(original + f"\n{helper} = ():\n" + body)
            manifest = Path(tmp) / "library_shaders.jo"
            manifest.write_text('pixel_art()\nprint(__VS2D, __FS2D)\n' + "".join(calls))
            inputs = [manifest, *inputs]
            library_env = dict(env, SLOPPY_LIB=str(library))
        for src in inputs:
            name = os.path.relpath(src, ROOT)
            out = Path(tmp) / "prog"
            run = subprocess.run([args.compiler, "build", "--target", "wasm", str(src), "-o", str(out)], env=library_env if src == inputs[0] and not args.sources else env, capture_output=True, text=True)
            if run.returncode:
                print(f"FAIL {name}: build failed\n{run.stderr}")
                failed += 1
                continue
            html = out.with_suffix(".html").read_text()
            embedded = re.search(r'const SLOPPY_WASM = "([^"]+)"', html)
            if not embedded:
                raise ValueError(f"{name}: no embedded Wasm")
            wasm = base64.b64decode(embedded[1])
            for source in shaders(wasm):
                if source in seen:
                    continue
                seen.add(source)
                try:
                    result = dict(program=name, **audit(source))
                    results.append(result)
                    if result["errors"]:
                        print(f"FAIL {name} {result['name']} {result['stage']}: {', '.join(result['errors'])}")
                        failed += 1
                except ValueError as e:
                    print(f"FAIL {name}: {e}")
                    failed += 1
    if not results:
        print("FAIL no GLSL sources found")
        failed += 1
    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n")
    print(f"{len(results)} WebGL2 stages from {len(inputs)} programs, {failed} failed")
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
