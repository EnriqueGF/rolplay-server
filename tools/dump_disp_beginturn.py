import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for ins, note in exe.disasm(0x7ca770, 0x7ca820):
    print(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
