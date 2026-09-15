import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
# Let's inspect the exact calls to ord632 (Mid$) or __vbaInStr in 0x736620..0x737180
# and which locals they store to (e.g. [ebp - ...])
for ins, note in exe.disasm(0x736780, 0x7371a0):
    if ins.mnemonic in ("call", "cmp", "test") or "L\"" in note:
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
