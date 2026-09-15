import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x738680, 0x738725
for ins, note in exe.disasm(fs, fe):
    print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")
