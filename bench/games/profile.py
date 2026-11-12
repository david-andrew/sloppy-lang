#!/usr/bin/env python3
"""Headless finished-game profiles, using an instrumented scratch copy of lib only."""

import argparse
import collections
import csv
import json
import os
import pathlib
import re
import shutil
import statistics
import subprocess

ROOT = pathlib.Path.home() / "dev/tmp/game-prof"
REPO = pathlib.Path(__file__).resolve().parents[2]
GAMES = {n: f"examples/{n}/{n}.jo" for n in ["rebound", "breakwater", "aces", "dunes"]}
GAMES.update(
    {
        f"new_{n}": f"lib/new/{n}.jo"
        for n in ["game", "3d", "character", "arcade", "platformer", "pico", "story"]
    }
)
GAMES.update({n: f"tests/render/{n}.jo" for n in ["pbr_grid", "sky_image"]})
INPUT = {
    "rebound": "5:enter+ 7:enter- 30:right+ 105:right- 106:left+ 180:left- 181:right+ 270:right- 271:left+ 355:left-",
    "breakwater": "5:enter+ 7:enter- 20:w+ 100:w- 101:d+ 180:d- 181:s+ 260:s- 261:a+ 350:a- 20:mouse_left+ 350:mouse_left-",
    "aces": "5:down+ 7:down- 10:down+ 12:down- 15:down+ 17:down- 20:enter+ 22:enter- 30:enter+ 32:enter- 60:space+ 350:space- 120:a+ 150:a- 210:s+ 240:s-",
    "dunes": "5:w+ 150:space+ 200:space- 240:w- 241:d+ 350:d- 60:q+ 90:q-",
    "new_game": "5:right+ 90:right- 91:down+ 180:down- 181:left+ 270:left- 271:up+ 360:up-",
    "new_3d": "5:mouse_left+ 7:mouse_left- 10:w+ 100:w- 105:d+ 180:d- 190:s+ 270:s- 280:a+ 360:a- 40:space+ 42:space- 60:mouse_left+ 62:mouse_left- 180:mouse_left+ 182:mouse_left-",
    "new_character": "5:w+ 80:shift+ 100:shift- 120:w- 121:d+ 180:d- 181:s+ 240:s- 241:a+ 300:a-",
    "pbr_grid": "",
    "sky_image": "",
}
C = r"""
#include <stdio.h>
#include <stdlib.h>
#include <valgrind/callgrind.h>
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>
#include <unistd.h>
static int vg, warmup, frames;
static int perf_fd = -1;
static long phase[12];
__attribute__((constructor)) static void init(void) {
 vg=RUNNING_ON_VALGRIND; if(vg) { CALLGRIND_STOP_INSTRUMENTATION; } warmup=atoi(getenv("GP_WARMUP")?:"60"); frames=atoi(getenv("SLOPPY_FRAMES")?:"360");
 if(atoi(getenv("GP_PERF")?:"0")) {
  struct perf_event_attr pe = {0};
  pe.type=PERF_TYPE_HARDWARE; pe.size=sizeof(pe); pe.config=PERF_COUNT_HW_INSTRUCTIONS;
  pe.disabled=1; pe.exclude_kernel=1; pe.exclude_hv=1; pe.inherit=1;
  perf_fd=syscall(SYS_perf_event_open,&pe,0,-1,-1,0);
  if(perf_fd<0) { perror("perf_event_open"); exit(2); }
 }
}
void gp_begin(long f) {
 // Leave the final screenshot/PNG frame outside the hardware sample.
 if(perf_fd>=0 && f>=warmup && f<frames-1) {
  ioctl(perf_fd,PERF_EVENT_IOC_RESET,0); ioctl(perf_fd,PERF_EVENT_IOC_ENABLE,0);
 }
 if(vg && f==warmup) { CALLGRIND_START_INSTRUMENTATION; }
 if(vg && f>=warmup && f<frames) { VALGRIND_MONITOR_COMMAND("zero"); }
}
void gp_phase(long p,long a,long b,long c,long d) {
 phase[p*4]=a;phase[p*4+1]=b;phase[p*4+2]=c;phase[p*4+3]=d;
}
void gp_end(long f,long a,long b,long c,long d,long live) {
 if(perf_fd>=0 && f>=warmup && f<frames-1) {
  unsigned long long instructions=0;
  ioctl(perf_fd,PERF_EVENT_IOC_DISABLE,0);
  if(read(perf_fd,&instructions,sizeof(instructions))!=sizeof(instructions)) { perror("perf read"); exit(2); }
  printf("GI,%ld,%llu\n",f,instructions); fflush(stdout);
 }
 if(vg && f>=warmup && f<frames) { VALGRIND_MONITOR_COMMAND("dump"); }
 if(!vg && f<frames) {
  printf("GP,%ld,%ld,%ld,%ld,%ld,%ld",f,a,b,c,d,live);
  for(int i=0;i<12;i++) printf(",%ld",phase[i]);
  puts(""); fflush(stdout);
 }
}
"""


