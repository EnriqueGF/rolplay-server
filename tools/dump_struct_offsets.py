import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x738700, 0x739000

# Look for:
# mov [ecx + edx + OFFSET], ...
# or mov [edx + ecx + OFFSET], ...
import re

for ins, note in exe.disasm(fs, fe):
    m = re.search(r'\[e[a-d]x \+ e[a-d]x \+ (0x[0-9a-f]+)\]', ins.op_str)
    if m:
        off = m.group(1)
        print(f"  {ins.address:#x}: {ins.mnemonic:4} offset {off:6} <- {ins.op_str.split(', ')[1]:20} {note}")
    elif note and any(k in note for k in ("Criatura", "Poder", "Amuleto", "StrCopy")):
        print(f"--- {note.strip()} @ {ins.address:#x} ---")
