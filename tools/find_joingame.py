import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for ins, note in exe.disasm(0x401000, 0x7eb000):
    if note and '#JOINGAME' in note:
        print(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
