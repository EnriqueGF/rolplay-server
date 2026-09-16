import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for addr in [0x729090, 0x729670, 0x732640]:
    fs, fe = exe.func_of(addr)
    print(f"=== Function at {addr:#x} ({fs:#x} - {fe:#x}) ===")
    for ins, note in exe.disasm(fs, fe):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:35} {note}")
