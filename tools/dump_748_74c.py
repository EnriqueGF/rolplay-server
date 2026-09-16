import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
for addr, name in [(0x73af90, "Method 0x748"), (0x73b100, "Method 0x74c")]:
    fs, fe = exe.func_of(addr)
    print(f"=== {name} ({fs:#x} - {fe:#x}) ===")
    for ins, note in list(exe.disasm(fs, min(fe, fs+100)))[:15]:
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
