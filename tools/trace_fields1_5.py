import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x736620, 0x736d80

# Print all instructions in this range that do Mid$, InStr, or StrMove
cur_step = 0
for ins, note in exe.disasm(fs, fe):
    if "InStr" in note:
        cur_step += 1
        print(f"\n--- Split step {cur_step} @ {ins.address:#x} ---")
    elif note or ins.mnemonic in ("mov", "lea", "push") and "ebp -" in ins.op_str:
        if any(k in ins.op_str for k in ("0x24", "0x28", "0x2c", "0x30", "0x34", "0x38", "0x3c", "0x40", "0x44", "0x48", "0x50", "0x60", "0x70", "0x80", "0x90", "0xa0", "0xb0")):
            print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
