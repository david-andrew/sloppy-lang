#!/bin/sh
# Build the Sloppy compiler from scratch: C bootstrap -> sloppy1 -> sloppy2 -> sloppy3 (must equal sloppy2).
set -e
cd "$(dirname "$0")/.."
make -s -C stage0
mkdir -p bin
export SLOPPY_LIB="$PWD/lib"
# (the C bootstrap compiler changes the global x where a function writes `x = ...`; the compiler's
# own code names its functions' variables apart from its globals, so both read it alike)
export SLOPPY_NO_SHADOW=1
build_tmp=$(mktemp -d "${TMPDIR:-/tmp}/sloppy-bootstrap-XXXXXX")
trap 'rm -rf "$build_tmp"' EXIT HUP INT TERM
./stage0/sloppy0 compiler/main.jo -o "$build_tmp/sloppy1"
"$build_tmp/sloppy1" build compiler/main.jo -o "$build_tmp/sloppy2"
"$build_tmp/sloppy2" build compiler/main.jo -o "$build_tmp/sloppy3"
if cmp -s "$build_tmp/sloppy2" "$build_tmp/sloppy3"; then
    rm -f bin/sloppy && cp "$build_tmp/sloppy2" bin/sloppy      # (rm: an editor may be running the old one)
    echo "bootstrap ok: bin/sloppy ($(stat -c %s bin/sloppy) bytes), self-compile is a fixed point"
else
    echo "bootstrap FAILED: sloppy2 and sloppy3 differ"
    exit 1
fi
