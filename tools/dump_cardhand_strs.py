import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x7365e0, 0x737500
for ins, note in exe.disasm(fs, fe):
    if note and 'L"' in note:
        print(f"  {ins.address:#x}: {note.strip()}")
