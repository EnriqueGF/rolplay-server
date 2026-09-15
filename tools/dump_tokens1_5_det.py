import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x736780, 0x736a50
for ins, note in exe.disasm(fs, fe):
    print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")
