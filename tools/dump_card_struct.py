import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# Let's see what is printed/loaded in 0x738700..0x739200
for ins, note in exe.disasm(0x738700, 0x738e00):
    if note:
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
