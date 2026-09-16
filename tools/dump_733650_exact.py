import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for ins, note in exe.disasm(0x733650, 0x7339cb):
    print(f"{ins.address:#x}: {ins.bytes.hex(' '):24} {ins.mnemonic:8} {ins.op_str:30} {note}")
