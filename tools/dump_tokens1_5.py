import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# Let's see what is extracted into locals before 0x736d80
for ins, note in exe.disasm(0x736780, 0x736d80):
    if "mov dword ptr [ebp" in ins.op_str and any(ins.op_str.endswith(f", {n}") for n in range(1, 10)):
        print(f"  {ins.address:#x}: {ins.op_str}")
    elif note and any(k in note for k in ("InStr", "Mid", "ord", "StrMove", "Poder", "Criatura")):
        print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:25} {note}")
