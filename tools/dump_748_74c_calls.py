import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for addr, name in [(0x73af90, "Method 0x748"), (0x73b100, "Method 0x74c")]:
    fs, fe = exe.func_of(addr)
    print(f"=== {name} ===")
    for ins, note in exe.disasm(fs, fe):
        if 'L"' in note or 'call' in ins.mnemonic:
            print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
