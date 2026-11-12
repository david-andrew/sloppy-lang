/* Check the byte layouts used by Sloppy against Windows' actual SDK declarations. */
#ifdef _WIN32
#include <windows.h>
#include <hidsdi.h>
#include <stddef.h>
__declspec(dllexport) int pad_hid_abi(void) {
    return sizeof(RAWINPUTHEADER) == 24 && sizeof(RAWINPUTDEVICELIST) == 16 &&
        sizeof(RAWINPUTDEVICE) == 16 && sizeof(RID_DEVICE_INFO) == 32 &&
        offsetof(RAWINPUT, data.hid.bRawData) == 32 &&
        offsetof(RAWINPUT, data.hid.dwSizeHid) == 24 &&
        offsetof(RID_DEVICE_INFO, hid.dwVendorId) == 8 &&
        offsetof(RID_DEVICE_INFO, hid.dwProductId) == 12 &&
        offsetof(RID_DEVICE_INFO, hid.usUsagePage) == 20 &&
        offsetof(RID_DEVICE_INFO, hid.usUsage) == 22 &&
        sizeof(HIDP_CAPS) == 64 && offsetof(HIDP_CAPS, NumberInputButtonCaps) == 46 &&
        offsetof(HIDP_CAPS, NumberInputValueCaps) == 48 &&
        sizeof(HIDP_BUTTON_CAPS) == 72 && sizeof(HIDP_VALUE_CAPS) == 72 &&
        offsetof(HIDP_VALUE_CAPS, ReportID) == 2 &&
        offsetof(HIDP_VALUE_CAPS, LinkCollection) == 6 &&
        offsetof(HIDP_VALUE_CAPS, IsRange) == 12 &&
        offsetof(HIDP_VALUE_CAPS, IsAbsolute) == 15 &&
        offsetof(HIDP_VALUE_CAPS, BitSize) == 18 &&
        offsetof(HIDP_VALUE_CAPS, ReportCount) == 20 &&
        offsetof(HIDP_VALUE_CAPS, LogicalMin) == 40 &&
        offsetof(HIDP_VALUE_CAPS, LogicalMax) == 44 &&
        offsetof(HIDP_VALUE_CAPS, Range.UsageMin) == 56 &&
        offsetof(HIDP_BUTTON_CAPS, Range.UsageMin) == 56 &&
        sizeof(OVERLAPPED) == 32;
}
#else
int pad_hid_abi(void) { return 1; }
#endif
