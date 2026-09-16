import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for ins, note in exe.disasm(0x734d60, 0x734dc5):
    print(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