def setup(tag, churn, library):
    d = ROOT / tag
    d.mkdir(exist_ok=True)
    lib = d / ("lib-churn" if churn else "lib-ir")
    if lib.exists():
        shutil.rmtree(lib)
    shutil.copytree(library, lib)
    helper = d / ("helper-churn.c" if churn else "helper-ir.c")
    helper.write_text(C)
    so = d / ("helper-churn.so" if churn else "helper-ir.so")
    includes = (
        ["-I/home/linuxbrew/.linuxbrew/include"]
        if pathlib.Path(
            "/home/linuxbrew/.linuxbrew/include/valgrind/callgrind.h"
        ).exists()
        else []
    )
    subprocess.run(
        [
            "cc",
            "-shared",
            "-fPIC",
            "-O2",
            *includes,
            str(helper),
            "-o",
            str(so) + ".new",
        ],
        check=True,
    )
    os.replace(str(so) + ".new", so)
    rt = lib / "core/rt.jo"
    s = rt.read_text()
    s += "\n__gp_a = 0\n__gp_b = 0\n__gp_c = 0\n__gp_d = 0\n"
    if churn:
        for func, glob, needle in [
            ("__alloc_z", "__gp_a", "    n = size + 16"),
            ("__free", "__gp_b", "    h = (p - 16) as *int"),
            ("__rc_inc", "__gp_c", "    h = p as *int"),
            ("__rc_dec_test", "__gp_d", "    h = p as *int"),
        ]:
            pos = s.index(func + " = (")
            end = s.find("\n\n", pos)
            part = s[pos:end]
            part = part.replace(
                needle, f"    global {glob}\n    {glob} += 1\n" + needle, 1
            )
            s = s[:pos] + part + s[end:]
    rt.write_text(s)
    # Games may seed from time_ns() explicitly; pin only that seed clock for repeatability.
    osjo = lib / "core/os.jo"
    s = osjo.read_text()
    s = s.replace(
        "time_ns = () -> int:",
        "time_ns = () -> int: 12345\n\n__gp_real_time_ns = () -> int:",
        1,
    )
    osjo.write_text(s)
    win = lib / "game/window.jo"
    s = win.read_text()
    s += f'\n@lib("{so}")\nextern gp_begin = (f: int)\n@lib("{so}")\nextern gp_phase = (p: int, a: int, b: int, c: int, d: int)\n@lib("{so}")\nextern gp_end = (f: int, a: int, b: int, c: int, d: int, live: int)\n'
    at = s.index("__run_frame = (")
    part = s[at:]
    part = part.replace(
        "    global __dt,",
        "    global __gp_a, __gp_b, __gp_c, __gp_d\n    __gp_a = 0\n    __gp_b = 0\n    __gp_c = 0\n    __gp_d = 0\n    global __dt,",
        1,
    )
    part = part.replace(
        "        update(sdt)\n",
        "        update(sdt)\n        gp_phase(0, __gp_a, __gp_b, __gp_c, __gp_d)\n",
        1,
    )
    part = part.replace(
        "        draw()\n",
        "        draw()\n        gp_phase(1, __gp_a, __gp_b, __gp_c, __gp_d)\n",
        1,
    )
    part = part.replace(
        "    __maybe_screenshot()",
        "    gp_phase(2, __gp_a, __gp_b, __gp_c, __gp_d)\n    __maybe_screenshot()",
        1,
    )
    s = s[:at] + part
    s = s.replace(
        "            __run_frame(dt, update, draw)",
        "            gp_begin(__frame_count)\n            __run_frame(dt, update, draw)",
    )
    s = s.replace(
        "            __frame_present += __last_present",
        "            __frame_present += __last_present\n            gp_end(__frame_count - 1, __gp_a, __gp_b, __gp_c, __gp_d, alloc_count())",
    )
    win.write_text(s)
    return lib


