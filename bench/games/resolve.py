import argparse
import json
import pathlib
import subprocess

parser = argparse.ArgumentParser(
    description="Resolve Sloppy addresses in game profiles"
)
parser.add_argument(
    "--output", type=pathlib.Path, default=pathlib.Path.home() / "dev/tmp/game-prof"
)
parser.add_argument("tags", nargs="+")
args = parser.parse_args()
root = args.output.expanduser().resolve()
for tag in args.tags:
    for d in sorted((root / tag).iterdir()):
        if not d.is_dir() or not (d / "self.json").exists():
            continue
        game, mode, renderer = d.name.rsplit("-", 2)
        exe = d.parent / f"{game}-{mode}"
        self = json.loads((d / "self.json").read_text())
        edges = json.loads((d / "edges.json").read_text())
        addrs = sorted(
            {fn for (_, fn), _ in self if fn.startswith("0x")}
            | {fn for edge, _ in edges for fn in edge if fn.startswith("0x")}
        )
        out = (
            subprocess.run(
                ["addr2line", "-f", "-e", str(exe), *addrs],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.splitlines()
            if addrs
            else []
        )
        if len(out) != 2 * len(addrs):
            raise RuntimeError(f"incomplete address resolution: {d}")
        names = {a: (out[2 * i], out[2 * i + 1]) for i, a in enumerate(addrs)}

        def name(fn):
            n, loc = names.get(fn, (fn, ""))
            return n + " (" + loc.replace(str(root) + "/", "") + ")" if loc else n

        (d / "resolved-self.json").write_text(
            json.dumps([(name(fn), v) for (_, fn), v in self], indent=2)
        )
        (d / "resolved-edges.json").write_text(
            json.dumps(
                [([name(src), name(dst)], v) for (src, dst), v in edges], indent=2
            )
        )
        total = json.loads((d / "summary.json").read_text())["total_Ir"]
        print("\n", tag, d.name)
        for (_, fn), v in self[:12]:
            print(f"{v / total * 100:5.1f}%", name(fn))
