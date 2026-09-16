import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x723240)
print(f"Func 0x723240: {fs:#x} to {fe:#x}")
for ins, note in exe.disasm(fs, min(fe, fs+150)):
    if any(k in note for k in ['L"', 'Socket', 'Send', 'Winsock', 'crypt', 'enc', 'dec']) or 'call' in ins.mnemonic:
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
