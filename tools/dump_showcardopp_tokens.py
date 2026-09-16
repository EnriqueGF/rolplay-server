import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
print("Token extraction in 0x73e960:")
for ins, note in exe.disasm(0x73ea00, 0x73f200):
    if any(k in note for k in ("InStr", "Mid", "I4", "I2", "R8", "StrVarVal", "ord632", "ord520")):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
