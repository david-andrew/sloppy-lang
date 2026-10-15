#!/bin/sh
# Check Sloppy on this machine's GPU, unattended, and write one report (build/gpucheck/report.txt):
# the machine and its Vulkan driver, the compiler built from scratch, the render tests drawn
# through Vulkan on this GPU (no display needed), the SPIR-V the compiler makes checked by
# spirv-val, random compute programs compared between the CPU and this GPU, and frame times of
# the example games. With a display, also every program drawn through OpenGL and Vulkan side by
# side (tools/vkcompare.py). A rented machine or a volunteer's runs the same thing.
# usage: tools/gpucheck.sh [--install]   (--install: the packages it needs first, with apt or dnf)
# On a machine with no C compiler (SteamOS: its system is read-only), it checks the bin/sloppy
# given to it (a release's) instead of building one; run over ssh, it finds the logged-in
# desktop's display by itself, for the OpenGL and windowed checks.
set -u
cd "$(dirname "$0")/.."
out=build/gpucheck
mkdir -p "$out"
rep="$out/report.txt"

if [ "${1:-}" = "--install" ]; then
    if command -v apt-get >/dev/null; then
        sudo apt-get update -q
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q gcc make python3 pciutils \
            mesa-vulkan-drivers libvulkan1 vulkan-tools spirv-tools
    elif command -v dnf >/dev/null; then
        sudo dnf install -y -q gcc make python3 pciutils mesa-vulkan-drivers vulkan-loader \
            vulkan-tools spirv-tools
    fi
fi

section() { printf '\n== %s\n' "$1"; }

# (over ssh: the desktop session of this user, if one is logged in)
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    rt="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    if [ -S "$rt/wayland-0" ]; then export XDG_RUNTIME_DIR="$rt" WAYLAND_DISPLAY=wayland-0
    elif [ -S /tmp/.X11-unix/X0 ]; then export DISPLAY=:0
    fi
fi
{
    section "machine"
    date -u
    uname -srm
    (lspci 2>/dev/null | grep -i -E 'vga|3d|display') || echo "(no lspci)"
    section "vulkan"
    (vulkaninfo --summary 2>/dev/null | grep -E 'deviceName|driverName|driverInfo|apiVersion|deviceType') || echo "(no vulkaninfo)"

    section "compiler"
    if command -v cc >/dev/null || command -v gcc >/dev/null; then tools/bootstrap.sh
    elif [ -x bin/sloppy ]; then echo "(no C compiler here: checking the bin/sloppy given, $(bin/sloppy --version))"
    else echo "no C compiler and no bin/sloppy: copy a release's bin/sloppy here"; exit 1
    fi
    echo "display: ${WAYLAND_DISPLAY:-}${DISPLAY:-(none)}"

    section "render tests through Vulkan on this GPU"
    python3 tools/rendertest.py --vulkan-only

    section "SPIR-V checked by spirv-val"
    python3 tools/spirvtest.py

    section "compute: the CPU and this GPU (and Mesa's software driver, if it is there)"
    lvp=""
    [ -e /usr/share/vulkan/icd.d/lvp_icd.x86_64.json ] || lvp="--no-lavapipe"
    python3 tools/gpufuzz.py 300 --seed 1 $lvp

    section "frame times (600 frames each, through Vulkan, no display)"
    for g in examples/breakwater/breakwater.jo examples/dunes/dunes.jo examples/rebound/rebound.jo examples/lowline/lowline.jo; do
        echo "-- $g"
        (cd "$(dirname "$g")" && env -u DISPLAY -u WAYLAND_DISPLAY SLOPPY_STATS=log SLOPPY_FRAMES=600 \
            SLOPPY_SCREENSHOT="$PWD/../../$out/$(basename "$g" .jo).png" timeout 300 \
            ../../bin/sloppy run --release "$(basename "$g")" 2>&1 | grep -v '^long frame' | tail -4)
    done

    if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        section "OpenGL and Vulkan side by side"
        python3 tools/vkcompare.py
    fi
    section "done"
} 2>&1 | tee "$rep"
echo "report: $rep"
