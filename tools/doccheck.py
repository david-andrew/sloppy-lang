#!/usr/bin/env python3
"""Check user-facing Sloppy examples, without executing them or accessing packages online.

Usage: python3 tools/doccheck.py [compiler] [--filter SOURCE] [--report FILE]

Every gdscript fence in docs/*.md and README.md is checked, including indented
fences and generated API declarations. Also checks library comment examples,
homepage snippets, playground programs, API programs, templates and examples/
(except skybarons, maintained separately). CI runs this command unchanged.

Fragments get explicit, typed context in doccheck_fixtures.json, keyed by the
SHA-256 prefix of their dedented text so API.md and its source comments share
fixtures. A fixture may prepend/append declarations, wrap a function, or supply
companion files. `uses` imports library paths relative to lib/, for portable context.
It must never replace a real API call. Conventional `...`
statement holes become `pass`; missing arguments must be made explicit in the source.
Intentionally invalid teaching examples use an exact expected diagnostic, not
an error-category allowlist. Non-Sloppy illustrations must say
`# doccheck: illustrative <reason>` in the source; report them separately.
New/changed fragments fail closed until their context is supplied. Unused
fixtures fail too, preventing stale exceptions from accumulating.
"""
import argparse
import ast
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^[ \t]*```gdscript[^\n]*\n(.*?)^[ \t]*```[ \t]*$", re.M | re.S)
COMMENTS = re.compile(r"^#   [^\n]*(?:\n(?:#   [^\n]*|#[ \t]*(?=\n|$)))*", re.M)


def normalize(code):
    return textwrap.dedent(code).strip() + "\n"


@dataclass
class Example:
    path: Path
    line: int
    code: str
    kind: str
    original: bool = False
    context: str = ""

    @property
    def key(self):
        return hashlib.sha256(normalize(self.code).encode()).hexdigest()[:16]

    @property
    def label(self):
        return f"{self.path.relative_to(ROOT)}:{self.line}"


