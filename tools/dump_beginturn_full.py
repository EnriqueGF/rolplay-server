import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x734890)
print(f"Func BEGINTURN (0x734890): {fs:#x} to {fe:#x}")
for ins, note in exe.disasm(fs, fe):
    if any(w in ins.mnemonic for w in ['call', 'jmp']) or 'L"' in note:
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
