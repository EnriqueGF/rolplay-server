import sys, struct
sys.path.append("tools")
from rpexe import Exe, IB
exe = Exe()
raw = exe.pe.get_memory_mapped_image()

b = struct.pack("<I", 0x416250) # Crear_Partida
p = 0
refs = []
while True:
    idx = raw.find(b, p)
    if idx == -1:
        break
    refs.append(IB + idx)
    p = idx + 4
print("Refs to Crear_Partida:", [hex(r) for r in refs])
for r in refs:
    if 0x401000 <= r < 0x7ce000:
        fs, fe = exe.func_of(r)
        print(f"In func {fs:#x}..{fe:#x}")
