import sys
sys.path.append("tools")
from rpexe import Exe
exe = Exe()

funcs = [0x767570, 0x7676c0, 0x7678c0, 0x767990, 0x767fb0, 0x7683d0, 0x7684d0, 0x768540, 0x769520]
for f in funcs:
    fs, fe = exe.func_of(f)
    strs = []
    for ins, note in exe.disasm(fs, fe):
        if note and 'L"' in note:
            strs.append(note.strip())
    print(f"{f:#x} (len {fe-fs}): {strs[:4]}")
