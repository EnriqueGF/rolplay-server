import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# In dump_apuesta.py:
# 0x729090..0x729280
# 0x729670..0x729760
# 0x732640..0x732730
for fs in (0x729090, 0x729670, 0x732640):
    fe = exe.func_of(fs)[1]
    print(f"\n=== Func {fs:#x}..{fe:#x} ===")
    for ins, note in exe.disasm(fs, fe):
        if note:
            print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