def parse(path):
    # Callgrind's compressed file/function IDs are scoped to one dump.
    ids = {}
    fn = "?"
    fl = "?"
    callee = None
    costs = collections.Counter()
    edges = collections.Counter()
    total = 0

    def expand(value, kind):
        m = re.match(r"\((\d+)\)(?: (.*))?$", value)
        if not m:
            return value
        key = (kind, m[1])
        if m[2] is not None:
            ids[key] = m[2]
        return ids.get(key, "?" + m[1])

    for line in path.open(errors="replace"):
        if line.startswith("totals:"):
            total = int(line.split()[1])
        elif line.startswith("fl="):
            fl = expand(line[3:].strip(), "fl")
        elif line.startswith("fn="):
            fn = expand(line[3:].strip(), "fn")
        elif line.startswith("cfn="):
            callee = expand(line[4:].strip(), "fn")
        elif line.startswith("cfl="):
            expand(line[4:].strip(), "fl")
        elif line and (line[0].isdigit() or line[0] in "+-*"):
            v = line.split()
            if len(v) < 2:
                continue
            try:
                n = int(v[-1])
            except ValueError:
                continue
            if callee is None:
                costs[(fl, fn)] += n
            else:
                edges[(fn, callee)] += n
                callee = None
    if not total:
        total = sum(costs.values())
    return total, costs, edges


