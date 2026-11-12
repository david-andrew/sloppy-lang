# HID controller fixtures

`gamepad_hid.jo` runs on Linux as well as Windows. `reader.jo` is a test-only short-item
HID descriptor reader and bit extractor: it translates actual descriptors to the Windows
HIDP capability ABI and supplies usage/value reads to the library's shared report parser.
Production uses Windows' `HidP_Get*` functions for this boundary. The library's capability
filtering, report-ID dispatch, sign extension, normalization, layout mapping, and Nintendo
packet decoding are the same code under test. This does not emulate Windows' HID driver.

The `.rdesc` files contain HID descriptor bytes; `.report` files contain constructed,
little-endian input packets. They are embedded, so tests do not need a controller, a device
node, or files beside the executable. Descriptor and report construction are independent.

- `ds4`: Sony 054c:05c4 USB input descriptor prefix, through its 64-byte input report;
  buttons Cross/L1/Share/L3/PS, up-right, sticks at opposite extremes, L2=255/R2=0.
- `dualsense`: Sony 054c:0ce6 USB input descriptor prefix, 64-byte report; the trigger and
  button offsets differ from DS4. Cross/Triangle/R1/R2/Options/R3/PS, up-left, R2=255.
  Both Sony descriptors' output/feature sections are omitted. The numeric descriptor data
  is recorded in [hid-tools' Sony device fixtures](https://gitlab.freedesktop.org/libevdev/hid-tools/-/blob/master/hidtools/device/sony_gamepad.py).
- `switch_usb`: Nintendo 057e:2009 USB descriptor, including the physical link collection
  and vendor reports; recorded in [Chromium's descriptor fixtures](https://chromium.googlesource.com/chromium/src/+/b86102f2a243/services/device/hid/test_report_descriptors.cc).
  Its advertised report 30 layout differs from its actual wire format. The packet uses the
  packed 12-bit sticks and button bitfields documented by [Nintendo Switch Reverse Engineering](https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/bluetooth_hid_notes.md).
  The test also constructs simple report 3f (16-bit sticks, hat and digital triggers), using
  the format documented in [SDL's Switch driver](https://github.com/libsdl-org/SDL/blob/main/src/joystick/hidapi/SDL_hidapi_switch.c).
- `generic`: constructed unnumbered joystick descriptor with 12 buttons, a one-based hat,
  six signed 16-bit axes. Windows' zero report-ID byte is included in the packet. Tests
  negative minima, extrema, axis roles, and a null hat.
- `8bitdo`: constructed descriptor/report for the common Pro 2 D-input layout (2dc8:6006).
  Its button/axis bindings follow the [Windows mappings in SDL_GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB/blob/master/gamecontrollerdb.txt).
  This is a layout fixture, not a recording of that controller's full descriptor.

Additional synthetic capabilities/reports test ranges, aliases, relative axes, ignored
vendor/array data, report IDs, link collections, malformed lengths, and out-of-range usages.
`gamepad_windows.jo` exercises real no-device enumeration/registration and injects batched
Raw Input envelopes to test staging, idle input edges, removal, and stable player numbers.
Its C companion checks all consumed ABI offsets against the Windows SDK headers. The
Windows test also sends startup commands through real overlapped file I/O and injects
ACKs to check the Switch USB handshake state machine without a controller.

Still requiring hardware verification: actual USB/Bluetooth transport and hot-plug delivery,
Switch Pro's overlapped USB startup sequence and factory stick calibration. Sony Bluetooth
extended reports (DS4 11 / DualSense 31), rumble, sensors, and touchpads are unsupported.
