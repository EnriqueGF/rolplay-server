import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = exe.func_of(0x751770)
for ins, note in exe.disasm(fs, fe):
    if note or ins.mnemonic in ("call", "cmp", "je", "jne", "jle", "jge"):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:30} {note}")
