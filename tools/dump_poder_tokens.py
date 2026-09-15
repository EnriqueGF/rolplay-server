import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x736da0, 0x736ed0
for ins, note in exe.disasm(fs, fe):
    if ins.mnemonic in ("mov", "call") and ("ebp -" in ins.op_str or note):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
