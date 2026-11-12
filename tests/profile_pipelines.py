#!/usr/bin/env python3
"""Measure cold startup and every initial frame through headless lavapipe.

Uses the finished-game profiler's scripted input and scratch-library hooks, with instruction
collection enabled from process entry. No game source is edited. Each game has isolated
empty driver/save caches. See docs/GRAPHICS.md for the loading API.
"""
import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("game_profile", REPO / "bench/games/profile.py")
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() / "dev/tmp/pipelines")
    parser.add_argument("--library", type=Path, default=REPO / "lib")
    parser.add_argument("--compiler", type=Path, default=REPO / "bin/sloppy")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--window", default="160x90")
    parser.add_argument("--stats-overlay", action="store_true", help="include the game statistics overlay in both matched runs")
    parser.add_argument("--icd", default="/usr/share/vulkan/icd.d/lvp_icd.x86_64.json")
    parser.add_argument("games", nargs="*", default=["breakwater", "aces", "dunes", "rebound", "new_3d"])
    args = parser.parse_args()
    if args.frames < 1 or Path(args.tag).name != args.tag or args.tag in (".", ".."):
        parser.error("use a positive frame count and a simple tag")
    if any(game not in gp.GAMES for game in args.games):
        parser.error("unknown game")
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "tmp").mkdir(exist_ok=True)
    os.environ["TMPDIR"] = str(output / "tmp")
    gp.ROOT = output
    # The existing helper starts at the warmup frame. Collect startup too, then dump/reset
    # all threads at each boundary: lavapipe's worker JIT belongs to its triggering frame.
    gp.C = gp.C.replace("CALLGRIND_STOP_INSTRUMENTATION", "CALLGRIND_START_INSTRUMENTATION")
    gp.C = gp.C.replace("void gp_begin(long f)", "void gp_begin(long f,long pipelines)")
    gp.C = gp.C.replace(
        " if(vg && f==warmup)",
        ' printf("PIPELINES,%ld,%ld\\n",f,pipelines); fflush(stdout);\n'
        ' if(vg && f==0) { VALGRIND_MONITOR_COMMAND("dump"); }\n'
        " if(vg && f==warmup)",
    )
    dest = output / args.tag
    dest.mkdir(exist_ok=True)
    lib = gp.setup(args.tag, False, args.library.expanduser().resolve())
    rt = lib / "core/rt.jo"
    rt.write_text(rt.read_text() + "\n__gp_pipelines = 0\n")
    vk = lib / "game/vkgl.jo"
    vk.write_text(vk.read_text().replace(
        "        __vk_check(vkCreateGraphicsPipelines",
        "        global __gp_pipelines\n        __gp_pipelines += 1\n"
        "        __vk_check(vkCreateGraphicsPipelines",
    ))
    window = lib / "game/window.jo"
    window.write_text(window.read_text().replace(
        "extern gp_begin = (f: int)", "extern gp_begin = (f: int, pipelines: int)"
    ).replace("gp_begin(__frame_count)", "gp_begin(__frame_count, __gp_pipelines)"))
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY", "SLOPPY_SOFTWARE")}
    env.update(
        SLOPPY_LIB=str(lib), SLOPPY_NO_AUDIO="1", SDL_AUDIODRIVER="dummy",
        SLOPPY_THREADS="1", LP_NUM_THREADS="1", SLOPPY_WINDOW=args.window,
        SLOPPY_SCALE="1", SLOPPY_SEED="12345", SLOPPY_FRAMES=str(args.frames),
        SLOPPY_VULKAN="1", SLOPPY_STATS="1" if args.stats_overlay else "0", SLOPPY_FRAME_STATS="1", GP_WARMUP="0",
        VK_ICD_FILENAMES=args.icd,
        DEBUGINFOD_CACHE_PATH=str(output / "debuginfod-cache"),
    )
    for game in args.games:
        exe = dest / game
        run = dest / (game + "-run")
        run.mkdir(exist_ok=True)
        for name in ("saves", "cache", "mesa"):
            shutil.rmtree(run / name, ignore_errors=True)
        for old in run.glob("callgrind.*"):
            old.unlink()
        runenv = dict(env, SLOPPY_INPUT=gp.INPUT.get(game, ""),
                      SLOPPY_SCREENSHOT=str(run / "last.png"), SLOPPY_SAVE_DIR=str(run / "saves"),
                      XDG_CACHE_HOME=str(run / "cache"), MESA_SHADER_CACHE_DIR=str(run / "mesa"))
        build = subprocess.run([str(args.compiler.resolve()), "build", str(REPO / gp.GAMES[game]), "-o", str(exe)],
                               env=runenv, capture_output=True, text=True)
        (run / "build.log").write_text(build.stdout + build.stderr)
        build.check_returncode()
        print("RUN", game, flush=True)
        with (run / "run.log").open("w") as log:
            subprocess.run([
                "valgrind", "--tool=callgrind", "--vgdb-prefix=" + str(output / "tmp/vgdb-pipe"),
                "--collect-atstart=yes", "--instr-atstart=yes",
                "--callgrind-out-file=" + str(run / "callgrind.%p"), str(exe),
            ], env=runenv, cwd=REPO / gp.GAMES[game].rsplit("/", 1)[0],
               stdout=log, stderr=log, check=True, timeout=7200)
        log = (run / "run.log").read_text()
        if "vulkan (" not in log:
            raise RuntimeError("requested Vulkan backend was not used: " + str(run))
        dumps = sorted(run.glob("callgrind.*.*"), key=lambda p: int(p.name.rsplit(".", 1)[1]))
        counts = [gp.parse(path)[0] for path in dumps]
        if len(counts) != args.frames + 1:
            raise RuntimeError("incomplete startup/frame dumps: " + str(run))
        startup, frames = counts[0], counts[1:]
        worst = frames.index(max(frames))
        shutil.copyfile(dumps[worst + 1], run / "worst.callgrind")
        pipelines = [list(map(int, line.split(",")[1:])) for line in log.splitlines() if line.startswith("PIPELINES,")]
        with (run / "frames.csv").open("w") as f:
            writer = csv.writer(f)
            writer.writerow(["frame", "Ir", "pipelines_before_frame"])
            writer.writerows((i, count, pipelines[i][1]) for i, count in enumerate(frames))
        summary = dict(startup_Ir=startup, frames=len(frames), median_Ir=statistics.median(frames),
                       worst_Ir=max(frames), worst_frame=worst,
                       pipelines_at_first_frame=pipelines[0][1], pipelines_at_last_frame=pipelines[-1][1])
        (run / "summary.json").write_text(json.dumps(summary, indent=2))
        for path in run.glob("callgrind.*"):
            path.unlink()
        print("DONE", game, json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
