"""Dumps raw HID reports from every readable interface of the A4Tech keyboard
(09DA:90C0). Press G-keys and watch what arrives.

Usage: python sniff.py [seconds]    (runs until Ctrl+C if no duration given)
"""
import sys
import time

import hid

VID, PID = 0x09DA, 0x90C0

devs = []
for d in hid.enumerate(VID, PID):
    # Windows opens the keyboard/mouse collections exclusively - skip them
    if (d['usage_page'], d['usage']) in ((0x1, 0x6), (0x1, 0x2)):
        continue
    h = hid.device()
    try:
        h.open_path(d['path'])
        h.set_nonblocking(True)
        name = f"page=0x{d['usage_page']:04X} usage=0x{d['usage']:02X}"
        devs.append((name, h))
        print("listening on", name)
    except OSError as e:
        print("failed to open", d['path'], e)

print("\nPress G-keys (Ctrl+C to quit)...\n")
end = time.time() + (float(sys.argv[1]) if len(sys.argv) > 1 else 1e9)
try:
    while time.time() < end:
        for name, h in devs:
            data = h.read(64)
            if data:
                print(f"{time.strftime('%H:%M:%S')}  {name}:  {' '.join(f'{b:02X}' for b in data)}")
        time.sleep(0.002)
except KeyboardInterrupt:
    pass
