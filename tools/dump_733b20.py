import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
fs, fe = 0x733b20, 0x733d70
for ins, note in exe.disasm(fs, fe):
    print(f"{ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
