import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# Let's search references to 0x41fd8c
import struct
b = struct.pack("<I", 0x41fd8c)
raw = exe.pe.get_memory_mapped_image()
p = 0
refs = []
while True:
    idx = raw.find(b, p)
    if idx == -1: break
    refs.append(0x400000 + idx)
    p = idx + 4
print("Refs to Apuesta_Gestion:", [hex(r) for r in refs])
for r in refs:
    fs, fe = exe.func_of(r)
    strs = []
    for ins, note in exe.disasm(fs, fe):
        if note and 'L"' in note: strs.append(note.strip())
    print(f"Func {fs:#x}..{fe:#x}: {strs[:4]}")
