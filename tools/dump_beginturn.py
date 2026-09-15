import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x734890)
print(f"BEGINTURN func {fs:#x}..{fe:#x}")
for ins, note in exe.disasm(fs, fe):
    if note or ins.mnemonic in ("call", "cmp", "je", "jne"):
        if "Free" in note: continue
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
