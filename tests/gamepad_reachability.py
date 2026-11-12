#!/usr/bin/env python3
"""Windows pad backends are linked only by pad readers, including controls and navigation.
Run: python3 tests/gamepad_reachability.py [compiler]
Builds only; no Windows device, display, or Wine required. TMPDIR controls scratch space.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPILER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "bin" / ("sloppy.exe" if os.name == "nt" else "sloppy")
DRAW = 'window("t", 320, 200)\ndraw = ():\n    clear(BLACK)\n    rect(1, 2, 3, 4, RED)\n    text("hi", vec2(3, 3), 12, WHITE)\n'
CASES = [("drawing", DRAW, False), ("mouse", DRAW + '    if mouse_down(.left): mouse_lock()\n', False)]
for reader in ("gamepads()", "gamepad_connected()", "gamepad_connected(0)", 'gamepad_name(0)',
               "gamepad_down(.a)", "gamepad_pressed(0, .a)", "gamepad_released(.a)",
               "gamepad_axis(0)", "left_stick()", "right_stick()", "left_stick(0)",
               "joystick_buttons(0)", "joystick_axes(0)", "joystick_button(0, 0)",
               "joystick_pressed(0, 0)", "joystick_axis(0, 0)", "input_axis()"):
    CASES.append((reader, DRAW + f"    print({reader})\n", True))
CASES += [
    ("fixed update without pad input", DRAW + 'update = (dt: f64): fixed_update(dt, (h: f64): pass)\n', False),
    ("actions", 'action("jump", [.button(.a)])\n' + DRAW + '    print(action_down("jump"))\n', True),
    ("ui", DRAW + '    ui_begin("menu", vec2(160, 20))\n    ui_button("Go")\n    ui_end()\n', True),
    ("hud mouse button", DRAW + '    hud_button(Rect(10, 10, 80, 30), "Go")\n', False),
    ("layout", 'import layout as ui\n' + DRAW + '    ui.at(Rect(0, 0, 300, 200), ():\n        ui.button("Go")\n    )\n', True),
]
MARKERS = (b"HidP_GetCaps", b"GetRawInputDeviceList", b"XInputGetState", b"xinput1_4.dll")
env = dict(os.environ, SLOPPY_LIB=str(ROOT / "lib"), SLOPPY_EMIT_WORKERS="1")
with tempfile.TemporaryDirectory(prefix="sloppy-pad-reachability-") as d:
    source, output = Path(d) / "game.jo", Path(d) / "game.exe"
    for flags in ([], ["--release"]):
        for name, code, wanted in CASES:
            source.write_text(code, encoding="utf-8")
            r = subprocess.run([str(COMPILER), "build", str(source), "--target", "windows", "-o", str(output), *flags],
                               env=env, capture_output=True, text=True)
            if r.returncode:
                sys.exit(f"FAIL {name} {flags}: {r.stdout}{r.stderr}")
            binary = output.read_bytes()
            for marker in MARKERS:
                if (marker in binary) != wanted:
                    sys.exit(f"FAIL {name} {flags}: {marker.decode()} {'missing' if wanted else 'linked without pad use'}")
print(f"{2 * len(CASES)} passed, 0 failed")
