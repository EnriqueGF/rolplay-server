import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x736620, 0x737500
for ins, note in exe.disasm(fs, fe):
    if any(k in note for k in ("InStr", "Mid", "I4", "I2", "R8", "Str", "ord520", "ord632", "Poder", "Criatura", "Amuleto")):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
