import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
print("Calls in 0x73e960:")
for ins, note in exe.disasm(0x73e960, 0x73f500):
    if ins.mnemonic == "call" or "InStr" in note or "; L" in note or "ord" in note:
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