def collect():
    import apidoc
    topics = {t[2]: t[3] for t in apidoc.TOPICS}
    modules = {p.stem: p.relative_to(ROOT / "lib").with_suffix("").as_posix() for p in (ROOT / "lib").rglob("*.jo")}
    for path in sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]:
        src = path.read_text(encoding="utf-8")
        for m in FENCE.finditer(src):
            context = ""
            if path.name == "API.md" and re.match(r"(?:error )?(?:struct|enum) ", normalize(m[1])):
                topic_headers = list(re.finditer(r"^## (.+)$", src[:m.start()], re.M))
                topic = topic_headers[-1] if topic_headers else None
                headings = re.findall(r"^### (\w+)\.jo$", src[topic.end() if topic else 0:m.start()], re.M)
                module = modules[headings[-1]] if headings else next(iter(topics.get(topic[1] if topic else "", [])), "")
                if isinstance(module, tuple): module = module[0]
                if module:
                    context = f"use '{ROOT / 'lib' / (module + '.jo')}'\n"
            yield Example(path, src[:m.start()].count("\n") + 2, m[1], "markdown", context=context)
    for path in sorted((ROOT / "lib").rglob("*.jo")):
        src = path.read_text(encoding="utf-8")
        for m in COMMENTS.finditer(src):
            code = re.sub(r"^#(?:   )?", "", m[0], flags=re.M)
            yield Example(path, src[:m.start()].count("\n") + 1, code, "comment")
    path = ROOT / "tools/site.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("HERO_CODE", "SNIPPETS") for t in node.targets):
            value = ast.literal_eval(node.value)
            for code in ([value] if isinstance(value, str) else [x[2] for x in value]):
                yield Example(path, node.lineno, code, "homepage")
    paths = sorted((ROOT / "tools/playground/examples").glob("*.jo"))
    # Read the playground's explicit selection too: adding a new source there
    # must not silently bypass the check. Parse literals, never run the builder.
    tree = ast.parse((ROOT / "tools/playground.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith(".jo") and node.value.startswith(("examples/", "lib/new/")):
            paths.append(ROOT / node.value)
    paths += sorted((ROOT / "docs/api").glob("*.jo"))
    paths += sorted((ROOT / "lib/new").glob("*.jo"))
    paths += [p for p in sorted((ROOT / "examples").rglob("*.jo")) if "skybarons" not in p.relative_to(ROOT).parts]
    for path in sorted(set(paths)):
        template = path.parent == ROOT / "lib/new"
        code = path.read_text(encoding="utf-8").replace("__TITLE__", "Example").replace("__NAME__", "example")
        yield Example(path, 1, code, "template" if template else "program", not template)


def statement_holes(code):
    """Turn a standalone ellipsis into pass, leaving strings/comments/spreads alone."""
    out = []
    i = 0
    quote = ""
    while i < len(code):
        if quote:
            if code[i] == "\\":
                out.append(code[i:i + 2]); i += 2
            elif code.startswith(quote, i):
                out.append(quote); i += len(quote); quote = ""
            else:
                out.append(code[i]); i += 1
        elif code[i] == "#":
            end = code.find("\n", i)
            if end < 0: end = len(code)
            out.append(code[i:end]); i = end
        elif code[i] in ("'", '"'):
            quote = code[i] * (3 if code.startswith(code[i] * 3, i) else 1)
            out.append(quote); i += len(quote)
        elif code.startswith("...", i):
            start = code.rfind("\n", 0, i) + 1
            end = code.find("\n", i)
            if end < 0: end = len(code)
            before, after = code[start:i].strip(), code[i + 3:end].strip()
            hole = (not before or before.endswith(":")) and (not after or after.startswith("#"))
            out.append("pass" if hole else "..."); i += 3
        else:
            out.append(code[i]); i += 1
    return "".join(out)


def accepted(returncode, stderr, expected=None):
    if expected is None:
        return returncode == 0
    errors = re.findall(r": error: ([^\n]*)", stderr)
    return returncode == 1 and errors == [expected] and "panic:" not in stderr and "internal compiler error" not in stderr


def prepare(code, fixture):
    code = statement_holes(normalize(code))
    if fixture.get("tail"):
        code += fixture["tail"]
    if fixture.get("scope"):
        code = fixture["scope"] + "\n" + textwrap.indent(code, "    ")
    if fixture.get("function"):
        code = f"doccheck_example = (){fixture['function']}:\n" + textwrap.indent(code, "    ")
    # Reference fragments omit imports already established by the surrounding
    # module/topic. Supply actual modules, never substitute API implementations.
    imports = ""
    for module in ("net", "http", "netplay", "invite", "physics", "physics3d", "sqlite", "crypto", "term", "layout"):
        if re.search(rf"\b{module}\.", code) and not re.search(rf"(?m)^(?:import|use) (?:{module}(?:\s|$)|[\'\"]{module}\.jo[\'\"])", code + fixture.get("before", "")):
            imports += f"import {module}\n"
    uses = "".join(f"use '{ROOT / 'lib' / (module + '.jo')}'\n" for module in fixture.get("uses", []))
    return uses + imports + fixture.get("before", "") + "\n" + code + "\n" + fixture.get("after", "") + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compiler", nargs="?", default=str(ROOT / "bin/sloppy"))
    parser.add_argument("--filter", default="")
    parser.add_argument("--report")
    args = parser.parse_args()
    fixtures = json.loads((ROOT / "tools/doccheck_fixtures.json").read_text(encoding="utf-8"))
    examples = list(collect())
    used = {e.key for e in examples}
    unused = fixtures.keys() - used
    if unused and not args.filter:
        for key in sorted(unused): print(f"FAIL unused fixture {key}: {fixtures[key].get('source', '')}")
    bad = len(unused) if not args.filter else 0
    counts = Counter()
    files = set()
    reports = []
    cache = {}
    env = dict(os.environ, SLOPPY_LIB=str(ROOT / "lib"))
    with tempfile.TemporaryDirectory(prefix="sloppy-doccheck-") as scratch:
        for i, ex in enumerate(examples):
            if args.filter and args.filter not in str(ex.path): continue
            files.add(str(ex.path.relative_to(ROOT)))
            fixture = fixtures.get(ex.key, {})
            code = normalize(ex.code)
            marker = re.search(r"(?m)^# doccheck: illustrative (.+)$", code)
            if marker:
                counts["illustrative"] += 1
                reports.append(dict(source=ex.label, kind=ex.kind, result="illustrative", reason=marker[1]))
                continue
            if re.search(r"\bpackage\(", code):
                bad += 1
                counts[ex.kind] += 1
                print(f"FAIL {ex.label}: package examples need an explicit illustrative marker; no network fetch attempted")
                reports.append(dict(source=ex.label, kind=ex.kind, result="fail"))
                continue
            counts[ex.kind] += 1
            identity = (ex.key, ex.context, str(ex.path) if ex.original else "")
            if identity not in cache:
                directory = Path(scratch) / str(i)
                directory.mkdir()
                if ex.kind == "template":
                    # Match `sloppy new`'s assets (notably character.glb).
                    for asset in ex.path.parent.iterdir():
                        if asset.is_file() and asset.suffix != ".jo": shutil.copy(asset, directory / asset.name)
                for name, content in fixture.get("files", {}).items():
                    dest = directory / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content, encoding="utf-8")
                # Byte assets are not decoded by `check`; stand-ins let the real
                # loader signatures be checked, without downloading sample art.
                for name in re.findall(r'\bembed\("([^"\n]+)"\)', code):
                    dest = directory / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists(): dest.write_bytes(b"")
                for name in re.findall(r'\bembed_dir\("([^"\n]+)"\)', code):
                    (directory / name).mkdir(parents=True, exist_ok=True)
                    (directory / name / "placeholder.txt").write_text("asset stand-in", encoding="utf-8")
                for name in re.findall(r'(?m)^\s*(?:icon|js) = "([^"\n]+)"', code):
                    dest = directory / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if name.endswith(".png"): shutil.copy(ROOT / "assets/icon-32.png", dest)
                    elif not dest.exists(): dest.write_text("// application glue\n", encoding="utf-8")
                source = ex.path if ex.original else directory / "example.jo"
                if not ex.original: source.write_text(ex.context + prepare(code, fixture), encoding="utf-8")
                try:
                    r = subprocess.run([str(Path(args.compiler).resolve()), "check", str(source)], capture_output=True, text=True, env=env, timeout=120)
                    ok = accepted(r.returncode, r.stderr, fixture.get("error"))
                    cache[identity] = (ok, r.stdout + r.stderr)
                except subprocess.TimeoutExpired:
                    cache[identity] = (False, "compiler timed out after 120 seconds")
            ok, output = cache[identity]
            reports.append(dict(source=ex.label, kind=ex.kind, result="pass" if ok else "fail", fixture=ex.key if fixture else None))
            if not ok:
                bad += 1
                print(f"FAIL {ex.label} [{ex.key}]\n{output}")
    checked = sum(v for k, v in counts.items() if k != "illustrative")
    print(f"{checked - bad} passed, {bad} failed; {checked} examples in {len(files)} files; {len(cache)} compiler checks")
    print(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if args.report: Path(args.report).write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
