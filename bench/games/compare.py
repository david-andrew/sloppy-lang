#!/usr/bin/env python3
"""Compare matching instruction profiles and require byte-identical captured PNGs."""

import argparse
import csv
import hashlib
import json
import pathlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before")
    p.add_argument("after")
    p.add_argument("--output", type=pathlib.Path, default=pathlib.Path.home() / "dev/tmp/game-prof")
    p.add_argument("--json", type=pathlib.Path, help="also write full comparison data")
    a = p.parse_args()
    root = a.output.expanduser().resolve()
    before, after = root / a.before, root / a.after
    cases = lambda d: {f.parent.name for f in d.glob("*/summary.json")}
    if not cases(before) or cases(before) != cases(after):
        p.error(f"profile sets differ: {sorted(cases(before) ^ cases(after))}")
    rows = []
    failed = []
    for name in sorted(cases(before)):
        bd, ad = before / name, after / name
        b = json.loads((bd / "summary.json").read_text())
        c = json.loads((ad / "summary.json").read_text())
        if b.get("counter") != c.get("counter") or "median_Ir" not in b or "median_Ir" not in c:
            p.error(f"incompatible counters: {name}")
        def frames(d):
            with (d / "frames.csv").open() as f:
                return [int(r["frame"]) for r in csv.DictReader(f)]
        if frames(bd) != frames(ad):
            p.error(f"sampled frame numbers differ: {name}")
        bp, ap = (bd / "last.png").read_bytes(), (ad / "last.png").read_bytes()
        identical = bp == ap
        if not identical:
            failed.append(name)
        rows.append({
            "case": name, "frames": b["frames"],
            "before_Ir": b["median_Ir"], "after_Ir": c["median_Ir"],
            "reduction_percent": (b["median_Ir"] - c["median_Ir"]) / b["median_Ir"] * 100,
            "before_worst_Ir": b["worst_Ir"], "after_worst_Ir": c["worst_Ir"],
            "identical_png": identical,
            "before_png_sha256": hashlib.sha256(bp).hexdigest(),
            "after_png_sha256": hashlib.sha256(ap).hexdigest(),
        })
    print("| Scene / mode / backend | Frames | Before M | After M | Reduction | Exact PNG |")
    print("|---|---:|---:|---:|---:|---|")
    for r in rows:
        print(f'| {r["case"]} | {r["frames"]} | {r["before_Ir"] / 1e6:.3f} | '
              f'{r["after_Ir"] / 1e6:.3f} | {r["reduction_percent"]:.2f}% | '
              f'{"yes" if r["identical_png"] else "MISMATCH"} |')
    if a.json:
        a.json.write_text(json.dumps(rows, indent=2) + "\n")
    if failed:
        raise SystemExit("PNG mismatches: " + ", ".join(failed))


if __name__ == "__main__":
    main()
