import sys
sys.path.append("tools")
from rpexe import Exe

exe = Exe()
fs, fe = 0x738790, 0x738b50
for ins, note in exe.disasm(fs, fe):
    if ins.mnemonic in ("mov", "call") and ("word ptr [" in ins.op_str or "dword ptr [" in ins.op_str or "StrCopy" in note):
        print(f"  {ins.address:#x}: {ins.mnemonic:6} {ins.op_str:35} {note}")
