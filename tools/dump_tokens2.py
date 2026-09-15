import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
for ins, note in exe.disasm(0x736d80, 0x736e00):
    print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")
