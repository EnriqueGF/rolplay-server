from rpexe import Exe, IB
import struct
import re

exe = Exe()
raw = exe.pe.get_memory_mapped_image()

needle = "#".encode("utf-16le")
pos = 0
found = []
while True:
    idx = raw.find(needle, pos)
    if idx == -1:
        break
    va = IB + idx
    s = exe.bstr(va)
    if len(s) > 3 and s.startswith("#") and re.match(r"^#[A-Z0-9_ ]+$", s):
        va_bytes = struct.pack("<I", va)
        refs = []
        rpos = 0
        while True:
            ridx = raw.find(va_bytes, rpos)
            if ridx == -1:
                break
            refs.append(IB + ridx)
            rpos = ridx + 4
        found.append((va, s.strip(), refs))
    pos = idx + 2

print(f"Total # strings found: {len(found)}")
for va, s, refs in sorted(found, key=lambda x: x[1]):
    ref_strs = ", ".join(f"{r:#x}" for r in refs[:4])
    print(f"{s:25}: string@{va:#x}, refs: [{ref_strs}]")