def main():
    global ROOT, REPO
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=pathlib.Path, default=ROOT)
    p.add_argument("--repo", type=pathlib.Path, default=REPO)
    p.add_argument("--compiler", type=pathlib.Path)
    p.add_argument("--library", type=pathlib.Path)
    p.add_argument("--tag", default="before")
    p.add_argument("--games", nargs="+", choices=list(GAMES), default=list(GAMES))
    p.add_argument(
        "--modes", nargs="+", choices=["debug", "release"], default=["debug", "release"]
    )
    p.add_argument(
        "--renderers", nargs="+", choices=["soft", "vk"], default=["soft", "vk"]
    )
    p.add_argument("--frames", type=int, default=360)
    p.add_argument("--warmup", type=int, default=60)
    p.add_argument("--window", default="320x180")
    p.add_argument("--threads", type=int, default=1, help="software worker limit (use a distinct tag for each count)")
    p.add_argument("--churn", action="store_true")
    p.add_argument("--perf", action="store_true", help="Linux instructions:u per software frame; excludes the final capture frame")
    p.add_argument("--prepare", action="store_true")
    p.add_argument("--build-only", action="store_true")
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--timeout", type=int, default=7200)
    a = p.parse_args()
    ROOT = a.output.expanduser().resolve()
    REPO = a.repo.expanduser().resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "tmp").mkdir(exist_ok=True)
    os.environ["TMPDIR"] = str(ROOT / "tmp")
    if a.frames <= a.warmup or a.warmup < 0:
        p.error("frames must exceed warmup >= 0")
    if a.threads < 1:
        p.error("threads must be positive")
    if a.perf and a.threads != 1:
        p.error("--perf measures only the main thread; use Callgrind for multiple threads")
    if a.perf and (a.churn or a.renderers != ["soft"] or a.frames <= a.warmup + 1):
        p.error("--perf needs --renderers soft, frames > warmup + 1, and no --churn")
    if pathlib.Path(a.tag).name != a.tag or a.tag in (".", ".."):
        p.error("tag must be a directory name")
    compiler = a.compiler.expanduser().resolve() if a.compiler else REPO / "bin/sloppy"
    lib = ROOT / a.tag / ("lib-churn" if a.churn else "lib-ir")
    if a.prepare or not lib.exists():
        lib = setup(a.tag, a.churn, a.library or REPO / "lib")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ["DISPLAY", "WAYLAND_DISPLAY", "SLOPPY_SOFTWARE", "SLOPPY_VULKAN"]
    }
    env.update(
        TMPDIR=str(ROOT / "tmp"),
        SLOPPY_LIB=str(lib),
        SLOPPY_NO_AUDIO="1",
        SDL_AUDIODRIVER="dummy",
        SLOPPY_THREADS=str(a.threads),
        SLOPPY_EMIT_WORKERS="2",
        LP_NUM_THREADS="1",
        SLOPPY_WINDOW=a.window,
        SLOPPY_SCALE="1",
        SLOPPY_SOFT_SCALE="0.5",
        SLOPPY_STATS="0",
        SLOPPY_FRAME_STATS="1",
        SLOPPY_SEED="12345",
        SLOPPY_FRAMES=str(a.frames),
        GP_WARMUP=str(a.warmup),
        GP_PERF="1" if a.perf else "0",
        VK_ICD_FILENAMES="/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
    )
    (ROOT / a.tag / "run.json").write_text(json.dumps({
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "compiler": str(compiler), "library": str(a.library or REPO / "lib"),
        "games": a.games, "modes": a.modes, "renderers": a.renderers,
        "threads": a.threads, "window": a.window, "warmup": a.warmup,
        "frames": a.frames, "perf": a.perf, "churn": a.churn,
    }, indent=2) + "\n")
    failed = []
    for game in a.games:
        for mode in a.modes:
            exe = ROOT / a.tag / f"{game}-{mode}{'-churn' if a.churn else ''}"
            if not a.reuse or not exe.exists():
                cmd = [
                    str(compiler),
                    "build",
                    str(REPO / GAMES[game]),
                    "-o",
                    str(exe),
                ] + (["--release"] if mode == "release" else [])
                r = subprocess.run(cmd, env=env, capture_output=True, text=True)
                (exe.parent / (exe.name + ".build.log")).write_text(r.stdout + r.stderr)
                if r.returncode:
                    raise RuntimeError(r.stderr)
            if a.build_only:
                continue
            for renderer in a.renderers:
                name = f"{game}-{mode}-{renderer}{'-churn' if a.churn else ''}"
                d = ROOT / a.tag / name
                d.mkdir(exist_ok=True)
                shutil.rmtree(d / "saves", ignore_errors=True)
                shutil.rmtree(d / "cache", ignore_errors=True)
                (d / "cache").mkdir()
                (d / "cache" / "mesa").mkdir()
                for artifact in [
                    "summary.json",
                    "frames.csv",
                    "self.json",
                    "edges.json",
                    "worst.callgrind",
                    "last.png",
                ]:
                    (d / artifact).unlink(missing_ok=True)
                for old_dump in d.glob("callgrind.*"):
                    old_dump.unlink()
                runenv = dict(
                    env,
                    SLOPPY_INPUT=INPUT.get(game, INPUT["new_game"]),
                    SLOPPY_SAVE_DIR=str(d / "saves"),
                    XDG_CACHE_HOME=str(d / "cache"),
                    MESA_SHADER_CACHE_DIR=str(d / "cache" / "mesa"),
                    SLOPPY_SCREENSHOT=str(d / "last.png"),
                )
                if renderer == "soft":
                    runenv["SLOPPY_SOFTWARE"] = "1"
                else:
                    runenv["SLOPPY_VULKAN"] = "1"
                cmd = (
                    [str(exe)]
                    if a.churn or a.perf
                    else [
                        "valgrind",
                        "--tool=callgrind",
                        "--vgdb-prefix=" + str(ROOT / "tmp/vgdb-pipe"),
                        "--collect-atstart=yes",
                        "--instr-atstart=no",
                        "--callgrind-out-file=" + str(d / "callgrind.%p"),
                        str(exe),
                    ]
                )
                print("RUN", a.tag, name, flush=True)
                try:
                    with (d / "run.log").open("w") as log:
                        r = subprocess.run(
                            cmd,
                            env=runenv,
                            cwd=REPO / GAMES[game].rsplit("/", 1)[0],
                            stdout=log,
                            stderr=log,
                            timeout=a.timeout,
                        )
                except subprocess.TimeoutExpired:
                    print("TIMEOUT", name, flush=True)
                    failed.append(name)
                    continue
                if r.returncode:
                    print("FAIL", name, r.returncode, flush=True)
                    failed.append(name)
                    continue
                log_text = (d / "run.log").read_text()
                backend = "vulkan (" if renderer == "vk" else "software renderer"
                if not (d / "last.png").exists() or backend not in log_text:
                    print(
                        "FAIL", name, "missing capture or requested backend", flush=True
                    )
                    failed.append(name)
                    continue
                if a.churn:
                    rows = [
                        list(map(int, l.strip().split(",")[1:]))
                        for l in (d / "run.log").read_text().splitlines()
                        if l.startswith("GP,")
                    ]
                    with (d / "frames.csv").open("w") as f:
                        w = csv.writer(f)
                        w.writerow(
                            ["frame", "alloc", "free", "inc", "dec", "live"]
                            + [
                                f"{z}_{k}"
                                for z in ["update", "draw_cumulative", "end_cumulative"]
                                for k in ["alloc", "free", "inc", "dec"]
                            ]
                        )
                        w.writerows(rows)
                    measured = [r for r in rows if r[0] >= a.warmup]
                    if len(measured) != a.frames - a.warmup:
                        raise RuntimeError(f"incomplete allocation samples: {d}")
                    summary = {
                        k: {
                            "median": statistics.median(r[i] for r in measured),
                            "max": max(r[i] for r in measured),
                            "mean": statistics.mean(r[i] for r in measured),
                        }
                        for i, k in enumerate(
                            ["frame", "alloc", "free", "inc", "dec", "live"]
                        )
                        if i > 0
                    }
                elif a.perf:
                    frames = [
                        list(map(int, line.split(",")[1:]))
                        for line in log_text.splitlines() if line.startswith("GI,")
                    ]
                    if len(frames) != a.frames - a.warmup - 1 or any(row[1] <= 0 for row in frames):
                        raise RuntimeError(f"incomplete hardware samples: {d}")
                    with (d / "frames.csv").open("w") as f:
                        w = csv.writer(f)
                        w.writerow(["frame", "Ir"])
                        w.writerows(frames)
                    summary = {
                        "counter": "perf_event_open instructions:u, software main thread",
                        "frames": len(frames),
                        "median_Ir": statistics.median(r[1] for r in frames),
                        "mean_Ir": statistics.mean(r[1] for r in frames),
                        "total_Ir": sum(r[1] for r in frames),
                        "worst_Ir": max(frames, key=lambda r: r[1])[::-1],
                    }
                else:
                    costs = collections.Counter()
                    edges = collections.Counter()
                    frames = []
                    worst = (0, None)
                    dumps = sorted(
                        d.glob("callgrind.*.*"),
                        key=lambda x: int(x.name.rsplit(".", 1)[1]),
                    )
                    for i, path in enumerate(dumps):
                        total, c, e = parse(path)
                        frames.append([a.warmup + i, total])
                        costs.update(c)
                        edges.update(e)
                        if total > worst[0]:
                            worst = (total, a.warmup + i)
                            shutil.copy(path, d / "worst.callgrind")
                        path.unlink()
                    if len(frames) != a.frames - a.warmup:
                        raise RuntimeError("incomplete per-frame dumps: " + str(d))
                    with (d / "frames.csv").open("w") as f:
                        w = csv.writer(f)
                        w.writerow(["frame", "Ir"])
                        w.writerows(frames)
                    summary = {
                        "frames": len(frames),
                        "median_Ir": statistics.median(r[1] for r in frames),
                        "mean_Ir": statistics.mean(r[1] for r in frames),
                        "worst_Ir": worst,
                        "top_self": [(list(k), v) for k, v in costs.most_common(35)],
                        "top_edges": [(list(k), v) for k, v in edges.most_common(60)],
                        "total_Ir": sum(r[1] for r in frames),
                    }
                    (d / "self.json").write_text(
                        json.dumps(
                            [(list(k), v) for k, v in costs.most_common()], indent=2
                        )
                    )
                    (d / "edges.json").write_text(
                        json.dumps(
                            [(list(k), v) for k, v in edges.most_common()], indent=2
                        )
                    )
                    for path in d.glob("callgrind.*"):
                        path.unlink()
                (d / "summary.json").write_text(json.dumps(summary, indent=2))
                print(
                    "DONE",
                    name,
                    json.dumps(
                        {k: v for k, v in summary.items() if not k.startswith("top_")}
                    ),
                    flush=True,
                )
    if failed:
        raise SystemExit("Failed profiles: " + ", ".join(failed))


if __name__ == "__main__":
    main()
