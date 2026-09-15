import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()

# In 0x736d80..0x737200, let's see which token index is passed to 0x721fe0:
# usually push <token_index>; push <string_var>; call 0x721fe0
for ins, note in exe.disasm(0x736d80, 0x737200):
    if ins.mnemonic == "push" and ins.op_str in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17"):
        print(f"  {ins.address:#x}: push token index {ins.op_str}")
    elif "Poder" in note or "Criatura" in note or "Amuleto" in note:
        print(f"--- {note.strip()} ---")
