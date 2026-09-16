import sys
sys.path.insert(0, 'tools')
from rpexe import Exe

exe = Exe()
fs, fe = 0x769070, 0x769500
for ins, note in exe.disasm(fs, fe):
    if any(k in note for k in ['L"', 'Node', 'Text', 'Item', 'Key', 'Split', 'InStr', 'Mid', 'Left']) or 'call' in ins.mnemonic:
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str:30} {note}")
