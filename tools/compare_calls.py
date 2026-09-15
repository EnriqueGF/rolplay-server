import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()

print("=== In rcv_joingamerps (0x769260..0x7692d0) ===")
for ins, note in exe.disasm(0x769260, 0x7692d0):
    print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")

print("\n=== In SETGAMEREADY (0x733960..0x7339d0) ===")
for ins, note in exe.disasm(0x733960, 0x7339d0):
    print(f"  {ins.address:#x}: {ins.mnemonic:7} {ins.op_str:30} {note}")
