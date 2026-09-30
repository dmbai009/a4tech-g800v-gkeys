"""Turns the G-keys of an A4Tech X7 G800V keyboard into standalone keys.

The keyboard reports G-key state on a vendor-defined HID interface (page 0xFFA0):
    04 xx xx <b3> <b4> ...   - bitmask of currently pressed G-keys.
This script reads that report and emulates the keys from MAPPING (F13-F24 etc.),
which don't exist on regular keyboards, so games / AHK / OBS can bind them.

Run: python gkeys.py      (with console, shows a log)
     pythonw gkeys.py     (in background, no window)
"""
import ctypes
import sys
import time
from ctypes import wintypes

import hid

VID, PID = 0x09DA, 0x90C0
VENDOR_PAGE = 0xFFA0

# Bit index (0 = b3&0x01, ... 7 = b3&0x80, 8 = b4&0x01, ... 15 = b4&0x80) -> G1..G16.
BIT_NAMES = {i: f"G{i + 1}" for i in range(16)}

# name -> (virtual key, scan code). Scan codes are explicit: on non-Japanese
# layouts MapVirtualKey returns 0 for the Japanese keys.
F_SCANS = [0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x76]
VK = {f"F{n}": (0x7C + i, F_SCANS[i]) for i, n in enumerate(range(13, 25))}
VK.update(
    KANA=(0x15, 0x70), CONVERT=(0x1C, 0x79), NONCONVERT=(0x1D, 0x7B),
    # left-side modifiers: generic VK_CONTROL shows up as both Ctrls in key testers
    CTRL=(0xA2, 0x1D), SHIFT=(0xA0, 0x2A), ALT=(0xA4, 0x38),
)

# G-key -> key combination (modifiers + key). Edit to taste.
MAPPING = {
    "G1": ["F13"], "G2": ["F14"], "G3": ["F15"], "G4": ["F16"],
    "G5": ["F17"], "G6": ["F18"], "G7": ["F19"],  # there is no physical G8
    "G9": ["F20"], "G10": ["F21"], "G11": ["F22"], "G12": ["F23"],
    "G13": ["F24"],
    # only 12 F-keys exist; the rest are Japanese keys that do nothing on RU/EN layouts
    "G14": ["KANA"], "G15": ["CONVERT"], "G16": ["NONCONVERT"],
}

# --- SendInput -------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
INPUT_KEYBOARD, KEYEVENTF_KEYUP = 1, 0x2
ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):  # only needed for the correct union size
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


held = {}  # key -> how many G-keys currently hold it (modifiers can be shared)


def send_keys(names, up):
    seq = reversed(names) if up else names
    inputs = []
    for n in seq:
        # press on the first holder, release on the last one
        if up:
            held[n] = held.get(n, 0) - 1
            if held[n] > 0:
                continue
        else:
            held[n] = held.get(n, 0) + 1
            if held[n] > 1:
                continue
        vk, scan = VK[n]
        inputs.append(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(
            wVk=vk, wScan=scan, dwFlags=KEYEVENTF_KEYUP if up else 0)))
    if not inputs:
        return
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


# --- main loop -------------------------------------------------------------
def open_device():
    for d in hid.enumerate(VID, PID):
        if d["usage_page"] == VENDOR_PAGE:
            h = hid.device()
            h.open_path(d["path"])
            return h
    return None


def log(msg):
    if sys.stdout:  # None under pythonw
        print(msg, flush=True)


def apply(prev, state):
    changed = state ^ prev
    for bit in range(16):
        if not changed & (1 << bit):
            continue
        pressed = bool(state & (1 << bit))
        name = BIT_NAMES.get(bit, f"bit{bit}")
        keys = MAPPING.get(name)
        log(f"{name} {'down' if pressed else 'up'} -> {'+'.join(keys) if keys else '(unmapped)'}")
        if keys:
            send_keys(keys, up=not pressed)


def run(h):
    prev = 0
    try:
        while True:
            data = h.read(64, 1000)
            # bytes 1-2 change whenever bindings are edited in the A4Tech app - ignore them
            if not data or len(data) < 5 or data[0] != 0x04:
                continue
            state = data[3] | (data[4] << 8)
            apply(prev, state)
            prev = state
    finally:
        apply(prev, 0)  # release everything still held so nothing gets stuck


def main():
    while True:
        h = open_device()
        if not h:
            log("keyboard not found, waiting...")
            time.sleep(3)
            continue
        log("listening for G-keys. Ctrl+C to quit.")
        try:
            run(h)
        except OSError:
            log("keyboard disconnected, reconnecting...")
            time.sleep(1)
        finally:
            h.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
