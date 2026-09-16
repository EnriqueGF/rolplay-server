import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
# In Torneo, methods from 0x334 to 0x424 are control accessors.
# Let's see what control is at 0x3a0 and 0x384
for va in [0x734ca9, 0x734cf5]:
    for ins, note in list(exe.disasm(va, va+35))[:6]:
        print(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
